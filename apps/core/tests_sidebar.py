"""Smoke tests del nuevo layout: sidebar + header + resaltado activo."""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from apps.obras.models import Obra


class SidebarLayoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='t', password='x')
        cls.obra = Obra.objects.create(
            nombre='Obra Test', ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )

    def setUp(self):
        self.client.login(username='t', password='x')

    def test_sidebar_presente_en_dashboard(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="sidebar"')
        self.assertContains(r, 'data-collapse="grp-obras"')
        self.assertContains(r, 'data-collapse="grp-operacion"')
        self.assertContains(r, 'data-collapse="grp-inventario"')
        self.assertContains(r, 'data-collapse="grp-personal"')
        self.assertContains(r, 'data-collapse="grp-maquinaria"')

    def test_dashboard_resaltado_activo(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        # El link de Dashboard debe tener aria-current="page"
        self.assertContains(r, 'aria-current="page"')

    def test_grupo_obras_abierto_en_detalle(self):
        r = self.client.get(f'/obras/{self.obra.pk}/')
        self.assertEqual(r.status_code, 200)
        # El sub-menú de OBRAS debe estar visible (no hidden)
        # El link "Listado" debe estar resaltado (bg-primary-600)
        self.assertContains(r, 'href="/obras/"')

    def test_grupo_personal_cerrado_en_obras(self):
        r = self.client.get('/obras/')
        self.assertEqual(r.status_code, 200)
        # El sub-menú de Personal debe estar oculto
        # Verificamos que el UL de personal está con hidden
        self.assertContains(r, 'id="grp-personal"')
        self.assertContains(r, 'id="grp-personal" class="mt-1')

    def test_header_con_logout(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="sidebarOpen"')
        self.assertContains(r, 'action="/logout/"')
        self.assertContains(r, 'sgco-header')

    def test_responsive_drawer(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        # Sidebar tiene translate-x-full por defecto (oculto en mobile)
        self.assertContains(r, '-translate-x-full')
        # En md: se muestra
        self.assertContains(r, 'md:translate-x-0')
        # Backdrop existe
        self.assertContains(r, 'id="sidebarBackdrop"')

    def test_grupo_operacion_abierto_en_gastos(self):
        r = self.client.get('/finanzas/gastos/')
        self.assertEqual(r.status_code, 200)
        # El link de Gastos debe estar visible
        self.assertContains(r, 'href="/finanzas/gastos/"')

    def test_grupo_inventario_abierto_en_materiales(self):
        r = self.client.get('/inventario/materiales/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'href="/inventario/materiales/"')

    def test_logout_form_es_post(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        # El form de logout debe ser POST
        self.assertContains(r, 'method="post" action="/logout/"')

    def test_pagina_login_no_tiene_sidebar(self):
        self.client.logout()
        r = self.client.get('/login/')
        self.assertEqual(r.status_code, 200)
        # La página de login es standalone, sin sidebar
        self.assertNotContains(r, 'id="sidebar"')

    def test_todos_los_enlaces_del_sidebar(self):
        r = self.client.get('/')
        # Verifica que los enlaces principales están todos
        self.assertContains(r, 'href="/obras/"')
        self.assertContains(r, 'href="/obras/nueva/"')
        self.assertContains(r, 'href="/fondos/"')
        self.assertContains(r, 'href="/finanzas/gastos/"')
        self.assertContains(r, 'href="/finanzas/otros/"')
        self.assertContains(r, 'href="/proveedores/facturas/"')
        self.assertContains(r, 'href="/proveedores/facturas/detalles/"')
        self.assertContains(r, 'href="/inventario/materiales/"')
        self.assertContains(r, 'href="/inventario/inventarios/"')
        self.assertContains(r, 'href="/inventario/movimientos/"')
        self.assertContains(r, 'href="/personal/"')
        self.assertContains(r, 'href="/personal/nominas/"')
        self.assertContains(r, 'href="/personal/nominas/detalles/"')
        self.assertContains(r, 'href="/maquinaria/"')
        self.assertContains(r, 'href="/maquinaria/usos/"')