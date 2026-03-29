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
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QFont, QPainter, QColor
from PySide6.QtCharts import QChart, QChartView, QPieSeries
from datetime import datetime, timedelta
from models.sale import Sale
from models.user import User, get_current_user
from database.connection import db
from utils.pdf_generator import InvoiceGenerator
from utils.excel_exporter import ExcelExporter
from utils.pdf_generator import generate_invoice


# ══════════════════════════════════════════════════════════════
#  Helpers de labels
# ══════════════════════════════════════════════════════════════

def _lbl(texto: str, color: str, size: int, bold: bool = False) -> QLabel:
    l = QLabel(texto)
    l.setStyleSheet(
        f"font-size: {size}px; color: {color}; "
        f"font-weight: {'700' if bold else '400'}; background: transparent;"
    )
    return l


def _lbl_bold(texto: str, color: str, size: int) -> QLabel:
    return _lbl(texto, color, size, bold=True)


# ══════════════════════════════════════════════════════════════
#  Estilos de botones de diálogo reutilizables
# ══════════════════════════════════════════════════════════════

_BTN_CANCEL_STYLE = """
    QPushButton {
        background: #F3F4F6; color: #374151;
        border-radius: 8px; font-weight: 600; padding: 0 18px;
    }
    QPushButton:hover { background: #E5E7EB; }
"""

_BTN_ANULAR_STYLE = """
    QPushButton {
        background: #EF4444; color: white;
        border-radius: 8px; font-weight: 700; padding: 0 18px;
    }
    QPushButton:hover { background: #DC2626; }
"""

_BTN_DESANULAR_STYLE = """
    QPushButton {
        background: #F59E0B; color: white;
        border-radius: 8px; font-weight: 700; padding: 0 18px;
    }
    QPushButton:hover { background: #D97706; }
"""

_INPUT_MASTER_STYLE = """
    QLineEdit {
        border: 1.5px solid #D1D5DB; border-radius: 8px;
        padding: 0 12px; font-size: 13px; background: white;
    }
    QLineEdit:focus { border-color: #EF4444; }
"""

