"""Vistas CRUD de Proveedores / Facturas / Detalles."""
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
from apps.core.choices import EstadoFacturaChoices, EstadoGastoChoices
from .models import Proveedor, FacturaProveedor, DetalleFactura
from apps.finanzas.models import GastoObra
from apps.finanzas.services import anular_gasto


# ---------------------------------------------------------------------------
# Proveedor
# ---------------------------------------------------------------------------
class ProveedorListView(LoginRequiredMixin, ListView):
    model = Proveedor
    paginate_by = 25
    template_name = 'proveedores/proveedor_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(nombre__icontains=q) | qs.filter(identificacion__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Anotar cantidad de facturas y monto total por proveedor
        proveedores = ctx['object_list']
        ids = [p.pk for p in proveedores]
        agg = (
            FacturaProveedor.objects
            .filter(proveedor_id__in=ids)
            .values('proveedor_id')
            .annotate(total=Sum('total'), count=Count('id'))
        )
        info = {row['proveedor_id']: row for row in agg}
        rows = []
        for p in proveedores:
            r = info.get(p.pk, {})
            rows.append({
                'obj': p,
                'facturas_count': r.get('count', 0),
                'facturas_total': r.get('total') or Decimal('0.00'),
            })
        ctx['rows'] = rows
        ctx['model_name'] = 'Proveedor'
        ctx['model_name_plural'] = 'Proveedores'
        ctx['list_url_name'] = 'proveedor_list'
        return ctx


