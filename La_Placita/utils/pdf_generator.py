"""
PDF Generator
Generate PDF invoices using reportlab
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,  HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
from pathlib import Path
from models.sale import Sale
from collections import defaultdict
from reportlab.platypus import Image
from pathlib import Path

LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo_laplacita.png"


class InvoiceGenerator:
    """Generate PDF invoices"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.create_custom_styles()
    
    def create_custom_styles(self):
        """Create custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#FF6B35'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_CENTER
        ))
        
        # Info style
        self.styles.add(ParagraphStyle(
            name='Info',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
        
        # Total style
        self.styles.add(ParagraphStyle(
            name='Total',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#FF6B35'),
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))
    
    def generate_invoice(self, sale: Sale, filename: str = None) -> str:
        """Generate PDF invoice for a sale"""

        if not filename:
            output_dir = Path.home() / '.restaurant_pos' / 'invoices'
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = output_dir / f"{sale.numero_factura}.pdf"

        doc = SimpleDocTemplate(
            str(filename), pagesize=A4,
            rightMargin=2*inch, leftMargin=2*inch,
            topMargin=1.5*inch, bottomMargin=1*inch
        )

        elements = []
        C_DARK   = colors.HexColor("#1F2937")
        C_GRAY   = colors.HexColor("#6B7280")
        C_LGRAY  = colors.HexColor("#F3F4F6")
        C_BORDER = colors.HexColor("#E5E7EB")
        C_ACCENT = colors.HexColor("#FF6B35")
        C_GREEN  = colors.HexColor("#10B981")
        C_WHITE  = colors.white

        styles = getSampleStyleSheet()

        def sty(name, **kw):
            return ParagraphStyle(name, parent=styles["Normal"], **kw)

        s_name     = sty("BizName", fontSize=18, fontName="Helvetica-Bold",
                        textColor=C_DARK, spaceAfter=2)
        s_sub      = sty("BizSub",  fontSize=9,  textColor=C_GRAY, spaceAfter=2)
        s_label    = sty("Label",   fontSize=8,  textColor=C_GRAY,
                        fontName="Helvetica-Bold", spaceAfter=1)
        s_value    = sty("Value",   fontSize=9,  textColor=C_DARK, spaceAfter=2)
        s_footer   = sty("Footer",  fontSize=8,  textColor=C_GRAY,
                        alignment=TA_CENTER)
        s_thanks   = sty("Thanks",  fontSize=10, textColor=C_DARK,
                        fontName="Helvetica-Bold", alignment=TA_CENTER,
                        spaceBefore=6, spaceAfter=2)

        # ── Encabezado: nombre + datos de factura en dos columnas ─────
        invoice_date = datetime.fromisoformat(
            sale.fecha_venta).strftime("%d/%m/%Y %H:%M")

        header_data = [[
            # Columna izquierda — empresa
            [
                Image(str(LOGO_PATH), width=1.2*inch, height=1.2*inch)
                if LOGO_PATH.exists() else Paragraph("La Placita", s_name),
                Spacer(1,4),
                Paragraph("Cafetería & Heladería", s_sub),
                Paragraph("Santa Fe, Santa Cruz — Bolivia", s_sub),
                Paragraph("+591 ", s_sub),
            ],
            # Columna derecha — datos de factura
            [
                Paragraph("FACTURA", sty("FT", fontSize=14,
                        fontName="Helvetica-Bold", textColor=C_ACCENT,
                        alignment=TA_RIGHT)),
                        Spacer(1,4),
                Paragraph(sale.numero_factura,
                        sty("FN", fontSize=9, textColor=C_GRAY,
                            alignment=TA_RIGHT)),
                Spacer(1, 6),
                Paragraph(f"<b>Fecha:</b> {invoice_date}",
                        sty("FD", fontSize=9, textColor=C_DARK,
                            alignment=TA_RIGHT)),
                Paragraph(f"<b>Cliente:</b> {sale.cliente or 'Cliente General'}",
                        sty("FC", fontSize=9, textColor=C_DARK,
                            alignment=TA_RIGHT)),
                Paragraph(f"<b>Pago:</b> {sale.metodo_pago.title()}",
                        sty("FP", fontSize=9, textColor=C_DARK,
                            alignment=TA_RIGHT)),
            ],
        ]]

        header_table = Table(header_data, colWidths=[8*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ("VALIGN",  (0,0), (-1,-1), "TOP"),
            ("PADDING", (0,0), (-1,-1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.4*inch))
        elements.append(HRFlowable(width="100%", thickness=1.5,
                                color=C_ACCENT, spaceAfter=14))

        # ── Agrupar productos repetidos ───────────────────────────────
        from collections import defaultdict
        agrupado = defaultdict(lambda: {"cantidad": 0, "precio": 0, "subtotal": 0})
        for item in sale.items:
            key = item.producto_nombre
            agrupado[key]["cantidad"]  += item.cantidad
            agrupado[key]["precio"]     = item.precio_unitario  # mismo precio
            agrupado[key]["subtotal"]  += item.subtotal

        # ── Tabla de productos ─────────────────────────────────────────
        table_data = [["Producto", "Cant.", "Precio Unit.", "Subtotal"]]
        for nombre, vals in agrupado.items():
            table_data.append([
                nombre,
                str(vals["cantidad"]),
                f"Bs {vals['precio']:,.2f}",
                f"Bs {vals['subtotal']:,.2f}",
            ])

        prod_table = Table(
            table_data,
            colWidths=[8.5*cm, 1.8*cm, 3.2*cm, 3*cm]
        )
        prod_table.setStyle(TableStyle([
            # Encabezado
            ("BACKGROUND",    (0,0), (-1,0), C_DARK),
            ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,0), 9),
            ("ALIGN",         (0,0), (0,0),  "LEFT"),
            ("ALIGN",         (1,0), (-1,0), "RIGHT"),
            ("BOTTOMPADDING", (0,0), (-1,0), 8),
            ("TOPPADDING",    (0,0), (-1,0), 8),
            # Cuerpo
            ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
            ("FONTSIZE",      (0,1), (-1,-1), 9),
            ("ALIGN",         (0,1), (0,-1),  "LEFT"),
            ("ALIGN",         (1,1), (-1,-1), "RIGHT"),
            ("TOPPADDING",    (0,1), (-1,-1), 6),
            ("BOTTOMPADDING", (0,1), (-1,-1), 6),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_LGRAY]),
            ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ]))
        elements.append(prod_table)
        elements.append(Spacer(1, 0.2*inch))

        # ── Totales ────────────────────────────────────────────────────
        totals_data = [["Subtotal:", f"Bs {sale.subtotal:,.2f}"]]
        if sale.descuento > 0:
            totals_data.append(["Descuento:", f"- Bs {sale.descuento:,.2f}"])
        totals_data.append(["TOTAL:", f"Bs {sale.total:,.2f}"])

        totals_table = Table(totals_data, colWidths=[12.5*cm, 4*cm])
        totals_style = TableStyle([
            ("ALIGN",         (0,0), (-1,-1), "RIGHT"),
            ("FONTNAME",      (0,0), (-1,-2), "Helvetica"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("TEXTCOLOR",     (0,0), (-1,-2), C_GRAY),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            # Fila TOTAL
            ("FONTNAME",      (0,-1), (-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,-1), (-1,-1), 12),
            ("TEXTCOLOR",     (0,-1), (-1,-1), C_DARK),
            ("LINEABOVE",     (0,-1), (-1,-1), 1.5, C_DARK),
            ("TOPPADDING",    (0,-1), (-1,-1), 8),
        ])
        totals_table.setStyle(totals_style)
        elements.append(totals_table)

        # ── Método de pago mixto desglose ─────────────────────────────
        if sale.metodo_pago == "mixto" and hasattr(sale, 'monto_efectivo'):
            elements.append(Spacer(1, 0.1*inch))
            mixto_data = []
            if getattr(sale, 'monto_efectivo', 0):
                mixto_data.append(["  Efectivo:", f"Bs {sale.monto_efectivo:,.2f}"])
            if getattr(sale, 'monto_qr', 0):
                mixto_data.append(["  QR:", f"Bs {sale.monto_qr:,.2f}"])
            if mixto_data:
                mt = Table(mixto_data, colWidths=[12.5*cm, 4*cm])
                mt.setStyle(TableStyle([
                    ("ALIGN",    (0,0), (-1,-1), "RIGHT"),
                    ("FONTSIZE", (0,0), (-1,-1), 8),
                    ("TEXTCOLOR",(0,0), (-1,-1), C_GRAY),
                ]))
                elements.append(mt)

        # ── Pie ────────────────────────────────────────────────────────
        elements.append(Spacer(1, 0.5*inch))
        elements.append(HRFlowable(width="100%", thickness=0.5,
                                color=C_BORDER, spaceAfter=10))
        elements.append(Paragraph("¡Gracias por su visita!", s_thanks))
        elements.append(Paragraph(
            f"La Placita Cafetería  ·  {datetime.now().strftime('%d/%m/%Y')}",
            s_footer))

        doc.build(elements)
        print(f"✓ Invoice generated: {filename}")
        return str(filename)
    
    def generate_sales_report(self, sales: list, filename: str, 
                             fecha_desde: str = None, fecha_hasta: str = None) -> str:
        """Generate sales report PDF"""
        
        doc = SimpleDocTemplate(
            filename,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        elements = []
        
        # Header
        elements.append(Paragraph("📊 Reporte de Ventas", self.styles['CustomTitle']))
        
        # Date range
        if fecha_desde and fecha_hasta:
            period = f"Periodo: {fecha_desde} - {fecha_hasta}"
        else:
            period = "Todas las ventas"
        
        elements.append(Paragraph(period, self.styles['CustomSubtitle']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary
        total_ventas = len(sales)
        total_ingresos = sum(sale.total for sale in sales)
        promedio = total_ingresos / total_ventas if total_ventas > 0 else 0
        
        summary = f"""
        <b>Total de ventas:</b> {total_ventas}<br/>
        <b>Ingresos totales:</b> Bs {total_ingresos:.2f}<br/>
        <b>Venta promedio:</b> Bs {promedio:.2f}
        """
        elements.append(Paragraph(summary, self.styles['Info']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Sales table
        if sales:
            table_data = [['Factura', 'Fecha', 'Cliente', 'Método', 'Total']]
            
            for sale in sales:
                fecha = datetime.fromisoformat(sale.fecha_venta).strftime("%d/%m/%Y")
                table_data.append([
                    sale.numero_factura,
                    fecha,
                    sale.cliente,
                    sale.metodo_pago.title(),
                    f"Bs {sale.total:.2f}"
                ])
            
            table = Table(table_data, colWidths=[1.5*inch, 1*inch, 2*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF6B35')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
            ]))
            
            elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        print(f"✓ Sales report generated: {filename}")
        return filename


# Convenience function
def generate_invoice(sale: Sale, filename: str = None) -> str:
    """Generate invoice PDF"""
    generator = InvoiceGenerator()
    return generator.generate_invoice(sale, filename)


def generate_sales_report(sales: list, filename: str, 
                          fecha_desde: str = None, fecha_hasta: str = None) -> str:
    """Generate sales report PDF"""
    generator = InvoiceGenerator()
    return generator.generate_sales_report(sales, filename, fecha_desde, fecha_hasta)


if __name__ == '__main__':
    # Test PDF generation
    from models.sale import Sale
    
    print("Testing PDF generation...")
    
    # Get a sale
    sales = Sale.get_all(limit=1)
    
    if sales:
        sale = Sale.get_by_id(sales[0].id)
        if sale:
            pdf_file = generate_invoice(sale)
            print(f"✓ Test invoice created: {pdf_file}")
    else:
        print("No sales found to test")
