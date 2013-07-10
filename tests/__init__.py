from xml.dom.minidom import parseString

from django.test import TestCase


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


class MiscTests(TestCase):
    """
    Miscellaneous stuff:
    """

    def test_datacash_constant_exist(self):
        from datacash import DATACASH
        self.assertEqual('Datacash', DATACASH)