class ProveedorCreateView(LoginRequiredMixin, CreateView):
    model = Proveedor
    fields = ['nombre', 'identificacion', 'telefono', 'email', 'direccion', 'activo']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('proveedores:proveedor_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Proveedor'
        ctx['is_update'] = False
        return ctx


class ProveedorUpdateView(LoginRequiredMixin, UpdateView):
    model = Proveedor
    fields = ['nombre', 'identificacion', 'telefono', 'email', 'direccion', 'activo']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('proveedores:proveedor_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Proveedor'
        ctx['is_update'] = True
        return ctx


class ProveedorDeleteView(LoginRequiredMixin, DeleteView):
    model = Proveedor
    template_name = 'sgco/_delete.html'
    success_url = reverse_lazy('proveedores:proveedor_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Proveedor'
        return ctx


class ProveedorDetailView(LoginRequiredMixin, DetailView):
    model = Proveedor
    template_name = 'proveedores/proveedor_detail.html'
    context_object_name = 'proveedor'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        p = self.object
        ctx['facturas'] = (
            FacturaProveedor.objects
            .filter(proveedor=p)
            .select_related('obra', 'gasto')
            .order_by('-fecha_emision', '-id')[:30]
        )
        agg = (
            FacturaProveedor.objects
            .filter(proveedor=p)
            .aggregate(total=Sum('total'), count=Count('id'))
        )
        ctx['facturas_count'] = agg['count'] or 0
        ctx['facturas_total'] = agg['total'] or Decimal('0.00')
        return ctx


# ---------------------------------------------------------------------------
# Factura
# ---------------------------------------------------------------------------
class FacturaListView(LoginRequiredMixin, ListView):
    model = FacturaProveedor
    paginate_by = 25
    template_name = 'proveedores/factura_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset().select_related('obra', 'proveedor', 'gasto')
        q = self.request.GET.get('q')
        obra_id = self.request.GET.get('obra')
        estado = self.request.GET.get('estado')
        if obra_id:
            qs = qs.filter(obra_id=obra_id)
        if estado:
            qs = qs.filter(estado=estado)
        if q:
            qs = qs.filter(folio__icontains=q) | qs.filter(proveedor__nombre__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obra_id = self.request.GET.get('obra')
        ctx['obra_filtro'] = Obra.objects.filter(pk=obra_id).first() if obra_id else None
        ctx['estado_filtro'] = self.request.GET.get('estado', '')
        ctx['obras'] = Obra.objects.all()
        ctx['estados'] = EstadoFacturaChoices.choices
        ctx['model_name'] = 'Factura'
        ctx['model_name_plural'] = 'Facturas de Proveedores'
        ctx['list_url_name'] = 'factura_list'
        return ctx


class FacturaCreateView(LoginRequiredMixin, CreateView):
    """Crear factura.

    La factura SIEMPRE crea su propio GastoObra vía el servicio
    `crear_gasto_con_factura`. El usuario NO puede seleccionar un
    GastoObra existente. Por eso excluimos `gasto` del form.
    """
    model = FacturaProveedor
    fields = ['obra', 'proveedor', 'folio', 'fecha_emision', 'impuesto', 'total', 'estado']
    template_name = 'sgco/_form_page.html'

    def get_initial(self):
        initial = super().get_initial()
        obra_id = self.request.GET.get('obra')
        if obra_id:
            initial['obra'] = obra_id
        return initial

    def form_valid(self, form):
        from apps.finanzas.services import crear_gasto_con_factura
        from apps.core.choices import (
            EstadoGastoChoices as EC,
            EstadoFacturaChoices as EF,
            TipoGastoChoices as TG,
        )
        _gasto, factura = crear_gasto_con_factura(
            obra=form.cleaned_data['obra'],
            proveedor=form.cleaned_data['proveedor'],
            folio=form.cleaned_data['folio'],
            fecha_emision=form.cleaned_data['fecha_emision'],
            total=form.cleaned_data['total'],
            impuesto=form.cleaned_data['impuesto'] or Decimal('0.00'),
            descripcion=f'Factura {form.cleaned_data["folio"]} - {form.cleaned_data["proveedor"].nombre}',
            tipo_gasto=TG.MATERIAL,
            estado=EC.BORRADOR,
            estado_factura=form.cleaned_data['estado'],
            usuario=self.request.user,
        )
        # Reemplazar el save por defecto: la factura ya está creada
        self.object = factura
        return self.response_class()

    def get_success_url(self):
        obra_id = self.request.GET.get('obra') or self.request.POST.get('obra')
        if obra_id:
            return f"{reverse_lazy('proveedores:factura_list')}?obra={obra_id}"
        return reverse_lazy('proveedores:factura_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Factura'
        ctx['is_update'] = False
        return ctx


class FacturaUpdateView(LoginRequiredMixin, UpdateView):
    model = FacturaProveedor
    fields = ['obra', 'proveedor', 'folio', 'fecha_emision', 'impuesto', 'total', 'estado']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('proveedores:factura_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Factura'
        ctx['is_update'] = True
        return ctx


# NOTA: FacturaProveedor NO se borra físicamente si tiene un
# GastoObra aprobado. El admin/protección de BD ya lo impide. Si
# realmente se necesita "eliminar" una factura errónea, se debe
# primero anular su GastoObra asociado.
#
# (No existe FacturaDeleteView en v1.2: solo se permite ANULAR el
# gasto asociado, lo que deja la factura como registro histórico.)


class FacturaDetailView(LoginRequiredMixin, DetailView):
    model = FacturaProveedor
    template_name = 'proveedores/factura_detail.html'
    context_object_name = 'factura'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        f = self.object
        ctx['detalles'] = (
            DetalleFactura.objects
            .filter(factura=f)
            .select_related('material')
            .order_by('id')
        )
        ctx['subtotal_calculado'] = f.subtotal
        ctx['total_calculado'] = f.total_calculado()
        ctx['es_consistente'] = f.es_consistente()
        return ctx


# ---------------------------------------------------------------------------
# DetalleFactura
# ---------------------------------------------------------------------------
class DetalleFacturaListView(LoginRequiredMixin, ListView):
    model = DetalleFactura
    paginate_by = 25
    template_name = 'proveedores/detalle_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset().select_related('factura__proveedor', 'material')
        factura_id = self.request.GET.get('factura')
        obra_id = self.request.GET.get('obra')
        if factura_id:
            qs = qs.filter(factura_id=factura_id)
        if obra_id:
            qs = qs.filter(factura__obra_id=obra_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        factura_id = self.request.GET.get('factura')
        ctx['factura_filtro'] = FacturaProveedor.objects.filter(pk=factura_id).first() if factura_id else None
        ctx['model_name'] = 'Detalle de Factura'
        ctx['model_name_plural'] = 'Detalles de Factura'
        ctx['list_url_name'] = 'detalle_list'
        return ctx


class DetalleFacturaCreateView(LoginRequiredMixin, CreateView):
    model = DetalleFactura
    fields = ['factura', 'material', 'cantidad', 'precio_unitario']
    template_name = 'sgco/_form_page.html'

    def get_initial(self):
        initial = super().get_initial()
        factura_id = self.request.GET.get('factura')
        if factura_id:
            initial['factura'] = factura_id
        return initial

    def get_success_url(self):
        factura_id = self.request.GET.get('factura') or self.request.POST.get('factura')
        if factura_id:
            return f"{reverse_lazy('proveedores:detalle_list')}?factura={factura_id}"
        return reverse_lazy('proveedores:detalle_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Detalle de Factura'
        ctx['is_update'] = False
        return ctx


class DetalleFacturaUpdateView(LoginRequiredMixin, UpdateView):
    model = DetalleFactura
    fields = ['factura', 'material', 'cantidad', 'precio_unitario']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('proveedores:detalle_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Detalle de Factura'
        ctx['is_update'] = True
        return ctx


class DetalleFacturaDeleteView(LoginRequiredMixin, DeleteView):
    model = DetalleFactura
    template_name = 'sgco/_delete.html'
    success_url = reverse_lazy('proveedores:detalle_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Detalle de Factura'
        return ctx