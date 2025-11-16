from django import template

register = template.Library()

@register.filter
def sum_attr(iterable, attr):
    return sum(getattr(item, attr, 0) for item in iterable if getattr(item, attr, 0))

@register.filter
def div(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0