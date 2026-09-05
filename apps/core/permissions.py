"""Mixin de permisos por rol (spec v1.2, problema 13).

Reglas mínimas (separación por defecto):
- REGISTRAR: crear nuevos registros
- EDITAR: modificar registros existentes
- ANULAR: cambiar estado a ANULADO
- APROBAR: cambiar estado a APROBADO
- CONSULTAR: solo lectura

Los superusuarios tienen acceso completo.

Un usuario autenticado sin permisos explícitos puede consultar pero
no modificar.

Los permisos se gestionan con grupos de Django:
- ADMIN: todos los permisos
- OPERADOR: REGISTRAR + EDITAR + ANULAR
- SUPERVISOR: REGISTRAR + EDITAR + ANULAR + APROBAR
- CONSULTOR: solo CONSULTAR

Pendiente de validación con cliente:
- Matriz fina de permisos por modelo y acción
- Permisos por obra
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class SGCOStaffRequiredMixin(LoginRequiredMixin):
    """Requiere usuario autenticado y staff=True."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class SGCOActionRequiredMixin:
    """Mixin para vistas que requieren una acción específica (REGISTRAR, EDITAR, etc.).

    Se usa junto con LoginRequiredMixin. El atributo `action_required`
    debe ser uno de los códigos SGCO: REGISTRAR, EDITAR, ANULAR, APROBAR.
    """
    action_required = 'CONSULTAR'  # valor por defecto

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()  # type: ignore
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)  # type: ignore

        # Verificar permiso por nombre (Django permission)
        app_label = 'finanzas'  # permisos se asignan por app
        if not request.user.has_perm(f'{app_label}.sgco_{self.action_required.lower()}'):
            raise PermissionDenied(
                f'Requiere permiso {self.action_required}'
            )
        return super().dispatch(request, *args, **kwargs)  # type: ignore


def es_operador_o_admin(user) -> bool:
    """True si el usuario puede crear/editar registros."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False
    grupos = user.groups.values_list('name', flat=True)
    return any(g in ('ADMIN', 'OPERADOR', 'SUPERVISOR') for g in grupos)


def usuario_puede_aprobar(user) -> bool:
    """True si el usuario puede cambiar estado a APROBADO."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    grupos = user.groups.values_list('name', flat=True)
    return any(g in ('ADMIN', 'SUPERVISOR') for g in grupos)


def usuario_puede_anular(user) -> bool:
    """True si el usuario puede cambiar estado a ANULADO."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    grupos = user.groups.values_list('name', flat=True)
    return any(g in ('ADMIN', 'OPERADOR', 'SUPERVISOR') for g in grupos)
