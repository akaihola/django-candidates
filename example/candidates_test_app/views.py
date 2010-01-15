from datetime import date, timedelta

from candidates.views import MetaBase, EditApplicationBase

from candidates_test_app.models import Application
from candidates_test_app.forms import ApplicationForm

class ApplicationMeta(MetaBase):
    @staticmethod
    def get_deadline():
        return date.today() + timedelta(2)

    @staticmethod
    def current_round_name():
        return unicode(ApplicationMeta.get_deadline().year)

    model = Application

class EditApplication(EditApplicationBase):
    meta = ApplicationMeta
    template_name = 'candidates_test_app/application_form.html'

    @classmethod
    def create_application_form(cls, data, instance, prefix):
        """Create an application form

        Create the application form for non-repeating information
        about the candidate.
        """
        return ApplicationForm(data, instance=instance, prefix=prefix)
