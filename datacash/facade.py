import random

from django.conf import settings
from oscar.apps.payment.exceptions import UnableToTakePayment, InvalidGatewayRequestError

from datacash import gateway
from datacash.models import OrderTransaction


class Facade(object):
    """
    A bridge between oscar's objects and the core gateway object
    """

    def __init__(self):
        self.gateway = gateway.Gateway(
            settings.DATACASH_HOST,
            getattr(settings, 'DATACASH_PATH', '/Transaction'),
            settings.DATACASH_CLIENT,
            settings.DATACASH_PASSWORD,
            getattr(settings, 'DATACASH_USE_CV2AVS', False),
            getattr(settings, 'DATACASH_CAPTURE_METHOD', 'ecomm'))

    def handle_response(self, method, order_number, amount, currency, response):

        # Maintain audit trail
        self.record_txn(method, order_number, amount, currency, response)

        # A response is either successful, declined or an error
        if response.is_successful():
            return response['datacash_reference']
        elif response.is_declined():
            msg = self.get_friendly_decline_message(response)
            raise UnableToTakePayment(msg)
        else:
            msg = self.get_friendly_error_message(response)
            raise InvalidGatewayRequestError(msg)

    def record_txn(self, method, order_number, amount, currency, response):
        OrderTransaction.objects.create(
            order_number=order_number,
            method=method,
            datacash_reference=response['datacash_reference'],
            merchant_reference=response['merchant_reference'],
            amount=amount,
            currency=currency or "",
            auth_code=response['auth_code'],
            status=response.status,
            reason=response['reason'],
            request_xml=response.request_xml,
            response_xml=response.response_xml)

    def get_friendly_decline_message(self, response):
        return 'The transaction was declined by your bank - please check your bankcard details and try again'

    def get_friendly_error_message(self, response):
        # TODO: expand this dict to handle the most common errors
        errors = {
            56: ('This transaction was submitted too soon after the '
                 'previous one.  Please wait for a minute then try again'),
            19: 'Unable to fulfill transaction',
        }
        default_msg = 'An error occurred when communicating with the payment gateway.'
        return errors.get(response.status, default_msg)

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
                      txn_reference=None, billing_address=None,
                      the3rdman_data=None, currency=None):
        """
        Ring-fence an amount of money from the given card.  This is the first
        stage of a two-stage payment process.  A further call to fulfill is
        required to debit the money.

        As there are SO MANY values that can be submitted to 3rdMan, a separate
        dict of data must be submitted as a kwarg.
        """
        if amount == 0:
            raise UnableToTakePayment("Order amount must be non-zero")
        if currency is None:
            currency = settings.DATACASH_CURRENCY
        merchant_ref = self.merchant_reference(order_number, gateway.PRE)
        address_data = self.extract_address_data(billing_address)
        if bankcard:
            response = self.gateway.pre(
                card_number=bankcard.card_number,
                expiry_date=bankcard.expiry_date,
                amount=amount,
                currency=currency,
                merchant_reference=merchant_ref,
                ccv=bankcard.ccv,
                the3rdman_data=the3rdman_data,
                **address_data)
        elif txn_reference:
            response = self.gateway.pre(
                amount=amount,
                currency=currency,
                merchant_reference=merchant_ref,
                previous_txn_reference=txn_reference,
                the3rdman_data=the3rdman_data,
                **address_data)
        else:
            raise ValueError(
                "You must specify either a bankcard or a previous txn reference")
        return self.handle_response(
            gateway.PRE, order_number, amount, currency, response)

    def merchant_reference(self, order_number, method):
        # Determine the previous number of these transactions.
        num_previous = OrderTransaction.objects.filter(
            order_number=order_number, method=method).count()
        # Get a random number to append to the end.  This solves the problem
        # where a previous request crashed out and didn't save a model
        # instance.  Hence we can get a clash of merchant references.
        rand = "%04.f" % (random.random() * 10000)
        return u'%s_%s_%d_%s' % (order_number, method.upper(), num_previous+1,
                                 rand)

    def fulfill_transaction(self, order_number, amount, txn_reference,
                            auth_code, currency=None):
        """
        Settle a previously ring-fenced transaction
        """
        if currency is None:
            currency = settings.DATACASH_CURRENCY
        # Split shipments require that fulfills after the first one must have a
        # different merchant reference to the original
        merchant_ref = self.merchant_reference(order_number, gateway.FULFILL)
        response = self.gateway.fulfill(amount=amount,
                                        currency=currency,
                                        merchant_reference=merchant_ref,
                                        txn_reference=txn_reference,
                                        auth_code=auth_code)
        return self.handle_response(gateway.FULFILL, order_number, amount,
                                    currency, response)

    def refund_transaction(self, order_number, amount, txn_reference,
                           currency=None):
        """
        Refund against a previous ransaction
        """
        if currency is None:
            currency = settings.DATACASH_CURRENCY
        response = self.gateway.txn_refund(amount=amount,
                                           currency=currency,
                                           txn_reference=txn_reference)
        return self.handle_response(gateway.TXN_REFUND, order_number, amount,
                                    currency, response)

    def cancel_transaction(self, order_number, txn_reference):
        """
        Refund against a previous ransaction
        """
        response = self.gateway.cancel(txn_reference)
        return self.handle_response(
            gateway.CANCEL, order_number, None, None, response)

    # ========================
    # API - 1 stage processing
    # ========================

    def authorise(self, order_number, amount, bankcard=None, txn_reference=None,
                  billing_address=None, the3rdman_data=None, currency=None):
        """
        Debit a bankcard for the given amount

        A bankcard object or a txn_reference can be passed depending on whether
        you are using a new or existing bankcard.
        """
        if amount == 0:
            raise UnableToTakePayment("Order amount must be non-zero")
        if currency is None:
            currency = settings.DATACASH_CURRENCY

        merchant_ref = self.merchant_reference(order_number, gateway.AUTH)
        address_data = self.extract_address_data(billing_address)
        if bankcard:
            response = self.gateway.auth(card_number=bankcard.card_number,
                                         expiry_date=bankcard.expiry_date,
                                         amount=amount,
                                         currency=currency,
                                         merchant_reference=merchant_ref,
                                         ccv=bankcard.ccv,
                                         the3rdman_data=the3rdman_data,
                                         **address_data)
        elif txn_reference:
            response = self.gateway.auth(amount=amount,
                                         currency=currency,
                                         merchant_reference=merchant_ref,
                                         previous_txn_reference=txn_reference,
                                         the3rdman_data=the3rdman_data,
                                         **address_data)
        else:
            raise ValueError(
                "You must specify either a bankcard or a previous txn reference")

        return self.handle_response(gateway.AUTH, order_number, amount,
                                    currency, response)

    def refund(self, order_number, amount, bankcard=None, txn_reference=None,
               currency=None):
        """
        Return funds to a bankcard
        """
        if currency is None:
            currency = settings.DATACASH_CURRENCY
        merchant_ref = self.merchant_reference(order_number, gateway.REFUND)
        if bankcard:
            response = self.gateway.refund(card_number=bankcard.card_number,
                                           expiry_date=bankcard.expiry_date,
                                           amount=amount,
                                           currency=currency,
                                           merchant_reference=merchant_ref,
                                           ccv=bankcard.ccv)
        elif txn_reference:
            response = self.gateway.refund(
                amount=amount, currency=currency,
                merchant_reference=merchant_ref,
                previous_txn_reference=txn_reference)
        else:
            raise ValueError("You must specify either a bankcard or a previous txn reference")
        return self.handle_response(gateway.REFUND, order_number, amount,
                                    currency, response)
