"""Mixin de permisos por rol.

Los permisos se manejan con grupos de Django (`auth.Group`):
- ADMIN: todos los permisos (incluye gestión de usuarios)
- OPERADOR: crear, editar, anular gastos, asignaciones, etc.
- CONSULTOR: solo lectura

Los superusuarios (`is_superuser=True`) tienen acceso completo
sin importar el grupo.

Pendiente de validación con cliente:
- Matriz fina de permisos por modelo y acción.
- Permisos por obra (un usuario solo ve "sus" obras).
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class SGCOStaffRequiredMixin(LoginRequiredMixin):
    """Requiere usuario autenticado y staff=True (puede acceder al admin)."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def es_operador_o_admin(user) -> bool:
    """True si el usuario puede crear/editar registros."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False
    # Operador/Admin: pertenece a grupos permitidos
    grupos = user.groups.values_list('name', flat=True)
    return any(g in ('ADMIN', 'OPERADOR') for g in grupos)
