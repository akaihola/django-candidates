# -*- coding: utf-8 -*-

import logging
from random import seed, choice
from datetime import datetime

from django.db import transaction
from django.http import HttpResponseRedirect
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils.cache import add_never_cache_headers
from django.contrib.auth import login, logout, authenticate
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.utils.datastructures import SortedDict

from classyviews import ClassyView

from candidates.forms import UserForm
from candidates.utils.users import generate_username

from pytz import timezone


class MetaBase:
    application_form_view_name = 'application-form'
    edit_application_view_name = 'edit-application'
    login_view_name = 'login'
    prefilled_login_view_name = 'applicant-login'

    @classmethod
    def current_round_name(cls):
        raise NotImplementedError(
            '%s must define the current_round_name() method' % cls.__name__)

    @staticmethod
    def get_deadline():
        raise NotImplementedError(
            'Define the get_deadline static method in the overridden meta '
            'class of views inherited from django-candidates')

    @classmethod
    def get_view_permission(cls):
        try:
            return cls.view_permission
        except AttributeError:
            pass
        try:
            return 'view_%s' % cls.model._meta.module_name
        except AttributeError:
            pass
        raise NotImplementedError(
            'Define either the model attribute, the get_view_permission class '
            'method or the view_permission string attribute in the overridden '
            'meta class of views inherited from django-candidates')


class ApplicationViewBase(ClassyView):
    meta = MetaBase

    def __init__(self, *args, **kwargs):
        super(ApplicationViewBase, self).__init__(*args, **kwargs)
        add_never_cache_headers(self)


