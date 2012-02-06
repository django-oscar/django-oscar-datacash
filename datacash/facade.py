import datetime

from django.db import transaction
from django.conf import settings
from oscar.apps.payment.exceptions import UnableToTakePayment, InvalidGatewayRequestError

from datacash import gateway
from datacash.models import OrderTransaction


class Facade(object):
    """
    A bridge between oscar's objects and the core gateway object
    """
    
    def __init__(self):
        self.gateway = gateway.Gateway(settings.DATACASH_HOST,
                                       settings.DATACASH_CLIENT, 
                                       settings.DATACASH_PASSWORD,
                                       getattr(settings, 'DATACASH_USE_CV2AVS', False),
                                       getattr(settings, 'DATACASH_CAPTURE_METHOD', 'ecomm')
                                      )
        self.currency = settings.DATACASH_CURRENCY

    def handle_response(self, method, order_number, amount, response):
        with transaction.commit_on_success():
            self.record_txn(method, order_number, amount, response)
        # A response is either successful, declined or an error
        if response.is_successful():
            return response['datacash_reference']
        elif response.is_declined():
            msg = self.get_friendly_decline_message(response)
            raise UnableToTakePayment(msg)
        else:
            msg = self.get_friendly_error_message(response)
            raise InvalidGatewayRequestError(msg)

    def record_txn(self, method, order_number, amount, response):
        txn = OrderTransaction.objects.create(order_number=order_number,
                                              method=method,
                                              datacash_reference=response['datacash_reference'],
                                              merchant_reference=response['merchant_reference'],
                                              amount=amount,
                                              auth_code=response['auth_code'],
                                              status=response.status,
                                              reason=response['reason'],
                                              request_xml=response.request_xml,
                                              response_xml=response.response_xml)

    def get_friendly_decline_message(self, response):
        return 'The transaction was declined by your bank - please check your bankcard details and try again'

    def get_friendly_error_message(self, response):
        return 'An error occurred when communicating with the payment gateway.'
        
    def generate_merchant_reference(self, order_number):
        return '%s_%s' % (order_number, datetime.datetime.now().microsecond)

    def extract_address_data(self, address):
        data = {}
        if not address:
            return data
        for i in range(1, 5):
            key = 'line%d' % i
            if hasattr(address, key):
                data['address_line%d' % i] = getattr(address, key)
        data['postcode'] = address.postcode
        return data

    # ========================
    # API - 2 stage processing
    # ========================

    def pre_authorise(self, order_number, amount, bankcard=None,
                      txn_reference=None, billing_address=None):
        """
        Ring-fence an amount of money from the given card.  This is the first stage
        of a two-stage payment process.  A further call to fulfill is required to 
        debit the money.
        """
        merchant_ref = self.generate_merchant_reference(order_number)
        address_data = self.extract_address_data(billing_address)
        if bankcard:
            response = self.gateway.pre(card_number=bankcard.card_number,
                                        expiry_date=bankcard.expiry_date,
                                        amount=amount,
                                        currency=self.currency,
                                        merchant_reference=self.generate_merchant_reference(order_number),
                                        ccv=bankcard.ccv,
                                        **address_data
                                        )
        elif txn_reference:
            response = self.gateway.pre(amount=amount,
                                        currency=self.currency,
                                        merchant_reference=merchant_ref,
                                        previous_txn_reference=txn_reference,
                                        **address_data)
        else:
            raise ValueError("You must specify either a bankcard or a previous txn reference")
        return self.handle_response(gateway.PRE, order_number, amount, response)

    def fulfill_transaction(self, order_number, amount, txn_reference, auth_code):
        """
        Settle a previously ring-fenced transaction
        """
        response = self.gateway.fulfill(amount=amount,
                                        currency=self.currency,
                                        txn_reference=txn_reference,
                                        auth_code=auth_code)
        return self.handle_response(gateway.FULFILL, order_number, amount, response)

    def refund_transaction(self, order_number, amount, txn_reference):
        """
        Refund against a previous ransaction
        """
        response = self.gateway.txn_refund(amount=amount,
                                           currency=self.currency,
                                           txn_reference=txn_reference)
        return self.handle_response(gateway.TXN_REFUND, order_number, amount, response)

    def cancel_transaction(self, order_number, txn_reference):
        """
        Refund against a previous ransaction
        """
        response = self.gateway.cancel(txn_reference)
        return self.handle_response(gateway.CANCEL, order_number, None, response)

    # ========================
    # API - 1 stage processing
    # ========================

    def authorise(self, order_number, amount, bankcard=None, txn_reference=None,
                  billing_address=None):
        """
        Debit a bankcard for the given amount

        A bankcard object or a txn_reference can be passed depending on whether
        you are using a new or existing bankcard.
        """
        merchant_ref = self.generate_merchant_reference(order_number)
        address_data = self.extract_address_data(billing_address)
        if bankcard:
            response = self.gateway.auth(card_number=bankcard.card_number,
                                         expiry_date=bankcard.expiry_date,
                                         amount=amount,
                                         currency=self.currency,
                                         merchant_reference=merchant_ref,
                                         ccv=bankcard.ccv,
                                         **address_data)
        elif txn_reference:
            response = self.gateway.auth(amount=amount,
                                         currency=self.currency,
                                         merchant_reference=merchant_ref,
                                         previous_txn_reference=txn_reference,
                                         **address_data)
        else:
            raise ValueError("You must specify either a bankcard or a previous txn reference")

        return self.handle_response(gateway.AUTH, order_number, amount, response)

    def refund(self, order_number, amount, bankcard=None, txn_reference=None):
        """
        Return funds to a bankcard
        """
        merchant_ref = self.generate_merchant_reference(order_number)
        if bankcard:
            response = self.gateway.refund(card_number=bankcard.card_number,
                                           expiry_date=bankcard.expiry_date,
                                           amount=amount,
                                           currency=self.currency,
                                           merchant_reference=merchant_ref,
                                           ccv=bankcard.ccv)
        elif txn_reference:
            response = self.gateway.refund(amount=amount,
                                           currency=self.currency,
                                           merchant_reference=merchant_ref,
                                           previous_txn_reference=txn_reference)
        else:
            raise ValueError("You must specify either a bankcard or a previous txn reference")
        return self.handle_response(gateway.REFUND, order_number, amount, response)
