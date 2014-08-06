from django.test import TestCase
from django.core.urlresolvers import reverse

SUCCESS_RESPONSE = b"""<?xml version="1.0"?>
<RealTimeResponse xmlns="T3MCallback">
    <aggregator_identifier/>
    <merchant_identifier>5567</merchant_identifier>
    <merchant_order_ref>12345</merchant_order_ref>
    <t3m_id>333333333</t3m_id>
    <score>0</score>
    <recommendation>1</recommendation>
    <message_digest></message_digest>
</RealTimeResponse>"""

HOLD_RESPONSE = b"""<?xml version="1.0" encoding="utf-8"?>
<RealTimeCallBack xmlns="T3MCallback">
    <aggregator_identifier/>
    <merchant_identifier>32217</merchant_identifier>
    <merchant_order_ref>100117</merchant_order_ref>
    <t3m_id>1815120370</t3m_id>
    <score>46</score>
    <recommendation>1</recommendation>
    <message_digest>baa7421d73c962ce92220e64526af1a559f26f46</message_digest>
</RealTimeCallBack>"""

RELEASE_RESPONSE = b"""<?xml version="1.0" encoding="utf-8"?>
<RealTimeCallBack xmlns="T3MCallback">
    <aggregator_identifier/>
    <merchant_identifier>32217</merchant_identifier>
    <merchant_order_ref>100117</merchant_order_ref>
    <t3m_id>1815120370</t3m_id>
    <score>46</score>
    <recommendation>0</recommendation>
    <message_digest>baa7421d73c962ce92220e64526af1a559f26f46</message_digest>
</RealTimeCallBack>"""


class TestCallbackView(TestCase):

    def test_success_response(self):
        url = reverse('datacash-3rdman-callback')
        response = self.client.post(url, SUCCESS_RESPONSE, content_type="text/xml")
        self.assertEquals(response.content, b"ok")

    def test_hold_then_release(self):
        url = reverse('datacash-3rdman-callback')
        response = self.client.post(url, HOLD_RESPONSE, content_type="text/xml")
        self.assertEquals(response.content, b"ok")
        response = self.client.post(url, RELEASE_RESPONSE, content_type="text/xml")
        self.assertEquals(response.content, b"ok")

    def test_error_response(self):
        url = reverse('datacash-3rdman-callback')
        response = self.client.post(url, b'<xml>', content_type="text/xml")
        self.assertEquals(response.content, b"error")
