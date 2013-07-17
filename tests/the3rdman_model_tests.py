from django.test import TestCase

from datacash import models

RESPONSE = """<?xml version="1.0"?>
<RealTimeResponse xmlns="T3MCallback">
    <aggregator_identifier/>
    <merchant_identifier>5567</merchant_identifier>
    <merchant_order_ref>12345</merchant_order_ref>
    <t3m_id>333333333</t3m_id>
    <score>%(score)s</score>
    <recommendation>%(recommendation)s</recommendation>
    <message_digest></message_digest>
</RealTimeResponse>"""

def stub_response(score=0, recommendation=0):
    return RESPONSE % {
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