class EditApplicationBase(ApplicationViewBase):
    """Base class for the edit application view

    Subclasses must define the following attributes:

    * :attr:`confirmation_request_template_name`: the template used
      for the confirmation request e-mail

    * :attr:`confirmation_request_subject`: the subject of the
      confirmation request e-mail

    * :attr:`meta`: the class for additional meta information (see
      :class:`MetaBase`)
    """
    template_name = 'candidates/application_form.html'
    confirmation_request_template_name = (
        'candidates/confirmation_request_email.txt')
    confirmation_request_subject = 'Please confirm your application'
    timezone = "US/Hawaii"

    @classmethod
    def GET(cls, request, username=''):
        return cls.handle_request(request,
                                  None, None, username)

    @classmethod
    @transaction.commit_on_success
    def POST(cls, request, username=''):
        return cls.handle_request(request,
                                  request.POST, request.FILES, username)

    @classmethod
    def handle_request(cls, request, data, files, username):
        """Handle HTTP requests for creating and editing applications

        Handle both GET and POST requests to the public and private
        interfaces.

        Return value can be:
        * the context dictionary to be used when rendering the
          template
        * a :class:`HttpResponseRedirect` object

        For the deadline, check against the US/Hawaii timezone by default since that's
        probably the westernmost timezone with applicants. This can be changed by
        overriding the `EditApplicationBase.timezone` class attribute in a child class.

        Public interface
        ================

        * Can't redirect due to embedding
        * Anonymous users, logged in users and the secretary always see a blank
          form
        * When a valid form is saved:
          * secretary sees a link to editing the new application through the
            private interface
          * anonymous and other users are logged in as the user of the new
            application

        Private interface
        =================

        * Only accessible to the secretary
        * Only for modifying existing applications
        """
        if data and 'clear' in data:
            logout(request)
            data = None
            files = None
            username = ''

        public_interface = username == ''
        secretary = request.user.has_perm('%s.%s' % (
                cls.meta.model._meta.app_label,
                cls.meta.model._meta.get_change_permission()))

        if not secretary:
            if not public_interface:
                return cls.redirect_to_login('')
            today = datetime.now(tz=timezone(cls.timezone)).date()
            if today > cls.meta.get_deadline():
                return {'past_deadline': True}

        user = None
        app = None

        if public_interface:
            if not secretary and request.user.is_authenticated():
                # Logged in user using the public interface: editing an
                # existing application
                user = request.user
            # Else the secretary or an anonymous user is using the public
            # interface to create a new application
        else:
            # Secretary is using the private interface to edit an existing
            # application
            user = User.objects.get(username=username)

        saved = False
        if user:
            try:
                app = cls.meta.model.objects.get(
                    user=user,
                    round_name=cls.meta.current_round_name())
                saved = True
            except cls.meta.model.DoesNotExist:
                logout(request)
                user = None

        if app is None:
            app = cls.meta.model()
            if user is not None:
                app.user = user

        forms = cls.create_forms(data, files, user, app)

        def all_valid_recursive(form_seq):
            """Validate forms in a nested list structure"""
            valid = True
            for item in form_seq:
                if callable(getattr(item, 'is_valid', None)):
                    if not item.is_valid():
                        valid = False
                elif not all_valid_recursive(item):
                    valid = False
            return valid

        all_forms_valid = all_valid_recursive(forms.values())
        if all_forms_valid:
            # The application is valid and should be saved.
            user = forms['user_form'].save(commit=False)
            other_forms = dict((k, v) for k, v in forms.items()
                               if k != 'user_form')
            username, application = cls.save(
                user, is_secretary=secretary, **other_forms)
            saved = True
            if application.send_confirmation_email:
                user, password = cls.assign_password(username)
                cls.send_confirmation_email(request, application, password)
                user = authenticate(username=username, password=password)
            else:
                user.backend = settings.AUTHENTICATION_BACKENDS[0]
            if secretary:
                # If the secretary saved a new valid application, show a link
                # for editing it in the private interface. We can't do a HTTP
                # redirect since the public interface is embedded on a CMS
                # page.
                return {'link_to_private': reverse(
                    cls.meta.edit_application_view_name,
                    kwargs={'username': username})}
            else:
                # A visitor saved a valid application. Log in as the user of
                # the application.
                login(request, user)
            forms = cls.create_forms(None, None, user, app)
        should_confirm = False
        if user:
            app = user.applications.get(
                round_name=cls.meta.current_round_name())
            should_confirm = \
                not app.send_confirmation_email and not app.confirmed
        return dict(
            forms=forms.values(),
            saved=saved,
            has_errors=data is not None and not all_forms_valid,
            should_confirm=should_confirm,
            deadline=cls.meta.get_deadline(),
            **forms)

    @classmethod
    def create_forms(cls, data, files, user, appl):
        """
        ``user``: an existing user (not secretary) or None
        ``appl``: an application instance, saved or new

        Inherited classes can extend this list of forms.  The first
        two items must always be the user form and the application
        form.

        Example:
        forms = super(InheritedClassName, cls).create_forms()
        forms.extend(...)
        return forms
        """
        forms = SortedDict()
        forms['user_form'] = cls.create_user_form(
            data, instance=user, prefix='user')
        forms['application_form'] = cls.create_application_form(
            data, instance=appl, prefix='application')
        forms.update(cls.create_extra_forms(data, files, user, appl))
        return forms

    @classmethod
    def create_user_form(cls, data, instance, prefix):
        return UserForm(data=data, instance=instance, prefix=prefix,
                        current_round_name=cls.meta.current_round_name())

    @classmethod
    def create_application_form(cls, data, instance, prefix):
        """Create an application form

        Subclasses must override this class method to create their
        project-specific application form.
        """
        raise NotImplementedError(
            '%s must implement the create_application_form class method' %
            cls.__name__)

    @classmethod
    def create_extra_forms(cls, data, files, user, appl):
        """Create any extra forms for the application

        Subclasses may override this class method to create extra
        forms related to the application, e.g. attachments or other
        repeated forms.
        """
        return SortedDict()

    @classmethod
    def save(cls, user, is_secretary=None, **forms):
        user = cls.save_user(user)
        application = cls.save_application(
            forms['application_form'], user, is_secretary)
        other_forms = dict((k, v) for k, v in forms.items()
                           if k != 'application_form')
        cls.save_extra_forms(user, application, **other_forms)
        return user.username, application

    @classmethod
    def save_user(cls, user):
        if not user.pk:
            # This is a new application, user will be saved for the first time.
            user.date_joined = datetime.now()
            user.is_active = True
            user.username = generate_username(
                user.first_name, user.last_name,
                cls.meta.current_round_name())
            n = 2
            while User.objects.filter(username=user.username):
                user.username = generate_username(
                    user.first_name, user.last_name,
                    cls.meta.current_round_name(), n)
                n += 1
        user.last_login = datetime.now()
        pk = user.pk
        user.save()
        logging.debug('Saved user %r as %r', pk, user.pk)
        return user

    @classmethod
    def save_application(cls,
                         application_form, user, is_secretary, commit=True):
        application = application_form.save(commit=False)
        application.user = user
        application.round_name = cls.meta.current_round_name()
        if is_secretary:
            application.confirmed = True
            application.send_confirmation_email = False
        pk = application.pk
        if commit:
            application.save()
            logging.debug('Saved application %r as %r', pk, application.pk)
            return cls.meta.model.objects.get(pk=application.pk)
        else:
            return application

    @classmethod
    def save_extra_forms(cls, user, application):
        """Save extra forms besides the user and application forms

        Override this method to save extra forms belonging to the
        application.  The :meth:`save` method calls this method after
        saving the user and application forms.
        """
        pass

    @staticmethod
    def assign_password(username):
        common = '23456789abcdefghijkmnpqrstuvwxyz'
        rare = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
        alphabet = 3 * common + rare
        seed()
        password = ''.join(choice(alphabet) for x in range(8))
        logging.debug(
            '********** setting password for %r to %r', username, password)
        user = User.objects.get(username=username)
        user.set_password(password)
        pk = user.pk
        user.save()
        logging.debug('Saved user %r as %r', pk, user.pk)
        logging.debug('---------> %r', user.password)
        return User.objects.get(pk=user.pk), password

    @classmethod
    def send_confirmation_email(cls, request, application, password):
        body = render_to_string(
            cls.confirmation_request_template_name,
            {'application': application,
             'password': password,
             'deadline': cls.meta.get_deadline(),
             'request': request,
             'settings': settings})
        send_mail(cls.confirmation_request_subject,
                  body,
                  settings.APPLICATION_EMAIL_SENDER,
                  [application.user.email],
                  fail_silently=False)
        application.send_confirmation_email = False
        return application.save()

    @classmethod
    def redirect_to_login(cls, username):
        url = reverse(cls.meta.prefilled_login_view_name,
                      kwargs={'username': username})
        return HttpResponseRedirect(url)


