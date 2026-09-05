"""Vistas CRUD de Asignaciones de Fondo."""
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from apps.obras.models import Obra
from .models import AsignacionFondo
from .services import anular_asignacion


class AsignacionFondoListView(LoginRequiredMixin, ListView):
    model = AsignacionFondo
    paginate_by = 25
    template_name = 'fondos/list.html'
    context_object_name = 'object_list'

    columns = [
        {'label': 'Obra', 'field': 'obra'},
        {'label': 'Fecha', 'field': 'fecha'},
        {'label': 'Tipo', 'field': 'get_tipo_display'},
        {'label': 'Monto', 'field': 'monto'},
        {'label': 'Referencia', 'field': 'referencia'},
        {'label': 'Estado', 'field': 'get_anulada_display'},
    ]

    def get_queryset(self):
        qs = super().get_queryset().select_related('obra')
        q = self.request.GET.get('q')
        obra_id = self.request.GET.get('obra')
        if obra_id:
            qs = qs.filter(obra_id=obra_id)
        if q:
            qs = qs.filter(obra__nombre__icontains=q) | qs.filter(referencia__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obra_id = self.request.GET.get('obra')
        ctx['obra_filtro'] = Obra.objects.filter(pk=obra_id).first() if obra_id else None
        ctx['obras'] = Obra.objects.all()
        ctx['model_name'] = 'Asignación de Fondo'
        ctx['model_name_plural'] = 'Asignaciones de Fondo'
        ctx['list_url_name'] = 'fondos_list'
        ctx['empty_message'] = 'Sin asignaciones registradas'
        ctx['show_actions'] = True
        ctx['show_detail'] = False
        ctx['show_update'] = True
        ctx['show_delete'] = False
        ctx['show_anular'] = True
        return ctx


class AsignacionFondoCreateView(LoginRequiredMixin, CreateView):
    model = AsignacionFondo
    fields = ['obra', 'fecha', 'tipo', 'monto', 'referencia', 'observaciones']
    template_name = 'sgco/_form_page.html'

    def get_initial(self):
        initial = super().get_initial()
        obra_id = self.request.GET.get('obra')
        if obra_id:
            initial['obra'] = obra_id
        return initial

    def form_valid(self, form):
        # Asignar el usuario autenticado
        form.instance.usuario = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        obra_id = self.request.GET.get('obra') or self.request.POST.get('obra')
        if obra_id:
            return f"{reverse_lazy('fondos:list')}?obra={obra_id}"
        return reverse_lazy('fondos:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Asignación de Fondo'
        ctx['is_update'] = False
        return ctx


class AsignacionFondoUpdateView(LoginRequiredMixin, UpdateView):
    """Editar asignación.

    Regla de inmutabilidad: NO se permite modificar obra, monto ni
    tipo. El modelo `AsignacionFondo.save()` lo valida y lanza
    ValidationError. El form solo expone los campos seguros
    (referencia, observaciones).
    """
    model = AsignacionFondo
    fields = ['referencia', 'observaciones']
    template_name = 'sgco/_form_page.html'

    def get_success_url(self):
        return reverse_lazy('fondos:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = 'Asignación de Fondo'
        ctx['is_update'] = True
        return ctx


class AsignacionFondoAnularView(LoginRequiredMixin, View):
    """Anula la asignación (no se borra físicamente)."""
    def post(self, request, pk):
        a = get_object_or_404(AsignacionFondo, pk=pk)
        anular_asignacion(a)
        messages.success(request, f'Asignación #{a.pk} anulada.')
        return redirect('fondos:list')