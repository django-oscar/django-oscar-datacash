from django.views import generic
from django import http

from datacash import models


class CallbackView(generic.View):
    """
    Datacash will POST to this view when they have a fraud score
    for a transaction.  This view must respond with a simple string
    response within 1 second for it to be acknowledged.
    """

    def post(self, request, *args, **kwargs):
        try:
            # Create a fraud response object.  Other processes should listen
            # to the post create signal in order to hook fraud processing into
            # this order pipeline.
            models.FraudResponse.create_from_xml(request.body)
        except Exception, e:
            return http.HttpResponseServerError("error")
        else:
            return http.HttpResponse("ok")