_INPUT_MOTIVO_STYLE = """
    QTextEdit {
        border: 1.5px solid #D1D5DB; border-radius: 10px;
        padding: 8px 12px; font-size: 13px; background: white;
    }
    QTextEdit:focus { border-color: #EF4444; }
"""


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
        self.showing_summary    = False
        self.current_sales      = []
        self._showing_anuladas  = False
        self._showing_marcadas  = False
        self._filter_timer      = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(400)
        self._filter_timer.timeout.connect(self._do_load_sales)
        self.init_ui()
        self.load_sales()
    
    def _make_btn_icono(self, emoji, color, color_hover, color_pressed, ancho=32):
        """Botón con emoji superpuesto — transparente al mouse en el label."""
        contenedor = QWidget()
        contenedor.setFixedSize(ancho, 28)

        btn = QPushButton("", contenedor)
        btn.setFixedSize(ancho, 28)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 5px;
            }}
            QPushButton:hover   {{ background-color: {color_hover}; }}
            QPushButton:pressed {{ background-color: {color_pressed}; }}
        """)

        lbl = QLabel(emoji, contenedor)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedSize(ancho, 28)
        lbl.setStyleSheet("background: transparent; font-size: 13px;")
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

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
        self._filter_btn = QPushButton("Filtrar")
        self._filter_btn.setFixedHeight(32)
        self._filter_btn.setFixedWidth(90)
        self._filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover   { background-color: #E85D2F; }
            QPushButton:disabled { background-color: #D1D5DB; color: #9CA3AF; }
        """)
        self._filter_btn.clicked.connect(self.load_sales)
        btn_col.addWidget(self._filter_btn)
        row.addLayout(btn_col)

        outer.addLayout(row)

        # Agregar al layout padre
        if isinstance(parent_layout, QHBoxLayout):
            parent_layout.addWidget(filter_frame, stretch=0)
        else:
            parent_layout.addWidget(filter_frame)
    
    def _create_action_buttons(self):
        """Botones de acción: toggles, imprimir, PDF."""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Toggle anuladas
        self._toggle_btn = QPushButton("🚫  Ver Anuladas")
        self._toggle_btn.setFixedHeight(40)
        self._toggle_btn.setStyleSheet(self._toggle_style_normal())
        self._toggle_btn.clicked.connect(self._toggle_anuladas)
        buttons_layout.addWidget(self._toggle_btn)

        self._badge_anuladas = QLabel()
        self._badge_anuladas.setFixedHeight(24)
        self._badge_anuladas.setStyleSheet("""
            background-color: #EF4444; color: white;
            font-size: 11px; font-weight: 700;
            border-radius: 12px; padding: 0 10px;
        """)
        self._badge_anuladas.hide()
        buttons_layout.addWidget(self._badge_anuladas)

        # Toggle marcadas — solo admin
        user = get_current_user()
        self._toggle_marcadas_btn = None
        if user and user.is_admin():
            self._toggle_marcadas_btn = QPushButton("⚑  Ver Marcadas")
            self._toggle_marcadas_btn.setFixedHeight(40)
            self._toggle_marcadas_btn.setStyleSheet(self._toggle_style_normal())
            self._toggle_marcadas_btn.clicked.connect(self._toggle_marcadas)
            buttons_layout.addWidget(self._toggle_marcadas_btn)

        self._badge_marcadas = QLabel()
        self._badge_marcadas.setFixedHeight(24)
        self._badge_marcadas.setStyleSheet("""
            background-color: #F59E0B; color: white;
            font-size: 11px; font-weight: 700;
            border-radius: 12px; padding: 0 10px;
        """)
        self._badge_marcadas.hide()
        buttons_layout.addWidget(self._badge_marcadas)

        buttons_layout.addStretch()

        pdf_btn = QPushButton("📄  Generar PDF")
        pdf_btn.setFixedHeight(40)
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444; color: white;
                padding: 0 20px; border-radius: 10px;
                font-weight: 600; font-size: 13px;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        pdf_btn.clicked.connect(self.generate_pdf)
        buttons_layout.addWidget(pdf_btn)

        self.main_layout.addLayout(buttons_layout)

    def _toggle_style_normal(self) -> str:
        return """
            QPushButton {
                background-color: #F3F4F6; color: #374151;
                padding: 0 20px; border-radius: 10px;
                font-weight: 700; font-size: 13px;
                border: 1.5px solid #E5E7EB;
            }
            QPushButton:hover { background-color: #E5E7EB; }
        """

    def _toggle_style_activo_rojo(self) -> str:
        return """
            QPushButton {
                background-color: #FEF2F2; color: #EF4444;
                padding: 0 20px; border-radius: 10px;
                font-weight: 700; font-size: 13px;
                border: 1.5px solid #FECACA;
            }
            QPushButton:hover { background-color: #FEE2E2; }
        """

    def _toggle_style_activo_amarillo(self) -> str:
        return """
            QPushButton {
                background-color: #FFFBEB; color: #D97706;
                padding: 0 20px; border-radius: 10px;
                font-weight: 700; font-size: 13px;
                border: 1.5px solid #FDE68A;
            }
            QPushButton:hover { background-color: #FEF3C7; }
        """

    def _toggle_anuladas(self):
        if self._showing_marcadas:
            self._showing_marcadas = False
            if self._toggle_marcadas_btn:
                self._toggle_marcadas_btn.setText("⚑  Ver Marcadas")
                self._toggle_marcadas_btn.setStyleSheet(self._toggle_style_normal())
        self._showing_anuladas = not self._showing_anuladas
        if self._showing_anuladas:
            self._toggle_btn.setText("✅  Ver Completadas")
            self._toggle_btn.setStyleSheet(self._toggle_style_activo_rojo())
        else:
            self._toggle_btn.setText("🚫  Ver Anuladas")
            self._toggle_btn.setStyleSheet(self._toggle_style_normal())
        self.load_sales()

    def _toggle_marcadas(self):
        if self._showing_anuladas:
            self._showing_anuladas = False
            self._toggle_btn.setText("🚫  Ver Anuladas")
            self._toggle_btn.setStyleSheet(self._toggle_style_normal())
        self._showing_marcadas = not self._showing_marcadas
        if self._toggle_marcadas_btn:
            if self._showing_marcadas:
                self._toggle_marcadas_btn.setText("✅  Ver Todas")
                self._toggle_marcadas_btn.setStyleSheet(
                    self._toggle_style_activo_amarillo())
            else:
                self._toggle_marcadas_btn.setText("⚑  Ver Marcadas")
                self._toggle_marcadas_btn.setStyleSheet(self._toggle_style_normal())
        self.load_sales()

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
        """Punto de entrada — deshabilita botón y lanza debounce."""
        self._filter_btn.setEnabled(False)
        self._filter_btn.setText("...")
        self._filter_timer.start()

    def _do_load_sales(self):
        """Ejecución real tras debounce."""
        try:
            self._load_sales_impl()
        finally:
            self._filter_btn.setEnabled(True)
            self._filter_btn.setText("Filtrar")

    def _load_sales_impl(self):
        id_factura  = self.id_filter.text().strip() or None
        cajero_id   = self.cajero_filter.currentData()
        metodo      = self.metodo_filter.currentData()
        fecha_desde = self.fecha_inicial.date().toString("yyyy-MM-dd")
        fecha_hasta = self.fecha_final.date().toString("yyyy-MM-dd")

        if self._showing_anuladas:
            estado_filtro = 'anulada'
            extra_where   = ""
        elif self._showing_marcadas:
            estado_filtro = 'completada'
            extra_where   = " AND v.marcada = '1'"
        else:
            estado_filtro = 'completada'
            extra_where   = ""

        query = f"""
            SELECT v.*, u.nombre as cajero_nombre
            FROM ventas v
            LEFT JOIN usuarios u ON v.usuario_id = u.id
            WHERE DATE(v.fecha_venta) BETWEEN ? AND ?
              AND v.estado = ?
              {extra_where}
        """
        params = [fecha_desde, fecha_hasta, estado_filtro]

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

        # Pedidos en batch
        self._pedidos_cache = {}
        if self.current_sales:
            sale_ids     = [s['id'] for s in self.current_sales]
            placeholders = ','.join('?' * len(sale_ids))
            rows_detalle = db.fetch_all(
                f"""SELECT dv.venta_id, p.nombre as producto_nombre, dv.cantidad
                    FROM detalle_ventas dv
                    JOIN productos p ON dv.producto_id = p.id
                    WHERE dv.venta_id IN ({placeholders})
                    ORDER BY dv.id""",
                tuple(sale_ids),
            )
            for r in rows_detalle:
                vid = r['venta_id']
                if vid not in self._pedidos_cache:
                    self._pedidos_cache[vid] = []
                self._pedidos_cache[vid].append(
                    f"{r['producto_nombre']} ({r['cantidad']})")

        # Badges
        row_an = db.fetch_one(
            """SELECT COUNT(*) as cnt FROM ventas
               WHERE DATE(fecha_venta) BETWEEN ? AND ?
                 AND estado = 'anulada'""",
            (fecha_desde, fecha_hasta),
        )
        cnt_anuladas = row_an['cnt'] if row_an else 0
        if cnt_anuladas > 0 and not self._showing_anuladas:
            self._badge_anuladas.setText(f"  {cnt_anuladas} anuladas  ")
            self._badge_anuladas.show()
        else:
            self._badge_anuladas.hide()

        user = get_current_user()
        if user and user.is_admin():
            row_m = db.fetch_one(
                """SELECT COUNT(*) as cnt FROM ventas
                   WHERE DATE(fecha_venta) BETWEEN ? AND ?
                     AND marcada = '1' AND estado = 'completada'""",
                (fecha_desde, fecha_hasta),
            )
            cnt_marcadas = row_m['cnt'] if row_m else 0
            if cnt_marcadas > 0 and not self._showing_marcadas:
                self._badge_marcadas.setText(
                    f"  ⚑ {cnt_marcadas} para revisar  ")
                self._badge_marcadas.show()
            else:
                self._badge_marcadas.hide()
        else:
            self._badge_marcadas.hide()

        self._update_stats()
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
        """Rellena la tabla usando cache de pedidos y soporta vista marcadas."""
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(self.current_sales))

        user = get_current_user()
        rol  = user.rol if user else 'cajero'

        metodos = {
            'efectivo': '💵 Efectivo',
            'qr':       '💱 QR',
            'tarjeta':  '💳 Tarjeta',
            'mixto':    '⚡ Mixto',
        }

        pedidos_cache = getattr(self, '_pedidos_cache', {})

        for row, sale in enumerate(self.current_sales):

            id_item = QTableWidgetItem(sale['numero_factura'])
            id_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            self.table.setItem(row, 0, id_item)

            self.table.setItem(row, 1,
                QTableWidgetItem(sale.get('cajero_nombre', 'N/A')))
            self.table.setItem(row, 2,
                QTableWidgetItem(sale['cliente'] or 'Cliente General'))

            lineas = pedidos_cache.get(sale['id'], [])
            self.table.setItem(row, 3,
                QTableWidgetItem("\n".join(lineas) if lineas else "N/A"))

            total_item = QTableWidgetItem(f"Bs {sale['total']:.2f}")
            total_item.setForeground(QColor("#10B981"))
            total_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            total_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, total_item)

            self.table.setItem(row, 5,
                QTableWidgetItem(metodos.get(sale['metodo_pago'],
                                             sale['metodo_pago'])))

            fecha_dt = datetime.fromisoformat(sale['fecha_venta'])
            self.table.setItem(row, 6,
                QTableWidgetItem(fecha_dt.strftime("%d/%m/%Y %H:%M")))

            # ── Acciones ───────────────────────────────────────
            aw = QWidget()
            aw.setStyleSheet("background: transparent;")
            al = QHBoxLayout(aw)
            al.setContentsMargins(2, 0, 2, 0)
            al.setSpacing(4)
            al.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # 👁 Ver — siempre
            view_w, view_btn = self._make_btn_icono(
                "👁", "#3B82F6", "#2563EB", "#1D4ED8")
            view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            view_btn.setToolTip("Ver detalle")
            view_btn.clicked.connect(
                lambda checked=False, s=sale: self.view_sale_detail(s))
            al.addWidget(view_w)

            if self._showing_marcadas and rol == 'admin':
                # Vista marcadas: botón revisar marca
                sale_copy = dict(sale)
                revisar_w, revisar_btn = self._make_btn_icono(
                    "⚑", "#F59E0B", "#D97706", "#B45309", ancho=32)
                revisar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                revisar_btn.setToolTip("Revisar motivo y decidir")
                revisar_btn.clicked.connect(
                    lambda checked=False, s=sale_copy:
                        self._dialogo_revisar_marca(s))
                al.addWidget(revisar_w)

            elif not self._showing_anuladas and not self._showing_marcadas:
                if rol == 'admin':
                    if sale.get('estado') != 'anulada':
                        cancel_w, cancel_btn = self._make_btn_icono(
                            "🚫", "#EF4444", "#DC2626", "#B91C1C")
                        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                        cancel_btn.setToolTip("Anular factura")
                        cancel_btn.clicked.connect(
                            lambda checked=False, s=sale:
                                self._dialogo_anular(s['id']))
                        al.addWidget(cancel_w)
                    else:
                        desanular_w, desanular_btn = self._make_btn_icono(
                            "✅", "#F59E0B", "#D97706", "#B45309")
                        desanular_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                        desanular_btn.setToolTip("Desanular factura")
                        desanular_btn.clicked.connect(
                            lambda checked=False, s=sale:
                                self._dialogo_desanular(s['id']))
                        al.addWidget(desanular_w)
                else:
                    # Cajero: marcar / desmarcar
                    ya_marcada   = str(sale.get('marcada', '0')) == '1'
                    flag_emoji   = "⚑" if not ya_marcada else "⚐"
                    flag_color   = "#F59E0B" if not ya_marcada else "#9CA3AF"
                    flag_hover   = "#D97706" if not ya_marcada else "#6B7280"
                    flag_pressed = "#B45309" if not ya_marcada else "#4B5563"
                    flag_w, flag_btn = self._make_btn_icono(
                        flag_emoji, flag_color, flag_hover, flag_pressed)
                    flag_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    flag_btn.setToolTip(
                        "Marcar para revisión del admin"
                        if not ya_marcada else "Quitar marca de revisión")
                    sale_copy = dict(sale)
                    flag_btn.clicked.connect(
                        lambda checked=False, s=sale_copy:
                            self.marcar_factura(s))
                    al.addWidget(flag_w)

            self.table.setCellWidget(row, 7, aw)
            self.table.setRowHeight(row, 60)

            # ── Estilo visual por estado ───────────────────────
            if self._showing_anuladas:
                for col in range(self.table.columnCount() - 1):
                    item = self.table.item(row, col)
                    if item:
                        item.setForeground(QColor("#9CA3AF"))
                        f = item.font()
                        f.setStrikeOut(True)
                        item.setFont(f)
            elif self._showing_marcadas or str(sale.get('marcada', '0')) == '1':
                for col in range(self.table.columnCount() - 1):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor("#FFFBEB"))

        self.table.setUpdatesEnabled(True)
    
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
            rl.setContentsMargins(10, 8, 14, 8)
            rl.setSpacing(12)

            # Número de posición — círculo de color
            num = QLabel(str(i + 1))
            num.setFixedSize(36, 36)
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setStyleSheet(f"""
                background-color: {t['num_bg']};
                color: {t['num_fg']};
                font-size: 16px;
                font-weight: 800;
                border-radius: 18px;
            """)
            rl.addWidget(num)

            # Nombre del producto
            name_lbl = QLabel(prod['nombre'])
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
            total_lbl.setFixedWidth(80)
            total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight |
                                   Qt.AlignmentFlag.AlignVCenter)
            total_lbl.setStyleSheet(
                "font-size: 14px; font-weight: 800; color: #059669;")
            rl.addWidget(total_lbl)

            self.top5_layout.addWidget(row_w)

        self.top5_layout.addStretch()

    # ══════════════════════════════════════════════════════════
    #  Diálogo: Revisar factura marcada (admin)
    # ══════════════════════════════════════════════════════════

    def _dialogo_revisar_marca(self, sale_dict: dict):
        sale_id       = sale_dict['id']
        numero        = sale_dict.get('numero_factura', str(sale_id))
        cajero_nombre = sale_dict.get('cajero_nombre', '—')

        row_m  = db.fetch_one(
            "SELECT motivo_marca FROM ventas WHERE id=?", (sale_id,))
        motivo = (row_m['motivo_marca'] if row_m and row_m['motivo_marca']
                  else "Sin motivo registrado")

        dlg = QDialog(self)
        dlg.setWindowTitle("Revisar Factura Marcada")
        dlg.setFixedSize(460, 300)
        dlg.setStyleSheet("background-color: #F9FAFB; border: none")

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)

        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background-color: #FFFBEB;
                border: none;
                border-radius: 12px;
            }
        """)
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 14, 16, 14)
        bl.setSpacing(12)
        ico = QLabel("⚑")
        ico.setStyleSheet("font-size: 26px; border: none;")
        ico.setFixedHeight(50),ico.setFixedWidth(50)
        bl.addWidget(ico)
        txts = QVBoxLayout()
        txts.setSpacing(4)
        txts.addWidget(_lbl_bold(f"Factura {numero}", "#92400E", 15))
        txts.addWidget(_lbl(f"Marcada por: {cajero_nombre}", "#B45309", 12))
        bl.addLayout(txts)
        layout.addWidget(banner)

        layout.addWidget(_lbl("Motivo del cajero:", "#374151", 13, bold=True))

        motivo_frame = QFrame()
        motivo_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1.5px solid #E5E7EB;
                border-radius: 10px;
            }
        """)
        ml = QVBoxLayout(motivo_frame)
        ml.setContentsMargins(14, 10, 14, 10)
        motivo_lbl = QLabel(motivo)
        motivo_lbl.setStyleSheet(
            "font-size: 13px; color: #374151; line-height: 1.5; border: none")
        motivo_lbl.setWordWrap(True)
        ml.addWidget(motivo_lbl)
        layout.addWidget(motivo_frame)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton("Cerrar")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet(_BTN_CANCEL_STYLE)
        cancel_btn.clicked.connect(dlg.reject)

        descartar_btn = QPushButton("⚐  Descartar Marca")
        descartar_btn.setFixedHeight(38)
        descartar_btn.setStyleSheet("""
            QPushButton {
                background: #F59E0B; color: white;
                border-radius: 8px; font-weight: 700;
                font-size: 13px; padding: 0 16px;
            }
            QPushButton:hover { background: #D97706; }
        """)

        anular_btn = QPushButton("🚫  Anular Factura")
        anular_btn.setFixedHeight(38)
        anular_btn.setStyleSheet("""
            QPushButton {
                background: #EF4444; color: white;
                border-radius: 8px; font-weight: 700;
                font-size: 13px; padding: 0 16px;
            }
            QPushButton:hover { background: #DC2626; }
        """)

        def _descartar():
            db.execute_query(
                "UPDATE ventas SET marcada='0', motivo_marca=NULL WHERE id=?",
                (sale_id,),
            )
            dlg.accept()
            self.load_sales()

        def _anular():
            dlg.accept()
            self._dialogo_anular(sale_id)

        descartar_btn.clicked.connect(_descartar)
        anular_btn.clicked.connect(_anular)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(descartar_btn)
        btn_row.addWidget(anular_btn)
        layout.addLayout(btn_row)
        dlg.exec()

    # ══════════════════════════════════════════════════════════
    #  Diálogos anular / desanular
    # ══════════════════════════════════════════════════════════

    def _dialogo_anular(self, sale_id: int, parent=None, on_accept=None):
        from ui.reset_password_dialog import get_master_hash
        from models.user import _verify_password
 
        sale = Sale.get_by_id(sale_id)
        if not sale:
            return
 
        dlg = QDialog(parent or self)
        dlg.setWindowTitle("Anular Factura")
        dlg.setFixedWidth(480)
        dlg.setStyleSheet("background-color: #F9FAFB;")
 
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(16)
 
        # Banner advertencia
        warn = QFrame()
        warn.setStyleSheet("""
            QFrame {
                background-color: #FEF2F2;
                border: 1.5px solid #FECACA;
                border-radius: 12px;
                padding: 4px;
            }
        """)
        wl = QHBoxLayout(warn)
        wl.setContentsMargins(16, 16, 16, 16)
        wl.setSpacing(14)
 
        ico = QLabel("⚠️")
        ico.setStyleSheet("font-size: 26px; background: transparent; border: none")
        ico.setFixedWidth(50),ico.setFixedHeight(50)
        ico.setAlignment(Qt.AlignmentFlag.AlignTop)
        wl.addWidget(ico)
 
        txts = QVBoxLayout()
        txts.setSpacing(6)
        title_lbl = QLabel(f"Anular {sale.numero_factura}")
        title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #991B1B; background: transparent; border: none")
        title_lbl.setWordWrap(True)
 
        desc_lbl = QLabel(
            "Esta acción requiere clave maestra.\n"
            "La factura dejará de contabilizarse en reportes.")
        desc_lbl.setStyleSheet(
            "font-size: 12px; color: #B91C1C; background: transparent; border: none")
        desc_lbl.setWordWrap(True)
 
        txts.addWidget(title_lbl)
        txts.addWidget(desc_lbl)
        wl.addLayout(txts, stretch=1)
        layout.addWidget(warn)
 
        # Clave maestra
        layout.addWidget(_lbl("Clave maestra *", "#374151", 13, bold=True))
        master_input = QLineEdit()
        master_input.setEchoMode(QLineEdit.EchoMode.Password)
        master_input.setPlaceholderText("Ingresa la clave maestra del sistema")
        master_input.setFixedHeight(40)
        master_input.setStyleSheet(_INPUT_MASTER_STYLE)
        layout.addWidget(master_input)
 
        # Motivo
        layout.addWidget(_lbl("Motivo de anulación *", "#374151", 13, bold=True))
        motivo_input = QTextEdit()
        motivo_input.setPlaceholderText(
            "Ej: Error en el pedido, devolución del cliente, duplicado...")
        motivo_input.setFixedHeight(90)
        motivo_input.setStyleSheet(_INPUT_MOTIVO_STYLE)
        layout.addWidget(motivo_input)
 
        # Botones
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()
 
        cancel = QPushButton("Cancelar")
        cancel.setFixedHeight(40)
        cancel.setMinimumWidth(100)
        cancel.setStyleSheet(_BTN_CANCEL_STYLE)
        cancel.clicked.connect(dlg.reject)
 
        confirm = QPushButton("🚫  Confirmar Anulación")
        confirm.setFixedHeight(40)
        confirm.setMinimumWidth(160)
        confirm.setStyleSheet(_BTN_ANULAR_STYLE)
 
        def _confirmar():
            master = master_input.text().strip()
            stored_hash = get_master_hash()
            if not stored_hash or not _verify_password(master, stored_hash):
                QMessageBox.critical(dlg, "Acceso denegado",
                                     "❌ La clave maestra es incorrecta.")
                master_input.clear()
                master_input.setFocus()
                return
            motivo = motivo_input.toPlainText().strip()
            if not motivo:
                motivo_input.setStyleSheet(
                    _INPUT_MOTIVO_STYLE + "QTextEdit { border-color: #EF4444; }")
                return
            db.execute_query(
                "UPDATE ventas SET estado='anulada', motivo_anulacion=?, "
                "marcada='0', motivo_marca=NULL WHERE id=?",
                (motivo, sale_id),
            )
            dlg.accept()
            if on_accept:
                on_accept()
            self.load_sales()
 
        confirm.clicked.connect(_confirmar)
        btn_row.addWidget(cancel)
        btn_row.addWidget(confirm)
        layout.addLayout(btn_row)
        dlg.exec()
 
    def _dialogo_desanular(self, sale_id: int, parent=None, on_accept=None):
        from ui.reset_password_dialog import get_master_hash
        from models.user import _verify_password
 
        sale = Sale.get_by_id(sale_id)
        if not sale:
            return
 
        dlg = QDialog(parent or self)
        dlg.setWindowTitle("Desanular Factura")
        dlg.setFixedWidth(460)
        dlg.setStyleSheet("background-color: #F9FAFB;")
 
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(16)
 
        # Banner info
        info = QFrame()
        info.setStyleSheet("""
            QFrame {
                background-color: #FFFBEB;
                border: 1.5px solid #FDE68A;
                border-radius: 12px;
                padding: 4px;
            }
        """)
        il = QHBoxLayout(info)
        il.setContentsMargins(16, 16, 16, 16)
        il.setSpacing(14)
 
        ico = QLabel("ℹ️")
        ico.setStyleSheet("font-size: 26px; background: transparent; border: none")
        ico.setFixedWidth(50), ico.setFixedHeight(50)
        ico.setAlignment(Qt.AlignmentFlag.AlignTop)
        il.addWidget(ico)
 
        txts = QVBoxLayout()
        txts.setSpacing(6)
        title_lbl = QLabel(f"Desanular {sale.numero_factura}")
        title_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #92400E; background: transparent; border: none")
        title_lbl.setWordWrap(True)
 
        desc_lbl = QLabel("La factura volverá a contabilizarse en reportes.")
        desc_lbl.setStyleSheet(
            "font-size: 12px; color: #B45309; background: transparent; border: none")
        desc_lbl.setWordWrap(True)
 
        txts.addWidget(title_lbl)
        txts.addWidget(desc_lbl)
        il.addLayout(txts, stretch=1)
        layout.addWidget(info)
 
        # Clave maestra
        layout.addWidget(_lbl("Clave maestra *", "#374151", 13, bold=True))
        master_input = QLineEdit()
        master_input.setEchoMode(QLineEdit.EchoMode.Password)
        master_input.setPlaceholderText("Ingresa la clave maestra del sistema")
        master_input.setFixedHeight(40)
        master_input.setStyleSheet(_INPUT_MASTER_STYLE)
        layout.addWidget(master_input)
 
        # Botones
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()
 
        cancel = QPushButton("Cancelar")
        cancel.setFixedHeight(40)
        cancel.setMinimumWidth(100)
        cancel.setStyleSheet(_BTN_CANCEL_STYLE)
        cancel.clicked.connect(dlg.reject)
 
        confirm = QPushButton("✅  Confirmar Desanulación")
        confirm.setFixedHeight(40)
        confirm.setMinimumWidth(170)
        confirm.setStyleSheet(_BTN_DESANULAR_STYLE)
 
        def _confirmar():
            master = master_input.text().strip()
            stored_hash = get_master_hash()
            if not stored_hash or not _verify_password(master, stored_hash):
                QMessageBox.critical(dlg, "Acceso denegado",
                                     "❌ La clave maestra es incorrecta.")
                master_input.clear()
                master_input.setFocus()
                return
            db.execute_query(
                "UPDATE ventas SET estado='completada', motivo_anulacion=NULL WHERE id=?",
                (sale_id,),
            )
            dlg.accept()
            if on_accept:
                on_accept()
            self.load_sales()
 
        confirm.clicked.connect(_confirmar)
        btn_row.addWidget(cancel)
        btn_row.addWidget(confirm)
        layout.addLayout(btn_row)
        dlg.exec()
 
    # ══════════════════════════════════════════════════════════
    #  Marcar / desmarcar (cajero)
    # ══════════════════════════════════════════════════════════

    def marcar_factura(self, sale_dict):
        ya_marcada = str(sale_dict.get('marcada', '0')) == '1'

        if ya_marcada:
            db.execute_query(
                "UPDATE ventas SET marcada='0', motivo_marca=NULL WHERE id=?",
                (sale_dict['id'],),
            )
            self.load_sales()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Marcar para revisión")
        dialog.setFixedSize(430, 255)
        dialog.setStyleSheet("background-color: #F9FAFB;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)

        warn = QFrame()
        warn.setStyleSheet("""
            QFrame {
                background-color: #FFFBEB;
                border: 1.5px solid #FDE68A;
                border-radius: 12px;
            }
        """)
        wl = QHBoxLayout(warn)
        wl.setContentsMargins(16, 12, 16, 12)
        wl.setSpacing(12)
        ico = QLabel("⚑")
        ico.setStyleSheet("font-size: 22px;")
        wl.addWidget(ico)
        txts = QVBoxLayout()
        txts.addWidget(_lbl_bold(
            f"Marcar {sale_dict['numero_factura']} para revisión",
            "#92400E", 13))
        txts.addWidget(_lbl(
            "El administrador verá esta factura destacada\n"
            "con un aviso en el panel de ventas.",
            "#B45309", 12))
        wl.addLayout(txts)
        layout.addWidget(warn)

        layout.addWidget(_lbl("¿Por qué la marcás? *", "#374151", 13, bold=True))

        motivo_input = QTextEdit()
        motivo_input.setPlaceholderText(
            "Ej: El cliente reclamó, hubo un error en el cobro...")
        motivo_input.setFixedHeight(65)
        motivo_input.setStyleSheet(_INPUT_MOTIVO_STYLE)
        layout.addWidget(motivo_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = QPushButton("Cancelar")
        cancel.setFixedHeight(36)
        cancel.setStyleSheet(_BTN_CANCEL_STYLE)
        cancel.clicked.connect(dialog.reject)

        confirm = QPushButton("⚑  Marcar Factura")
        confirm.setFixedHeight(36)
        confirm.setStyleSheet(_BTN_DESANULAR_STYLE)

        def _confirmar():
            motivo = motivo_input.toPlainText().strip()
            if not motivo:
                motivo_input.setStyleSheet(
                    _INPUT_MOTIVO_STYLE + "QTextEdit { border-color: #F59E0B; }")
                return
            db.execute_query(
                "UPDATE ventas SET marcada='1', motivo_marca=? WHERE id=?",
                (motivo, sale_dict['id']),
            )
            dialog.accept()
            self.load_sales()

        confirm.clicked.connect(_confirmar)
        btn_row.addWidget(cancel)
        btn_row.addWidget(confirm)
        layout.addLayout(btn_row)
        dialog.exec()

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

        # ── Encabezado ─────────────────────────────────────────
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
            "font-size: 18px; font-weight: 800; color: #1F2937; border: none")
        fecha_lbl = QLabel(
            datetime.fromisoformat(sale.fecha_venta).strftime("%d/%m/%Y  %H:%M"))
        fecha_lbl.setStyleSheet("font-size: 12px; color: #6B7280; border: none")
        left.addWidget(factura_lbl)
        left.addWidget(fecha_lbl)
        hl.addLayout(left)
        hl.addStretch()

        color_estado = "#10B981" if sale.estado == "completada" else "#EF4444"
        estado_lbl = QLabel(f"  {sale.estado.title()}  ")
        estado_lbl.setStyleSheet(f"""
            background-color: {color_estado};
            color: white;
            font-size: 12px; font-weight: 700;
            border-radius: 8px; padding: 4px 8px;
            border: 1px solid {color_estado}40;
        """)
        hl.addWidget(estado_lbl)

        if sale.estado == 'anulada':
            row_m = db.fetch_one(
                "SELECT motivo_anulacion FROM ventas WHERE id=?", (sale.id,))
            if row_m and row_m['motivo_anulacion']:
                motivo_frame = QFrame()
                motivo_frame.setStyleSheet("""
                    QFrame {
                        background-color: #FEF2F2;
                        border: 1px solid #FECACA;
                        border-radius: 8px;
                    }
                """)
                ml = QHBoxLayout(motivo_frame)
                ml.setContentsMargins(12, 8, 12, 8)
                motivo_lbl = QLabel(
                    f"Motivo de anulación: {row_m['motivo_anulacion']}")
                motivo_lbl.setStyleSheet("font-size: 12px; color: #991B1B;border: none")
                motivo_lbl.setWordWrap(True)
                ml.addWidget(motivo_lbl)
                hl.addWidget(motivo_frame)

        layout.addWidget(header_frame)

        # ── Info cliente y método ──────────────────────────────
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
            lbl_w = QLabel(label)
            lbl_w.setStyleSheet(
                "font-size: 10px; font-weight: 700; color: #9CA3AF; "
                "letter-spacing: 0.5px;border: none")
            val_w = QLabel(value)
            val_w.setStyleSheet(
                "font-size: 13px; font-weight: 600; color: #1F2937;border: none")
            col.addWidget(lbl_w)
            col.addWidget(val_w)
            return col

        metodos = {
            "efectivo": "💵 Efectivo", "qr": "💱 QR",
            "tarjeta":  "💳 Tarjeta",  "mixto": "⚡ Mixto"
        }
        il.addLayout(info_col("CLIENTE", sale.cliente or "Cliente General"))
        il.addLayout(info_col(
            "MÉTODO DE PAGO",
            metodos.get(sale.metodo_pago, sale.metodo_pago.title())))
        il.addStretch()
        layout.addWidget(info_frame)

        # ── Tabla de productos ─────────────────────────────────
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

        agrupado = {}
        orden = []
        for item in sale.items:
            key = item.producto_nombre
            if key not in agrupado:
                agrupado[key] = {"cantidad": 0,
                                 "precio": item.precio_unitario,
                                 "subtotal": 0}
                orden.append(key)
            agrupado[key]["cantidad"] += item.cantidad
            agrupado[key]["subtotal"] += item.subtotal

        items_table.setRowCount(len(orden))
        for row_i, key in enumerate(orden):
            vals = agrupado[key]
            items_table.setItem(row_i, 0, QTableWidgetItem(key))

            cant = QTableWidgetItem(str(vals["cantidad"]))
            cant.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items_table.setItem(row_i, 1, cant)

            precio = QTableWidgetItem(f"Bs {vals['precio']:,.2f}")
            precio.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items_table.setItem(row_i, 2, precio)

            sub = QTableWidgetItem(f"Bs {vals['subtotal']:,.2f}")
            sub.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            sub.setForeground(QColor("#10B981"))
            sub.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            items_table.setItem(row_i, 3, sub)
            items_table.setRowHeight(row_i, 40)

        hdr = items_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        items_table.setColumnWidth(1, 60)
        items_table.setColumnWidth(2, 110)
        items_table.setColumnWidth(3, 110)
        layout.addWidget(items_table)

        # ── Totales ────────────────────────────────────────────
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
            rw = QHBoxLayout()
            lbl_w = QLabel(label)
            lbl_w.setStyleSheet(
                f"font-size: {'14' if big else '12'}px; "
                f"font-weight: {'700' if bold else '500'}; color: #6B7280; border: none")
            val_w = QLabel(valor)
            val_w.setStyleSheet(
                f"font-size: {'16' if big else '12'}px; "
                f"font-weight: {'800' if bold else '500'}; color: {color};border: none")
            rw.addStretch()
            rw.addWidget(lbl_w)
            rw.addSpacing(24)
            rw.addWidget(val_w)
            tl.addLayout(rw)

        total_row("Subtotal:", f"Bs {sale.subtotal:,.2f}")
        if sale.descuento and sale.descuento > 0:
            total_row("Descuento:", f"- Bs {sale.descuento:,.2f}", color="#EF4444")

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E5E7EB;")
        tl.addWidget(line)
        total_row("TOTAL:", f"Bs {sale.total:,.2f}",
                  bold=True, color="#10B981", big=True)
        layout.addWidget(totals_frame)

        # ── Botones del diálogo ────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        pdf_btn = QPushButton("📄 Generar PDF")
        pdf_btn.setFixedHeight(38)
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6; color: white;
                border-radius: 8px; font-weight: 600;
                font-size: 13px; padding: 0 16px;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)
        pdf_btn.clicked.connect(lambda: self._generar_pdf(sale, dialog))
        btn_row.addWidget(pdf_btn)

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

        user = get_current_user()
        if user and user.rol == 'admin':
            if sale.estado != 'anulada':
                anular_btn = QPushButton("🚫 Anular")
                anular_btn.setFixedHeight(38)
                anular_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #EF4444; color: white;
                        border-radius: 8px; font-weight: 600;
                        font-size: 13px; padding: 0 16px;
                    }
                    QPushButton:hover { background-color: #DC2626; }
                """)
                anular_btn.clicked.connect(
                    lambda: self._dialogo_anular(
                        sale.id, parent=dialog, on_accept=dialog.reject))
                btn_row.addWidget(anular_btn)
            else:
                desanular_btn = QPushButton("✅ Desanular")
                desanular_btn.setFixedHeight(38)
                desanular_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F59E0B; color: white;
                        border-radius: 8px; font-weight: 600;
                        font-size: 13px; padding: 0 16px;
                    }
                    QPushButton:hover { background-color: #D97706; }
                """)
                desanular_btn.clicked.connect(
                    lambda: self._dialogo_desanular(
                        sale.id, parent=dialog, on_accept=dialog.reject))
                btn_row.addWidget(desanular_btn)

        btn_row.addStretch()

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
        close_btn.setDefault(True)
        close_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)
        dialog.exec()

    def _generar_pdf(self, sale, parent_dialog=None):
        try:
            
            filepath = generate_invoice(sale)
            QMessageBox.information(
                parent_dialog or self, "Éxito",
                f"Factura generada:\n{filepath}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                parent_dialog or self, "Error",
                f"Error al generar factura:\n{traceback.format_exc()}")

    def _imprimir_ticket(self, sale):
        try:
            from utils.printer import imprimir_recibo
            ok, msg = imprimir_recibo(
                sale,
                nombre_negocio="La Placita",
                nombre="Cafetería & Heladería",
                subtitulo="Sucursal Santa Fe",
                telefono="77113371",
                mensaje_pie="¡Gracias por su visita!\nVuelva pronto",
                abrir_cajon=False,
            )
            if ok:
                QMessageBox.information(self, "Éxito", "Ticket impreso correctamente.")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo imprimir:\n{msg}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al imprimir:\n{str(e)}")


    
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
            filepath = InvoiceGenerator().generate_sales_report(sales, filename, fecha_desde, fecha_hasta)
            
            QMessageBox.information(self, "Éxito", f"Reporte PDF generado:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar PDF:\n{str(e)}")