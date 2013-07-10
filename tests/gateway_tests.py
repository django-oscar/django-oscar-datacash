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


class TestGatewayWithCV2AVSMock(TestCase, XmlTestingMixin):
    """
    Gateway using CV2AVS
    """

    def setUp(self):
        self.gateway = Gateway('example.com', '/Transaction', 'dummyclient', 'dummypassword', True)

    def gateway_auth(self, amount=D('1000.00'), currency='GBP', card_number='1000350000000007',
            expiry_date='10/12', merchant_reference='TEST_132473839018', response_xml=fixtures.SAMPLE_RESPONSE, **kwargs):
        self.gateway._fetch_response_xml = Mock(return_value=response_xml)
        response = self.gateway.auth(amount=amount,
                                     currency=currency,
                                     card_number=card_number,
                                     expiry_date=expiry_date,
                                     merchant_reference=merchant_reference,
                                     **kwargs)
        return response

    def test_zero_amount_raises_exception(self):
        with self.assertRaises(ValueError):
            self.gateway_auth(amount=D('0.00'))

    def test_cvv_is_included_in_request(self):
        response = self.gateway_auth(cvv='456')
        self.assertXmlElementEquals(response.request_xml, '456', 'Request.Transaction.CardTxn.Card.Cv2Avs.cv2')

    def test_capture_method_defaults_to_ecomm(self):
        response = self.gateway_auth()
        self.assertXmlElementEquals(response.request_xml, 'ecomm', 'Request.Transaction.TxnDetails.capturemethod')


class TestGatewayWithoutCV2AVSMock(TestCase, XmlTestingMixin):
    """
    Gateway without CV2AVS
    """

    def setUp(self):
        self.gateway = Gateway('example.com', '/Transaction', 'dummyclient', 'dummypassword')

    def gateway_auth(self, amount=D('1000.00'), currency='GBP', card_number='1000350000000007',
            expiry_date='10/12', merchant_reference='TEST_132473839018', response_xml=fixtures.SAMPLE_RESPONSE, **kwargs):
        self.gateway._fetch_response_xml = Mock(return_value=response_xml)
        response = self.gateway.auth(amount=amount,
                                     currency=currency,
                                     card_number=card_number,
                                     expiry_date=expiry_date,
                                     merchant_reference=merchant_reference,
                                     **kwargs)
        return response

    def gateway_cancel(self, datacash_reference='132473839018', response_xml=fixtures.SAMPLE_RESPONSE, **kwargs):
        self.gateway._fetch_response_xml = Mock(return_value=response_xml)
        return self.gateway.cancel(datacash_reference, **kwargs)

    def test_successful_auth(self):
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <CardTxn>
        <authcode>100000</authcode>
        <card_scheme>Mastercard</card_scheme>
        <country>United Kingdom</country>
    </CardTxn>
    <datacash_reference>4000203021904745</datacash_reference>
    <merchantreference>TEST_132473839018</merchantreference>
    <mode>TEST</mode>
    <reason>ACCEPTED</reason>
    <status>1</status>
    <time>1324738433</time>
