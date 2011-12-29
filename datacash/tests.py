from decimal import Decimal as D
from xml.dom.minidom import parseString
import datetime
import math
import time
from mock import Mock
from unittest import skipUnless

from django.test import TestCase
from django.conf import settings
from datacash.models import OrderTransaction
from datacash.gateway import Gateway, Response
from datacash.facade import Facade
from oscar.apps.payment.utils import Bankcard


SAMPLE_REQUEST = """<?xml version="1.0" encoding="UTF-8" ?>
<Request>
    <Authentication>
        <client>99000001</client>
        <password>boomboom</password>
    </Authentication>
    <Transaction>
    <CardTxn>
        <Card>
            <pan>1000011100000004</pan>
            <expirydate>04/06</expirydate>
            <startdate>01/04</startdate>
        </Card>
        <method>auth</method>
    </CardTxn>
    <TxnDetails>
        <merchantreference>1000001</merchantreference>
        <amount currency="GBP">95.99</amount>
    </TxnDetails>
    </Transaction>
</Request>"""

SAMPLE_RESPONSE = """<?xml version="1.0" encoding="UTF-8" ?>
<Response>
    <CardTxn>
        <authcode>060642</authcode>
        <card_scheme>Switch</card_scheme>
        <country>United Kingdom</country>
        <issuer>HSBC</issuer>
    </CardTxn>
    <datacash_reference>3000000088888888</datacash_reference>
    <merchantreference>1000001</merchantreference>
    <mode>LIVE</mode>
    <reason>ACCEPTED</reason>
    <status>1</status>
    <time>1071567305</time>
</Response>"""


class XmlTestingMixin(object):

    def assertXmlElementEquals(self, xml_str, value, element_path):
        doc = parseString(xml_str)
        elements = element_path.split('.')
        parent = doc
        for element_name in elements:
            sub_elements = parent.getElementsByTagName(element_name)
            if len(sub_elements) == 0:
                self.fail("No element matching '%s' found using XML string '%s'" % (element_name, element_path))
                return
            parent = sub_elements[0]
        self.assertEqual(value, parent.firstChild.data)


class FacadeTests(TestCase, XmlTestingMixin):

    def setUp(self):
        self.facade = Facade()

    def test_mechant_refs_are_unique(self):
        order_num = '12345'
        ref1 = self.facade.generate_merchant_reference(order_num)
        ref2 = self.facade.generate_merchant_reference(order_num)
        self.assertNotEquals(ref1, ref2)


class TransactionModelTests(TestCase, XmlTestingMixin):
    
    def test_cc_numbers_are_not_saved_in_xml(self):
        txn = OrderTransaction.objects.create(order_number='1000',
                                              method='auth',
                                              datacash_ref='3000000088888888',
                                              merchant_ref='1000001',
                                              amount=D('95.99'),
                                              status=1,
                                              reason='ACCEPTED',
                                              request_xml=SAMPLE_REQUEST,
                                              response_xml=SAMPLE_RESPONSE)
        self.assertXmlElementEquals(txn.request_xml, 'XXXXXXXXXXXX0004', 'Request.Transaction.CardTxn.Card.pan')


class GatewayWithCV2AVSMockTests(TestCase, XmlTestingMixin):

    def setUp(self):
        self.gateway = Gateway('example.com', 'dummyclient', 'dummypassword', True)

    def gateway_auth(self, amount=D('1000.00'), currency='GBP', card_number='1000350000000007',
            expiry_date='10/12', merchant_reference='TEST_132473839018', response_xml=SAMPLE_RESPONSE, **kwargs):
        self.gateway._fetch_response_xml = Mock(return_value=response_xml)
        response = self.gateway.auth(amount=amount,
                                     currency=currency,
                                     card_number=card_number,
                                     expiry_date=expiry_date,
                                     merchant_reference=merchant_reference,
                                     **kwargs)
        return response

    def test_ccv_is_included_in_request(self):
        response = self.gateway_auth(ccv='456')
        self.assertXmlElementEquals(response.request_xml, '456', 'Request.Transaction.CardTxn.Card.Cv2Avs.cv2')


class GatewayWithoutCV2AVSMockTests(TestCase, XmlTestingMixin):

    def setUp(self):
        self.gateway = Gateway('example.com', 'dummyclient', 'dummypassword')

    def gateway_auth(self, amount=D('1000.00'), currency='GBP', card_number='1000350000000007',
            expiry_date='10/12', merchant_reference='TEST_132473839018', response_xml=SAMPLE_RESPONSE, **kwargs):
        self.gateway._fetch_response_xml = Mock(return_value=response_xml)
        response = self.gateway.auth(amount=amount,
                                     currency=currency,
                                     card_number=card_number,
                                     expiry_date=expiry_date,
                                     merchant_reference=merchant_reference,
                                     **kwargs)
        return response

    def gateway_cancel(self, datacash_reference='132473839018', response_xml=SAMPLE_RESPONSE, **kwargs):
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

    def test_issue_number_is_included_in_request_xml(self):
        response = self.gateway_auth(issue_number='01')
        self.assertXmlElementEquals(response.request_xml, '01', 'Request.Transaction.CardTxn.Card.issuenumber')

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

    def test_prev_card_request(self):
        self.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
        response = self.gateway.auth(amount=D('1000.00'),
                                     currency='GBP',
                                     merchant_reference='TEST_132473839018',
                                     previous_txn_reference='4500203021916406')
        self.assertXmlElementEquals(response.request_xml, 
            '4500203021916406', 'Request.Transaction.CardTxn.card_details')


class ResponseTests(TestCase):

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


@skipUnless(getattr(settings, 'DATACASH_ENABLE_INTEGRATION_TESTS', False), "Currently disabled")
class GatewayIntegrationTests(TestCase):
    """
    There can be problems with DataCash speed limits when running these tests as
    you aren't supposed to perform a transaction with the same card more
    than once every two minutes.
    """

    def setUp(self):
        self.gateway = Gateway(settings.DATACASH_HOST,
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