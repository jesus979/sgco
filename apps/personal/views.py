"""Vistas CRUD de Personal (Empleado, Nomina, NominaDetalle)."""
from decimal import Decimal
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, View,
)
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Count

from apps.obras.models import Obra
from apps.core.permissions import SGCOStaffRequiredMixin
from apps.finanzas.services import anular_gasto
from .models import Empleado, Nomina, NominaDetalle
from .services import recalcular_total_nomina


# ---------------------------------------------------------------------------
# Empleado
# ---------------------------------------------------------------------------
class EmpleadoListView(LoginRequiredMixin, ListView):
    model = Empleado
    paginate_by = 25
    template_name = 'personal/empleado_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = (
                qs.filter(cedula__icontains=q)
                | qs.filter(nombres__icontains=q)
                | qs.filter(apellidos__icontains=q)
                | qs.filter(cargo__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Empleado'
        ctx['model_name_plural'] = 'Empleados'
        ctx['list_url_name'] = 'empleado_list'
        return ctx


class EmpleadoCreateView(LoginRequiredMixin, CreateView):
    model = Empleado
    fields = ['cedula', 'nombres', 'apellidos', 'cargo', 'salario_diario', 'activo']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('personal:empleado_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Empleado'
        ctx['is_update'] = False
        return ctx


class EmpleadoUpdateView(LoginRequiredMixin, UpdateView):
    model = Empleado
    fields = ['cedula', 'nombres', 'apellidos', 'cargo', 'salario_diario', 'activo']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('personal:empleado_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Empleado'
        ctx['is_update'] = True
        return ctx


class EmpleadoDeleteView(LoginRequiredMixin, DeleteView):
    model = Empleado
    template_name = 'sgco/_delete.html'
    success_url = reverse_lazy('personal:empleado_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Empleado'
        return ctx


class EmpleadoDetailView(LoginRequiredMixin, DetailView):
    model = Empleado
    template_name = 'personal/empleado_detail.html'
    context_object_name = 'empleado'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        e = self.object
        ctx['nominas'] = (
            NominaDetalle.objects
            .filter(empleado=e)
            .select_related('nomina__obra')
            .order_by('-nomina__periodo_desde', '-id')[:20]
        )
        agg = (
            NominaDetalle.objects
            .filter(empleado=e)
            .aggregate(total=Sum('monto'), count=Count('id'))
        )
        ctx['total_cobrado'] = agg['total'] or Decimal('0.00')
        ctx['nominas_count'] = agg['count'] or 0
        return ctx


# ---------------------------------------------------------------------------
# Nomina
# ---------------------------------------------------------------------------
class NominaListView(LoginRequiredMixin, ListView):
    model = Nomina
    paginate_by = 25
    template_name = 'personal/nomina_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset().select_related('obra', 'gasto')
        obra_id = self.request.GET.get('obra')
        if obra_id:
            qs = qs.filter(obra_id=obra_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obra_id = self.request.GET.get('obra')
        ctx['obra_filtro'] = Obra.objects.filter(pk=obra_id).first() if obra_id else None
        ctx['obras'] = Obra.objects.all()
        ctx['model_name'] = 'Nómina'
        ctx['model_name_plural'] = 'Nóminas'
        ctx['list_url_name'] = 'nomina_list'
        return ctx


class NominaCreateView(LoginRequiredMixin, CreateView):
    """Crear nómina: cabecera sin líneas (se agregan después).

    La cabecera se crea con `monto=0` y sin detalles. Las líneas se
    agregan en `/nominas/detalles/nuevo/?nomina=<id>`. Después se
    puede recalcular el total con el botón "Recalcular total".
    """
    model = Nomina
    fields = ['obra', 'fecha', 'periodo_desde', 'periodo_hasta']
    template_name = 'sgco/_form_page.html'

    def get_initial(self):
        initial = super().get_initial()
        obra_id = self.request.GET.get('obra')
        if obra_id:
            initial['obra'] = obra_id
        return initial

    def form_valid(self, form):
        from decimal import Decimal
        from apps.finanzas.services import crear_nomina_con_gasto
        from apps.core.choices import EstadoGastoChoices as EC
        obra = form.cleaned_data['obra']
        fecha = form.cleaned_data['fecha']
        periodo_desde = form.cleaned_data['periodo_desde']
        periodo_hasta = form.cleaned_data['periodo_hasta']
        _gasto, nomina = crear_nomina_con_gasto(
            obra=obra,
            fecha=fecha,
            periodo_desde=periodo_desde,
            periodo_hasta=periodo_hasta,
            detalles=[],  # sin líneas al inicio
            tipo_gasto='PERSONAL',
            estado=EC.BORRADOR,
            usuario=self.request.user,
        )
        self.object = nomina
        return self.response_class()

    def get_success_url(self):
        obra_id = self.request.GET.get('obra') or self.request.POST.get('obra')
        if obra_id:
            return f"{reverse_lazy('personal:nomina_list')}?obra={obra_id}"
        return reverse_lazy('personal:nomina_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Nómina'
        ctx['is_update'] = False
        return ctx


class NominaUpdateView(LoginRequiredMixin, UpdateView):
    model = Nomina
    fields = ['obra', 'fecha', 'periodo_desde', 'periodo_hasta']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('personal:nomina_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Nómina'
        ctx['is_update'] = True
        return ctx


# NOTA: Nomina NO se borra físicamente. Se anula vía NominaAnularView
# (que anula el GastoObra subyacente).


class NominaDetailView(LoginRequiredMixin, DetailView):
    model = Nomina
    template_name = 'personal/nomina_detail.html'
    context_object_name = 'nomina'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        n = self.object
        ctx['detalles'] = (
            NominaDetalle.objects
            .filter(nomina=n)
            .select_related('empleado')
            .order_by('empleado__apellidos')
        )
        ctx['total_calculado'] = (
            ctx['detalles'].aggregate(s=Sum('monto'))['s']
            or Decimal('0.00')
        )
        return ctx


class NominaRecalcularView(SGCOStaffRequiredMixin, View):
    """Recalcula el total de la nómina a partir de sus detalles."""
    def post(self, request, pk):
        n = get_object_or_404(Nomina, pk=pk)
        total = recalcular_total_nomina(n)
        messages.success(
            request,
            f'Nómina #{n.pk} recalculada: total = ${{total|floatformat:2}}',
        )
        return redirect('personal:nomina_detail', pk=n.pk)


class NominaAnularView(SGCOStaffRequiredMixin, View):
    def post(self, request, pk):
        n = get_object_or_404(Nomina, pk=pk)
        anular_gasto(n.gasto)
        messages.success(request, f'Nómina #{n.pk} anulada.')
        return redirect('personal:nomina_list')


# ---------------------------------------------------------------------------
# NominaDetalle
# ---------------------------------------------------------------------------
class NominaDetalleListView(LoginRequiredMixin, ListView):
    model = NominaDetalle
    paginate_by = 25
    template_name = 'personal/nomina_detalle_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset().select_related('nomina__obra', 'empleado')
        nomina_id = self.request.GET.get('nomina')
        obra_id = self.request.GET.get('obra')
        if nomina_id:
            qs = qs.filter(nomina_id=nomina_id)
        if obra_id:
            qs = qs.filter(nomina__obra_id=obra_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        nomina_id = self.request.GET.get('nomina')
        ctx['nomina_filtro'] = Nomina.objects.filter(pk=nomina_id).first() if nomina_id else None
        ctx['model_name'] = 'Detalle de Nómina'
        ctx['model_name_plural'] = 'Detalles de Nómina'
        ctx['list_url_name'] = 'nomina_detalle_list'
        return ctx


class NominaDetalleCreateView(LoginRequiredMixin, CreateView):
    model = NominaDetalle
    fields = ['nomina', 'empleado', 'monto']
    template_name = 'sgco/_form_page.html'

    def get_initial(self):
        initial = super().get_initial()
        nomina_id = self.request.GET.get('nomina')
        if nomina_id:
            initial['nomina'] = nomina_id
        return initial

    def get_success_url(self):
        nomina_id = self.request.GET.get('nomina') or self.request.POST.get('nomina')
        if nomina_id:
            return f"{reverse_lazy('personal:nomina_detalle_list')}?nomina={nomina_id}"
        return reverse_lazy('personal:nomina_detalle_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Detalle de Nómina'
        ctx['is_update'] = False
        return ctx


class NominaDetalleUpdateView(LoginRequiredMixin, UpdateView):
    model = NominaDetalle
    fields = ['nomina', 'empleado', 'monto']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('personal:nomina_detalle_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Detalle de Nómina'
        ctx['is_update'] = True
        return ctx


class NominaDetalleDeleteView(LoginRequiredMixin, DeleteView):
    model = NominaDetalle
    template_name = 'sgco/_delete.html'
    success_url = reverse_lazy('personal:nomina_detalle_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Detalle de Nómina'
        return ctx

    def form_valid(self, form):
        # Regla: no se puede eliminar un detalle si la nómina está aprobada.
        # Si está aprobada, se debe anular la nómina completa.
        nomina = self.get_object().nomina
        if nomina.gasto.estado == 'APROBADO':
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(
                self.request,
                f'No se puede eliminar el detalle porque la nómina #{nomina.pk} está APROBADA. '
                'Anule la nómina completa en su lugar.',
            )
            return redirect('personal:nomina_detalle_list')
        return super().form_valid(form)