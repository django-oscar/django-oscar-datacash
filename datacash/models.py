import re
from xml.dom.minidom import parseString

from django.db import models

from .the3rdman import signals


def prettify_xml(xml_str):
    xml_str = re.sub(r'\s*\n\s*', '', xml_str)
    ugly = parseString(xml_str).toprettyxml(indent='    ')
    regex = re.compile(r'>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
    return regex.sub('>\g<1></', ugly)


class OrderTransaction(models.Model):

    # Note we don't use a foreign key as the order hasn't been created
    # by the time the transaction takes place
    order_number = models.CharField(max_length=128, db_index=True)

    # The 'method' of the transaction - one of 'auth', 'pre', 'cancel', ...
    method = models.CharField(max_length=12)
    amount = models.DecimalField(decimal_places=2, max_digits=12, blank=True, null=True)
    merchant_reference = models.CharField(max_length=128, blank=True, null=True)

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

    def save(self, *args, **kwargs):
        # Ensure sensitive data isn't saved
        if not self.pk:
            cc_regex = re.compile(r'\d{12}')
            self.request_xml = cc_regex.sub('XXXXXXXXXXXX', self.request_xml)
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
    t3m_id = models.CharField(max_length=128, unique=True)
    score = models.IntegerField()

    RELEASE, HOLD, REJECT, UNDER_INVESTIGATION = 0, 1, 2, 9
    recommendation = models.IntegerField()
    message_digest = models.CharField(max_length=128, blank=True)
    raw_response = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u"<t3m %s (score: %s, recommendation: %s)>" % (
            self.t3m_id, self.score, self.recommendation)

    @classmethod
    def create_from_xml(cls, payload):
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

        doc = parseString(payload)
        response = cls.objects.create(
            aggregator_identifier=tag_text(doc, 'aggregator_identifier'),
            merchant_identifier=tag_text(doc, 'merchant_identifier'),
            merchant_order_ref=tag_text(doc, 'merchant_order_ref'),
            t3m_id=tag_text(doc, 't3m_id'),
            score=tag_text(doc, 'score'),
            recommendation=tag_text(doc, 'recommendation'),
            message_digest=tag_text(doc, 'message_digest'),
            raw_response=payload)

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
        return self.recommendation == self.REJECTED

    @property
    def order_number(self):
        """
        Return the order number from the original transaction.

        This assumes the merchant ref was generated using the datacash.facade
        class
        """
        return self.merchant_order_ref.split("_")[0]
