from os.path import join, dirname
PROJECT_ROOT = dirname(__file__)

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = join(PROJECT_ROOT, 'example.sqlite')
DATABASE_SUPPORTS_TRANSACTIONS = False

ROOT_URLCONF = 'example.urls'

DEBUG = True
TEMPLATE_DEBUG = True

INSTALLED_APPS = ('django.contrib.auth',
                  'django.contrib.contenttypes',
                  'django.contrib.sessions',
                  'django_nose',
                  'candidates',
                  'candidates_test_app',)
TEST_RUNNER = 'django_nose.run_tests'
