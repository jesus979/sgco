"""Tags para resaltar la ruta activa en el sidebar."""
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def is_active(context, app_name: str, url_name: str = None) -> bool:
    """Devuelve True si la URL actual pertenece a app_name (y opcionalmente url_name).

    Uso:
        {% is_active 'obras' 'list' as activo %}
        <a class="{% if activo %}bg-primary-50{% endif %}">...</a>
    """
    request = context.get('request')
    if not request:
        return False
    match = getattr(request, 'resolver_match', None)
    if not match:
        return False
    if match.app_name != app_name:
        return False
    if url_name is None:
        return True
    return match.url_name == url_name


@register.simple_tag(takes_context=True)
def is_active_group(context, app_names) -> bool:
    """True si la URL actual está en alguno de los app_names dados.

    app_names puede ser string con coma-separados o lista.
    """
    request = context.get('request')
    if not request:
        return False
    match = getattr(request, 'resolver_match', None)
    if not match:
        return False
    if isinstance(app_names, str):
        app_names = [n.strip() for n in app_names.split(',') if n.strip()]
    return match.app_name in app_names


@register.simple_tag(takes_context=True)
def current_app(context) -> str:
    """Devuelve el app_name de la URL actual (vacío si no hay match)."""
    request = context.get('request')
    if not request:
        return ''
    match = getattr(request, 'resolver_match', None)
    if not match:
        return ''
    return match.app_name or ''