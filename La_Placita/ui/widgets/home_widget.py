"""
Home Widget - Dashboard
Main dashboard with statistics, charts, and recent activity
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from datetime import datetime, timedelta
from models.sale import Sale
from models.product import Product
from database.connection import db


class StatCard(QFrame):
    """Redesigned stat card matching web version"""
    
    def __init__(self, icon, value, label, color="#FF6B35"):
        super().__init__()
        self.setObjectName("stat-card")
        self.setStyleSheet(f"""
            QFrame#stat-card {{
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 24px;
                min-height: 120px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            background-color: {color}15;
            color: {color};
            font-size: 32px;
            padding: 12px;
            border-radius: 12px;
            min-width: 26px;
            max-width: 26px;
            min-height: 26px;
            max-height: 26px;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #1F2937;
        """)
        layout.addWidget(value_label)
        
        # Label
        label_label = QLabel(label)
        label_label.setStyleSheet("""
            font-size: 14px;
            color: #6B7280;
            font-weight: 500;
        """)
        layout.addWidget(label_label)
        
        layout.addStretch()


class TopItemCard(QFrame):
    """Card for top items (plates, drinks, extras)"""
    
    def __init__(self, title, items, color="#FF6B35"):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Header
        header = QLabel(title)
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #1F2937;
        """)
        layout.addWidget(header)
        
        # Items list
        if not items:
            no_data = QLabel("Sin datos disponibles")
            no_data.setStyleSheet("color: #9CA3AF; font-size: 14px; padding: 20px 0;")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_data)
        else:
            for i, item in enumerate(items[:5], 1):
                item_widget = self._create_item_row(i, item, color)
                layout.addWidget(item_widget)
        
        layout.addStretch()
    
    def _create_item_row(self, rank, item, color):
        """Create a row for top item"""
        widget = QWidget()
        widget_layout = QHBoxLayout(widget)
        widget_layout.setContentsMargins(0, 0, 0, 0)
        widget_layout.setSpacing(12)
        
        # Rank badge
        rank_label = QLabel(str(rank))
        rank_label.setFixedSize(32, 32)
        rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if rank == 1:
            bg_color = "#FFD700"  # Gold
        elif rank == 2:
            bg_color = "#C0C0C0"  # Silver
        elif rank == 3:
            bg_color = "#CD7F32"  # Bronze
        else:
            bg_color = "#E5E7EB"  # Gray
        
        rank_label.setStyleSheet(f"""
            background-color: {bg_color};
            color: white;
            font-weight: 700;
            border-radius: 16px;
            font-size: 14px;
        """)
        widget_layout.addWidget(rank_label)
        
        # Product info
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        name_label = QLabel(item['nombre'])
        name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1F2937;")
        info_layout.addWidget(name_label)
        
        detail_label = QLabel(f"{item['cantidad_vendida']} unidades · Bs {item['ingresos']:.2f}")
        detail_label.setStyleSheet("font-size: 12px; color: #6B7280;")
        info_layout.addWidget(detail_label)
        
        widget_layout.addWidget(info_widget)
        widget_layout.addStretch()
        
        return widget


