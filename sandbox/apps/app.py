from oscar.app import Shop
from apps.checkout.app import application  as checkout_app


class DatacashShop(Shop):
    # Specify a local checkout app where we override the payment details view
    checkout_app = checkout_app


shop = DatacashShop()
