"""
Sales Widget - Redesigned
Complete sales management with statistics, filters, charts and reports
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit,
    QComboBox, QDateEdit, QScrollArea, QHeaderView, QDialog,
    QDialogButtonBox, QTextEdit, QMessageBox, QSizePolicy
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
from utils.pdf_generator import generate_invoice, generate_sales_report

class StatCard(QFrame):
    """Stat card con fondo de color."""

    THEMES = {
        "green":  {"bg": "#F9FAFB", "accent": "#374151", "icon_bg": "#E5E7EB"},
        "blue":   {"bg": "#F9FAFB", "accent": "#374151", "icon_bg": "#E5E7EB"},
        "orange": {"bg": "#F9FAFB", "accent": "#374151", "icon_bg": "#E5E7EB"},
        "purple": {"bg": "#F9FAFB", "accent": "#374151", "icon_bg": "#E5E7EB"},
    }

    def __init__(self, icon, value, label, change=None,
                 change_positive=True, theme="orange"):
        super().__init__()
        t = self.THEMES.get(theme, self.THEMES["orange"])
        self.setObjectName("stat-card")
        self.setStyleSheet(f"""
            QFrame#stat-card {{
                background-color: {t['bg']};
                border: 1.5px solid {t['icon_bg']};
                border-radius: 16px;
                padding: 20px;
                min-height: 110px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Ícono
        icon_label = QLabel(icon)
        icon_label.setFixedSize(48, 48)
        icon_label.setStyleSheet(f"""
            background-color: {t['icon_bg']};
            color: {t['accent']};
            font-size: 24px;
            border-radius: 12px;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Valor + cambio
        val_row = QHBoxLayout()
        val_row.setSpacing(8)
        value_label = QLabel(value)
        value_label.setStyleSheet(
            f"font-size: 26px; font-weight: 800; color: {t['accent']};")
        val_row.addWidget(value_label)

        if change is not None:
            arrow = "↑" if change_positive else "↓"
            c_col = "#059669" if change_positive else "#DC2626"
            chg = QLabel(f"{arrow} {abs(change):.1f}%")
            chg.setStyleSheet(
                f"font-size: 12px; font-weight: 600; color: {c_col};")
            val_row.addWidget(chg)

        val_row.addStretch()
        layout.addLayout(val_row)

        # Etiqueta
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"font-size: 12px; color: {t['accent']}; font-weight: 600; "
            "opacity: 0.8;")
        layout.addWidget(lbl)
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
    def _make_btn_icono(self, emoji, color, color_hover, color_pressed, ancho=32):
        """Botón con emoji perfectamente centrado usando QLabel overlay."""
        contenedor = QWidget()
        contenedor.setFixedSize(ancho, 28)
        
        # Botón de fondo (sin texto)
        btn = QPushButton("", contenedor)
        btn.setFixedSize(ancho, 28)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: {color_hover}; }}
            QPushButton:pressed {{ background-color: {color_pressed}; }}
        """)
        
        # Label con el emoji centrado encima
        lbl = QLabel(emoji, contenedor)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedSize(ancho, 28)
        lbl.setStyleSheet("background: transparent; font-size: 13px;")
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # 👈 clicks pasan al botón
        
        return contenedor, btn
    
    def init_ui(self):
        """Initialize UI"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(40, 30, 40, 40)
        self.main_layout.setSpacing(24)

        # 1. Header
        self._create_header()

        # 2. Stats 4 cards en fila completa
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(16)
        stats_wrapper = QWidget()
        stats_wrapper.setLayout(self.stats_grid)
        self.main_layout.addWidget(stats_wrapper)

        # 3. Gráfico torta (60%) + Top 5 productos (40%)
        self._create_summary_section()

        # 4. Filtro horizontal
        self._create_filters_panel(self.main_layout)

        # 5. Botones de acción
        self._create_action_buttons()

        # 6. Tabla
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
    
    def _create_summary_section(self):
        """Gráfico torta (izq 60%) + Top 5 productos (der 40%) — siempre visible."""
        row = QHBoxLayout()
        row.setSpacing(20)

        # ── Gráfico de torta ──────────────────────────────────────────
        chart_frame = QFrame()
        chart_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 20px;
            }
        """)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setSpacing(12)

        chart_title = QLabel("📊 Ventas por Producto")
        chart_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #1F2937;")
        chart_layout.addWidget(chart_title)

        self.chart_placeholder = QLabel("Sin datos — filtrá para ver el gráfico")
        self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_placeholder.setStyleSheet(
            "color: #9CA3AF; font-size: 13px; padding: 60px 0;")
        chart_layout.addWidget(self.chart_placeholder)

        # El QChartView se inserta dinámicamente en _update_chart
        self.chart_container = chart_layout
        row.addWidget(chart_frame, stretch=3)

        # ── Top 5 productos más vendidos ──────────────────────────────
        top5_frame = QFrame()
        top5_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 20px;
            }
        """)
        self.top5_layout = QVBoxLayout(top5_frame)
        self.top5_layout.setSpacing(10)

        top5_title = QLabel("🏆 Top 5 Productos más Vendidos")
        top5_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #1F2937;")
        self.top5_layout.addWidget(top5_title)

        self.top5_placeholder = QLabel("Sin datos — filtrá para ver el ranking")
        self.top5_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.top5_placeholder.setStyleSheet(
            "color: #9CA3AF; font-size: 13px; padding: 40px 0;")
        self.top5_layout.addWidget(self.top5_placeholder)
        self.top5_layout.addStretch()

        row.addWidget(top5_frame, stretch=2)
        self.main_layout.addLayout(row)

    def _create_filters_panel(self, parent_layout):
        """Barra de filtros horizontal — ancho completo."""

        class _SmartCombo(QComboBox):
            def wheelEvent(self, e):
                super().wheelEvent(e) if self.view().isVisible() else e.ignore()

        class _SmartDate(QDateEdit):
            def wheelEvent(self, e):
                super().wheelEvent(e) if self.hasFocus() else e.ignore()

        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 14px;
                padding: 16px 20px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        outer = QVBoxLayout(filter_frame)
        outer.setSpacing(10)
        outer.setContentsMargins(0, 0, 0, 0)

        # Título
        title = QLabel("🔍 Filtros de Búsqueda")
        title.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #1F2937;")
        outer.addWidget(title)

        input_style = """
            QLineEdit, QComboBox, QDateEdit {
                border: none;
                border-bottom: 1px solid #D1D5DB;
                border-radius: 0px;
                padding: 4px 8px;
                font-size: 13px;
                background: white;
                min-height: 32px;
                max-height: 32px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border-bottom: 2px solid #FF6B35;
            }
            QComboBox::drop-down { border: none; }
        """

        def lbl(text):
            l = QLabel(text)
            l.setStyleSheet(
                "font-weight: 600; color: #9CA3AF; font-size: 11px; "
                "letter-spacing: 0.5px;")
            l.setFixedHeight(16)
            return l

        # Fila única horizontal con todos los campos
        row = QHBoxLayout()
        row.setSpacing(16)

        def add_field(label_text, widget, stretch=1):
            col = QVBoxLayout()
            col.setSpacing(3)
            col.setContentsMargins(0, 0, 0, 0)
            col.addWidget(lbl(label_text))
            col.addWidget(widget)
            row.addLayout(col, stretch)

        # ID Factura
        self.id_filter = QLineEdit()
        self.id_filter.setPlaceholderText("FACT-20251208-0001")
        self.id_filter.setStyleSheet(input_style)
        add_field("ID FACTURA", self.id_filter, stretch=2)

        # Cajero
        self.cajero_filter = _SmartCombo()
        self.cajero_filter.setStyleSheet(input_style)
        self.cajero_filter.addItem("Todos los cajeros", None)
        for user in User.get_all():
            self.cajero_filter.addItem(user.nombre, user.id)
        add_field("CAJERO", self.cajero_filter, stretch=1)

        # Método
        self.metodo_filter = _SmartCombo()
        self.metodo_filter.setStyleSheet(input_style)
        self.metodo_filter.addItem("Todos los métodos", None)
        self.metodo_filter.addItem("💵 Efectivo", "efectivo")
        self.metodo_filter.addItem("💱 QR", "qr")
        self.metodo_filter.addItem("⚡ Mixto", "mixto")
        add_field("MÉTODO DE PAGO", self.metodo_filter, stretch=1)

        # Fecha Inicial
        self.fecha_inicial = _SmartDate()
        self.fecha_inicial.setCalendarPopup(True)
        self.fecha_inicial.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_inicial.setDisplayFormat("dd/MM/yyyy")
        self.fecha_inicial.setStyleSheet(input_style)
        add_field("FECHA INICIAL", self.fecha_inicial, stretch=1)

        # Fecha Final
        self.fecha_final = _SmartDate()
        self.fecha_final.setCalendarPopup(True)
        self.fecha_final.setDate(QDate.currentDate())
        self.fecha_final.setDisplayFormat("dd/MM/yyyy")
        self.fecha_final.setStyleSheet(input_style)
        add_field("FECHA FINAL", self.fecha_final, stretch=1)

        # Botón alineado al fondo
        btn_col = QVBoxLayout()
        btn_col.setSpacing(3)
        btn_col.setContentsMargins(0, 0, 0, 0)
        btn_col.addWidget(lbl(""))
        filter_btn = QPushButton("Filtrar")
        filter_btn.setFixedHeight(32)
        filter_btn.setFixedWidth(90)
        filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #E85D2F; }
        """)
        filter_btn.clicked.connect(self.load_sales)
        btn_col.addWidget(filter_btn)
        row.addLayout(btn_col)

        outer.addLayout(row)

        # Agregar al layout padre
        if isinstance(parent_layout, QHBoxLayout):
            parent_layout.addWidget(filter_frame, stretch=0)
        else:
            parent_layout.addWidget(filter_frame)
    
    def _create_action_buttons(self):
        """Botones de acción — sin botón Resumen."""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.addStretch()

        print_btn = QPushButton("🖨️ Imprimir")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                padding: 10px 24px;
                border-radius: 10px;
                font-weight: 600;
                min-height: 40px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        print_btn.clicked.connect(self.print_report)
        buttons_layout.addWidget(print_btn)

        pdf_btn = QPushButton("📄 Generar PDF")
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                padding: 10px 24px;
                border-radius: 10px;
                font-weight: 600;
                min-height: 40px;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        pdf_btn.clicked.connect(self.generate_pdf)
        buttons_layout.addWidget(pdf_btn)

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
        
        #self.table.verticalHeader().setDefaultSectionSize(150)
        self.table.setColumnWidth(7, 180)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
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
        """Actualiza las 4 stat cards en fila horizontal con colores."""
        while self.stats_grid.count():
            item = self.stats_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today     = datetime.now().date()
        yesterday = today - timedelta(days=1)

        today_sales     = [s for s in self.current_sales
                           if datetime.fromisoformat(s['fecha_venta']).date() == today]
        yesterday_sales = [s for s in self.current_sales
                           if datetime.fromisoformat(s['fecha_venta']).date() == yesterday]

        today_total     = sum(s['total'] for s in today_sales) if today_sales else 0
        yesterday_total = sum(s['total'] for s in yesterday_sales) if yesterday_sales else 0
        change_percent  = ((today_total - yesterday_total) / yesterday_total * 100) \
                          if yesterday_total > 0 else 0

        qr_count       = sum(1 for s in self.current_sales if s['metodo_pago'] == 'qr')
        efectivo_count = sum(1 for s in self.current_sales if s['metodo_pago'] == 'efectivo')

        # 4 cards en fila: col 0,1,2,3 — fila 0
        cards = [
            (StatCard("💰", f"Bs {today_total:.2f}",
                      "Ingreso Total del Día", change_percent,
                      change_percent >= 0, theme="green"),  0),
            (StatCard("🎫", str(len(today_sales)),
                      "Facturas Emitidas Hoy", None,
                      theme="blue"),                         1),
            (StatCard("💱", str(qr_count),
                      "Ventas con QR", None,
                      theme="purple"),                       2),
            (StatCard("💵", str(efectivo_count),
                      "Ventas en Efectivo", None,
                      theme="orange"),                       3),
        ]

        for card, col in cards:
            self.stats_grid.addWidget(card, 0, col)

        self._update_chart()
        self._update_top5()
    
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
            aw = QWidget()
            aw.setStyleSheet("background: transparent;")
            al = QHBoxLayout(aw)
            al.setContentsMargins(2, 0, 2, 0)
            al.setSpacing(4)
            al.setAlignment(Qt.AlignmentFlag.AlignCenter)

            view_w, view_btn = self._make_btn_icono("👁", "#3B82F6", "#2563EB", "#1D4ED8")
            view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            view_btn.clicked.connect(lambda checked=False, s=sale: self.view_sale_detail(s))

            print_w, print_btn = self._make_btn_icono("📄", "#10B981", "#059669", "#047857")
            print_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            print_btn.clicked.connect(lambda checked=False, s=sale: self.print_invoice(s))

            al.addWidget(view_w)
            al.addWidget(print_w)

            self.table.setCellWidget(row, 7, aw)
            self.table.setRowHeight(row, 60)
    
    def _update_chart(self):
        """Actualiza el gráfico de torta con los datos filtrados."""
        # Limpiar contenedor (conservar solo el título en índice 0)
        while self.chart_container.count() > 1:
            item = self.chart_container.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        product_sales = self._get_product_sales()

        if not product_sales:
            lbl = QLabel("Sin datos para mostrar")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #9CA3AF; font-size: 13px; padding: 60px 0;")
            self.chart_container.addWidget(lbl)
            return

        colors = ['#FF6B35', '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
                  '#8B5CF6', '#EC4899', '#14B8A6', '#F97316', '#06B6D4']

        series = QPieSeries()
        for i, (product, quantity) in enumerate(product_sales[:10]):
            sl = series.append(f"{product}  {quantity}", quantity)
            sl.setColor(QColor(colors[i % len(colors)]))
            sl.setLabelVisible(True)

        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        chart.setBackgroundVisible(False)
        chart.setMargins(__import__('PySide6.QtCore', fromlist=['QMargins']).QMargins(0, 0, 0, 0))

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(320)
        self.chart_container.addWidget(chart_view)

    def _update_top5(self):
        """Top 5 productos — números grandes, columnas limpias."""
        while self.top5_layout.count() > 1:
            item = self.top5_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        top5 = self._get_top_products(None, 5)

        if not top5:
            lbl = QLabel("Sin datos — filtrá para ver el ranking")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #9CA3AF; font-size: 13px; padding: 30px 0;")
            self.top5_layout.addWidget(lbl)
            self.top5_layout.addStretch()
            return

        # Colores vibrantes por posición
        themes = [
            {"bg": "#FFF7ED", "border": "#FED7AA", "num_bg": "#F97316",
             "num_fg": "white",  "txt": "#9A3412"},
            {"bg": "#F0F9FF", "border": "#BAE6FD", "num_bg": "#0EA5E9",
             "num_fg": "white",  "txt": "#0C4A6E"},
            {"bg": "#F0FDF4", "border": "#BBF7D0", "num_bg": "#22C55E",
             "num_fg": "white",  "txt": "#14532D"},
            {"bg": "#F5F3FF", "border": "#DDD6FE", "num_bg": "#8B5CF6",
             "num_fg": "white",  "txt": "#4C1D95"},
            {"bg": "#FFF1F2", "border": "#FECDD3", "num_bg": "#F43F5E",
             "num_fg": "white",  "txt": "#881337"},
        ]

        for i, prod in enumerate(top5):
            t = themes[i]

            row_w = QFrame()
            row_w.setStyleSheet(f"""
                QFrame {{
                    background-color: {t['bg']};
                    border: 1.5px solid {t['border']};
                    border-radius: 12px;
                }}
            """)
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(14, 10, 14, 10)
            rl.setSpacing(8)

            # Número de posición — círculo de color
            num = QLabel()
            num.setFixedSize(22, 22)
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setStyleSheet(f"""              
                background-color: {t['num_bg']};
                color: white;
                font-size: 18px;
                
                border-radius: 16px;
            """)
            num.setText(str(i + 1))
            rl.addWidget(num)

            # Nombre del producto
            name_lbl = QLabel(prod['nombre'])
            name_lbl.setMaximumWidth(160)
            name_lbl.setWordWrap(False)
            name_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            name_lbl.setStyleSheet(
                f"font-size: 14px; font-weight: 700; color: {t['txt']};")
            rl.addWidget(name_lbl, stretch=1)
            

            # Cantidad — badge
            qty_badge = QFrame()
            qty_badge.setStyleSheet(f"""
                QFrame {{
                    background-color: {t['border']};
                    border-radius: 8px;
                    padding: 2px 8px;
                }}
            """)
            qty_lay = QHBoxLayout(qty_badge)
            qty_lay.setContentsMargins(8, 4, 8, 4)
            qty_lay.setSpacing(0)
            qty_lbl = QLabel(f"{prod['cantidad']} uds")
            qty_lbl.setStyleSheet(
                f"font-size: 12px; font-weight: 700; color: {t['txt']};")
            qty_lay.addWidget(qty_lbl)
            rl.addWidget(qty_badge)

            # Total en verde fuerte
            total_lbl = QLabel(f"Bs {prod['total']:.2f}")
            total_lbl.setFixedWidth(110)
            total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight |
                                   Qt.AlignmentFlag.AlignVCenter)
            total_lbl.setStyleSheet(
                "font-size: 14px; font-weight: 800; color: #059669;")
            rl.addWidget(total_lbl)

            self.top5_layout.addWidget(row_w)

        self.top5_layout.addStretch()

    def toggle_summary(self):
        """Toggle summary view — mantenido por compatibilidad."""
        pass

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
        dialog.setWindowTitle(f"Factura {sale.numero_factura}")
        dialog.setMinimumSize(560, 520)
        dialog.setStyleSheet("background-color: #F9FAFB;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        # ── Encabezado ─────────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }
        """)
        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(16, 14, 16, 14)

        left = QVBoxLayout()
        left.setSpacing(2)
        factura_lbl = QLabel(sale.numero_factura)
        factura_lbl.setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #1F2937;")
        fecha_lbl = QLabel(
            datetime.fromisoformat(
                sale.fecha_venta).strftime("%d/%m/%Y  %H:%M"))
        fecha_lbl.setStyleSheet("font-size: 12px; color: #6B7280;")
        left.addWidget(factura_lbl)
        left.addWidget(fecha_lbl)
        hl.addLayout(left)
        hl.addStretch()

        # Badge estado
        estado_lbl = QLabel(f"  {sale.estado.title()}  ")
        color_estado = "#10B981" if sale.estado == "completada" else "#F59E0B"
        estado_lbl.setStyleSheet(f"""
            background-color: {color_estado}20;
            color: {color_estado};
            font-size: 12px; font-weight: 700;
            border-radius: 8px; padding: 4px 8px;
            border: 1px solid {color_estado}40;
        """)
        hl.addWidget(estado_lbl)
        layout.addWidget(header_frame)

        # ── Info cliente y pago ────────────────────────────────────
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }
        """)
        il = QHBoxLayout(info_frame)
        il.setContentsMargins(16, 12, 16, 12)
        il.setSpacing(32)

        def info_col(label, value):
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet(
                "font-size: 10px; font-weight: 700; color: #9CA3AF; "
                "letter-spacing: 0.5px;")
            val = QLabel(value)
            val.setStyleSheet("font-size: 13px; font-weight: 600; color: #1F2937;")
            col.addWidget(lbl)
            col.addWidget(val)
            return col

        metodos = {
            "efectivo": "💵 Efectivo", "qr": "💱 QR",
            "tarjeta": "💳 Tarjeta",  "mixto": "⚡ Mixto"
        }
        il.addLayout(info_col(
            "CLIENTE", sale.cliente or "Cliente General"))
        il.addLayout(info_col(
            "MÉTODO DE PAGO",
            metodos.get(sale.metodo_pago, sale.metodo_pago.title())))
        il.addStretch()
        layout.addWidget(info_frame)

        # ── Tabla de productos ─────────────────────────────────────
        items_table = QTableWidget()
        items_table.setColumnCount(4)
        items_table.setHorizontalHeaderLabels(
            ["Producto", "Cant.", "Precio Unit.", "Subtotal"])
        items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        items_table.verticalHeader().setVisible(False)
        items_table.setAlternatingRowColors(True)
        items_table.setShowGrid(False)
        items_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                background-color: white;
                font-size: 13px;
                alternate-background-color: #F9FAFB;
            }
            QTableWidget::item { padding: 8px 10px; }
            QHeaderView::section {
                background-color: #F3F4F6;
                color: #6B7280; font-weight: 700;
                font-size: 11px; padding: 8px 10px;
                border: none; border-bottom: 1px solid #E5E7EB;
            }
        """)

        # Agrupar productos repetidos
        from collections import defaultdict
        agrupado = {}
        orden = []
        for item in sale.items:
            key = item.producto_nombre
            if key not in agrupado:
                agrupado[key] = {"cantidad": 0, "precio": item.precio_unitario,
                                "subtotal": 0}
                orden.append(key)
            agrupado[key]["cantidad"] += item.cantidad
            agrupado[key]["subtotal"] += item.subtotal

        items_table.setRowCount(len(orden))
        for row, key in enumerate(orden):
            vals = agrupado[key]
            items_table.setItem(row, 0, QTableWidgetItem(key))

            cant = QTableWidgetItem(str(vals["cantidad"]))
            cant.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items_table.setItem(row, 1, cant)

            precio = QTableWidgetItem(f"Bs {vals['precio']:,.2f}")
            precio.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items_table.setItem(row, 2, precio)

            sub = QTableWidgetItem(f"Bs {vals['subtotal']:,.2f}")
            sub.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            sub.setForeground(QColor("#10B981"))
            sub.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            items_table.setItem(row, 3, sub)
            items_table.setRowHeight(row, 40)

        hdr = items_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        items_table.setColumnWidth(1, 60)
        items_table.setColumnWidth(2, 110)
        items_table.setColumnWidth(3, 110)
        layout.addWidget(items_table)

        # ── Totales ────────────────────────────────────────────────
        totals_frame = QFrame()
        totals_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }
        """)
        tl = QVBoxLayout(totals_frame)
        tl.setContentsMargins(16, 12, 16, 12)
        tl.setSpacing(6)

        def total_row(label, valor, bold=False, color="#4B5563", big=False):
            row_w = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"font-size: {'14' if big else '12'}px; "
                f"font-weight: {'700' if bold else '500'}; color: #6B7280;")
            val = QLabel(valor)
            val.setStyleSheet(
                f"font-size: {'16' if big else '12'}px; "
                f"font-weight: {'800' if bold else '500'}; color: {color};")
            row_w.addStretch()
            row_w.addWidget(lbl)
            row_w.addSpacing(24)
            row_w.addWidget(val)
            tl.addLayout(row_w)

        total_row("Subtotal:", f"Bs {sale.subtotal:,.2f}")
        if sale.descuento and sale.descuento > 0:
            total_row("Descuento:", f"- Bs {sale.descuento:,.2f}", color="#EF4444")

        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E5E7EB;")
        tl.addWidget(line)

        total_row("TOTAL:", f"Bs {sale.total:,.2f}",
                bold=True, color="#10B981", big=True)
        layout.addWidget(totals_frame)

        # ── Botones ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        print_btn = QPushButton("🖨️ Imprimir Ticket")
        print_btn.setFixedHeight(38)
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981; color: white;
                border-radius: 8px; font-weight: 600;
                font-size: 13px; padding: 0 16px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        print_btn.clicked.connect(lambda: self._imprimir_ticket(sale))
        btn_row.addWidget(print_btn)

        close_btn = QPushButton("Cerrar")
        close_btn.setFixedHeight(38)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1F2937; color: white;
                border-radius: 8px; font-weight: 600;
                font-size: 13px; padding: 0 16px;
            }
            QPushButton:hover { background-color: #374151; }
        """)
        close_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)
        dialog.exec()
    def print_invoice(self, sale_dict):
        sale = Sale.get_by_id(sale_dict['id'])
        if not sale:
            return
        try:
            filepath = generate_invoice(sale)  
            QMessageBox.information(self, "Éxito", f"Factura generada:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar factura:\n{str(e)}")

    def print_report(self):
        QMessageBox.information(self, "Imprimir", "Enviando a impresora...")
    def _imprimir_ticket(self, sale):
        """Imprime el ticket de la venta en la impresora 58mm"""
        from utils.printer import imprimir_recibo 
        ok, msg = imprimir_recibo(
            sale,
            nombre_negocio="La Placita",
            nombre="Cafetería & Heladería",
            subtitulo="Sucursal Santa Fe",
            telefono="77113371",
            mensaje_pie="¡Gracias por su visita!\nVuelva pronto",
            abrir_cajon=False  
        )
        if ok:
            QMessageBox.information(self, "Éxito", "Ticket impreso correctamente.")
        else:
            QMessageBox.critical(self, "Error", f"No se pudo imprimir:\n{msg}")

    def generate_pdf(self):
        if not self.current_sales:
            QMessageBox.warning(self, "Sin datos", "No hay ventas para generar PDF")
            return
        try:
            fecha_desde = self.fecha_inicial.date().toString("yyyy-MM-dd")
            fecha_hasta = self.fecha_final.date().toString("yyyy-MM-dd")
            
            sales = [Sale.get_by_id(s['id']) for s in self.current_sales]
            sales = [s for s in sales if s is not None]
            
            filename = f"ventas_{fecha_desde}_{fecha_hasta}.pdf"
            filepath = generate_sales_report(sales, filename, fecha_desde, fecha_hasta)  
            
            QMessageBox.information(self, "Éxito", f"Reporte PDF generado:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar PDF:\n{str(e)}")