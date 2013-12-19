from django.conf.urls import *

from datacash.dashboard.app import application


urlpatterns = patterns('',
    # Include dashboard URLs
    (r'^dashboard/datacash/', include(application.urls)),
    (r'^datacash/', include('datacash.urls')),
)
