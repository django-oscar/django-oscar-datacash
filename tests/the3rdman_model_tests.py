from django.test import TestCase

from datacash import models

XML_RESPONSE = """<?xml version="1.0"?>
<RealTimeResponse xmlns="T3MCallback">
    <aggregator_identifier/>
    <merchant_identifier>5567</merchant_identifier>
    <merchant_order_ref>12345</merchant_order_ref>
    <t3m_id>333333333</t3m_id>
    <score>%(score)s</score>
    <recommendation>%(recommendation)s</recommendation>
    <message_digest></message_digest>
</RealTimeResponse>"""

QUERY_RESPONSE = "aggregator_identifier=&merchant_identifier=32195&merchant_order_ref=100032&t3m_id=1701673332&score=114&recommendation=2&message_digest=87d81ea49035fe2f8d59ceea3f16b1f43744701c"


def stub_response(score=0, recommendation=0):
    return XML_RESPONSE % {
        'score': score,
        'recommendation': recommendation}


class TestFraudResponseModel(TestCase):

    def test_recognises_release_response(self):
        xml = stub_response(recommendation=0)
        response = models.FraudResponse.create_from_xml(xml)
        self.assertTrue(response.released)

    def test_recognises_on_hold_response(self):
        xml = stub_response(recommendation=1)
        response = models.FraudResponse.create_from_xml(xml)
        self.assertTrue(response.on_hold)

    def test_recognises_reject_response(self):
        xml = stub_response(recommendation=2)
        response = models.FraudResponse.create_from_xml(xml)
        self.assertTrue(response.rejected)


class TestFormURLEncodedResponse(TestCase):

    def test_for_smoke(self):
        response = models.FraudResponse.create_from_querystring(QUERY_RESPONSE)
        self.assertTrue(response.rejected)
