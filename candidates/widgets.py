from django import forms
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

class ViewTextarea(forms.Widget):
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        value = force_unicode(value)
        return mark_safe(u'<span class="textarea">%s</span>' %
                         conditional_escape(force_unicode(value)))
