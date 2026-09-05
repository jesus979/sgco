"""Vistas CRUD de Maquinaria / UsoMaquinaria."""
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
from apps.core.permissions import SGCOStaffRequiredMixin
from apps.finanzas.services import anular_gasto
from .models import Maquinaria, UsoMaquinaria


class MaquinariaListView(LoginRequiredMixin, ListView):
    model = Maquinaria
    paginate_by = 25
    template_name = 'maquinaria/maquinaria_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = (
                qs.filter(nombre__icontains=q)
                | qs.filter(identificacion__icontains=q)
                | qs.filter(marca__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Maquinaria'
        ctx['model_name_plural'] = 'Maquinarias'
        ctx['list_url_name'] = 'maquinaria_list'
        return ctx


class MaquinariaCreateView(LoginRequiredMixin, CreateView):
    model = Maquinaria
    fields = ['nombre', 'marca', 'modelo', 'identificacion', 'costo_hora', 'activo']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('maquinaria:maquinaria_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Maquinaria'
        ctx['is_update'] = False
        return ctx


class MaquinariaUpdateView(LoginRequiredMixin, UpdateView):
    model = Maquinaria
    fields = ['nombre', 'marca', 'modelo', 'identificacion', 'costo_hora', 'activo']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('maquinaria:maquinaria_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Maquinaria'
        ctx['is_update'] = True
        return ctx


class MaquinariaDeleteView(LoginRequiredMixin, DeleteView):
    model = Maquinaria
    template_name = 'sgco/_delete.html'
    success_url = reverse_lazy('maquinaria:maquinaria_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Maquinaria'
        return ctx


class MaquinariaDetailView(LoginRequiredMixin, DetailView):
    model = Maquinaria
    template_name = 'maquinaria/maquinaria_detail.html'
    context_object_name = 'maquinaria'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        m = self.object
        ctx['usos'] = (
            UsoMaquinaria.objects
            .filter(maquinaria=m)
            .select_related('obra', 'gasto')
            .order_by('-fecha', '-id')[:30]
        )
        agg = (
            UsoMaquinaria.objects
            .filter(maquinaria=m)
            .aggregate(horas=Sum('horas'), total=Sum('gasto__monto'))
        )
        ctx['total_horas'] = agg['horas'] or Decimal('0.00')
        ctx['total_costo'] = agg['total'] or Decimal('0.00')
        return ctx


class UsoListView(LoginRequiredMixin, ListView):
    model = UsoMaquinaria
    paginate_by = 25
    template_name = 'maquinaria/uso_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        qs = super().get_queryset().select_related('obra', 'maquinaria', 'gasto')
        obra_id = self.request.GET.get('obra')
        if obra_id:
            qs = qs.filter(obra_id=obra_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obra_id = self.request.GET.get('obra')
        ctx['obra_filtro'] = Obra.objects.filter(pk=obra_id).first() if obra_id else None
        ctx['obras'] = Obra.objects.all()
        ctx['model_name'] = 'Uso de Maquinaria'
        ctx['model_name_plural'] = 'Usos de Maquinaria'
        ctx['list_url_name'] = 'uso_list'
        return ctx


class UsoCreateView(LoginRequiredMixin, CreateView):
    """Crear uso de maquinaria. El GastoObra se crea automáticamente vía servicio.

    Por eso `gasto` no está en el form.
    """
    model = UsoMaquinaria
    fields = ['obra', 'maquinaria', 'fecha', 'horas']
    template_name = 'sgco/_form_page.html'

    def get_initial(self):
        initial = super().get_initial()
        obra_id = self.request.GET.get('obra')
        if obra_id:
            initial['obra'] = obra_id
        return initial

    def form_valid(self, form):
        from apps.finanzas.services import crear_uso_maquinaria_con_gasto
        from apps.core.choices import EstadoGastoChoices as EC, TipoGastoChoices as TC
        _gasto, uso = crear_uso_maquinaria_con_gasto(
            obra=form.cleaned_data['obra'],
            maquinaria=form.cleaned_data['maquinaria'],
            fecha=form.cleaned_data['fecha'],
            horas=form.cleaned_data['horas'],
            tipo_gasto=TC.MAQUINARIA,
            estado=EC.BORRADOR,
            usuario=self.request.user,
        )
        self.object = uso
        return self.response_class()

    def get_success_url(self):
        obra_id = self.request.GET.get('obra') or self.request.POST.get('obra')
        if obra_id:
            return f"{reverse_lazy('maquinaria:uso_list')}?obra={obra_id}"
        return reverse_lazy('maquinaria:uso_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Uso de Maquinaria'
        ctx['is_update'] = False
        return ctx


class UsoUpdateView(LoginRequiredMixin, UpdateView):
    model = UsoMaquinaria
    fields = ['obra', 'maquinaria', 'fecha', 'horas']
    template_name = 'sgco/_form_page.html'
    success_url = reverse_lazy('maquinaria:uso_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Uso de Maquinaria'
        ctx['is_update'] = True
        return ctx


# NOTA: UsoMaquinaria NO se borra físicamente. Se anula vía UsoAnularView.


class UsoAnularView(SGCOStaffRequiredMixin, View):
    def post(self, request, pk):
        u = get_object_or_404(UsoMaquinaria, pk=pk)
        anular_gasto(u.gasto)
        messages.success(request, f'Uso de maquinaria #{u.pk} anulado.')
        obra_id = request.GET.get('obra')
        if obra_id:
            return redirect(f"{reverse_lazy('maquinaria:uso_list')}?obra={obra_id}")
        return redirect('maquinaria:uso_list')