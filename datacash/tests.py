from decimal import Decimal as D
from xml.dom.minidom import parseString
import datetime
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

SAMPLE_CV2AVS_REQUEST = """<?xml version="1.0" ?>
<Request>
    <Authentication>
        <client>99001381</client>
        <password>hbANDMzErH</password>
    </Authentication>
    <Transaction>
        <CardTxn>
            <method>pre</method>
            <Card>
                <pan>XXXXXXXXXXXX0007</pan>
                <expirydate>02/12</expirydate>
                <Cv2Avs>
                    <street_address1>1
                    house</street_address1>
                    <street_address2/>
                    <street_address3/>
                    <street_address4/>
                    <postcode>n12
                    9et</postcode>
                    <cv2>123</cv2>
                </Cv2Avs>
            </Card>
        </CardTxn>
        <TxnDetails>
            <merchantreference>100024_182223</merchantreference>
            <amount currency="GBP">35.21</amount>
            <capturemethod>ecomm</capturemethod>
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


class MockBillingAddress(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


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

    def test_auth_request_creates_txn_model(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', ccv='345')
        self.facade.authorise('100001', D('123.22'), card)
        txn = OrderTransaction.objects.filter(order_number='100001')[0]
        self.assertEquals('auth', txn.method)
        self.assertEquals(D('123.22'), txn.amount)
        self.assertTrue(len(txn.request_xml) > 0)
        self.assertTrue(len(txn.response_xml) > 0)

    def test_auth_request_with_integer_ccv(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', ccv=345)
        self.facade.authorise('100001', D('123.22'), card)

    def test_pre_request_creates_txn_model(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', ccv='345')
        self.facade.pre_authorise('100001', D('123.22'), card)
        txn = OrderTransaction.objects.filter(order_number='100001')[0]
        self.assertEquals('pre', txn.method)
        self.assertEquals(D('123.22'), txn.amount)
        self.assertTrue(len(txn.request_xml) > 0)
        self.assertTrue(len(txn.response_xml) > 0)

    def test_pre_request_uses_billing_address_fields(self):
        mock = Mock(return_value=SAMPLE_RESPONSE)
        self.facade.gateway._fetch_response_xml = mock
        card = Bankcard('1000350000000007', '10/13', ccv='345')
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
        mock = Mock(return_value=SAMPLE_RESPONSE)
        self.facade.gateway._fetch_response_xml = mock
        card = Bankcard('1000350000000007', '10/13', ccv='345')
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
        mock = Mock(return_value=SAMPLE_RESPONSE)
        self.facade.gateway._fetch_response_xml = mock
        self.facade.refund_transaction('100001', D('123.22'),
                                       txn_reference='12345')
        request_xml = mock.call_args[0][0]
        self.assertTrue('currency' not in request_xml)

    def test_auth_request_returns_datacash_ref(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', ccv='345')
        ref = self.facade.authorise('100001', D('123.22'), card)
        self.assertEquals('3000000088888888', ref)

    def test_auth_request_using_previous_txn_ref(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
        ref = self.facade.authorise('100001', D('123.22'), txn_reference='3000000088888888')
        self.assertEquals('3000000088888888', ref)

    def test_refund_request(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
        card = Bankcard('1000350000000007', '10/13', ccv='345')
        ref = self.facade.refund('100005', D('123.22'), card)
        txn = OrderTransaction.objects.filter(order_number='100005')[0]
        self.assertEquals('refund', txn.method)

    def test_pre_auth_using_history_txn(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
        ref = self.facade.pre_authorise('100001', D('123.22'), txn_reference='3000000088888888')
        self.assertEquals('3000000088888888', ref)

    def test_refund_using_historic_txn(self):
        self.facade.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
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
        card = Bankcard('1000350000000007', '10/13', ccv='345')
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
        card = Bankcard('1000350000000007', '10/13', ccv='345')
        with self.assertRaises(InvalidGatewayRequestError):
            self.facade.pre_authorise('100001', D('123.22'), card)


class TransactionModelTests(TestCase, XmlTestingMixin):

    def test_unicode_method(self):
        txn = OrderTransaction.objects.create(order_number='1000',
                                              method='auth',
                                              datacash_reference='3000000088888888',
                                              merchant_reference='1000001',
                                              amount=D('95.99'),
                                              status=1,
                                              reason='ACCEPTED',
                                              request_xml=SAMPLE_CV2AVS_REQUEST,
                                              response_xml=SAMPLE_RESPONSE)
        self.assertTrue('Datacash txn ' in  str(txn))

    def test_ccv_numbers_are_not_saved_in_xml(self):
        txn = OrderTransaction.objects.create(order_number='1000',
                                              method='auth',
                                              datacash_reference='3000000088888888',
                                              merchant_reference='1000001',
                                              amount=D('95.99'),
                                              status=1,
                                              reason='ACCEPTED',
                                              request_xml=SAMPLE_CV2AVS_REQUEST,
                                              response_xml=SAMPLE_RESPONSE)
        self.assertXmlElementEquals(txn.request_xml, 'XXX',
                                    'Request.Transaction.CardTxn.Card.Cv2Avs.cv2')
    
    def test_cc_numbers_are_not_saved_in_xml(self):
        txn = OrderTransaction.objects.create(order_number='1000',
                                              method='auth',
                                              datacash_reference='3000000088888888',
                                              merchant_reference='1000001',
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

    def test_capture_method_defaults_to_ecomm(self):
        response = self.gateway_auth()
        self.assertXmlElementEquals(response.request_xml, 'ecomm', 'Request.Transaction.TxnDetails.capturemethod')


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
        self.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
        response = self.gateway.auth(amount=D('1000.00'),
                                     currency='GBP',
                                     merchant_reference='TEST_132473839018',
                                     previous_txn_reference='4500203021916406')
        self.assertXmlElementEquals(response.request_xml, 
            '4500203021916406', 'Request.Transaction.CardTxn.card_details')

    def test_request_xml_for_pre_using_previous_transaction_ref(self):
        self.gateway._fetch_response_xml = Mock(return_value=SAMPLE_RESPONSE)
        response = self.gateway.pre(amount=D('1000.00'),
                                    currency='GBP',
                                    merchant_reference='TEST_132473839018',
                                    previous_txn_reference='4500203021916406')
        self.assertXmlElementEquals(response.request_xml, 
            '4500203021916406', 'Request.Transaction.CardTxn.card_details')


class GatewayErrorTests(TestCase):

    def test_exception_raised_with_bad_host(self):
        with self.assertRaises(RuntimeError):
            Gateway('http://test.datacash.com', client='', password='')


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


class MiscTests(TestCase):

    def test_constant_exist(self):
        from datacash import DATACASH
        self.assertEqual('Datacash', DATACASH)


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