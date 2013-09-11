from django.db.models import get_model

Order = get_model('order', 'Order')


def build_data_dict(request=None, user=None, email=None, order_number=None,
                    basket=None, shipping_address=None, billing_address=None):
    """
    Build a dict of the fields that can be passed as 3rdMan data
    """
    if request and user is None:
        user = request.user
    if request and basket is None:
        basket = request.basket
    data = {
        'customer_info': build_customer_info(
            request, user, email, order_number, shipping_address),
        'delivery_info': build_delivery_info(
            shipping_address),
        'billing_info': build_billing_info(
            billing_address),
        'account_info': {},  # Not implemented for now
        'order_info': build_order_info(basket),
    }
    return data


def build_customer_info(request, user, email, order_number, shipping_address):
    # We only use fields denoted 'R' (for Retail)
    payload = {}

    if user and user.is_authenticated():
        payload['customer_reference'] = user.id
        payload['email'] = user.email
        payload['forename'] = user.first_name
        payload['surname'] = user.last_name

    if email:
        payload['email'] = email

    if shipping_address:
        payload['delivery_forename'] = shipping_address.first_name
        payload['delivery_phone_number'] = shipping_address.phone_number
        payload['delivery_surname'] = shipping_address.last_name
        payload['delivery_title'] = shipping_address.title

    if request and 'REMOTE_ADDR' in request.META:
        payload['ip_address'] = request.META['REMOTE_ADDR']
    # We let HTTP_X_FORWARDED_FOR take precedence if it exists
    if request and 'HTTP_X_FORWARDED_FOR' in request.META:
        payload['ip_address'] = request.META['HTTP_X_FORWARDED_FOR']

    if order_number:
        payload['order_number'] = order_number

    payload['sales_channel'] = 3  # Internet

    return payload


def build_delivery_info(shipping_address):
    payload = {}
    if not shipping_address:
        return payload
    payload['street_address_1'] = shipping_address.line1
    payload['street_address_2'] = shipping_address.line2
    payload['city'] = shipping_address.line4
    payload['county'] = shipping_address.state
    payload['postcode'] = shipping_address.postcode
    payload['country'] = u"%.03d" % shipping_address.country.iso_3166_1_numeric
    return payload


def build_billing_info(billing_address):
    payload = {}
    if not billing_address:
        return payload
    payload['street_address_1'] = billing_address.line1
    payload['street_address_2'] = billing_address.line2
    payload['city'] = billing_address.line4
    payload['county'] = billing_address.state
    payload['postcode'] = billing_address.postcode
    return payload


def build_order_info(basket):
    if not basket:
        return {}
    payload = {'products': []}
    for line in basket.all_lines():
        product = line.product
        stockrecord = product.stockrecord
        datum = {
            'code': product.upc,
            'price': stockrecord.price_incl_tax,
            'prod_description': product.description,
            'prod_id': product.id,
            'quantity': line.quantity,
        }
        payload['products'].append(datum)
    return payload
