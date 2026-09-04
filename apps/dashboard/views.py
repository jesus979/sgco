from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Sum, Count
from decimal import Decimal

from apps.obras.models import Obra
from apps.fondos.models import AsignacionFondo
from apps.finanzas.models import GastoObra
from apps.core.choices import (
    EstadoObraChoices,
    EstadoGastoChoices,
    TipoGastoChoices,
)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # ----- KPIs globales ------------------------------------------
        total_asignado_global = (
            AsignacionFondo.objects.aggregate(s=Sum('monto'))['s']
            or Decimal('0.00')
        )
        total_gastado_global = (
            GastoObra.objects
            .filter(estado=EstadoGastoChoices.APROBADO)
            .aggregate(s=Sum('monto'))['s']
            or Decimal('0.00')
        )
        saldo_global = total_asignado_global - total_gastado_global
        if total_asignado_global > 0:
            porcentaje_global = (
                (total_gastado_global / total_asignado_global) * Decimal('100')
            )
        else:
            porcentaje_global = Decimal('0.00')

        obras_activas_qs = Obra.objects.exclude(estado=EstadoObraChoices.CULMINADA)

        ctx.update({
            'total_obras': Obra.objects.count(),
            'obras_activas': obras_activas_qs.count(),
            'obras_ejecucion': Obra.objects.filter(estado=EstadoObraChoices.EN_EJECUCION).count(),
            'obras_planificacion': Obra.objects.filter(estado=EstadoObraChoices.PLANIFICACION).count(),
            'obras_culminadas': Obra.objects.filter(estado=EstadoObraChoices.CULMINADA).count(),

            'total_asignado_global': total_asignado_global,
            'total_gastado_global': total_gastado_global,
            'saldo_global': saldo_global,
            'porcentaje_global': porcentaje_global,

            # ----- Obras con resumen financiero ------------------------
            'obras_resumen': self._obras_resumen(),

            # ----- Últimos gastos --------------------------------------
            'ultimos_gastos': (
                GastoObra.objects
                .select_related('obra')
                .order_by('-fecha', '-id')[:8]
            ),

            # ----- Distribución por tipo -------------------------------
            'gastos_por_tipo': self._gastos_por_tipo(),

            # ----- Datos para Chart.js ----------------------------------
            'gastos_por_tipo_chart': self._gastos_por_tipo_chart(),
            'obras_por_estado_chart': self._obras_por_estado_chart(),
        })
        return ctx

    def _obras_resumen(self):
        """Una fila por obra con totales financieros."""
        from apps.finanzas.services import (
            total_asignado, total_gastado, saldo, porcentaje_ejecucion,
        )
        rows = []
        for obra in Obra.objects.all():
            a = total_asignado(obra)
            g = total_gastado(obra)
            s = saldo(obra)
            p = porcentaje_ejecucion(obra)
            rows.append({
                'obra': obra,
                'asignado': a,
                'gastado': g,
                'saldo': s,
                'porcentaje': p,
                'estado_badge': self._estado_badge(obra.estado),
            })
        return rows

    def _estado_badge(self, estado):
        mapping = {
            EstadoObraChoices.PLANIFICACION: 'bg-blue-100 text-blue-800',
            EstadoObraChoices.EN_EJECUCION: 'bg-emerald-100 text-emerald-800',
            EstadoObraChoices.PAUSADA: 'bg-amber-100 text-amber-800',
            EstadoObraChoices.CULMINADA: 'bg-slate-200 text-slate-700',
        }
        return mapping.get(estado, 'bg-slate-100 text-slate-700')

    def _gastos_por_tipo(self):
        agg = (
            GastoObra.objects
            .filter(estado=EstadoGastoChoices.APROBADO)
            .values('tipo_gasto')
            .annotate(total=Sum('monto'), count=Count('id'))
            .order_by('-total')
        )
        choices_map = dict(TipoGastoChoices.choices)
        total_general = sum((row['total'] for row in agg), Decimal('0.00'))
        rows = []
        for row in agg:
            pct = (
                (row['total'] / total_general * Decimal('100'))
                if total_general > 0 else Decimal('0.00')
            )
            rows.append({
                'tipo': row['tipo_gasto'],
                'label': choices_map.get(row['tipo_gasto'], row['tipo_gasto']),
                'total': row['total'],
                'count': row['count'],
                'porcentaje': pct,
            })
        return rows

    def _gastos_por_tipo_chart(self):
        """Datos para Chart.js: gastos aprobados por tipo."""
        agg = (
            GastoObra.objects
            .filter(estado=EstadoGastoChoices.APROBADO)
            .values('tipo_gasto')
            .annotate(total=Sum('monto'))
            .order_by('-total')
        )
        from apps.core.choices import TipoGastoChoices
        choices_map = dict(TipoGastoChoices.choices)
        return {
            'labels': [choices_map.get(r['tipo_gasto'], r['tipo_gasto']) for r in agg],
            'values': [float(r['total']) for r in agg],
        }

    def _obras_por_estado_chart(self):
        """Datos para Chart.js: obras agrupadas por estado."""
        from apps.core.choices import EstadoObraChoices
        agg = (
            Obra.objects
            .values('estado')
            .annotate(count=Count('id'))
        )
        choices_map = dict(EstadoObraChoices.choices)
        return {
            'labels': [choices_map.get(r['estado'], r['estado']) for r in agg],
            'values': [r['count'] for r in agg],
        }