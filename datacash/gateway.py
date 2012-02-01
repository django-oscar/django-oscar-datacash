import datetime
from xml.dom.minidom import Document, parseString
import httplib
import urllib
import re
from collections import Mapping

from django.conf import settings
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.core.mail import mail_admins

from oscar.apps.payment.exceptions import TransactionDeclined, GatewayError, InvalidGatewayRequestError

from datacash.models import OrderTransaction

# Methods
AUTH = 'auth'
PRE = 'pre'
REFUND = 'refund'
ERP = 'erp'
CANCEL = 'cancel'
FULFILL = 'fulfill'
TXN_REFUND = 'txn_refund'

# Status codes
ACCEPTED, DECLINED, INVALID_CREDENTIALS = '1', '7', '10'


class Response(object):
    """
    Encapsulate a Datacash response
    """

    def __init__(self, request_xml, response_xml):
        self.request_xml = request_xml
        self.response_xml = response_xml
        self.data = self._extract_data(response_xml)

    def _extract_data(self, response_xml):
        doc = parseString(response_xml)
        data = {'status': self._get_element_text(doc, 'status'),
                'datacash_reference': self._get_element_text(doc, 'datacash_reference'),
                'merchant_reference': self._get_element_text(doc, 'merchantreference'),
                'reason': self._get_element_text(doc, 'reason'),
                'card_scheme': self._get_element_text(doc, 'card_scheme'),
                'country': self._get_element_text(doc, 'country'),
                'auth_code': self._get_element_text(doc, 'authcode')
                }
        return data

    def _get_element_text(self, doc, tag):
        try:
            ele = doc.getElementsByTagName(tag)[0]
        except IndexError:
            return None
        return ele.firstChild.data

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.response_xml

    @property
    def status(self):
        if 'status' in self.data and self.data['status'] is not None:
            return int(self.data['status'])
        return None
 
    def is_successful(self):
        return self.data.get('status', None) == ACCEPTED

    def is_declined(self):
        return self.data.get('status', None) == DECLINED


