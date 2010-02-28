from django.test import TestCase, Client
from django.core.handlers.wsgi import WSGIRequest
from django.core.handlers.base import BaseHandler
from nose.tools import ok_, eq_

from candidates_test_app.views import EditApplication
from candidates_test_app.models import Application


class RequestFactory(Client):
    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        request = WSGIRequest(environ)
        handler = BaseHandler()
        handler.load_middleware()
        for middleware_method in handler._request_middleware:
            if middleware_method(request):
                raise Exception("Couldn't create request mock object - "
                                "request middleware returned a response")
        return request

rf = RequestFactory()


class ValidateApplicationFormsTests(TestCase):

    def test_form_classes(self):
        response = EditApplication(rf.post('/', {}), _render=False)
        forms = response._context['forms']
        eq_([f.__class__.__name__ for f in forms],
            ['UserForm', 'ApplicationForm'])

    def test_empty_user_form_is_invalid(self):
        data = {'user-email': '', 'user-first_name': '', 'user-last_name': ''}
        response = EditApplication(rf.post('/', data), _render=False)
        user_form = response._context['forms'][0]
        ok_(not user_form.is_valid())

    def test_filled_user_form_is_valid(self):
        data = {'user-email': 'edwin@moses.com',
                'user-first_name': 'Edwin',
                'user-last_name': 'Moses'}
        response = EditApplication(rf.post('/', data), _render=False)
        user_form = response._context['forms'][0]
        ok_(user_form.is_valid())

    def test_empty_application_form_is_invalid(self):
        data = {'application-cv': '',
                'application-experience_years': ''}
        response = EditApplication(rf.post('/', data), _render=False)
        application_form = response._context['forms'][1]
        ok_(not application_form.is_valid())

    def test_filled_application_form_is_valid(self):
        data = {'application-cv': "I'm good",
                'application-experience_years': '5'}
        response = EditApplication(rf.post('/', data), _render=False)
        application_form = response._context['forms'][1]
        eq_(application_form.errors, {})
        ok_(application_form.is_valid())


class SaveApplicationTests(TestCase):

    def test_user_form_save(self):
        data = {'user-email': 'edwin@moses.com',
                'user-first_name': 'Edwin',
                'user-last_name': 'Moses'}
        response = EditApplication(rf.post('/', data), _render=False)
        user_form = response._context['forms'][0]
        ok_(user_form.is_valid())

    def test_save_application(self):
        data = {'user-email': 'edwin@moses.com',
                'user-first_name': 'Edwin',
                'user-last_name': 'Moses',
                'application-cv': "I'm good",
                'application-experience_years': '5'}
        response = EditApplication(rf.post('/', data), _render=False)
        eq_(response.status_code, 200)
        eq_(Application.objects.count(), 1)
        appl = Application.objects.get(pk=1)
        eq_(appl.confirmed, False)
        eq_(appl.round_name, u'2010')
        eq_(appl.cv, u"I'm good")
        eq_(appl.experience_years, 5)
        eq_(appl.send_confirmation_email, False)
        eq_(appl.user.username, u'edwinmoses2010')
        eq_(appl.user.last_name, u'Moses')
        eq_(appl.user.first_name, u'Edwin')
