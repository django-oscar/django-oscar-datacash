from django.conf.urls.defaults import *
from django.views.decorators.csrf import csrf_exempt

from .the3rdman import views


# Responses from the3rdman are posted back
urlpatterns = patterns('',
    url(r'^the3rdman/', csrf_exempt(views.CallbackView.as_view()),
        name='datacash-3rdman-callback'),
)
