import datetime

from django.db import transaction
from django.conf import settings

from datacash import gateway
from datacash.models import OrderTransaction


class Facade(object):
    """
    Responsible for dealing with oscar objects
    """
    
    def __init__(self):
        self.gateway = gateway.Gateway(settings.DATACASH_HOST,
                                       settings.DATACASH_CLIENT, 
                                       settings.DATACASH_PASSWORD,
                                       settings.DATACASH_USE_CV2AVS)
        self.currency = settings.DATACASH_CURRENCY

    def handle_response(self, order_number, amount, response):
        self.record_txn(order_number, amount, response)
        # A response is either successful, declined or an error
        if response.is_successful():
            return response['datacash_reference']
        elif response.is_declined():
            msg = self.get_friendly_decline_message(response)
            raise TransactionDeclined(msg)
        else:
            msg = self.get_friendly_error_message(response)
            raise InvalidGatewayRequestError(msg)

    def record_txn(self, order_number, amount, response):
        txn = OrderTransaction.objects.create(order_number=order_number,
                                              method=gateway.AUTH,
                                              datacash_reference=response['datacash_reference'],
                                              merchant_reference=response['merchant_reference'],
                                              amount=amount,
                                              auth_code=response['auth_code'],
                                              status=int(response['status']),
                                              reason=response['reason'],
                                              request_xml=response.request_xml,
                                              response_xml=response.response_xml)

    def get_friendly_decline_message(self, response):
        return 'The transaction was declined by your bank - please check your bankcard details and try again'

    def get_friendly_error_message(self, response):
        return 'An error occurred when communicating with the payment gateway.'

    def pre_auth(self):
        pass

    def fulfil(self):
        pass

    def refund(self):
        pass
    
    def authorise(self, order_number, amount, bankcard=None, txn_reference=None):
        """
        Debit a bankcard for the given amount

        A bankcard object or a txn_reference can be passed.
        """
        with transaction.commit_on_success():
            response = self.gateway.auth(card_number=bankcard.card_number,
                                         expiry_date=bankcard.expiry_date,
                                         amount=amount,
                                         currency=self.currency,
                                         merchant_reference=self.generate_merchant_reference(order_number),
                                         ccv=bankcard.ccv)
            return self.handle_response(order_number, amount, response)
        
    def generate_merchant_reference(self, order_number):
        return '%s_%s' % (order_number, datetime.datetime.now().microsecond)
