from django import template
from django.urls import reverse

register = template.Library()


@register.filter
def get_attr(obj, attr):
    """Obtiene un atributo o método sin argumentos del objeto."""
    try:
        value = getattr(obj, attr)
        if callable(value):
            return value()
        return value
    except (AttributeError, TypeError):
        return ''


def _reverse_or_hash(namespace, name, args=None):
    full = f'{namespace}:{name}'
    try:
        return reverse(full, args=args or [])
    except Exception:
        return '#'


@register.filter
def detail_url(obj, list_url_name):
    """
    Devuelve la URL de detalle basada en el list_url_name.
    'fondos_list' → 'fondos:detail'
    """
    app = obj._meta.app_label
    base = list_url_name.replace('_list', '')
    return _reverse_or_hash(app, f'{base}_detail', args=[obj.pk])


@register.filter
def update_url(obj, list_url_name):
    app = obj._meta.app_label
    base = list_url_name.replace('_list', '')
    return _reverse_or_hash(app, f'{base}_update', args=[obj.pk])


@register.filter
def delete_url(obj, list_url_name):
    app = obj._meta.app_label
    base = list_url_name.replace('_list', '')
    return _reverse_or_hash(app, f'{base}_delete', args=[obj.pk])


@register.filter
def anular_url(obj, list_url_name):
    """URL para anular (POST) un modelo financiero."""
    app = obj._meta.app_label
    base = list_url_name.replace('_list', '')
    return _reverse_or_hash(app, f'{base}_anular', args=[obj.pk])