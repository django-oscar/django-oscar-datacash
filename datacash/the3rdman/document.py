from xml.dom.minidom import Document, parseString


def create_element(doc, parent, tag, value=None, attributes=None):
    """
    Creates an XML element
    """
    ele = doc.createElement(tag)
    parent.appendChild(ele)
    if value:
        text = doc.createTextNode(str(value))
        ele.appendChild(text)
    if attributes:
        [ele.setAttribute(k, str(v)) for k, v in attributes.items()]
    return ele


def add_fraud_fields(doc, element=None, customer_info=None, delivery_info=None,
                     billing_info=None, account_info=None, order_info=None):
    """
    Submit a transaction to The3rdMan for Batch Fraud processing

    Doesn't support (yet):
        - Previous orders
        - Additional delivery addreses
        - Alternative payments

    See section 2.4.7 of the Developer Guide
    """
    # Build the request XML
    if element is None:
        element = Document()
    envelope = create_element(doc, element, 'The3rdMan')
    add_customer_information(doc, envelope, customer_info)
    add_delivery_address(doc, envelope, delivery_info)
    add_billing_address(doc, envelope, billing_info)
    add_account_information(doc, envelope, account_info)
    add_order_information(doc, envelope, order_info)
    return doc


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
