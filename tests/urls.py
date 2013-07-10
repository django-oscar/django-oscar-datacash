from django.conf.urls.defaults import *

from datacash.dashboard.app import application


urlpatterns = patterns('',
    # Include dashboard URLs
    (r'^dashboard/datacash/', include(application.urls)),
    (r'^datacash/', include('datacash.urls')),
)
