from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Template filter to lookup a key in a dictionary"""
    if dictionary and key in dictionary:
        return dictionary[key]
    return None
