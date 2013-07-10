from decimal import Decimal as D

from django.test import TestCase

from datacash.models import OrderTransaction
from . import XmlTestingMixin, fixtures


class TransactionModelTests(TestCase, XmlTestingMixin):

    def test_unicode_method(self):
        txn = OrderTransaction.objects.create(order_number='1000',
                                              method='auth',
                                              datacash_reference='3000000088888888',
                                              merchant_reference='1000001',
                                              amount=D('95.99'),
                                              status=1,
                                              reason='ACCEPTED',
                                              request_xml=fixtures.SAMPLE_CV2AVS_REQUEST,
                                              response_xml=fixtures.SAMPLE_RESPONSE)
        self.assertTrue('AUTH txn ' in  str(txn))

    def test_password_is_not_saved_in_xml(self):
        txn = OrderTransaction.objects.create(order_number='1000',
                                              method='auth',
                                              datacash_reference='3000000088888888',
                                              merchant_reference='1000001',
                                              amount=D('95.99'),
                                              status=1,
                                              reason='ACCEPTED',
                                              request_xml=fixtures.SAMPLE_CV2AVS_REQUEST,
                                              response_xml=fixtures.SAMPLE_RESPONSE)
        self.assertXmlElementEquals(txn.request_xml, 'XXX',
                                    'Request.Transaction.CardTxn.Card.Cv2Avs.cv2')

    def test_cvv_numbers_are_not_saved_in_xml(self):
        txn = OrderTransaction.objects.create(order_number='1000',
                                              method='auth',
                                              datacash_reference='3000000088888888',
                                              merchant_reference='1000001',
                                              amount=D('95.99'),
                                              status=1,
                                              reason='ACCEPTED',
                                              request_xml=fixtures.SAMPLE_CV2AVS_REQUEST,
                                              response_xml=fixtures.SAMPLE_RESPONSE)
        self.assertXmlElementEquals(txn.request_xml, 'XXX',
                                    'Request.Authentication.password')

    def test_cc_numbers_are_not_saved_in_xml(self):
        txn = OrderTransaction.objects.create(order_number='1000',
                                              method='auth',
                                              datacash_reference='3000000088888888',
                                              merchant_reference='1000001',
                                              amount=D('95.99'),
                                              status=1,
                                              reason='ACCEPTED',
                                              request_xml=fixtures.SAMPLE_REQUEST,
                                              response_xml=fixtures.SAMPLE_RESPONSE)
        self.assertXmlElementEquals(txn.request_xml, 'XXXXXXXXXXXX0004', 'Request.Transaction.CardTxn.Card.pan')