class HomeWidget(QWidget):
    """Redesigned dashboard matching web version"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        # Content widget
        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(40, 30, 40, 40)
        main_layout.setSpacing(30)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel("Dashboard")
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: 700;
            color: #1F2937;
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel(f"Resumen general de tu restaurante · {datetime.now().strftime('%d de %B, %Y')}")
        subtitle.setStyleSheet("""
            font-size: 14px;
            color: #6B7280;
        """)
        header_layout.addWidget(subtitle)
        
        main_layout.addLayout(header_layout)
        
        # Stats cards (4 cards in a row)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # Get data
        stats = self.get_dashboard_stats()
        
        # Card 1: Ventas de Hoy
        card1 = StatCard(
            "💰",
            f"Bs {stats['ventas_hoy']:.2f}",
            "Ventas de Hoy",
            "#FF6B35"
        )
        stats_layout.addWidget(card1)
        
        # Card 2: Órdenes Completadas
        card2 = StatCard(
            "🎫",
            str(stats['ordenes_completadas']),
            "Órdenes Completadas",
            "#10B981"
        )
        stats_layout.addWidget(card2)
        
        # Card 3: Plato del Día
        card3 = StatCard(
            "🍽️",
            stats['plato_del_dia']['nombre'] if stats['plato_del_dia'] else "N/A",
            "Plato del Día",
            "#3B82F6"
        )
        stats_layout.addWidget(card3)
        
        # Card 4: Ticket Promedio
        card4 = StatCard(
            "📊",
            f"Bs {stats['ticket_promedio']:.2f}",
            "Ticket Promedio",
            "#F59E0B"
        )
        stats_layout.addWidget(card4)
        
        main_layout.addLayout(stats_layout)
        
        # Top items section (3 columns)
        top_items_layout = QHBoxLayout()
        top_items_layout.setSpacing(20)
        
        # Top 5 Platos
        top_plates = TopItemCard(
            "🏆 Top 5 Platos Más Populares",
            stats['top_platos'],
            "#FF6B35"
        )
        top_items_layout.addWidget(top_plates)
        
        # Top 5 Bebidas
        top_drinks = TopItemCard(
            "🥤 Top 5 Bebidas Más Populares",
            stats['top_bebidas'],
            "#3B82F6"
        )
        top_items_layout.addWidget(top_drinks)
        
        # Top 5 Extras
        top_extras = TopItemCard(
            "🍟 Top 5 Extras Más Populares",
            stats['top_extras'],
            "#10B981"
        )
        top_items_layout.addWidget(top_extras)
        
        main_layout.addLayout(top_items_layout)
        
        # Charts section (2 charts side by side)
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(20)
        
        # Sales chart
        sales_chart = self.create_sales_chart(stats['ventas_mes'])
        charts_layout.addWidget(sales_chart, 2)
        
        # Payment methods chart
        payment_chart = self.create_payment_methods_chart(stats['metodos_pago'])
        charts_layout.addWidget(payment_chart, 1)
        
        main_layout.addLayout(charts_layout)
        
        # Recent sales table
        recent_sales_widget = self.create_recent_sales_table(stats['ventas_recientes'])
        main_layout.addWidget(recent_sales_widget)
        
        scroll.setWidget(content)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
    
    def get_dashboard_stats(self):
        """Get all dashboard statistics"""
        today = datetime.now().date()
        month_start = datetime.now().replace(day=1).date()
        
        # Ventas de hoy
        query_today = """
            SELECT COALESCE(SUM(total), 0) as total, COUNT(*) as count
            FROM ventas 
            WHERE DATE(fecha_venta) = ? AND estado = 'completada'
        """
        today_result = db.fetch_one(query_today, (str(today),))
        ventas_hoy = float(today_result['total']) if today_result else 0.0
        ordenes_completadas = int(today_result['count']) if today_result else 0
        
        # Ticket promedio
        ticket_promedio = ventas_hoy / ordenes_completadas if ordenes_completadas > 0 else 0.0
        
        # Plato del día (más vendido hoy)
        query_plato_dia = """
            SELECT p.nombre, SUM(dv.cantidad) as cantidad
            FROM detalle_ventas dv
            JOIN productos p ON dv.producto_id = p.id
            JOIN ventas v ON dv.venta_id = v.id
            JOIN categorias c ON p.categoria_id = c.id
            WHERE DATE(v.fecha_venta) = ? AND c.nombre = 'Comidas'
            GROUP BY p.nombre
            ORDER BY cantidad DESC
            LIMIT 1
        """
        plato_dia_result = db.fetch_one(query_plato_dia, (str(today),))
        plato_del_dia = {'nombre': plato_dia_result['nombre']} if plato_dia_result else None
        
        # Top productos por categoría
        top_platos = self.get_top_by_category('Comidas')
        top_bebidas = self.get_top_by_category('Bebidas')
        top_extras = self.get_top_by_category('Extras')
        
        # Ventas del mes (últimos 30 días)
        ventas_mes = self.get_sales_by_day(30)
        
        # Métodos de pago
        query_payment = """
            SELECT metodo_pago, COUNT(*) as cantidad, SUM(total) as total
            FROM ventas
            WHERE DATE(fecha_venta) >= ? AND estado = 'completada'
            GROUP BY metodo_pago
        """
        payment_result = db.fetch_all(query_payment, (str(month_start),))
        metodos_pago = {
            'efectivo': 0,
            'qr': 0,
            'tarjeta': 0
        }
        for row in payment_result:
            metodos_pago[row['metodo_pago']] = int(row['cantidad'])
        
        # Ventas recientes
        ventas_recientes = self.get_recent_sales(10)
        
        return {
            'ventas_hoy': ventas_hoy,
            'ordenes_completadas': ordenes_completadas,
            'plato_del_dia': plato_del_dia,
            'ticket_promedio': ticket_promedio,
            'top_platos': top_platos,
            'top_bebidas': top_bebidas,
            'top_extras': top_extras,
            'ventas_mes': ventas_mes,
            'metodos_pago': metodos_pago,
            'ventas_recientes': ventas_recientes
        }
    
    def get_top_by_category(self, category_name, limit=5):
        """Get top products by category"""
        query = """
            SELECT p.nombre, SUM(dv.cantidad) as cantidad_vendida, 
                   SUM(dv.subtotal) as ingresos
            FROM detalle_ventas dv
            JOIN productos p ON dv.producto_id = p.id
            JOIN categorias c ON p.categoria_id = c.id
            JOIN ventas v ON dv.venta_id = v.id
            WHERE c.nombre = ? AND v.estado = 'completada'
            GROUP BY p.id, p.nombre
            ORDER BY cantidad_vendida DESC
            LIMIT ?
        """
        results = db.fetch_all(query, (category_name, limit))
        return [dict(row) for row in results]
    
    def get_sales_by_day(self, days=30):
        """Get sales grouped by day for the last N days"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        query = """
            SELECT DATE(fecha_venta) as fecha, SUM(total) as total
            FROM ventas
            WHERE DATE(fecha_venta) BETWEEN ? AND ? AND estado = 'completada'
            GROUP BY DATE(fecha_venta)
            ORDER BY fecha
        """
        results = db.fetch_all(query, (str(start_date), str(end_date)))
        
        # Create dict with all days
        sales_dict = {}
        current_date = start_date
        while current_date <= end_date:
            sales_dict[str(current_date)] = 0.0
            current_date += timedelta(days=1)
        
        # Fill with actual data
        for row in results:
            sales_dict[row['fecha']] = float(row['total'])
        
        return sales_dict
    
    def get_recent_sales(self, limit=10):
        """Get recent sales with details"""
        query = """
            SELECT v.id, v.numero_factura, v.cliente, v.total, v.metodo_pago, v.fecha_venta
            FROM ventas v
            WHERE v.estado = 'completada'
            ORDER BY v.fecha_venta DESC
            LIMIT ?
        """
        results = db.fetch_all(query, (limit,))
        
        sales = []
        for row in results:
            # Get products for this sale
            query_products = """
                SELECT p.nombre, dv.cantidad
                FROM detalle_ventas dv
                JOIN productos p ON dv.producto_id = p.id
                WHERE dv.venta_id = ?
            """
            products = db.fetch_all(query_products, (row['id'],))
            products_str = ", ".join([f"{p['nombre']} ({p['cantidad']})" for p in products])
            
            sales.append({
                'orden': row['numero_factura'],
                'cliente': row['cliente'] or 'Cliente General',
                'productos': products_str,
                'total': float(row['total']),
                'metodo_pago': row['metodo_pago'],
                'fecha': row['fecha_venta']
            })
        
        return sales
    
    def create_sales_chart(self, sales_data):
        """Create bar chart for monthly sales"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("📈 Ventas del Mes")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #1F2937;
        """)
        layout.addWidget(title)
        
        # Create chart
        series = QBarSeries()
        bar_set = QBarSet("Ventas")
        bar_set.setColor("#FF6B35")
        
        categories = []
        for date_str in sorted(sales_data.keys())[-30:]:  # Last 30 days
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            categories.append(date_obj.strftime("%d/%m"))
            bar_set.append(sales_data[date_str])
        
        series.append(bar_set)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundVisible(False)
        
        # Axis
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setLabelFormat("Bs %.0f")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        
        # Chart view
        from PySide6.QtGui import QPainter
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(300)
        
        layout.addWidget(chart_view)
        
        return widget
    
    def create_payment_methods_chart(self, payment_data):
        """Create pie chart for payment methods"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("💳 Métodos de Pago")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #1F2937;
        """)
        layout.addWidget(title)
        
        # Create pie chart
        series = QPieSeries()
        
        total = sum(payment_data.values())
        if total > 0:
            if payment_data['efectivo'] > 0:
                slice_efectivo = series.append(f"Efectivo\n{payment_data['efectivo']}", payment_data['efectivo'])
                slice_efectivo.setColor("#10B981")
                slice_efectivo.setLabelVisible(True)
            
            if payment_data['qr'] > 0:
                slice_qr = series.append(f"QR\n{payment_data['qr']}", payment_data['qr'])
                slice_qr.setColor("#3B82F6")
                slice_qr.setLabelVisible(True)
            
            if payment_data['tarjeta'] > 0:
                slice_tarjeta = series.append(f"Tarjeta\n{payment_data['tarjeta']}", payment_data['tarjeta'])
                slice_tarjeta.setColor("#F59E0B")
                slice_tarjeta.setLabelVisible(True)
        else:
            series.append("Sin datos", 1)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.setBackgroundVisible(False)
        
        # Chart view
        from PySide6.QtGui import QPainter
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(300)
        
        layout.addWidget(chart_view)
        
        return widget
    
    def create_recent_sales_table(self, sales):
        """Create recent sales table"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("📋 Ventas Recientes")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #1F2937;
        """)
        layout.addWidget(title)
        
        # Table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Orden", "Cliente", "Productos", "Total", "Método de Pago"])
        table.setRowCount(len(sales))
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        
        # Set column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # Populate table
        for row, sale in enumerate(sales):
            # Orden
            orden_item = QTableWidgetItem(sale['orden'])
            orden_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            table.setItem(row, 0, orden_item)
            
            # Cliente
            cliente_item = QTableWidgetItem(sale['cliente'])
            table.setItem(row, 1, cliente_item)
            
            # Productos
            productos_item = QTableWidgetItem(sale['productos'])
            table.setItem(row, 2, productos_item)
            
            # Total
            total_item = QTableWidgetItem(f"Bs {sale['total']:.2f}")
            total_item.setForeground(Qt.GlobalColor.darkGreen)
            total_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row, 3, total_item)
            
            # Método de pago
            metodo_icons = {
                'efectivo': '💵 Efectivo',
                'qr': '💱 QR',
                'tarjeta': '💳 Tarjeta'
            }
            metodo_item = QTableWidgetItem(metodo_icons.get(sale['metodo_pago'], sale['metodo_pago']))
            table.setItem(row, 4, metodo_item)
        
        # Set row height
        for row in range(table.rowCount()):
            table.setRowHeight(row, 50)
        
        table.setMinimumHeight(400)
        layout.addWidget(table)
        
        return widget