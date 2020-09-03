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


@register.filter("snapsummary")
def return_item(input):
    try:
        return f"{input[0]}...{input[-1]}"
    except:  # noqa
        return None
