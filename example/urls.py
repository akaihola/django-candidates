from django.conf.urls.defaults import *

urlpatterns = patterns(
    '',

    url(regex='^',
        view=include('candidates_test_app.urls')),
)
