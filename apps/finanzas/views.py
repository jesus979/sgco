"""Vistas CRUD de Finanzas: GastoObra + OtroGasto."""
from decimal import Decimal
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, View,
)
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from apps.obras.models import Obra
from apps.core.choices import EstadoGastoChoices
from .models import GastoObra, OtroGasto
from .services import anular_gasto


class GastoObraListView(LoginRequiredMixin, ListView):
    model = GastoObra
    paginate_by = 25
    template_name = 'finanzas/gasto_list.html'
    context_object_name = 'object_list'

    columns = [
        {'label': 'Fecha', 'field': 'fecha'},
        {'label': 'Obra', 'field': 'obra'},
        {'label': 'Tipo', 'field': 'get_tipo_gasto_display'},
        {'label': 'Descripción', 'field': 'descripcion'},
        {'label': 'Monto', 'field': 'monto'},
        {'label': 'Estado', 'field': 'get_estado_display'},
    ]

    def get_queryset(self):
        qs = super().get_queryset().select_related('obra')
        q = self.request.GET.get('q')
        obra_id = self.request.GET.get('obra')
        estado = self.request.GET.get('estado')
        tipo = self.request.GET.get('tipo')
        if obra_id:
            qs = qs.filter(obra_id=obra_id)
        if estado:
            qs = qs.filter(estado=estado)
        if tipo:
            qs = qs.filter(tipo_gasto=tipo)
        if q:
            qs = qs.filter(obra__nombre__icontains=q) | qs.filter(descripcion__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obra_id = self.request.GET.get('obra')
        ctx['obra_filtro'] = Obra.objects.filter(pk=obra_id).first() if obra_id else None
        ctx['estado_filtro'] = self.request.GET.get('estado', '')
        ctx['tipo_filtro'] = self.request.GET.get('tipo', '')
        ctx['obras'] = Obra.objects.all()
        ctx['estados'] = EstadoGastoChoices.choices
        from apps.core.choices import TipoGastoChoices
        ctx['tipos'] = TipoGastoChoices.choices
        ctx['model_name'] = 'Gasto de Obra'
        ctx['model_name_plural'] = 'Gastos de Obra'
        ctx['list_url_name'] = 'gasto_list'
        return ctx


class GastoObraCreateView(LoginRequiredMixin, CreateView):
    model = GastoObra
    fields = ['obra', 'fecha', 'tipo_gasto', 'descripcion', 'monto', 'estado']
    template_name = 'sgco/_form_page.html'

    def get_initial(self):
        initial = super().get_initial()
        obra_id = self.request.GET.get('obra')
        if obra_id:
            initial['obra'] = obra_id
        return initial

    def get_success_url(self):
        obra_id = self.request.GET.get('obra') or self.request.POST.get('obra')
        if obra_id:
            return f"{reverse_lazy('finanzas:gasto_list')}?obra={obra_id}"
        return reverse_lazy('finanzas:gasto_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Gasto de Obra'
        ctx['is_update'] = False
        return ctx


class GastoObraUpdateView(LoginRequiredMixin, UpdateView):
    model = GastoObra
    fields = ['obra', 'fecha', 'tipo_gasto', 'descripcion', 'monto', 'estado']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('finanzas:gasto_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Gasto de Obra'
        ctx['is_update'] = True
        return ctx


class GastoObraDeleteView(LoginRequiredMixin, DeleteView):
    model = GastoObra
    template_name = 'sgco/_delete.html'
    success_url = reverse_lazy('finanzas:gasto_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Gasto de Obra'
        return ctx


class GastoObraDetailView(LoginRequiredMixin, DetailView):
    model = GastoObra
    template_name = 'finanzas/gasto_detail.html'
    context_object_name = 'gasto'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.object
        # Documentos origen posibles (solo uno estará presente)
        ctx['factura'] = getattr(g, 'factura_proveedor', None)
        ctx['nomina'] = getattr(g, 'nomina', None)
        ctx['uso_maquinaria'] = getattr(g, 'uso_maquinaria', None)
        ctx['otro_gasto'] = getattr(g, 'otro_gasto', None)
        return ctx


class GastoObraAnularView(LoginRequiredMixin, View):
    def post(self, request, pk):
        g = get_object_or_404(GastoObra, pk=pk)
        anular_gasto(g)
        messages.success(request, f'Gasto #{g.pk} anulado. Ya no afecta el saldo de la obra.')
        obra_id = request.GET.get('obra')
        if obra_id:
            return redirect(f"{reverse_lazy('finanzas:gasto_list')}?obra={obra_id}")
        return redirect('finanzas:gasto_list')


# ---------------------------------------------------------------------------
# OtroGasto
# ---------------------------------------------------------------------------
class OtroGastoListView(LoginRequiredMixin, ListView):
    model = OtroGasto
    paginate_by = 25
    template_name = 'finanzas/otro_list.html'
    context_object_name = 'object_list'

    columns = [
        {'label': 'Fecha', 'field': 'fecha'},
        {'label': 'Obra', 'field': 'obra'},
        {'label': 'Concepto', 'field': 'concepto'},
        {'label': 'Comprobante', 'field': 'comprobante'},
        {'label': 'Proveedor', 'field': 'proveedor'},
        {'label': 'Monto', 'field': 'gasto.monto'},
    ]

    def get_queryset(self):
        qs = super().get_queryset().select_related('obra', 'proveedor', 'gasto')
        obra_id = self.request.GET.get('obra')
        if obra_id:
            qs = qs.filter(obra_id=obra_id)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(concepto__icontains=q) | qs.filter(comprobante__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obra_id = self.request.GET.get('obra')
        ctx['obra_filtro'] = Obra.objects.filter(pk=obra_id).first() if obra_id else None
        ctx['obras'] = Obra.objects.all()
        ctx['model_name'] = 'Otro Gasto'
        ctx['model_name_plural'] = 'Otros Gastos'
        ctx['list_url_name'] = 'otro_list'
        return ctx


class OtroGastoCreateView(LoginRequiredMixin, CreateView):
    model = OtroGasto
    fields = ['obra', 'gasto', 'fecha', 'concepto', 'comprobante', 'proveedor', 'observaciones']
    template_name = 'sgco/_form_page.html'

    def get_initial(self):
        initial = super().get_initial()
        obra_id = self.request.GET.get('obra')
        if obra_id:
            initial['obra'] = obra_id
        return initial

    def get_success_url(self):
        obra_id = self.request.GET.get('obra') or self.request.POST.get('obra')
        if obra_id:
            return f"{reverse_lazy('finanzas:otro_list')}?obra={obra_id}"
        return reverse_lazy('finanzas:otro_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Otro Gasto'
        ctx['is_update'] = False
        return ctx


class OtroGastoUpdateView(LoginRequiredMixin, UpdateView):
    model = OtroGasto
    fields = ['obra', 'gasto', 'fecha', 'concepto', 'comprobante', 'proveedor', 'observaciones']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('finanzas:otro_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Otro Gasto'
        ctx['is_update'] = True
        return ctx


class OtroGastoDeleteView(LoginRequiredMixin, DeleteView):
    model = OtroGasto
    template_name = 'sgco/_delete.html'
    success_url = reverse_lazy('finanzas:otro_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Otro Gasto'
        return ctx


class OtroGastoAnularView(LoginRequiredMixin, View):
    """Anula el GastoObra asociado (OtroGasto no mantiene estado propio)."""
    def post(self, request, pk):
        o = get_object_or_404(OtroGasto, pk=pk)
        anular_gasto(o.gasto)
        messages.success(request, f'Otro gasto #{o.pk} → GastoObra #{o.gasto_id} anulado.')
        obra_id = request.GET.get('obra')
        if obra_id:
            return redirect(f"{reverse_lazy('finanzas:otro_list')}?obra={obra_id}")
        return redirect('finanzas:otro_list')