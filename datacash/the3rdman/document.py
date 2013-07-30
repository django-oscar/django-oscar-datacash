from datacash.xmlutils import create_element
from xml.dom.minidom import Document, parseString


def add_fraud_fields(doc=None, element=None, customer_info=None, delivery_info=None,
                     billing_info=None, account_info=None, order_info=None,
                     **kwargs):
    """
    Submit a transaction to The3rdMan for Batch Fraud processing

    Doesn't support (yet):
        - Previous orders
        - Additional delivery addreses
        - Alternative payments

    See section 2.4.7 of the Developer Guide
    """
    # Build the request XML
    if doc is None:
        doc = Document()
    if element is None:
        element = doc

    envelope = create_element(
        doc, element, 'The3rdMan', attributes={'type': 'realtime'})

    if 'callback_url' in kwargs:
        callback_format = kwargs.get('callback_format', 'XML')
        callback_url = kwargs['callback_url']
        add_realtime_information(doc, envelope, callback_format, callback_url)

    add_customer_information(doc, envelope, customer_info)
    add_delivery_address(doc, envelope, delivery_info)
    add_billing_address(doc, envelope, billing_info)
    add_account_information(doc, envelope, account_info)
    add_order_information(doc, envelope, order_info)
    return doc


def add_realtime_information(doc, ele, format, url):
    rt_ele = create_element(doc, ele, 'Realtime')
    create_element(doc, rt_ele, 'real_time_callback_format', format)
    create_element(doc, rt_ele, 'real_time_callback', url)


def add_xml_fields(doc, parent, fields, values):
    for field in fields:
        if field in values and values[field] is not None:
            create_element(doc, parent, field, values[field])


def intersects(fields, values):
    """
    Test if there are any fields in the values
    """
    overlap = set(fields).intersection(values.keys())
    return len(overlap) > 0


def add_customer_information(doc, envelope, customer_info):
    if not customer_info:
        return
    cust_ele = create_element(doc, envelope, 'CustomerInformation')
    cust_fields = (
        'alt_telephone', 'customer_dob', 'customer_reference',
        'delivery_forename', 'delivery_phone_number', 'delivery_surname',
        'delivery_title', 'driving_license_number', 'email',
        'first_purchase_date', 'forename', 'introduced_by', 'ip_address',
        'order_number', 'sales_channel', 'surname', 'telephone',
        'time_zone', 'title')
    add_xml_fields(doc, cust_ele, cust_fields, customer_info)


def add_delivery_address(doc, envelope, delivery_info):
    if not delivery_info:
        return
    delivery_ele = create_element(doc, envelope, 'DeliveryAddress')
    delivery_fields = (
        'street_address_1', 'street_address_2', 'city',
        'county', 'postcode', 'country')
    add_xml_fields(doc, delivery_ele, delivery_fields, delivery_info)


def add_billing_address(doc, envelope, billing_info):
    if not billing_info:
        return
    billing_ele = create_element(doc, envelope, 'BillingAddress')
    billing_fields = (
        'street_address_1', 'street_address_2', 'city', 'county',
        'postcode', 'country')
    add_xml_fields(doc, billing_ele, billing_fields, billing_info)


def add_account_information(doc, envelope, account_info):
    if not account_info:
        return
    account_ele = create_element(doc, envelope, 'AccountInformation')

    # Bank information
    bank_fields = (
        'account_number', 'bank_address', 'bank_country', 'bank_name',
        'customer_name', 'sort_code')
    if intersects(bank_fields, account_info):
        bank_ele = create_element(doc, account_ele, 'BankInformation')
        add_xml_fields(doc, bank_ele, bank_fields, account_info)

    purchase_fields = ('avg', 'max', 'min')
    if intersects(purchase_fields, account_info):
        purchase_ele = create_element(doc, account_ele, 'PurchaseInformation')
        add_xml_fields(doc, purchase_ele, purchase_fields, account_info)


def add_order_information(doc, envelope, order_info):
    if not order_info or 'products' not in order_info:
        return
    order_ele = create_element(doc, envelope, 'OrderInformation')
    products_ele = create_element(
        doc, order_ele, 'Products',
        attributes={'count': len(order_info['products'])})
    product_fields = ('code', 'prod_id', 'quantity', 'price', 'prod_category',
                      'prod_description')
    for product_info in order_info['products']:
        product_ele = create_element(doc, products_ele, 'Product')
        add_xml_fields(doc, product_ele, product_fields, product_info)
