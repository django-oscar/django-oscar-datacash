import logging

from django.views import generic
from django import http

from datacash import models

logger = logging.getLogger('datacash.the3rdman')


class CallbackView(generic.View):
    """
    Datacash will POST to this view when they have a fraud score
    for a transaction.  This view must respond with a simple string
    response within 1 second for it to be acknowledged.
    """

    def post(self, request, *args, **kwargs):
        content_type = request.META['CONTENT_TYPE']
        try:
            # Create a fraud response object.  Other processes should listen
            # to the post create signal in order to hook fraud processing into
            # this order pipeline.
            if content_type == 'application/x-www-form-urlencoded':
                response = models.FraudResponse.create_from_querystring(request.body)
            else:
                response = models.FraudResponse.create_from_xml(request.body)
        except Exception, e:
            logger.error("Error raised handling response:\n%s", request.body)
            logger.exception(e)
            return http.HttpResponseServerError("error")
        else:
            logger.info("Successful response received with merchant ref %s",
                        response.merchant_order_ref)
            return http.HttpResponse("ok")
