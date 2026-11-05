from django import template
from django.conf import settings
from django.templatetags.static import static
from browse.data_integrity import metabolite_image_path

register = template.Library()


@register.simple_tag
def metabolite_image(identifier, cid, folder):
    path = metabolite_image_path(settings.BASE_DIR, identifier, cid, folder)
    return static(path) if path else ''
