# -*- coding: utf-8 -*-

import logging
from random import seed, choice
from datetime import date, datetime

from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.utils.cache import add_never_cache_headers
from django.contrib.auth import login, logout, authenticate
from django.forms.formsets import all_valid
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from classyviews import ClassyView

from candidates.forms import UserForm
from candidates.utils.users import generate_username

class MetaBase:
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
        try: return cls.view_permission
        except AttributeError: pass
        try: return 'view_%s' % cls.model._meta.module_name
        except AttributeError: pass
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

    @classmethod
    def GET(self, request, username=''):
        return self.handle_request(request,
                                   None, None, username)

    @classmethod
    @transaction.commit_on_success
    def POST(self, request, username=''):
        return self.handle_request(request,
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
            elif date.today() > cls.meta.get_deadline():
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

        if app is None:
            app = cls.meta.model()
            if user is not None:
                app.user = user

        forms = cls.create_forms(data, files, user, app)
        all_forms_valid = all_valid(forms)
        if all_forms_valid:
            # The application is valid and should be saved.
            user = forms[0].save(commit=False)
            username, application = cls.save(
                user, *forms[1:], **{'is_secretary': secretary})
            saved = True
            if application.send_confirmation_email:
                user, password = cls.assign_password(username)
                cls.send_confirmation_email(application, password)
                user = authenticate(username=username, password=password)
            else:
                user.backend = settings.AUTHENTICATION_BACKENDS[0]
            if secretary:
                # If the secretary saved a new valid application, show a link
                # for editing it in the private interface. We can't do a HTTP
                # redirect since the public interface is embedded on a CMS
                # page.
                return {'link_to_private': reverse(
                        'edit-application', kwargs={'username': username})}
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
            forms=forms,
            user_form=forms[0],
            application_form=forms[1],
            saved=saved,
            has_errors=data is not None and not all_forms_valid,
            should_confirm=should_confirm,
            deadline=cls.meta.get_deadline())

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
        forms = [
            cls.create_user_form(
                data, instance=user, prefix='user'),
            cls.create_application_form(
                data, instance=appl, prefix='application')]
        forms.extend(cls.create_extra_forms(data, files, user, appl))
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
        return []

    @classmethod
    def save(cls, user, application_form, *extra_forms, **kwargs):
        user = cls.save_user(user)
        application = cls.save_application(
            application_form, user, kwargs.pop('is_secretary'))
        cls.save_extra_forms(user, application, *extra_forms)
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
        logging.debug('Saved user %r as %r' % (pk, user.pk))
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
            logging.debug('Saved application %r as %r' % (pk, application.pk))
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
            '********** setting password for %r to %r' % (username, password))
        user = User.objects.get(username=username)
        user.set_password(password)
        pk = user.pk
        user.save()
        logging.debug('Saved user %r as %r' % (pk, user.pk))
        logging.debug('---------> %r' % user.password)
        return User.objects.get(pk=user.pk), password

    @classmethod
    def send_confirmation_email(cls, application, password):
        body = render_to_string(
            cls.confirmation_request_template_name,
            {'application': application,
             'password': password,
             'deadline': cls.meta.get_deadline()})
        send_mail(cls.confirmation_request_subject,
                  body,
                  settings.APPLICATION_EMAIL_SENDER,
                  [application.user.email],
                  fail_silently=False)
        application.send_confirmation_email = False
        return application.save()

class ConfirmApplicationBase(ApplicationViewBase):
    template_name = 'candidates/confirm_application.html'

    def __init__(self, *args, **kwargs):
        super(ConfirmApplicationBase, self).__init__(*args, **kwargs)
        add_never_cache_headers(self)

class ApplicationListBase(ApplicationViewBase):
    template_name = 'candidates/application_list.html'

    def __init__(self, *args, **kwargs):
        super(ApplicationListBase, self).__init__(*args, **kwargs)
        add_never_cache_headers(self)