class Gateway(object):

    def __init__(self, host, client, password, cv2avs=False, capturemethod='ecomm'):
        if host.startswith('http'):
            raise RuntimeError("DATACASH_HOST should not include http")
        self._host = host
        self._client = client
        self._password = password
        self._cv2avs = cv2avs
        self._capturemethod = capturemethod

    def _fetch_response_xml(self, request_xml):
        # Need to fill in HTTP request here
        conn = httplib.HTTPSConnection(self._host, 443, timeout=30)
        headers = {"Content-type": "application/xml",
                   "Accept": ""}
        conn.request("POST", "/Transaction", request_xml, headers)
        response = conn.getresponse()
        response_xml = response.read()
        if response.status != httplib.OK:
            raise GatewayError("Unable to communicate with payment gateway (code: %s, response: %s)" % (response.status, response_xml))
        conn.close()
        return response_xml

    def _build_request_xml(self, method_name, **kwargs):
        """
        Builds the XML for a transaction
        """
        doc = Document()
        req = self._create_element(doc, doc, 'Request')
        
        # Authentication
        auth = self._create_element(doc, req, 'Authentication')
        self._create_element(doc, auth, 'client', self._client)
        self._create_element(doc, auth, 'password', self._password)
            
        # Transaction    
        txn = self._create_element(doc, req, 'Transaction') 
        
        # CardTxn
        if 'card_number' in kwargs or 'previous_txn_reference' in kwargs:
            card_txn = self._create_element(doc, txn, 'CardTxn')
            self._create_element(doc, card_txn, 'method', method_name)
            
            if 'card_number' in kwargs:
                card = self._create_element(doc, card_txn, 'Card')
                self._create_element(doc, card, 'pan', kwargs['card_number'])
                self._create_element(doc, card, 'expirydate', kwargs['expiry_date'])
                
                if 'start_date' in kwargs:
                    self._create_element(doc, card, 'startdate', kwargs['start_date'])
                if 'issue_number' in kwargs:
                    self._create_element(doc, card, 'issuenumber', kwargs['issue_number'])
                if 'auth_code' in kwargs:
                    self._create_element(doc, card, 'authcode', kwargs['auth_code'])
                if self._cv2avs:
                    self._add_cv2avs_elements(doc, card, kwargs) 
                
            elif 'previous_txn_reference' in kwargs:
                self._create_element(doc, card_txn, 'card_details', kwargs['previous_txn_reference'],
                                     attributes={'type': 'preregistered'})
            
        
        # HistoricTxn
        if 'txn_reference' in kwargs:
            historic_txn = self._create_element(doc, txn, 'HistoricTxn')
            self._create_element(doc, historic_txn, 'reference', kwargs['txn_reference'])
            self._create_element(doc, historic_txn, 'method', method_name)
            if 'auth_code' in kwargs:
                self._create_element(doc, historic_txn, 'authcode', kwargs['auth_code'])
        
        # TxnDetails
        txn_details = self._create_element(doc, txn, 'TxnDetails')
        if 'merchant_reference' in kwargs:
            self._create_element(doc, txn_details, 'merchantreference', kwargs['merchant_reference'])
        if 'amount' in kwargs:
            self._create_element(doc, txn_details, 'amount', str(kwargs['amount']), {'currency': kwargs['currency']})
        self._create_element(doc, txn_details, 'capturemethod', self._capturemethod)
        
        return doc.toxml()
        
    def _do_request(self, method, **kwargs):
        request_xml = self._build_request_xml(method, **kwargs)
        response_xml = self._fetch_response_xml(request_xml)
        return Response(request_xml, response_xml)

    def _add_cv2avs_elements(self, doc, card, kwargs):
        """
        Add CV2AVS anti-fraud elements.  Extended policy isn't 
        handled yet.
        """
        cv2avs = self._create_element(doc, card, 'Cv2Avs')
        for n in range(1, 5):
            key = 'address_line%d' % n
            if key in kwargs:
                self._create_element(doc, cv2avs, 'street_address%n' % n, kwargs[key])
        if 'postcode' in kwargs:
            self._create_element(doc, cv2avs, 'postcode', kwargs['postcode'])
        if 'ccv' in kwargs:
            self._create_element(doc, cv2avs, 'cv2', kwargs['ccv'])

    def _create_element(self, doc, parent, tag, value=None, attributes=None):
        """
        Creates an XML element
        """
        ele = doc.createElement(tag)
        parent.appendChild(ele)
        if value:
            text = doc.createTextNode(str(value))
            ele.appendChild(text)
        if attributes:
            [ele.setAttribute(k, v) for k,v in attributes.items()]
        return ele

    def _check_kwargs(self, kwargs, required_keys):
        for key in required_keys:
            if key not in kwargs:
                raise ValueError('You must provide a "%s" argument' % key)
        for key in kwargs:
            value = kwargs[key]
            if key in ('expiry_date', 'start_date') and not re.match(r'^\d{2}/\d{2}$', value):
                raise ValueError("%s not in format dd/yy" % key)
            if key == 'issue_number' and not re.match(r'^\d{1,2}$', kwargs[key]):
                raise ValueError("Issue number must be one or two digits (passed value: %s)" % value)
            if key == 'currency' and not re.match(r'^[A-Z]{3}$', kwargs[key]):
                raise ValueError("Currency code must be a 3 character ISO 4217 code")
            if key == 'merchant_reference' and not (6 <= len(value) <= 32):
                raise ValueError("Merchant reference must be between 6 and 32 characters")

    # ===
    # API
    # ===

    # "Initial" transaction types    

    def auth(self, **kwargs):
        """
        Performs an 'auth' request, which is to debit the money immediately
        as a one-off transaction.
        
        Note that currency should be ISO 4217 Alphabetic format.
        """ 
        self._check_kwargs(kwargs, ['amount', 'currency', 'merchant_reference'])
        return self._do_request(AUTH, **kwargs)
        
    def pre(self, **kwargs):
        """
        Performs an 'pre' request, which is to ring-fence the requested money
        so it can be fulfilled at a later time.
        """ 
        self._check_kwargs(kwargs, ['amount', 'currency', 'merchant_reference'])
        return self._do_request(PRE, **kwargs)

    def refund(self, **kwargs):
        """
        Refund against a card
        """
        self._check_kwargs(kwargs, ['amount', 'currency', 'merchant_reference'])
        return self._do_request(REFUND, **kwargs)
        
    def erp(self, **kwargs):
        self._check_kwargs(kwargs, ['amount', 'currency', 'merchant_reference'])
        return self._do_request(ERP, **kwargs)
        
    # "Historic" transaction types    
        
    def cancel(self, txn_reference): 
        """
        Cancel an AUTH or PRE transaction. 

        AUTH txns can only be cancelled before the end of the day when they
        are settled.
        """
        return self._do_request(CANCEL, txn_reference=txn_reference)
    
    def fulfill(self, **kwargs):
        """
        Settle a previous PRE transaction.  The actual settlement will take place
        the next working day.
        """
        self._check_kwargs(kwargs, ['amount', 'currency', 'txn_reference', 'auth_code'])
        return self._do_request(FULFILL, **kwargs)
    
    def txn_refund(self, **kwargs):
        """
        Refund against a specific transaction
        """
        self._check_kwargs(kwargs, ['amount', 'currency', 'txn_reference'])
        return self._do_request(TXN_REFUND, **kwargs)
