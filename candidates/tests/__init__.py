from django.test import TestCase
from django.conf import settings

from candidates.views import MetaBase, EditApplicationBase
from candidates.tests.models import TestModel

saved_settings = {}

def setUp():
    saved_settings['INSTALLED_APPS'] = settings.INSTALLED_APPS
    settings.INSTALLED_APPS = 'candidates.tests',

def tearDown():
    settings.INSTALLED_APPS = saved_settings['INSTALLED_APPS']

class MetaBaseTests(TestCase):
    def test_01_abstract_meta(self):
        self.assertRaises(NotImplementedError,
                          MetaBase.get_deadline)
        self.assertRaises(NotImplementedError,
                          MetaBase.get_view_permission)

class MetaSubclassTests(TestCase):
    def test_01_default_view_permission(self):
        class meta(MetaBase):
            model = TestModel
        self.assertEqual(meta.model._meta.module_name, 'testmodel')
        self.assertEqual(meta.get_view_permission(),
                         'view_testmodel')

    def test_02_view_permission_attribute(self):
        class meta(MetaBase):
            model = TestModel
            view_permission = 'custom_permission'
        self.assertEqual(meta.get_view_permission(),
                         'custom_permission')

    def test_03_get_view_permission(self):
        class meta(MetaBase):
            @classmethod
            def get_view_permission(cls):
                return 'view_mymodel'
        self.assertEqual(meta.get_view_permission(),
                         'view_mymodel')

class EditApplicationBaseTests(TestCase):
    def test_01_abstract_meta(self):
        self.assertRaises(NotImplementedError,
                          EditApplicationBase.meta.get_deadline)
        self.assertRaises(NotImplementedError,
                          EditApplicationBase.meta.get_view_permission)
