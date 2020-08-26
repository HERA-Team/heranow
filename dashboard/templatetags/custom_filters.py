from django.template import Library
import json

register = Library()


@register.filter("listify")
def listify(data):
    """Ensure input data is a list."""
    if not isinstance(data, list):
        data = [data]
    return data


@register.filter("islist")
def islist(data):
    """Check if input data is a list."""
    return isinstance(data, list)