class ConfirmApplicationBase(ApplicationViewBase):
    template_name = 'candidates/confirm_application.html'

    def __init__(self, *args, **kwargs):
        super(ConfirmApplicationBase, self).__init__(*args, **kwargs)
        add_never_cache_headers(self)

    def GET(self, request, application_id, confirmation_code):
        application = get_object_or_404(self.meta.model, pk=application_id)
        if confirmation_code == application.confirmation_code:
            application.confirmed = True
            application.save()
        return HttpResponseRedirect(
            reverse('application-confirmation-result',
                    kwargs={'application_id': application.pk}))


class ApplicationListBase(ApplicationViewBase):
    template_name = 'candidates/application_list.html'

    def __init__(self, *args, **kwargs):
        super(ApplicationListBase, self).__init__(*args, **kwargs)
        add_never_cache_headers(self)


class LoginBase(ClassyView):
    template_name = 'candidates/login.html'

    def GET(self, request, username=''):
        form = AuthenticationForm(request, initial={'username': username})
        return self.display_form(request, form, username)

    def POST(self, request, username=None):
        # ``username=None`` here temporarily because people might have the old
        # login form in cache.  The old version POSTed to the
        # ``login-applicant`` view which includes the username in the URL.
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            return self.login(request, form.get_user())
        return self.display_form(request, form, request.POST['username'])

    @classmethod
    def login(cls, request, user):
        """
        Log in a user whose password has been checked.  Redirect to the
        application list, if the user has permission (secretary, board members
        and the superuser).  If an applicant has an unconfirmed application,
        confirm it show a confirmation page.  If an applicant already has a
        confirmed application, just show the filled in form.
        """
        login(request, user)
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()

        if user.has_perm('%s.%s' % (
                        cls.meta.model._meta.app_label,
                        cls.meta.get_view_permission())):
            # secretary and board members go to the application list
            return HttpResponseRedirect(reverse(
                    'application-list', kwargs={
                        'round': cls.meta.current_round_name()}))

        # Confirm application and show it.  Username not in URL,
        # logged in.
        redirect_to = reverse(cls.meta.application_form_view_name)
        try:
            app = user.applications.get(
                round_name=cls.meta.current_round_name())
            if not app.confirmed:
                app.confirmed = True
                app.save()
                redirect_to = reverse(
                    'application-confirmation-result',
                    kwargs={'application_id': app.pk})
        except cls.meta.model.DoesNotExist:
            # no application is found, show an empty application form
            pass
        return HttpResponseRedirect(redirect_to)

    @classmethod
    def display_form(cls, request, form, username):
        request.session.set_test_cookie()
        return {'form': form,
                'username': username,
                'login_url': reverse(cls.meta.login_view_name)}


class ApplicationConfirmationResultBase(ClassyView):
    confirmed_template_name = 'candidates/confirmed.html'
    invalid_code_template_name = 'candidates/invalid_confirmation_code.html'

    def GET(self, request, application_id):
        application = get_object_or_404(self.meta.model, pk=application_id)
        username = application.user.username
        context = dict(
            deadline=self.meta.get_deadline(),
            username=username)
        if application.confirmed:
            self.template_name = self.confirmed_template_name
            context['form'] = AuthenticationForm(
                request, initial={'username': username})
        else:
            self.template_name = 'candidates/invalid_confirmation_code.html'
        return context
