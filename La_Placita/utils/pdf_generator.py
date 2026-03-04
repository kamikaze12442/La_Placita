"""
PDF Generator
Generate PDF invoices using reportlab
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
from pathlib import Path
from models.sale import Sale


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
            # Generate filename
            output_dir = Path.home() / '.restaurant_pos' / 'invoices'
            output_dir.mkdir(exist_ok=True)
            filename = output_dir / f"{sale.numero_factura}.pdf"
        
        # Create PDF
        doc = SimpleDocTemplate(
            str(filename),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for elements
        elements = []
        
        # Header
        elements.append(Paragraph("🍽️ Restaurant POS", self.styles['CustomTitle']))
        elements.append(Paragraph("Sistema de Punto de Venta", self.styles['CustomSubtitle']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Company info
        company_info = """
        <b>Dirección:</b> Calle Principal #123<br/>
        <b>Teléfono:</b> +591 12345678<br/>
        <b>Email:</b> info@restaurant.com
        """
        elements.append(Paragraph(company_info, self.styles['Info']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Invoice info
        invoice_date = datetime.fromisoformat(sale.fecha_venta).strftime("%d/%m/%Y %H:%M")
        
        invoice_info = f"""
        <b>FACTURA: {sale.numero_factura}</b><br/>
        <b>Fecha:</b> {invoice_date}<br/>
        <b>Cliente:</b> {sale.cliente}<br/>
        <b>Método de Pago:</b> {sale.metodo_pago.title()}
        """
        elements.append(Paragraph(invoice_info, self.styles['Info']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Items table
        table_data = [['#', 'Producto', 'Cantidad', 'Precio Unit.', 'Subtotal']]
        
        for i, item in enumerate(sale.items, 1):
            table_data.append([
                str(i),
                item.producto_nombre,
                str(item.cantidad),
                f"Bs {item.precio_unitario:.2f}",
                f"Bs {item.subtotal:.2f}"
            ])
        
        # Create table
        table = Table(table_data, colWidths=[0.5*inch, 3*inch, 1*inch, 1.2*inch, 1.2*inch])
        
        # Style table
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF6B35')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Body
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
            
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Totals
        totals_data = [
            ['Subtotal:', f"Bs {sale.subtotal:.2f}"],
        ]
        
        if sale.descuento > 0:
            totals_data.append(['Descuento:', f"Bs {sale.descuento:.2f}"])
        
        totals_data.append(['<b>TOTAL:</b>', f"<b>Bs {sale.total:.2f}</b>"])
        
        totals_table = Table(totals_data, colWidths=[4.5*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#FF6B35')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#FF6B35')),
        ]))
        
        elements.append(totals_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Footer
        footer = """
        <para alignment="center">
        <b>¡Gracias por su compra!</b><br/>
        Este documento es una factura válida
        </para>
        """
        elements.append(Paragraph(footer, self.styles['Info']))
        
        # Build PDF
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
