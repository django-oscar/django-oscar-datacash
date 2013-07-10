from django.test import TestCase
from django.core.urlresolvers import reverse

SUCCESS_RESPONSE = """<?xml version="1.0"?>
<RealTimeResponse xmlns="T3MCallback">
    <aggregator_identifier/>
    <merchant_identifier>5567</merchant_identifier>
    <merchant_order_ref>12345</merchant_order_ref>
    <t3m_id>333333333</t3m_id>
    <score>0</score>
    <recommendation>1</recommendation>
    <message_digest></message_digest>
</RealTimeResponse>"""


class TestCallbackView(TestCase):

    def test_success_response(self):
        url = reverse('datacash-3rdman-callback')
        response = self.client.post(url, SUCCESS_RESPONSE, content_type="text/xml")
        self.assertEquals(response.content, "ok")

    def test_error_response(self):
        url = reverse('datacash-3rdman-callback')
        response = self.client.post(url, '<xml>', content_type="text/xml")
        self.assertEquals(response.content, "error")
