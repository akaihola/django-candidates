from django import forms
from candidates.forms import autostrip
from example.candidates_test_app.models import Application

class BaseApplicationForm(forms.ModelForm):
    class Meta:
        model = Application

class ApplicationForm(BaseApplicationForm):
    pass

ApplicationForm = autostrip(ApplicationForm)
