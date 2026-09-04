"""Servicio para generar el reporte PDF de una obra."""
from decimal import Decimal
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

from apps.finanzas.services import resumen_financiero_obras
from apps.fondos.models import AsignacionFondo
from apps.finanzas.models import GastoObra
from apps.proveedores.models import FacturaProveedor
from apps.core.choices import EstadoGastoChoices, EstadoFacturaChoices


def generar_reporte_obra(obra, usuario=None) -> bytes:
    """Genera el PDF de una obra y devuelve los bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f'Reporte de Obra - {obra.nombre}',
        author='SGCO',
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Titulo',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=6,
        textColor=colors.HexColor('#0e1219'),
    ))
    styles.add(ParagraphStyle(
        name='Subtitulo',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name='Seccion',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0e1219'),
        spaceBefore=10,
        spaceAfter=6,
    ))

    story = []

    # ---------- ENCABEZADO ----------
    story.append(Paragraph(f'<b>Reporte de Obra</b>', styles['Titulo']))
    story.append(Paragraph(
        f'<b>{obra.nombre}</b> · Estado: {obra.get_estado_display()} '
        f'· Ubicación: {obra.ubicacion}',
        styles['Subtitulo'],
    ))

    # ---------- KPIs FINANCIEROS ----------
    resumen = resumen_financiero_obras(__import__('apps.obras.models', fromlist=['Obra']).Obra.objects.filter(pk=obra.pk))
    datos = resumen.get(obra.pk, {
        'asignado': Decimal('0.00'),
        'gastado': Decimal('0.00'),
        'saldo': Decimal('0.00'),
        'porcentaje': Decimal('0.00'),
    })
    ta = datos['asignado']
    tg = datos['gastado']
    s = datos['saldo']
    p = datos['porcentaje']

    kpi_data = [
        ['Total Asignado', 'Total Gastado (APROBADO)', 'Saldo Disponible', '% Ejecución'],
        [
            f'${ta:,.2f}',
            f'${tg:,.2f}',
            f'${s:,.2f}',
            f'{p:.2f}%',
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[4.2 * cm] * 4)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0e1219')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, 1), 12),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5 * cm))

    # ---------- INFORMACIÓN GENERAL ----------
    story.append(Paragraph('Información general', styles['Seccion']))
    info_data = [
        ['Inicio', obra.fecha_inicio.strftime('%d/%m/%Y')],
        ['Fin estimado', obra.fecha_fin_estimada.strftime('%d/%m/%Y')],
        ['Estado', obra.get_estado_display()],
        ['Ubicación', obra.ubicacion],
    ]
    info_table = Table(info_data, colWidths=[3 * cm, 14 * cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748b')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#e2e8f0')),
    ]))
    story.append(info_table)

    # ---------- ASIGNACIONES DE FONDO ----------
    story.append(Paragraph('Asignaciones de fondo', styles['Seccion']))
    asignaciones = AsignacionFondo.objects.filter(obra=obra).order_by('-fecha')
    if asignaciones.exists():
        asig_data = [['Fecha', 'Tipo', 'Monto', 'Referencia']]
        for a in asignaciones:
            asig_data.append([
                a.fecha.strftime('%d/%m/%Y'),
                a.get_tipo_display(),
                f'${a.monto:,.2f}',
                (a.referencia or '')[:50],
            ])
        asig_table = Table(asig_data, colWidths=[2.5 * cm, 4 * cm, 3 * cm, 7.5 * cm])
        asig_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
        ]))
        story.append(asig_table)
    else:
        story.append(Paragraph('Sin asignaciones registradas.', styles['Subtitulo']))

    # ---------- GASTOS (últimos 20) ----------
    story.append(Paragraph('Gastos (últimos 20)', styles['Seccion']))
    gastos = GastoObra.objects.filter(obra=obra).order_by('-fecha')[:20]
    if gastos.exists():
        gasto_data = [['Fecha', 'Tipo', 'Descripción', 'Monto', 'Estado']]
        for g in gastos:
            gasto_data.append([
                g.fecha.strftime('%d/%m/%Y'),
                g.get_tipo_gasto_display(),
                (g.descripcion or '')[:40],
                f'${g.monto:,.2f}',
                g.get_estado_display(),
            ])
        gasto_table = Table(gasto_data, colWidths=[2 * cm, 3 * cm, 5.5 * cm, 3 * cm, 3.5 * cm])
        gasto_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
        ]))
        story.append(gasto_table)
    else:
        story.append(Paragraph('Sin gastos registrados.', styles['Subtitulo']))

    # ---------- FACTURAS ----------
    story.append(Paragraph('Facturas de proveedores', styles['Seccion']))
    facturas = FacturaProveedor.objects.filter(obra=obra).select_related('proveedor').order_by('-fecha_emision')[:20]
    if facturas.exists():
        fact_data = [['Folio', 'Proveedor', 'Emisión', 'Total', 'Estado']]
        for f in facturas:
            fact_data.append([
                f.folio,
                (f.proveedor.nombre or '')[:40],
                f.fecha_emision.strftime('%d/%m/%Y'),
                f'${f.total:,.2f}',
                f.get_estado_display(),
            ])
        fact_table = Table(fact_data, colWidths=[2.5 * cm, 5.5 * cm, 2.5 * cm, 3 * cm, 3.5 * cm])
        fact_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
        ]))
        story.append(fact_table)
    else:
        story.append(Paragraph('Sin facturas registradas.', styles['Subtitulo']))

    # ---------- PIE DE PÁGINA ----------
    story.append(Spacer(1, 1 * cm))
    user_str = usuario.username if usuario else 'sistema'
    story.append(Paragraph(
        f'Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")} por {user_str} · SGCO',
        styles['Subtitulo'],
    ))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf