from decimal import Decimal as D
import math
import time
from mock import Mock
from unittest import skipUnless

from django.test import TestCase
from django.conf import settings
from oscar.apps.payment.exceptions import UnableToTakePayment, InvalidGatewayRequestError

from datacash.models import OrderTransaction
from datacash.gateway import Gateway, Response
from datacash.facade import Facade


@skipUnless(getattr(settings, 'DATACASH_ENABLE_INTEGRATION_TESTS', False), "Currently disabled")
class GatewayIntegrationTests(TestCase):
    """
    There can be problems with DataCash speed limits when running these tests as
    you aren't supposed to perform a transaction with the same card more
    than once every two minutes.
    """

    def setUp(self):
        self.gateway = Gateway(settings.DATACASH_HOST,
                               '/Transaction',
                               settings.DATACASH_CLIENT,
                               settings.DATACASH_PASSWORD)

    def generate_merchant_reference(self):
        return 'TEST_%s' % int(math.floor(time.time() * 100))

    def test_successful_auth(self):
        # Using test card from Datacash's docs
        ref = self.generate_merchant_reference()
        response = self.gateway.auth(amount=D('1000.00'),
                                     currency='GBP',
                                     card_number='1000350000000007',
                                     expiry_date='10/12',
                                     merchant_reference=ref)
        self.assertEquals('1', response['status'])
        self.assertEquals(ref, response['merchant_reference'])
        self.assertEquals('ACCEPTED', response['reason'])
        self.assertEquals('100000', response['auth_code'])
        self.assertEquals('Mastercard', response['card_scheme'])
        self.assertEquals('United Kingdom', response['country'])

    def test_declined_auth(self):
        ref = self.generate_merchant_reference()
        response = self.gateway.auth(amount=D('1000.02'),
                                     currency='GBP',
                                     card_number='4444333322221111',
                                     expiry_date='10/12',
                                     merchant_reference=ref)
        self.assertEquals('7', response['status'])
        self.assertEquals(ref, response['merchant_reference'])
        self.assertEquals('DECLINED', response['reason'])
        self.assertEquals('VISA', response['card_scheme'])

    def test_cancel_auth(self):
        ref = self.generate_merchant_reference()
        response = self.gateway.auth(amount=D('1000.00'),
                                     currency='GBP',
                                     card_number='1000011000000005',
                                     expiry_date='10/12',
                                     merchant_reference=ref)
        self.assertTrue(response.is_successful())
        cancel_response = self.gateway.cancel(response['datacash_reference'])
        self.assertEquals('1', response['status'])

    def test_refund_auth(self):
        ref = self.generate_merchant_reference()
        refund_response = self.gateway.refund(amount=D('200.00'),
                                              currency='GBP',
                                              card_number='1000010000000007',
                                              expiry_date='10/12',
                                              merchant_reference=ref)
        self.assertTrue(refund_response.is_successful())

    def test_txn_refund_of_auth(self):
        ref = self.generate_merchant_reference()
        response = self.gateway.auth(amount=D('1000.00'),
                                     currency='GBP',
                                     card_number='1000011100000004',
                                     expiry_date='10/12',
                                     merchant_reference=ref)
        self.assertTrue(response.is_successful())
        cancel_response = self.gateway.txn_refund(txn_reference=response['datacash_reference'],
                                                  amount=D('1000.00'),
                                                  currency='GBP')
        self.assertTrue(response.is_successful())

    def test_pre(self):
        ref = self.generate_merchant_reference()
        response = self.gateway.pre(amount=D('1000.00'),
                                    currency='GBP',
                                    card_number='1000020000000014',
                                    expiry_date='10/12',
                                    merchant_reference=ref)
        self.assertTrue(response.is_successful())
        self.assertTrue(response['auth_code'])

    def test_fulfill(self):
        ref = self.generate_merchant_reference()
        pre_response = self.gateway.pre(amount=D('1000.00'),
                                        currency='GBP',
                                        card_number='1000070000000001',
                                        expiry_date='10/12',
                                        merchant_reference=ref)
        self.assertTrue(pre_response.is_successful())

        response = self.gateway.fulfill(amount=D('800.00'),
                                        currency='GBP',
                                        auth_code=pre_response['auth_code'],
                                        txn_reference=pre_response['datacash_reference'])
        self.assertEquals('FULFILLED OK', response['reason'])
        self.assertTrue(response.is_successful())
