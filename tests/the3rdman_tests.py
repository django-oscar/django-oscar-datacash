from decimal import Decimal as D

from django.test import TestCase
from oscar_testsupport import factories
from oscar.apps.basket.models import Basket

from datacash import the3rdman


class TestRequestGeneration(TestCase):

    def test_for_smoke(self):
        doc = the3rdman.add_fraud_fields(customer_info={'title': 'mr'})
        print doc.toprettyxml()


class TestBuildingDataDict(TestCase):

    def test_for_smoke(self):
        print the3rdman.build_data_dict(
            request=None, user=None,
            order_number="1234", basket=None)


class TestIntegration(TestCase):

    def test_basket_lines_are_converted_to_xml(self):
        product = factories.create_product(price=D('12.99'))
        basket = Basket()
        basket.add_product(product)
        data = the3rdman.build_data_dict(
            basket=basket)
        doc = the3rdman.add_fraud_fields(**data)
        print doc.toprettyxml()
