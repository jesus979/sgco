"""Vistas CRUD + Detalle de Obra + Reporte PDF."""
from decimal import Decimal
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.db.models import Sum, Count, Q
from django.http import HttpResponse

from apps.finanzas.services import (
    total_asignado,
    total_gastado,
    saldo,
    porcentaje_ejecucion,
)
from apps.core.choices import (
    EstadoObraChoices,
    EstadoGastoChoices,
    EstadoFacturaChoices,
    TipoAsignacionFondoChoices,
)
from .models import Obra
from .pdf import generar_reporte_obra


# ---------------------------------------------------------------------------
# CRUD básico
# ---------------------------------------------------------------------------
class ObraListView(LoginRequiredMixin, ListView):
    model = Obra
    paginate_by = 25
    template_name = 'obras/list.html'
    context_object_name = 'object_list'

    columns = [
        {'label': 'Nombre', 'field': 'nombre'},
        {'label': 'Ubicación', 'field': 'ubicacion'},
        {'label': 'Inicio', 'field': 'fecha_inicio'},
        {'label': 'Fin est.', 'field': 'fecha_fin_estimada'},
        {'label': 'Estado', 'field': 'get_estado_display'},
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(nombre__icontains=q) | qs.filter(ubicacion__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.finanzas.services import resumen_financiero_obras
        resumen = resumen_financiero_obras(ctx['object_list'])
        rows = []
        for obra in ctx['object_list']:
            data = resumen.get(obra.id, {
                'asignado': Decimal('0.00'),
                'gastado': Decimal('0.00'),
                'saldo': Decimal('0.00'),
                'porcentaje': Decimal('0.00'),
            })
            rows.append({
                'obra': obra,
                'asignado': data['asignado'],
                'gastado': data['gastado'],
                'saldo': data['saldo'],
                'porcentaje': data['porcentaje'],
            })
        ctx['rows'] = rows
        ctx['model_name'] = 'Obra'
        ctx['model_name_plural'] = 'Obras'
        ctx['create_url'] = 'obras:create'
        ctx['columns'] = self.columns
        return ctx


class ObraCreateView(LoginRequiredMixin, CreateView):
    model = Obra
    fields = ['nombre', 'ubicacion', 'fecha_inicio', 'fecha_fin_estimada', 'estado']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('obras:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Obra'
        ctx['is_update'] = False
        return ctx


class ObraUpdateView(LoginRequiredMixin, UpdateView):
    model = Obra
    fields = ['nombre', 'ubicacion', 'fecha_inicio', 'fecha_fin_estimada', 'estado']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('obras:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Obra'
        ctx['is_update'] = True
        return ctx


class ObraDeleteView(LoginRequiredMixin, DeleteView):
    model = Obra
    template_name = 'sgco/_delete.html'
    success_url = reverse_lazy('obras:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Obra'
        return ctx


# ---------------------------------------------------------------------------
# Detalle de obra
# ---------------------------------------------------------------------------
class ObraDetailView(LoginRequiredMixin, DetailView):
    model = Obra
    template_name = 'obras/detail.html'
    context_object_name = 'obra'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obra = self.object

        # ----- KPIs financieros (servicio de resumen agregado) ---------
        from apps.finanzas.services import resumen_financiero_obras
        resumen = resumen_financiero_obras(Obra.objects.filter(pk=obra.pk))
        datos = resumen.get(obra.pk, {
            'asignado': Decimal('0.00'),
            'gastado': Decimal('0.00'),
            'saldo': Decimal('0.00'),
            'porcentaje': Decimal('0.00'),
        })
        ctx['total_asignado'] = datos['asignado']
        ctx['total_gastado'] = datos['gastado']
        ctx['saldo'] = datos['saldo']
        ctx['porcentaje'] = datos['porcentaje']

        # ----- Fondos -------------------------------------------------
        from apps.fondos.models import AsignacionFondo
        ctx['asignaciones'] = (
            AsignacionFondo.objects
            .filter(obra=obra)
            .order_by('-fecha', '-id')
        )

        # ----- Gastos (todos) -----------------------------------------
        from apps.finanzas.models import GastoObra
        ctx['gastos'] = (
            GastoObra.objects
            .filter(obra=obra)
            .select_related('obra')
            .order_by('-fecha', '-id')[:50]
        )
        ctx['gastos_aprobados_count'] = (
            GastoObra.objects
            .filter(obra=obra, estado=EstadoGastoChoices.APROBADO)
            .count()
        )
        ctx['gastos_borrador_count'] = (
            GastoObra.objects
            .filter(obra=obra, estado=EstadoGastoChoices.BORRADOR)
            .count()
        )
        ctx['gastos_anulados_count'] = (
            GastoObra.objects
            .filter(obra=obra, estado=EstadoGastoChoices.ANULADO)
            .count()
        )

        # ----- Facturas ----------------------------------------------
        from apps.proveedores.models import FacturaProveedor
        ctx['facturas'] = (
            FacturaProveedor.objects
            .filter(obra=obra)
            .select_related('proveedor')
            .order_by('-fecha_emision', '-id')[:20]
        )
        ctx['facturas_pendientes'] = (
            FacturaProveedor.objects
            .filter(obra=obra, estado=EstadoFacturaChoices.PENDIENTE)
            .count()
        )

        # ----- Inventario (estado actual) -----------------------------
        from apps.inventario.models import InventarioObra, MovimientoMaterial
        ctx['inventarios'] = (
            InventarioObra.objects
            .filter(obra=obra)
            .select_related('material')
            .order_by('material__nombre')
        )
        ctx['movimientos'] = (
            MovimientoMaterial.objects
            .filter(obra=obra)
            .select_related('material', 'usuario')
            .order_by('-fecha', '-id')[:15]
        )

        # ----- Nóminas ------------------------------------------------
        from apps.personal.models import Nomina, NominaDetalle
        ctx['nominas'] = (
            Nomina.objects
            .filter(obra=obra)
            .order_by('-periodo_desde', '-id')[:10]
        )

        # ----- Maquinaria ---------------------------------------------
        from apps.maquinaria.models import UsoMaquinaria
        ctx['usos_maquinaria'] = (
            UsoMaquinaria.objects
            .filter(obra=obra)
            .select_related('maquinaria')
            .order_by('-fecha', '-id')[:10]
        )

        # ----- Distribución por tipo ----------------------------------
        gastos_por_tipo = (
            GastoObra.objects
            .filter(obra=obra, estado=EstadoGastoChoices.APROBADO)
            .values('tipo_gasto')
            .annotate(total=Sum('monto'))
            .order_by('-total')
        )
        from apps.core.choices import TipoGastoChoices
        choices_map = dict(TipoGastoChoices.choices)
        total_general = sum((r['total'] for r in gastos_por_tipo), Decimal('0.00'))
        rows = []
        for r in gastos_por_tipo:
            pct = (
                (r['total'] / total_general * Decimal('100'))
                if total_general > 0 else Decimal('0.00')
            )
            rows.append({
                'tipo': r['tipo_gasto'],
                'label': choices_map.get(r['tipo_gasto'], r['tipo_gasto']),
                'total': r['total'],
                'porcentaje': pct,
            })
        ctx['gastos_por_tipo'] = rows

        # ----- Estado del proyecto ------------------------------------
        from apps.core.choices import EstadoObraChoices
        ctx['estado_badge'] = self._estado_badge(obra.estado)
        return ctx

    def _estado_badge(self, estado):
        mapping = {
            EstadoObraChoices.PLANIFICACION: 'bg-blue-100 text-blue-800',
            EstadoObraChoices.EN_EJECUCION: 'bg-emerald-100 text-emerald-800',
            EstadoObraChoices.PAUSADA: 'bg-amber-100 text-amber-800',
            EstadoObraChoices.CULMINADA: 'bg-slate-200 text-slate-700',
        }
        return mapping.get(estado, 'bg-slate-100 text-slate-700')


class ObraReportePDFView(LoginRequiredMixin, View):
    """Genera y devuelve el PDF del reporte financiero de una obra."""
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404
        obra = get_object_or_404(Obra, pk=pk)
        pdf_bytes = generar_reporte_obra(obra, usuario=request.user)
        filename = f'reporte_obra_{obra.pk}_{obra.nombre[:30]}.pdf'
        # Sanitizar filename
        filename = filename.replace(' ', '_').replace('/', '-')
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response