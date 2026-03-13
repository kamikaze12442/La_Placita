"""
Sales Widget - Redesigned
Complete sales management with statistics, filters, charts and reports
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit,
    QComboBox, QDateEdit, QScrollArea, QHeaderView, QDialog,
    QDialogButtonBox, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QPainter, QColor
from PySide6.QtCharts import QChart, QChartView, QPieSeries
from datetime import datetime, timedelta
from models.sale import Sale
from models.user import User
from database.connection import db
from utils.pdf_generator import InvoiceGenerator
from utils.excel_exporter import ExcelExporter


class StatCard(QFrame):
    """Stat card with comparison indicator"""
    
    def __init__(self, icon, value, label, change=None, change_positive=True):
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
            background-color: #FF6B35;
            color: #FF6B35;
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
        
        # Value with change indicator
        value_layout = QHBoxLayout()
        value_layout.setSpacing(8)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #1F2937;")
        value_layout.addWidget(value_label)
        
        if change is not None:
            change_color = "#10B981" if change_positive else "#EF4444"
            change_arrow = "↑" if change_positive else "↓"
            change_label = QLabel(f"{change_arrow} {abs(change):.1f}%")
            change_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {change_color};")
            value_layout.addWidget(change_label)
        
        value_layout.addStretch()
        layout.addLayout(value_layout)
        
        # Label
        label_label = QLabel(label)
        label_label.setStyleSheet("font-size: 14px; color: #6B7280; font-weight: 500;")
        layout.addWidget(label_label)
        
        layout.addStretch()


class TopProductCard(QFrame):
    """Card showing top products"""
    
    def __init__(self, title, products, icon="🏆"):
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
        header = QLabel(f"{icon} {title}")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        layout.addWidget(header)
        
        # Products
        if not products:
            no_data = QLabel("Sin datos")
            no_data.setStyleSheet("color: #9CA3AF; padding: 20px 0;")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_data)
        else:
            for i, prod in enumerate(products[:3], 1):
                prod_widget = self._create_product_row(i, prod)
                layout.addWidget(prod_widget)
        
        layout.addStretch()
    
    def _create_product_row(self, rank, product):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Rank
        rank_label = QLabel(str(rank))
        rank_label.setFixedSize(32, 32)
        rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        colors = {1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32"}
        rank_label.setStyleSheet(f"""
            background-color: {colors.get(rank, '#E5E7EB')};
            color: white;
            font-weight: 700;
            border-radius: 16px;
            font-size: 14px;
        """)
        layout.addWidget(rank_label)
        
        # Info
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        name = QLabel(product['nombre'])
        name.setStyleSheet("font-size: 14px; font-weight: 600; color: #1F2937;")
        info_layout.addWidget(name)
        
        detail = QLabel(f"{product['cantidad']} unidades · Bs {product['total']:.2f}")
        detail.setStyleSheet("font-size: 12px; color: #6B7280;")
        info_layout.addWidget(detail)
        
        layout.addWidget(info_widget)
        layout.addStretch()
        
        return widget


class SalesWidget(QWidget):
    """Redesigned sales widget with advanced features"""
    
    def __init__(self):
        super().__init__()
        self.showing_summary = False
        self.current_sales = []
        self.init_ui()
        self.load_sales()
    
    def init_ui(self):
        """Initialize UI"""
        # Main scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        # Content
        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(40, 30, 40, 40)
        self.main_layout.setSpacing(30)
        
        # Header
        self._create_header()
        
        # Stats cards
        self.stats_container = QWidget()
        self.stats_layout = QHBoxLayout(self.stats_container)
        self.stats_layout.setSpacing(20)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.stats_container)
        
        # Filters
        self._create_filters()
        
        # Action buttons
        self._create_action_buttons()
        
        # Summary section (initially hidden)
        self.summary_widget = QWidget()
        self.summary_layout = QVBoxLayout(self.summary_widget)
        self.summary_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_layout.setSpacing(20)
        self.summary_widget.hide()
        self.main_layout.addWidget(self.summary_widget)
        
        # Table
        self._create_table()
        
        scroll.setWidget(content)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
    
    def _create_header(self):
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel("Ventas")
        title.setStyleSheet("font-size: 32px; font-weight: 700; color: #1F2937;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("Gestión completa de ventas y facturación")
        subtitle.setStyleSheet("font-size: 14px; color: #6B7280;")
        header_layout.addWidget(subtitle)
        
        self.main_layout.addLayout(header_layout)
    
    def _create_filters(self):
        """Create filter section"""
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        filter_layout = QVBoxLayout(filter_frame)
        filter_layout.setSpacing(16)
        
        # Title
        filter_title = QLabel("🔍 Filtros de Búsqueda")
        filter_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        filter_layout.addWidget(filter_title)
        
        # Filters row 1
        row1 = QHBoxLayout()
        row1.setSpacing(16)
        
        # ID Factura
        id_container = QVBoxLayout()
        id_label = QLabel("ID Factura")
        id_label.setStyleSheet("font-weight: 600; color: #4B5563; font-size: 13px;")
        self.id_filter = QLineEdit()
        self.id_filter.setPlaceholderText("FACT-20251208-0001")
        id_container.addWidget(id_label)
        id_container.addWidget(self.id_filter)
        row1.addLayout(id_container)
        
        # Cajero
        cajero_container = QVBoxLayout()
        cajero_label = QLabel("Cajero")
        cajero_label.setStyleSheet("font-weight: 600; color: #4B5563; font-size: 13px;")
        self.cajero_filter = QComboBox()
        self.cajero_filter.addItem("Todos los cajeros", None)
        cajero_container.addWidget(cajero_label)
        cajero_container.addWidget(self.cajero_filter)
        row1.addLayout(cajero_container)
        
        # Load cajeros
        users = User.get_all()
        for user in users:
            self.cajero_filter.addItem(user.nombre, user.id)
        
        # Método de pago
        metodo_container = QVBoxLayout()
        metodo_label = QLabel("Método de Pago")
        metodo_label.setStyleSheet("font-weight: 600; color: #4B5563; font-size: 13px;")
        self.metodo_filter = QComboBox()
        self.metodo_filter.addItem("Todos los métodos", None)
        self.metodo_filter.addItem("💵 Efectivo", "efectivo")
        self.metodo_filter.addItem("💱 QR", "qr")
        #self.metodo_filter.addItem("💳 Tarjeta", "tarjeta")
        self.metodo_filter.addItem("⚡ Mixto", "mixto")
        metodo_container.addWidget(metodo_label)
        metodo_container.addWidget(self.metodo_filter)
        row1.addLayout(metodo_container)
        
        filter_layout.addLayout(row1)
        
        # Filters row 2
        row2 = QHBoxLayout()
        row2.setSpacing(16)
        
        # Fecha inicial
        fecha_ini_container = QVBoxLayout()
        fecha_ini_label = QLabel("Fecha Inicial")
        fecha_ini_label.setStyleSheet("font-weight: 600; color: #4B5563; font-size: 13px;")
        self.fecha_inicial = QDateEdit()
        self.fecha_inicial.setCalendarPopup(True)
        self.fecha_inicial.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_inicial.setDisplayFormat("dd/MM/yyyy")
        fecha_ini_container.addWidget(fecha_ini_label)
        fecha_ini_container.addWidget(self.fecha_inicial)
        row2.addLayout(fecha_ini_container)
        
        # Fecha final
        fecha_fin_container = QVBoxLayout()
        fecha_fin_label = QLabel("Fecha Final")
        fecha_fin_label.setStyleSheet("font-weight: 600; color: #4B5563; font-size: 13px;")
        self.fecha_final = QDateEdit()
        self.fecha_final.setCalendarPopup(True)
        self.fecha_final.setDate(QDate.currentDate())
        self.fecha_final.setDisplayFormat("dd/MM/yyyy")
        fecha_fin_container.addWidget(fecha_fin_label)
        fecha_fin_container.addWidget(self.fecha_final)
        row2.addLayout(fecha_fin_container)
        
        # Filter button
        filter_btn = QPushButton("🔍 Filtrar Resultados")
        filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: 600;
                min-height: 44px;
                margin-top: 25px;
            }
            QPushButton:hover { background-color: #E85D2F; }
        """)
        filter_btn.clicked.connect(self.load_sales)
        row2.addWidget(filter_btn)
        
        filter_layout.addLayout(row2)
        self.main_layout.addWidget(filter_frame)
    
    def _create_action_buttons(self):
        """Create action buttons"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        # Resumen/Mostrar button
        self.summary_btn = QPushButton("📊 Resumen")
        self.summary_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: 600;
                min-height: 44px;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)
        self.summary_btn.clicked.connect(self.toggle_summary)
        buttons_layout.addWidget(self.summary_btn)
        
        # Imprimir button
        print_btn = QPushButton("🖨️ Imprimir")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: 600;
                min-height: 44px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        print_btn.clicked.connect(self.print_report)
        buttons_layout.addWidget(print_btn)
        
        # PDF button
        pdf_btn = QPushButton("📄 Generar PDF")
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: 600;
                min-height: 44px;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        pdf_btn.clicked.connect(self.generate_pdf)
        buttons_layout.addWidget(pdf_btn)
        
        buttons_layout.addStretch()
        self.main_layout.addLayout(buttons_layout)
    
    def _create_table(self):
        """Create sales table"""
        self.table = QTableWidget()
        self.table.setColumnCount(8)


        self.table.setHorizontalHeaderLabels([
            "ID Factura", "Cajero", "Cliente", "Pedido", 
            "Total", "Método", "Fecha", "Acciones"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(1200)
        
        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        #self.table.verticalHeader().setDefaultSectionSize(150)
        self.table.setColumnWidth(7, 180)
        self.main_layout.addWidget(self.table)
    
    def load_sales(self):
        """Load sales with filters"""
        # Get filters
        id_factura = self.id_filter.text().strip() or None
        cajero_id = self.cajero_filter.currentData()
        metodo = self.metodo_filter.currentData()
        fecha_desde = self.fecha_inicial.date().toString("yyyy-MM-dd")
        fecha_hasta = self.fecha_final.date().toString("yyyy-MM-dd")
        
        # Build query
        query = """
            SELECT v.*, u.nombre as cajero_nombre
            FROM ventas v
            LEFT JOIN usuarios u ON v.usuario_id = u.id
            WHERE DATE(v.fecha_venta) BETWEEN ? AND ?
        """
        params = [fecha_desde, fecha_hasta]
        
        if id_factura:
            query += " AND v.numero_factura LIKE ?"
            params.append(f"%{id_factura}%")
        
        if cajero_id:
            query += " AND v.usuario_id = ?"
            params.append(cajero_id)
        
        if metodo:
            query += " AND v.metodo_pago = ?"
            params.append(metodo)
        
        query += " ORDER BY v.fecha_venta DESC"
        
        results = db.fetch_all(query, tuple(params))
        self.current_sales = [dict(row) for row in results]
        
        # Update stats
        self._update_stats()
        
        # Update table
        self._update_table()
    
    def _update_stats(self):
        """Update stat cards"""
        # Clear existing stats
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not self.current_sales:
            return
        
        # Calculate today's stats
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        today_sales = [s for s in self.current_sales if datetime.fromisoformat(s['fecha_venta']).date() == today]
        yesterday_sales = [s for s in self.current_sales if datetime.fromisoformat(s['fecha_venta']).date() == yesterday]
        
        # Ingreso total del día
        today_total = sum(s['total'] for s in today_sales)
        yesterday_total = sum(s['total'] for s in yesterday_sales)
        change_percent = ((today_total - yesterday_total) / yesterday_total * 100) if yesterday_total > 0 else 0
        
        card1 = StatCard(
            "💰",
            f"Bs {today_total:.2f}",
            "Ingreso Total del Día",
            change_percent,
            change_percent >= 0
        )
        self.stats_layout.addWidget(card1)
        
        # Facturas emitidas
        card2 = StatCard(
            "🎫",
            str(len(today_sales)),
            "Facturas Emitidas Hoy",
            None
        )
        self.stats_layout.addWidget(card2)
        
        # % QR
        total_count = len(self.current_sales)
        qr_count = sum(1 for s in self.current_sales if s['metodo_pago'] == 'qr')
        qr_percent = (qr_count / total_count * 100) if total_count > 0 else 0
        
        card3 = StatCard(
            "💱",
            f"{qr_percent:.1f}%",
            "Pagos con QR",
            None
        )
        self.stats_layout.addWidget(card3)
        
        # % Efectivo
        efectivo_count = sum(1 for s in self.current_sales if s['metodo_pago'] == 'efectivo')
        efectivo_percent = (efectivo_count / total_count * 100) if total_count > 0 else 0
        
        card4 = StatCard(
            "💵",
            f"{efectivo_percent:.1f}%",
            "Pagos en Efectivo",
            None
        )
        self.stats_layout.addWidget(card4)
    
    def _update_table(self):
        """Update table with current sales"""
        self.table.setRowCount(len(self.current_sales))
        
        for row, sale in enumerate(self.current_sales):
            # Get sale details
            sale_obj = Sale.get_by_id(sale['id'])
            
            # ID Factura
            id_item = QTableWidgetItem(sale['numero_factura'])
            id_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            self.table.setItem(row, 0, id_item)
            
            # Cajero
            cajero_item = QTableWidgetItem(sale.get('cajero_nombre', 'N/A'))
            self.table.setItem(row, 1, cajero_item)
            
            # Cliente
            cliente_item = QTableWidgetItem(sale['cliente'] or 'Cliente General')
            self.table.setItem(row, 2, cliente_item)
            
            # Pedido (detallado)
            if sale_obj:
                pedido = "\n".join([f"{item.producto_nombre} ({item.cantidad})" for item in sale_obj.items])
            else:
                pedido = "N/A"
            pedido_item = QTableWidgetItem(pedido)
            self.table.setItem(row, 3, pedido_item)
            
            # Total
            total_item = QTableWidgetItem(f"Bs {sale['total']:.2f}")
            total_item.setForeground(QColor("#10B981"))
            total_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, total_item)
            
            # Método
            metodos = {
                'efectivo': '💵 Efectivo',
                'qr':       '💱 QR',
                'tarjeta':  '💳 Tarjeta',
                'mixto':    '⚡ Mixto',     # ← agregar esta línea
            }
            metodo_item = QTableWidgetItem(metodos.get(sale['metodo_pago'], sale['metodo_pago']))
            self.table.setItem(row, 5, metodo_item)
            
            # Fecha
            fecha_dt = datetime.fromisoformat(sale['fecha_venta'])
            fecha_item = QTableWidgetItem(fecha_dt.strftime("%d/%m/%Y %H:%M"))
            self.table.setItem(row, 6, fecha_item)
            
            # Acciones
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(1, 1, 1, 1)
            actions_layout.setSpacing(1)
            
            view_btn = QPushButton("👁")
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3B82F6;
                    color: white;
                    border-radius: 6px;
                    padding: 4px 4px;
                    
                }
                QPushButton:hover { background-color: #2563EB; }
            """)
            view_btn.clicked.connect(lambda checked=False, s=sale: self.view_sale_detail(s))
            actions_layout.addWidget(view_btn)
            
            print_btn = QPushButton("🖨️")
            print_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10B981;
                    color: white;
                    border-radius: 6px;
                    padding: 4px 4px;
                    
                    
                }
                QPushButton:hover { background-color: #059669; }
            """)
            print_btn.clicked.connect(lambda checked=False, s=sale: self.print_invoice(s))
            actions_layout.addWidget(print_btn)
            
            self.table.setCellWidget(row, 7, actions_widget)
            self.table.setRowHeight(row, 60)
    
    def toggle_summary(self):
        """Toggle summary view"""
        if not self.showing_summary:
            self._show_summary()
            self.summary_btn.setText("📋 Mostrar Tabla")
            self.showing_summary = True
        else:
            self._hide_summary()
            self.summary_btn.setText("📊 Resumen")
            self.showing_summary = False
    
    def _show_summary(self):
        """Show summary section"""
        # Clear previous summary
        while self.summary_layout.count():
            child = self.summary_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Top section: Chart + Top products
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        
        # Pie chart
        chart_widget = self._create_products_chart()
        top_layout.addWidget(chart_widget, 2)
        
        # Top products column
        tops_layout = QVBoxLayout()
        tops_layout.setSpacing(16)
        
        top_all = self._get_top_products(None, 3)
        top_comidas = self._get_top_products('Comidas', 3)
        top_bebidas = self._get_top_products('Bebidas', 3)
        top_extras = self._get_top_products('Extras', 3)
        
        tops_layout.addWidget(TopProductCard("Top 3 Productos", top_all, "🏆"))
        tops_layout.addWidget(TopProductCard("Top 3 Comidas", top_comidas, "🍽️"))
        tops_layout.addWidget(TopProductCard("Top 3 Bebidas", top_bebidas, "🥤"))
        tops_layout.addWidget(TopProductCard("Top 3 Extras", top_extras, "🍟"))
        
        top_layout.addLayout(tops_layout, 1)
        self.summary_layout.addLayout(top_layout)
        
        # Legend: Products by color with totals
        legend_widget = self._create_products_legend()
        self.summary_layout.addWidget(legend_widget)
        
        self.summary_widget.show()
        self.table.hide()
    
    def _hide_summary(self):
        """Hide summary section"""
        self.summary_widget.hide()
        self.table.show()
    
    def _create_products_chart(self):
        """Create pie chart of product sales"""
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
        layout.setSpacing(16)
        
        title = QLabel("📊 Ventas por Producto")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        layout.addWidget(title)
        
        # Get product sales
        product_sales = self._get_product_sales()
        
        series = QPieSeries()
        colors = ['#FF6B35', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', 
                  '#8B5CF6', '#EC4899', '#14B8A6', '#F97316', '#06B6D4']
        
        for i, (product, quantity) in enumerate(product_sales[:10]):
            slice_obj = series.append(f"{product}\n{quantity}", quantity)
            slice_obj.setColor(QColor(colors[i % len(colors)]))
            slice_obj.setLabelVisible(True)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        chart.setBackgroundVisible(False)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(400)
        
        layout.addWidget(chart_view)
        return widget
    
    def _create_products_legend(self):
        """Create legend with all products"""
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
        layout.setSpacing(16)
        
        title = QLabel("🎨 Leyenda de Productos")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        layout.addWidget(title)
        
        # Grid for products
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(12)
        
        product_sales = self._get_product_sales()
        colors = ['#FF6B35', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', 
                  '#8B5CF6', '#EC4899', '#14B8A6', '#F97316', '#06B6D4']
        
        for i, (product, quantity) in enumerate(product_sales):
            row = i // 5
            col = i % 5
            
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(8)
            
            # Color box
            color_box = QLabel()
            color_box.setFixedSize(20, 20)
            color_box.setStyleSheet(f"background-color: {colors[i % len(colors)]}; border-radius: 4px;")
            item_layout.addWidget(color_box)
            
            # Text
            text = QLabel(f"{product}: {quantity} unidades")
            text.setStyleSheet("font-size: 13px; color: #4B5563;")
            item_layout.addWidget(text)
            item_layout.addStretch()
            
            grid.addWidget(item_widget, row, col)
        
        layout.addLayout(grid)
        return widget
    
    def _get_product_sales(self):
        """Get product sales for current filtered sales"""
        if not self.current_sales:
            return []
        
        sale_ids = [s['id'] for s in self.current_sales]
        placeholders = ','.join('?' * len(sale_ids))
        
        query = f"""
            SELECT p.nombre, SUM(dv.cantidad) as cantidad
            FROM detalle_ventas dv
            JOIN productos p ON dv.producto_id = p.id
            WHERE dv.venta_id IN ({placeholders})
            GROUP BY p.nombre
            ORDER BY cantidad DESC
        """
        results = db.fetch_all(query, tuple(sale_ids))
        return [(r['nombre'], int(r['cantidad'])) for r in results]
    
    def _get_top_products(self, category, limit=3):
        """Get top products by category"""
        if not self.current_sales:
            return []
        
        sale_ids = [s['id'] for s in self.current_sales]
        placeholders = ','.join('?' * len(sale_ids))
        
        query = f"""
            SELECT p.nombre, SUM(dv.cantidad) as cantidad, SUM(dv.subtotal) as total
            FROM detalle_ventas dv
            JOIN productos p ON dv.producto_id = p.id
            JOIN categorias c ON p.categoria_id = c.id
            WHERE dv.venta_id IN ({placeholders})
        """
        params = list(sale_ids)
        
        if category:
            query += " AND c.nombre = ?"
            params.append(category)
        
        query += f" GROUP BY p.nombre ORDER BY cantidad DESC LIMIT {limit}"
        
        results = db.fetch_all(query, tuple(params))
        return [dict(r) for r in results]
    
    def view_sale_detail(self, sale_dict):
        """View sale details in dialog"""
        sale = Sale.get_by_id(sale_dict['id'])
        if not sale:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalle de Venta - {sale.numero_factura}")
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(20)
        
        # Header
        header = QLabel(f"📋 Factura: {sale.numero_factura}")
        header.setStyleSheet("font-size: 20px; font-weight: 700; color: #1F2937;")
        layout.addWidget(header)
        
        # Info
        info_text = f"""
        <b>Fecha:</b> {datetime.fromisoformat(sale.fecha_venta).strftime('%d/%m/%Y %H:%M')}<br>
        <b>Cliente:</b> {sale.cliente or 'Cliente General'}<br>
        <b>Método de Pago:</b> {sale.metodo_pago.title()}<br>
        <b>Estado:</b> {sale.estado.title()}
        """
        info_label = QLabel(info_text)
        info_label.setStyleSheet("font-size: 14px; color: #4B5563; line-height: 1.6;")
        layout.addWidget(info_label)
        
        # Items table
        items_table = QTableWidget()
        items_table.setColumnCount(4)
        items_table.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio Unit.", "Subtotal"])
        items_table.setRowCount(len(sale.items))
        
        for row, item in enumerate(sale.items):
            items_table.setItem(row, 0, QTableWidgetItem(item.producto_nombre))
            items_table.setItem(row, 1, QTableWidgetItem(str(item.cantidad)))
            items_table.setItem(row, 2, QTableWidgetItem(f"Bs {item.precio_unitario:.2f}"))
            items_table.setItem(row, 3, QTableWidgetItem(f"Bs {item.subtotal:.2f}"))
        
        layout.addWidget(items_table)
        
        # Totals
        totals_text = f"""
        <b>Subtotal:</b> Bs {sale.subtotal:.2f}<br>
        <b>Descuento:</b> Bs {sale.descuento:.2f}<br>
        <b style="font-size: 18px; color: #10B981;">TOTAL: Bs {sale.total:.2f}</b>
        """
        totals_label = QLabel(totals_text)
        totals_label.setStyleSheet("font-size: 16px; color: #1F2937;")
        layout.addWidget(totals_label)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec()
    
    def print_invoice(self, sale_dict):
        """Print invoice"""
        sale = Sale.get_by_id(sale_dict['id'])
        if not sale:
            return
        
        try:
            filepath = InvoiceGenerator.generate_invoice(sale)
            QMessageBox.information(self, "Éxito", f"Factura generada:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar factura:\n{str(e)}")
    
    def print_report(self):
        """Print report"""
        QMessageBox.information(self, "Imprimir", "Enviando a impresora...")
    
    def generate_pdf(self):
        """Generate PDF report"""
        if not self.current_sales:
            QMessageBox.warning(self, "Sin datos", "No hay ventas para generar PDF")
            return
        
        try:
            fecha_desde = self.fecha_inicial.date().toString("yyyy-MM-dd")
            fecha_hasta = self.fecha_final.date().toString("yyyy-MM-dd")
            
            # Convert to Sale objects
            sales = [Sale.get_by_id(s['id']) for s in self.current_sales]
            sales = [s for s in sales if s is not None]
            
            filename = f"ventas_{fecha_desde}_{fecha_hasta}.pdf"
            filepath = InvoiceGenerator.generate_sales_report(sales, filename, fecha_desde, fecha_hasta)
            
            QMessageBox.information(self, "Éxito", f"Reporte PDF generado:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar PDF:\n{str(e)}")