from django.test import TestCase
from django.conf import settings

from candidates.views import MetaBase, EditApplicationBase
from candidates.tests.models import TestModel

saved_settings = {}


class OverrideSettingsTestCase(TestCase):
    def setUp(self):
        saved_settings['INSTALLED_APPS'] = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = 'candidates.tests',

    def tearDown(self):
        settings.INSTALLED_APPS = saved_settings['INSTALLED_APPS']


class MetaBaseTests(OverrideSettingsTestCase):
    def test_01_abstract_meta(self):
        self.assertRaises(NotImplementedError,
                          MetaBase.get_deadline)
        self.assertRaises(NotImplementedError,
                          MetaBase.get_view_permission)


class MetaSubclassTests(OverrideSettingsTestCase):
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


class EditApplicationBaseTests(OverrideSettingsTestCase):
    def test_01_abstract_meta(self):
        self.assertRaises(NotImplementedError,
                          EditApplicationBase.meta.get_deadline)
        self.assertRaises(NotImplementedError,
                          EditApplicationBase.meta.get_view_permission)
