from decimal import Decimal as D

from django.test import TestCase
from oscar_testsupport import factories
from oscar.apps.basket.models import Basket

from datacash import the3rdman, models
from . import XmlTestingMixin


class TestRequestGeneration(TestCase, XmlTestingMixin):

    def test_for_smoke(self):
        doc = the3rdman.add_fraud_fields(customer_info={'title': 'mr'})
        xml = doc.toxml()
        self.assertXmlElementEquals(xml, 'mr',
                                    'The3rdMan.CustomerInformation.title')


class TestBuildingDataDict(TestCase):

    def test_includes_sales_channel(self):
        data = the3rdman.build_data_dict(
            request=None, user=None,
            order_number="1234", basket=None)
        self.assertEquals(3, data['customer_info']['sales_channel'])


class TestIntegration(TestCase, XmlTestingMixin):

    def test_basket_lines_are_converted_to_xml(self):
        product = factories.create_product(price=D('12.99'))
        basket = Basket()

        # Nasty hack to make test suite work with both Oscar 0.5 and 0.6
        try:
            from oscar.apps.partner import strategy
        except ImportError:
            pass
        else:
            basket.strategy = strategy.Default()

        basket.add_product(product)
        data = the3rdman.build_data_dict(
            basket=basket)
        doc = the3rdman.add_fraud_fields(**data)
        xml = doc.toxml()
        self.assertXmlElementEquals(xml, '3',
                                    'The3rdMan.CustomerInformation.sales_channel')
