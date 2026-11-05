from django import template

register = template.Library()

# @register.filter
# def split(value, arg):
#     return value.split(arg)

@register.filter
def split(value, arg):
    if value is None:
        return []  # or return an empty string, depending on your requirement
    return value.split(arg)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)