</Response>"""
        response = self.gateway_auth(response_xml=response_xml)
        self.assertEquals('1', response['status'])
        self.assertEquals('TEST_132473839018', response['merchant_reference'])
        self.assertEquals('ACCEPTED', response['reason'])
        self.assertEquals('100000', response['auth_code'])
        self.assertEquals('Mastercard', response['card_scheme'])
        self.assertEquals('United Kingdom', response['country'])
        self.assertTrue(response.is_successful())

    def test_unsuccessful_auth(self):
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
        response = self.gateway_auth(response_xml=response_xml)
        self.assertEquals('7', response['status'])
        self.assertEquals('AA004630', response['merchant_reference'])
        self.assertEquals('DECLINED', response['reason'])
        self.assertEquals('Mastercard', response['card_scheme'])
        self.assertEquals('United Kingdom', response['country'])
        self.assertFalse(response.is_successful())

    def test_startdate_is_included_in_request_xml(self):
        response = self.gateway_auth(start_date='10/10')
        self.assertXmlElementEquals(response.request_xml, '10/10', 'Request.Transaction.CardTxn.Card.startdate')

    def test_auth_code_is_included_in_request_xml(self):
        response = self.gateway_auth(auth_code='11122')
        self.assertXmlElementEquals(response.request_xml, '11122',
                                    'Request.Transaction.CardTxn.Card.authcode')

    def test_issue_number_is_included_in_request_xml(self):
        response = self.gateway_auth(issue_number='01')
        self.assertXmlElementEquals(response.request_xml, '01', 'Request.Transaction.CardTxn.Card.issuenumber')

    def test_issue_number_is_validated_for_format(self):
        with self.assertRaises(ValueError):
            self.gateway_auth(issue_number='A')

    def test_dates_are_validated_for_format(self):
        with self.assertRaises(ValueError):
            self.gateway_auth(expiry_date='10/2012')

    def test_issuenumber_is_validated_for_format(self):
        with self.assertRaises(ValueError):
            self.gateway.auth(issue_number='123')

    def test_currency_is_validated_for_format(self):
        with self.assertRaises(ValueError):
            self.gateway_auth(currency='BGRR')

    def test_merchant_ref_is_validated_for_min_length(self):
        with self.assertRaises(ValueError):
            self.gateway_auth(merchant_reference='12345')

    def test_merchant_ref_is_validated_for_max_length(self):
        with self.assertRaises(ValueError):
            self.gateway_auth(merchant_reference='123456789012345678901234567890123')

    def test_successful_cancel_response(self):
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <datacash_reference>4500203021916406</datacash_reference>
  <merchantreference>4500203021916406</merchantreference>
  <mode>TEST</mode>
  <reason>CANCELLED OK</reason>
  <status>1</status>
  <time>1324832003</time>
</Response>"""
        response = self.gateway_cancel(response_xml=response_xml)
        self.assertEquals('CANCELLED OK', response['reason'])
        self.assertTrue(response.is_successful())

    def test_request_xml_for_auth_using_previous_transaction_ref(self):
        self.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        response = self.gateway.auth(amount=D('1000.00'),
                                     currency='GBP',
                                     merchant_reference='TEST_132473839018',
                                     previous_txn_reference='4500203021916406')
        self.assertXmlElementEquals(response.request_xml,
            '4500203021916406', 'Request.Transaction.CardTxn.card_details')

    def test_request_xml_for_pre_using_previous_transaction_ref(self):
        self.gateway._fetch_response_xml = Mock(return_value=fixtures.SAMPLE_RESPONSE)
        response = self.gateway.pre(amount=D('1000.00'),
                                    currency='GBP',
                                    merchant_reference='TEST_132473839018',
                                    previous_txn_reference='4500203021916406')
        self.assertXmlElementEquals(response.request_xml,
            '4500203021916406', 'Request.Transaction.CardTxn.card_details')


class GatewayErrorTests(TestCase):

    def test_exception_raised_with_bad_host(self):
        with self.assertRaises(RuntimeError):
            Gateway('http://test.datacash.com', '/Transaction', client='', password='')


class ResponseTests(TestCase):

    def test_str_version_is_response_xml(self):
        response_xml = '<?xml version="1.0" ?><Response />'
        r = Response('', response_xml)
        self.assertEqual(response_xml, str(r))

    def test_none_is_returned_for_missing_status(self):
        r = Response('', '<?xml version="1.0" ?><Response />')
        self.assertIsNone(r.status)


class SuccessfulResponseTests(TestCase):

    def setUp(self):
        request_xml = ""
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <datacash_reference>4500203021916406</datacash_reference>
  <merchantreference>4500203021916406</merchantreference>
  <mode>TEST</mode>
  <reason>CANCELLED OK</reason>
  <status>1</status>
  <time>1324832003</time>
</Response>"""
        self.response = Response(request_xml, response_xml)

    def test_dict_access(self):
        self.assertEquals('1', self.response['status'])

    def test_in_access(self):
        self.assertTrue('status' in self.response)

    def test_is_successful(self):
        self.assertTrue(self.response.is_successful())

    def test_status_is_returned_correctly(self):
        self.assertEquals(1, self.response.status)


class DeclinedResponseTests(TestCase):

    def setUp(self):
        request_xml = ""
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
        self.response = Response(request_xml, response_xml)

    def test_is_successful(self):
        self.assertFalse(self.response.is_successful())

    def test_is_declined(self):
        self.assertTrue(self.response.is_declined())
