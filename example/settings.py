DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = ':memory:'
DATABASE_SUPPORTS_TRANSACTIONS = False

INSTALLED_APPS = ('candidates',
                  'django_nose',)
TEST_RUNNER = 'django_nose.run_tests'
