import django.dispatch

response_received = django.dispatch.Signal(providing_args=["response"])
