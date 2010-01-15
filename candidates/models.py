try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1
from base64 import b32encode

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

class ApplicationBase(models.Model):
    user = models.ForeignKey(
        User,
        related_name='applications',
        editable=False)
    round_name = models.CharField(
        _('season'),
        max_length=20,
        editable=False,
        help_text=_('Year of first possible month of stay'))
    send_confirmation_email = models.BooleanField(
        _('Send confirmation e-mail'),
        default=True,
        editable=False)
    confirmed = models.BooleanField(
        _('Confirmed'),
        default=False,
        editable=False)
    date_created = models.DateTimeField(
        _('When created'),
        auto_now_add=True,
        editable=False)
    date_updated = models.DateTimeField(
        _('Last update'),
        auto_now=True,
        editable=False)

    def _get_confirmation_code(self):
        """
        The code is part of a one-time one-click confirmation URL sent in an
        e-mail after the application is first saved.  The application can also
        be confirmed just by logging in with the username and password included
        in the e-mail.
        """
        plaintext = '%d%s%s' % (self.pk, self.user.email, settings.SECRET_KEY)
        return b32encode(sha1(plaintext).digest())[:12]
    confirmation_code = property(_get_confirmation_code)

    def username(self):
        return u'%s, %s' % (self.user.last_name, self.user.first_name)

    def email(self):
        return self.user.email

    class Meta:
        abstract = True
        verbose_name = _('application')
        verbose_name_plural = _('applications')
        unique_together = ('user', 'round_name'),
        permissions = ('view_application', 'Can view application'),
