import re
from xml.dom.minidom import parseString
import urlparse

from django.db import models
from django.conf import settings

from .the3rdman import signals


def prettify_xml(xml_str):
    xml_str = re.sub(r'\s*\n\s*', '', xml_str)
    ugly = parseString(xml_str.encode('utf8')).toprettyxml(indent='    ')
    regex = re.compile(r'>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
    return regex.sub('>\g<1></', ugly)


class OrderTransaction(models.Model):

    # Note we don't use a foreign key as the order hasn't been created
    # by the time the transaction takes place
    order_number = models.CharField(max_length=128, db_index=True)

    # The 'method' of the transaction - one of 'auth', 'pre', 'cancel', ...
    method = models.CharField(max_length=12)
    amount = models.DecimalField(
        decimal_places=2, max_digits=12, blank=True, null=True)
    currency = models.CharField(
        max_length=12, default=settings.DATACASH_CURRENCY)
    merchant_reference = models.CharField(
        max_length=128, blank=True, null=True)

    # Response fields
    datacash_reference = models.CharField(max_length=128, blank=True, null=True)
    auth_code = models.CharField(max_length=128, blank=True, null=True)
    status = models.PositiveIntegerField()
    reason = models.CharField(max_length=255)

    # Store full XML for debugging purposes
    request_xml = models.TextField()
    response_xml = models.TextField()

    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-date_created',)

    def _replace_credit_card_number(self, matchobj):
        """ Credit card number can be from 13 to 19 digits long. Shown only
        last 4 of them and replace others with 'X' still keeping
        number of digits """
        return "<%(element)s>%(hidden)s%(last4)s</%(element)s>" % {
            'element': matchobj.group(1),
            'hidden': "X" * len(matchobj.group(2)),
            'last4': matchobj.group(3),
        }

    def save(self, *args, **kwargs):
        # Ensure sensitive data isn't saved
        if not self.pk:
            cc_regex = re.compile(r'<(pan|alt_pan)>(\d+)(\d{4})</\1>')
            self.request_xml = cc_regex.sub(self._replace_credit_card_number,
                                            self.request_xml)
            ccv_regex = re.compile(r'<cv2>\d+</cv2>')
            self.request_xml = ccv_regex.sub('<cv2>XXX</cv2>', self.request_xml)
            pw_regex = re.compile(r'<password>.*</password>')
            self.request_xml = pw_regex.sub('<password>XXX</password>', self.request_xml)
        super(OrderTransaction, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'%s txn for order %s - ref: %s, status: %s' % (
            self.method.upper(),
            self.order_number,
            self.datacash_reference,
            self.status)

    @property
    def pretty_request_xml(self):
        return prettify_xml(self.request_xml)

    @property
    def pretty_response_xml(self):
        return prettify_xml(self.response_xml)

    @property
    def accepted(self):
        return self.status == 1

    @property
    def declined(self):
        return self.status == 7


class FraudResponse(models.Model):
    aggregator_identifier = models.CharField(max_length=15, blank=True)
    merchant_identifier = models.CharField(max_length=15)
    merchant_order_ref = models.CharField(max_length=250, db_index=True)
    t3m_id = models.CharField(max_length=128, db_index=True)
    score = models.IntegerField()

    RELEASE, HOLD, REJECT, UNDER_INVESTIGATION = 0, 1, 2, 9
    recommendation = models.IntegerField()
    message_digest = models.CharField(max_length=128, blank=True)
    raw_response = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u"t3m ID %s (score: %s, recommendation: %s)" % (
            self.t3m_id, self.score, self.recommendation)

    class Meta:
        ordering = ('-date_created',)

    @classmethod
    def create_from_xml(cls, xml_string):
        """
        Create a fraud response instance from an XML payload
        """
        # Helper function for text extraction
        def tag_text(doc, tag_name):
            try:
                ele = doc.getElementsByTagName(tag_name)[0]
            except IndexError:
                return ''
            if ele.firstChild:
                return ele.firstChild.data
            return ''

        doc = parseString(xml_string)
        return cls.create_from_payload(xml_string, doc, tag_text)

    @classmethod
    def create_from_querystring(cls, query):
        """
        Create a fraud response instance from a querystring payload
        """
        def extract(data, key):
            return data.get(key, [""])[0]

        data = urlparse.parse_qs(query)
        return cls.create_from_payload(query, data, extract)

    @classmethod
    def create_from_payload(cls, raw, payload, extract_fn):
        response = cls.objects.create(
            aggregator_identifier=extract_fn(payload, 'aggregator_identifier'),
            merchant_identifier=extract_fn(payload, 'merchant_identifier'),
            merchant_order_ref=extract_fn(payload, 'merchant_order_ref'),
            t3m_id=extract_fn(payload, 't3m_id'),
            score=int(extract_fn(payload, 'score')),
            recommendation=int(extract_fn(payload, 'recommendation')),
            message_digest=extract_fn(payload, 'message_digest'),
            raw_response=raw)

        # Raise signal so other processes can update orders based on this fraud
        # response.
        signals.response_received.send_robust(sender=cls, response=response)

        return response

    @property
    def on_hold(self):
        return self.recommendation == self.HOLD

    @property
    def released(self):
        return self.recommendation == self.RELEASE

    @property
    def rejected(self):
        return self.recommendation == self.REJECT

    @property
    def order_number(self):
        """
        Return the order number from the original transaction.

        This assumes the merchant ref was generated using the datacash.facade
        class
        """
        return self.merchant_order_ref.split("_")[0]

    @property
    def recommendation_text(self):
        mapping = {
            self.RELEASE: "Released",
            self.HOLD: "On hold",
            self.REJECT: "Rejected",
            self.UNDER_INVESTIGATION: "Under investigation",
        }
        return mapping.get(self.recommendation, "Unknown")

    @property
    def gatekeeper_url(self):
        """
        Return the transaction detail URL on the Gatekeeper site
        """
        is_live = 'mars' in settings.DATACASH_HOST
        host = 'cnpanalyst.com' if is_live else 'test.cnpanalyst.com'
        return 'https://%s/TransactionDetails.aspx?TID=%s' % (
            host, self.t3m_id)
