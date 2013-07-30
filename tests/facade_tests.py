# -*- coding: utf-8 -*-
from decimal import Decimal as D
import math
import time
from mock import Mock
from unittest import skipUnless

from django.test import TestCase
from django.conf import settings
from oscar.apps.payment.utils import Bankcard
from oscar.apps.payment.exceptions import UnableToTakePayment, InvalidGatewayRequestError

from datacash.models import OrderTransaction
from datacash.gateway import Gateway, Response
from datacash.facade import Facade

from . import XmlTestingMixin, fixtures


class MockBillingAddress(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FacadeTests(TestCase, XmlTestingMixin):

    def setUp(self):
        self.facade = Facade()

    def test_unicode_handling(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        self.facade.pre_authorise(
            '1234', D('10.00'), card,
            the3rdman_data={
                'customer_info': {
                    'surname': u'Smörgåsbord'
                }
            })

    def test_second_fulfill_has_merchant_ref(self):
        # Initial pre-auth
        self.facade.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        ref = self.facade.pre_authorise('1234', D('100.00'), card)
        txn = OrderTransaction.objects.get(datacash_reference=ref)

        # First fulfill
        self.facade.gateway._fetch_response_xml = Mock(
            return_value=fixtures.SAMPLE_SUCCESSFUL_FULFILL_RESPONSE)
        self.facade.fulfill_transaction('1234', D('50.00'),
                                        txn.datacash_reference, txn.auth_code)

        self.facade.fulfill_transaction('1234', D('40.00'),
                                        txn.datacash_reference, txn.auth_code)
        fulfill_txn = OrderTransaction.objects.get(
            order_number='1234',
            amount=D('40.00')
        )
        self.assertTrue('merchantreference' in fulfill_txn.request_xml)

    def test_zero_amount_for_pre_raises_exception(self):
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        with self.assertRaises(UnableToTakePayment):
            self.facade.pre_authorise('1234', D('0.00'), card)

    def test_zero_amount_for_auth_raises_exception(self):
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        with self.assertRaises(UnableToTakePayment):
            self.facade.authorise('1234', D('0.00'), card)

    def test_auth_request_creates_txn_model(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        self.facade.authorise('100001', D('123.22'), card)
        txn = OrderTransaction.objects.filter(order_number='100001')[0]
        self.assertEquals('auth', txn.method)
        self.assertEquals(D('123.22'), txn.amount)
        self.assertTrue(len(txn.request_xml) > 0)
        self.assertTrue(len(txn.response_xml) > 0)

    def test_auth_request_with_integer_cvv(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', cvv=345)
        self.facade.authorise('100001', D('123.22'), card)

    def test_pre_request_creates_txn_model(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        self.facade.pre_authorise('100001', D('123.22'), card)
        txn = OrderTransaction.objects.filter(order_number='100001')[0]
        self.assertEquals('pre', txn.method)
        self.assertEquals(D('123.22'), txn.amount)
        self.assertTrue(len(txn.request_xml) > 0)
        self.assertTrue(len(txn.response_xml) > 0)

    def test_pre_request_uses_billing_address_fields(self):
        mock = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        self.facade.gateway._fetch_response_xml = mock
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        address = MockBillingAddress(line1='1 Egg Street',
                                     line2='Farmville',
                                     line4='Greater London',
                                     postcode='N1 8RT')
        self.facade.pre_authorise('100001', D('123.22'), card,
                                  billing_address=address)
        request_xml = mock.call_args[0][0]
        self.assertXmlElementEquals(request_xml, '1 Egg Street',
                                    'Request.Transaction.CardTxn.Card.Cv2Avs.street_address1')
        self.assertXmlElementEquals(request_xml, 'Farmville',
                                    'Request.Transaction.CardTxn.Card.Cv2Avs.street_address2')
        self.assertXmlElementEquals(request_xml, 'N1 8RT',
                                    'Request.Transaction.CardTxn.Card.Cv2Avs.postcode')

    def test_auth_request_uses_billing_address_fields(self):
        mock = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        self.facade.gateway._fetch_response_xml = mock
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        address = MockBillingAddress(line1='1 Egg Street',
                                     line2='Farmville',
                                     line4='Greater London',
                                     postcode='N1 8RT')
        self.facade.authorise('100001', D('123.22'), card, billing_address=address)
        request_xml = mock.call_args[0][0]
        self.assertXmlElementEquals(request_xml, '1 Egg Street',
                                    'Request.Transaction.CardTxn.Card.Cv2Avs.street_address1')
        self.assertXmlElementEquals(request_xml, 'Farmville',
                                    'Request.Transaction.CardTxn.Card.Cv2Avs.street_address2')
        self.assertXmlElementEquals(request_xml, 'N1 8RT',
                                    'Request.Transaction.CardTxn.Card.Cv2Avs.postcode')

    def test_refund_request_doesnt_include_currency_attribute(self):
        mock = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        self.facade.gateway._fetch_response_xml = mock
        self.facade.refund_transaction('100001', D('123.22'),
                                       txn_reference='12345')
        request_xml = mock.call_args[0][0]
        self.assertTrue('currency' not in request_xml)

    def test_auth_request_returns_datacash_ref(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        ref = self.facade.authorise('100001', D('123.22'), card)
        self.assertEquals('3000000088888888', ref)

    def test_auth_request_using_previous_txn_ref(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        ref = self.facade.authorise('100001', D('123.22'), txn_reference='3000000088888888')
        self.assertEquals('3000000088888888', ref)

    def test_refund_request(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        ref = self.facade.refund('100005', D('123.22'), card)
        txn = OrderTransaction.objects.filter(order_number='100005')[0]
        self.assertEquals('refund', txn.method)

    def test_pre_auth_using_history_txn(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        ref = self.facade.pre_authorise('100001', D('123.22'), txn_reference='3000000088888888')
        self.assertEquals('3000000088888888', ref)

    def test_refund_using_historic_txn(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        ref = self.facade.refund('100001', D('123.22'), txn_reference='3000000088888888')
        self.assertEquals('3000000088888888', ref)

    def test_refund_without_source_raises_exception(self):
        with self.assertRaises(ValueError):
            ref = self.facade.refund('100001', D('123.22'))

    def test_pre_auth_without_source_raises_exception(self):
        with self.assertRaises(ValueError):
            ref = self.facade.pre_authorise('100001', D('123.22'))

    def test_auth_without_source_raises_exception(self):
        with self.assertRaises(ValueError):
            ref = self.facade.authorise('100001', D('123.22'))

    def test_successful_cancel_request(self):
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <datacash_reference>4900200000000001</datacash_reference>
    <merchantreference>4900200000000001</merchantreference>
    <mode>TEST</mode>
    <reason>CANCELLED OK</reason>
    <status>1</status>
    <time>1151567456</time>
</Response>"""
        self.facade.gateway._fetch_response_xml = Mock(return_value=response_xml)
        ref = self.facade.cancel_transaction('100001', '3000000088888888')
        self.assertEquals('4900200000000001', ref)

    def test_successful_fulfill_request(self):
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <datacash_reference>3900200000000001</datacash_reference>
    <merchantreference>3900200000000001</merchantreference>
    <mode>LIVE</mode>
    <reason>FULFILLED OK</reason>
    <status>1</status>
    <time>1071567356</time>
</Response>"""
        self.facade.gateway._fetch_response_xml = Mock(return_value=response_xml)
        self.facade.fulfill_transaction('100002', D('45.00'), '3000000088888888', '1234')
        txn = OrderTransaction.objects.filter(order_number='100002')[0]
        self.assertEquals('fulfill', txn.method)

    def test_successful_refund_request(self):
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <datacash_reference>4000000088889999</datacash_reference>
    <HistoricTxn>
        <authcode>896876</authcode>
    </HistoricTxn>
    <merchantreference>4100000088888888</merchantreference>
    <mode>LIVE</mode>
    <reason>ACCEPTED</reason>
    <status>1</status>
    <time>1071567375</time>
</Response>"""
        self.facade.gateway._fetch_response_xml = Mock(return_value=response_xml)
        self.facade.refund_transaction('100003', D('45.00'), '3000000088888888')
        txn = OrderTransaction.objects.filter(order_number='100003')[0]
        self.assertEquals('txn_refund', txn.method)

    def test_transaction_declined_exception_raised_for_decline(self):
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <CardTxn>
        <authcode>DECLINED</authcode>
        <card_scheme>Mastercard</card_scheme>
        <country>United Kingdom</country>
    </CardTxn>
    <datacash_reference>4400200045583767</datacash_reference>
    <merchantreference>AA004630</merchantreference>
    <mode>TEST</mode>
    <reason>DECLINED</reason>
    <status>7</status>
    <time>1169223906</time>
</Response>"""
        self.facade.gateway._fetch_response_xml = Mock(return_value=response_xml)
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        with self.assertRaises(UnableToTakePayment):
            self.facade.pre_authorise('100001', D('123.22'), card)

    def test_invalid_request_exception_raised_for_error(self):
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <datacash_reference>21859999000005679</datacash_reference>
    <information>This vTID is not configured to process pre-registered card transactions.</information>
    <merchantreference>123403</merchantreference>
    <reason>Prereg: Merchant Not Subscribed</reason>
    <status>251</status>
    <time>1074692433</time>
</Response>"""
        self.facade.gateway._fetch_response_xml = Mock(return_value=response_xml)
        card = Bankcard('1000350000000007', '10/13', cvv='345')
        with self.assertRaises(InvalidGatewayRequestError):
            self.facade.pre_authorise('100001', D('123.22'), card)






