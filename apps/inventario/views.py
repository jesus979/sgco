"""Vistas de Inventario."""
from decimal import Decimal
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, View,
)
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum

from apps.obras.models import Obra
from .models import Material, InventarioObra, MovimientoMaterial


class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    paginate_by = 25
    template_name = 'inventario/material_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(nombre__icontains=q) | qs.filter(categoria__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Material'
        ctx['model_name_plural'] = 'Materiales'
        ctx['list_url_name'] = 'material_list'
        return ctx


class MaterialCreateView(LoginRequiredMixin, CreateView):
    model = Material
    fields = ['nombre', 'unidad', 'categoria', 'precio_unitario_referencia', 'activo']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('inventario:material_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Material'
        ctx['is_update'] = False
        return ctx


class MaterialUpdateView(LoginRequiredMixin, UpdateView):
    model = Material
    fields = ['nombre', 'unidad', 'categoria', 'precio_unitario_referencia', 'activo']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('inventario:material_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Material'
        ctx['is_update'] = True
        return ctx


class MaterialDeleteView(LoginRequiredMixin, DeleteView):
    model = Material
    template_name = 'sgco/_delete.html'
    success_url = reverse_lazy('inventario:material_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Material'
        return ctx


class MaterialDetailView(LoginRequiredMixin, DetailView):
    model = Material
    template_name = 'inventario/material_detail.html'
    context_object_name = 'material'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        m = self.object
        ctx['inventarios'] = (
            InventarioObra.objects
            .filter(material=m)
            .select_related('obra')
            .order_by('obra__nombre')
        )
        ctx['total_stock'] = (
            ctx['inventarios'].aggregate(s=Sum('cantidad_actual'))['s']
            or Decimal('0.00')
        )
        ctx['ultimos_movimientos'] = (
            MovimientoMaterial.objects
            .filter(material=m)
            .select_related('obra', 'usuario')
            .order_by('-fecha', '-id')[:15]
        )
        return ctx


class InventarioListView(LoginRequiredMixin, ListView):
    model = InventarioObra
    paginate_by = 25
    template_name = 'inventario/inventario_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset().select_related('obra', 'material')
        obra_id = self.request.GET.get('obra')
        if obra_id:
            qs = qs.filter(obra_id=obra_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obra_id = self.request.GET.get('obra')
        ctx['obra_filtro'] = Obra.objects.filter(pk=obra_id).first() if obra_id else None
        ctx['obras'] = Obra.objects.all()
        ctx['model_name'] = 'Inventario'
        ctx['model_name_plural'] = 'Inventarios de Obra'
        ctx['list_url_name'] = 'inventario_list'
        return ctx


class InventarioUpdateView(LoginRequiredMixin, UpdateView):
    """Solo se permite editar la cantidad; no se elimina."""
    model = InventarioObra
    fields = ['cantidad_actual']
    template_name = 'sgco/_form_page.html'

    def get_success_url(self):
        obra_id = self.object.obra_id
        return f"{reverse_lazy('inventario:inventario_list')}?obra={obra_id}"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Inventario'
        ctx['is_update'] = True
        return ctx


class MovimientoListView(LoginRequiredMixin, ListView):
    model = MovimientoMaterial
    paginate_by = 25
    template_name = 'inventario/movimiento_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset().select_related('obra', 'material', 'usuario')
        obra_id = self.request.GET.get('obra')
        if obra_id:
            qs = qs.filter(obra_id=obra_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obra_id = self.request.GET.get('obra')
        ctx['obra_filtro'] = Obra.objects.filter(pk=obra_id).first() if obra_id else None
        ctx['obras'] = Obra.objects.all()
        ctx['model_name'] = 'Movimiento de Material'
        ctx['model_name_plural'] = 'Movimientos de Material'
        ctx['list_url_name'] = 'movimiento_list'
        return ctx


class MovimientoCreateView(LoginRequiredMixin, CreateView):
    """Solo lectura-friendly: NO actualiza stock automáticamente.

    Se documenta en el template que para afectar inventario debe usarse
    un servicio transaccional (apps.inventario.services).
    """
    model = MovimientoMaterial
    fields = ['obra', 'material', 'usuario', 'tipo', 'cantidad', 'fecha',
              'referencia', 'observaciones']
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
            return f"{reverse_lazy('inventario:movimiento_list')}?obra={obra_id}"
        return reverse_lazy('inventario:movimiento_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Movimiento de Material'
        ctx['is_update'] = False
        return ctx