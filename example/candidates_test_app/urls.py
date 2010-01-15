from django.conf.urls.defaults import *

urlpatterns = patterns(
    'candidates_test_app.views',

    url(regex='^application/$',
        view='EditApplication',
        name='edit-application'),
)
