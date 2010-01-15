from django import forms
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User

from candidates.widgets import ViewTextarea

def autostrip(cls):
    """
    Decorate form class to strip leading/trailing whitespace

    From http://www.djangosnippets.org/snippets/956/

    Here is a class decorator that allows not to bother with stripping leading
    and trailing white space from user input provided via forms. This could be
    a temporary solution for an issue addressed in the ticket #6362.
    """
    fields = [(key, value) for key, value in cls.base_fields.iteritems()
              if isinstance(value, forms.CharField)]
    for field_name, field_object in fields:
        def get_clean_func(original_clean):
            return lambda value: original_clean(value and value.strip())
        clean_func = get_clean_func(getattr(field_object, 'clean'))
        setattr(field_object, 'clean', clean_func)
    return cls

def user_exists(email, last_name, first_name, current_round_name):
    # @@@ TODO: applications relation still hard coded here
    return User.objects.filter(
        first_name__iexact=first_name,
        last_name__iexact=last_name,
        email__iexact=email,
        applications__round_name__exact=current_round_name).count()

class BaseUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = 'last_name', 'first_name', 'email',

class ViewUserForm(BaseUserForm):
    def __init__(self, *args, **kwargs):
        super(ViewUserForm, self).__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget = ViewTextarea()

class UserForm(BaseUserForm):
    last_name = forms.CharField(required=True, label=_('last name'))
    first_name = forms.CharField(required=True, label=_('first name'))
    email = forms.EmailField(required=True, label=_('e-mail address'))

    def __init__(self, current_round_name=None, **kwargs):
        """Create a user details model form

        UserForm needs to receive the :func:`get_current_round_name`
        function as an argument to be able to validate that the user
        details don't already exist for the current round.
        """
        super(UserForm, self).__init__(**kwargs)
        if current_round_name is None:
            raise ValueError('The current round name must be passed '
                             'to UserForm() as an argument')
        self.current_round_name = current_round_name

    def clean(self):
        """Validate that candidate doesn't already exist

        If a new user is being created, check that a candidate with an
        identical name and e-mail address hasn't already been
        registered on this round.
        """
        c = self.cleaned_data
        if (self.instance.pk is None and
            c.get('email') and
            user_exists(c.get('email'),
                        c.get('last_name'),
                        c.get('first_name'),
                        self.current_round_name)):
            raise forms.ValidationError(
                ugettext('APPLICATION_EXISTS PLEASE_LOGIN'))
        return c
UserForm = autostrip(UserForm)
