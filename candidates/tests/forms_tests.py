from nose.tools import eq_, ok_
from django.test import TestCase

from django.contrib.auth.models import User
from candidates_test_app.models import Application

from candidates.forms import user_exists

class UserExistsTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create(
            last_name='Candidate', first_name='Candy', email='candy@cool.net')
        self.appl = Application.objects.create(
            user=self.user, round_name='2010', cv='cv', experience_years=2)

    def test_exists(self):
        ok_(user_exists('candy@cool.net', 'Candidate', 'Candy', '2010'))

    def test_email_mismatch(self):
        eq_(user_exists('candy2@cool.net', 'Candidate', 'Candy', '2010'), False)
