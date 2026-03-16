"""
Finance Widget - Complete Financial Analysis
Monthly revenue, expenses, profit margin, and detailed product analysis
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
    QScrollArea, QHeaderView, QDialog, QDialogButtonBox,
    QLineEdit, QDoubleSpinBox, QMessageBox, QSpinBox,
    QDateEdit, QTextEdit, QFormLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor
from datetime import datetime
from database.connection import db
from utils.excel_exporter import ExcelExporter
from utils.pdf_generator import InvoiceGenerator
import calendar


# ──────────────────────────────────────────────────────────────────────────────
# Smart widgets — evitan scroll accidental al navegar la pantalla
# ──────────────────────────────────────────────────────────────────────────────

class SmartComboBox(QComboBox):
    """ComboBox que solo permite scroll cuando el desplegable está abierto."""
    def wheelEvent(self, event):
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


class SmartSpinBox(QSpinBox):
    """SpinBox que solo permite scroll cuando tiene el foco."""
    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class SmartDoubleSpinBox(QDoubleSpinBox):
    """DoubleSpinBox que solo permite scroll cuando tiene el foco."""
    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


# ──────────────────────────────────────────────────────────────────────────────
# StatCard
# ──────────────────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    """Financial stat card"""

    def __init__(self, icon, value, label, color="#FF6B35", editable=False, on_edit=None):
        super().__init__()
        self.value_text = value
        self.editable   = editable
        self.on_edit    = on_edit

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

        top_layout = QHBoxLayout()

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
        top_layout.addWidget(icon_label)

        if editable:
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(26, 10)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3B82F6;
                    color: white;
                    border-radius: 6px;
                    min-width: 26px; max-width: 26px;
                    min-height: 26px; max-height: 26px;
                    margin: 0px 0px 0px 80px;
                }
                QPushButton:hover { background-color: #2563EB; }
            """)
            edit_btn.clicked.connect(self.on_edit)
            top_layout.addWidget(edit_btn)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            "font-size: 28px; font-weight: 700; color: #1F2937;")
        layout.addWidget(self.value_label)

        label_label = QLabel(label)
        label_label.setStyleSheet(
            "font-size: 14px; color: black; font-weight: 500;")
        layout.addWidget(label_label)

        layout.addStretch()

    def update_value(self, value):
        self.value_text = value
        self.value_label.setText(value)


# ──────────────────────────────────────────────────────────────────────────────
# Constantes compartidas
# ──────────────────────────────────────────────────────────────────────────────

CATEGORIAS_COSTO = [
    ("🏠", "Alquiler / Infraestructura"),
    ("👥", "Personal / Sueldos"),
    ("💡", "Servicios (agua, luz, gas)"),
    ("📦", "Otros"),
]

EJEMPLOS_COSTO = {
    "fijo":     "• Alquiler&nbsp;&nbsp;• Sueldos fijos&nbsp;&nbsp;• Seguros&nbsp;&nbsp;• Servicios básicos",
    "variable": "• Insumos extra&nbsp;&nbsp;• Horas extra&nbsp;&nbsp;• Comisiones&nbsp;&nbsp;• Gastos eventuales",
}

MESES_ES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]


# ──────────────────────────────────────────────────────────────────────────────
# AddCostDialog — dialog para agregar un costo individual
# ──────────────────────────────────────────────────────────────────────────────

class AddCostDialog(QDialog):
    """Dialog para agregar un nuevo costo (fijo o variable)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar Costo")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(28, 24, 28, 24)

        title = QLabel("💼 Nuevo Costo")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1F2937;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Tipo
        self.tipo_combo = SmartComboBox()
        self.tipo_combo.addItem("🏢  Costo Fijo",     "fijo")
        self.tipo_combo.addItem("📊  Costo Variable", "variable")
        self.tipo_combo.setStyleSheet("font-size: 14px; padding: 6px;")
        self.tipo_combo.currentIndexChanged.connect(self._update_info)
        form.addRow("Tipo: *", self.tipo_combo)

        # Concepto
        self.concepto_input = QLineEdit()
        self.concepto_input.setPlaceholderText("Ej: Alquiler local, Sueldo mesero…")
        self.concepto_input.setStyleSheet("font-size: 14px; padding: 6px;")
        form.addRow("Concepto: *", self.concepto_input)

        # Categoría
        self.categoria_combo = SmartComboBox()
        for icono, nombre in CATEGORIAS_COSTO:
            self.categoria_combo.addItem(f"{icono}  {nombre}", nombre)
        self.categoria_combo.setStyleSheet("font-size: 14px; padding: 6px;")
        form.addRow("Categoría:", self.categoria_combo)

        # Monto
        self.monto_input = SmartDoubleSpinBox()
        self.monto_input.setPrefix("Bs ")
        self.monto_input.setRange(0.01, 999999.99)
        self.monto_input.setDecimals(2)
        self.monto_input.setSingleStep(10)
        self.monto_input.setStyleSheet("font-size: 15px; padding: 6px;")
        form.addRow("Monto: *", self.monto_input)

        # Fecha
        self.fecha_input = QDateEdit()
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setDate(QDate.currentDate())
        self.fecha_input.setDisplayFormat("dd/MM/yyyy")
        self.fecha_input.setStyleSheet("font-size: 14px; padding: 6px;")
        form.addRow("Fecha:", self.fecha_input)

        # Descripción
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(70)
        self.desc_input.setPlaceholderText("Nota adicional (opcional)…")
        self.desc_input.setStyleSheet("font-size: 13px; padding: 4px;")
        form.addRow("Descripción:", self.desc_input)

        layout.addLayout(form)

        # Panel informativo contextual
        self.info_label = QLabel()
        self.info_label.setStyleSheet("""
            color: #6B7280; font-size: 13px; padding: 12px;
            background-color: #F9FAFB; border-radius: 8px;
            border: 1px solid #E5E7EB;
        """)
        self.info_label.setWordWrap(True)
        self.info_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.info_label)
        self._update_info()

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("💾 Guardar")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _update_info(self):
        tipo  = self.tipo_combo.currentData()
        color = "#3B82F6" if tipo == "fijo" else "#F59E0B"
        desc  = ("No varía con el volumen de ventas."
                 if tipo == "fijo" else
                 "Cambia según la actividad del negocio.")
        self.info_label.setText(
            f"<b style='color:{color}'>Costo {'fijo' if tipo=='fijo' else 'variable'}:</b> {desc}"
            f"<br><span style='color:#9CA3AF'>Ejemplos: {EJEMPLOS_COSTO.get(tipo,'')}</span>"
        )

    def _validate_and_accept(self):
        if not self.concepto_input.text().strip():
            QMessageBox.warning(self, "Campo requerido", "El concepto es obligatorio.")
            self.concepto_input.setFocus()
            return
        if self.monto_input.value() <= 0:
            QMessageBox.warning(self, "Campo requerido", "El monto debe ser mayor a 0.")
            self.monto_input.setFocus()
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "tipo":        self.tipo_combo.currentData(),
            "concepto":    self.concepto_input.text().strip(),
            "categoria":   self.categoria_combo.currentData(),
            "monto":       self.monto_input.value(),
            "fecha_gasto": self.fecha_input.date().toString("yyyy-MM-dd"),
            "descripcion": self.desc_input.toPlainText().strip(),
        }


# ──────────────────────────────────────────────────────────────────────────────
# VerCostosDialog — dialog para ver, filtrar y eliminar costos registrados
# ──────────────────────────────────────────────────────────────────────────────

class VerCostosDialog(QDialog):
    """Dialog con tabla filtrable de todos los costos del período seleccionado."""

    def __init__(self, current_year: int, current_month: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📋 Costos Registrados")
        self.setMinimumSize(780, 560)
        self.setModal(True)
        self._year          = current_year
        self._month         = current_month
        self._all_rows      = []
        self._finance_widget = parent   # referencia directa, no depende de self.parent()
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # Título
        title = QLabel("📋 Costos Registrados")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1F2937;")
        layout.addWidget(title)

        # ── Barra de filtros ──────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }
        """)
        fl = QHBoxLayout(filter_frame)
        fl.setSpacing(10)
        fl.setContentsMargins(14, 10, 14, 10)

        def lbl(text):
            l = QLabel(text)
            l.setStyleSheet("font-weight: 600; color: #4B5563; font-size: 13px;")
            return l

        # Mes
        fl.addWidget(lbl("Mes:"))
        self.f_month = SmartComboBox()
        self.f_month.addItem("Todos", 0)
        for i, m in enumerate(MESES_ES, 1):
            self.f_month.addItem(m, i)
        self.f_month.setCurrentIndex(self._month)   # preseleccionar mes actual
        self.f_month.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.f_month)

        # Año
        fl.addWidget(lbl("Año:"))
        self.f_year = SmartSpinBox()
        self.f_year.setRange(2020, 2030)
        self.f_year.setValue(self._year)
        self.f_year.valueChanged.connect(self._on_year_changed)
        fl.addWidget(self.f_year)

        # Tipo
        fl.addWidget(lbl("Tipo:"))
        self.f_tipo = SmartComboBox()
        self.f_tipo.addItem("Todos",       "todos")
        self.f_tipo.addItem("🏢 Fijo",     "fijo")
        self.f_tipo.addItem("📊 Variable", "variable")
        self.f_tipo.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.f_tipo)

        # Categoría
        fl.addWidget(lbl("Categoría:"))
        self.f_cat = SmartComboBox()
        self.f_cat.addItem("Todas", "todas")
        for _, nombre in CATEGORIAS_COSTO:
            self.f_cat.addItem(nombre, nombre)
        self.f_cat.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.f_cat)

        fl.addStretch()

        clear_btn = QPushButton("↺ Limpiar")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #E5E7EB; color: #4B5563;
                padding: 6px 14px; border-radius: 7px;
                font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background-color: #D1D5DB; }
        """)
        clear_btn.clicked.connect(self._clear_filters)
        fl.addWidget(clear_btn)

        layout.addWidget(filter_frame)

        # Resumen
        self.resumen_lbl = QLabel()
        self.resumen_lbl.setStyleSheet("font-size: 13px; color: #6B7280;")
        self.resumen_lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.resumen_lbl)

        # ── Tabla ─────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Tipo", "Concepto", "Categoría", "Monto", "Fecha", ""]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E5E7EB; border-radius: 10px;
                font-size: 13px; background-color: white;
                alternate-background-color: #F9FAFB;
            }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #F3F4F6; }
            QHeaderView::section {
                background-color: #F3F4F6; color: #6B7280;
                font-weight: 600; font-size: 12px;
                padding: 10px 8px; border: none;
                border-bottom: 2px solid #E5E7EB;
            }
        """)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 48)

        layout.addWidget(self.table)

        # Botón cerrar
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B7280; color: white;
                padding: 10px 28px; border-radius: 8px;
                font-weight: 600; font-size: 13px;
            }
            QPushButton:hover { background-color: #4B5563; }
        """)
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    # ── Carga y filtrado ──────────────────────────────────────────────

    def _load_data(self):
        """Carga todos los costos del año desde la BD."""
        year  = self.f_year.value()
        rows  = db.fetch_all(
            "SELECT id, tipo, concepto, categoria, monto, fecha_gasto "
            "FROM gastos WHERE strftime('%Y', fecha_gasto)=? "
            "ORDER BY fecha_gasto DESC, id DESC",
            (str(year),)
        )
        self._all_rows = [dict(r) for r in rows] if rows else []
        self._apply_filters()

    def _on_year_changed(self):
        """Al cambiar el año vuelve a consultar la BD."""
        self._load_data()

    def _apply_filters(self):
        mes_sel  = self.f_month.currentData()   # 0 = todos
        tipo_sel = self.f_tipo.currentData()
        cat_sel  = self.f_cat.currentData()

        filtered = []
        for r in self._all_rows:
            if mes_sel != 0:
                if int(r["fecha_gasto"][5:7]) != mes_sel:
                    continue
            if tipo_sel != "todos" and r["tipo"] != tipo_sel:
                continue
            if cat_sel != "todas" and r.get("categoria", "") != cat_sel:
                continue
            filtered.append(r)

        self._fill_table(filtered)

    def _fill_table(self, rows: list):
        self.table.setRowCount(len(rows))
        total_fijo = total_var = 0.0

        for i, r in enumerate(rows):
            es_fijo = r["tipo"] == "fijo"
            monto   = float(r["monto"])
            if es_fijo:
                total_fijo += monto
            else:
                total_var  += monto

            # Tipo badge
            tipo_lbl = QLabel("🏢 Fijo" if es_fijo else "📊 Variable")
            tipo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tipo_lbl.setStyleSheet(
                f"background-color:{'#EFF6FF' if es_fijo else '#FFFBEB'};"
                f"color:{'#3B82F6' if es_fijo else '#D97706'};"
                "font-size:12px;font-weight:600;"
                "padding:4px 8px;border-radius:6px;margin:4px;"
            )
            self.table.setCellWidget(i, 0, tipo_lbl)

            self.table.setItem(i, 1, QTableWidgetItem(r["concepto"]))

            cat_item = QTableWidgetItem(r.get("categoria") or "—")
            cat_item.setForeground(QColor("#6B7280"))
            self.table.setItem(i, 2, cat_item)

            monto_item = QTableWidgetItem(f"Bs {monto:.2f}")
            monto_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            monto_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            self.table.setItem(i, 3, monto_item)

            try:
                fecha_fmt = datetime.strptime(
                    r["fecha_gasto"], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                fecha_fmt = r["fecha_gasto"]
            fecha_item = QTableWidgetItem(fecha_fmt)
            fecha_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            fecha_item.setForeground(QColor("#6B7280"))
            self.table.setItem(i, 4, fecha_item)

            del_btn = QPushButton("🗑️")
            del_btn.setToolTip("Eliminar")
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color:#FEE2E2;color:#EF4444;
                    border:none;border-radius:6px;
                    font-size:14px;padding:4px;margin:4px;
                }
                QPushButton:hover{background-color:#FECACA;}
            """)
            gid = r["id"]
            del_btn.clicked.connect(lambda checked=False, g=gid: self._delete_cost(g))
            self.table.setCellWidget(i, 5, del_btn)
            self.table.setRowHeight(i, 44)

        total = total_fijo + total_var
        self.resumen_lbl.setText(
            f"{len(rows)} registro(s)  ·  "
            f"Fijos: <b>Bs {total_fijo:.2f}</b>  |  "
            f"Variables: <b>Bs {total_var:.2f}</b>  |  "
            f"Total: <b>Bs {total:.2f}</b>"
        )

    def _delete_cost(self, gasto_id: int):
        reply = QMessageBox.question(
            self, "Confirmar eliminación",
            "¿Eliminar este costo? Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                gasto_id = int(gasto_id)
                conn = db.get_connection()
                conn.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))
                conn.commit()
                self._all_rows = [r for r in self._all_rows if int(r["id"]) != gasto_id]
                self._apply_filters()
                if self._finance_widget and hasattr(self._finance_widget, "refresh_after_cost_change"):
                    self._finance_widget.refresh_after_cost_change()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el costo:\n{str(e)}")

    def _clear_filters(self):
        self.f_month.setCurrentIndex(0)
        self.f_tipo.setCurrentIndex(0)
        self.f_cat.setCurrentIndex(0)


# ──────────────────────────────────────────────────────────────────────────────
# CostosCard — card compacta (misma fila que Ingresos / Gastos / Ganancia)
# ──────────────────────────────────────────────────────────────────────────────

class CostosCard(QFrame):
    """Card compacta de Costos con totales y botones Agregar / Ver."""

    def __init__(self, parent_widget):
        super().__init__()
        self._parent         = parent_widget
        self._year           = datetime.now().year
        self._month          = datetime.now().month
        self._total_fijo     = 0.0
        self._total_variable = 0.0

        self.setObjectName("costos-stat-card")
        self.setStyleSheet("""
            QFrame#costos-stat-card {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
            }
        """)
        self.setFixedSize(300, 250)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # ── Ícono fijo 52x52 ──────────────────────────────────────────
        icon_lbl = QLabel("💼")
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setStyleSheet("""
            background-color: #8B5CF620;
            color: #8B5CF6;
            font-size: 24px;
            border-radius: 12px;
        """)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        # ── Valor total ───────────────────────────────────────────────
        self.total_lbl = QLabel("Bs 0.00")
        self.total_lbl.setFixedHeight(38)
        self.total_lbl.setStyleSheet(
            "font-size: 26px; font-weight: 700; color: #1F2937;")
        layout.addWidget(self.total_lbl)

        # ── Título ────────────────────────────────────────────────────
        title_lbl = QLabel("Costos del Mes")
        title_lbl.setFixedHeight(20)
        title_lbl.setStyleSheet(
            "font-size: 13px; color: #111827; font-weight: 500;")
        layout.addWidget(title_lbl)

        # ── Desglose Fijo / Variable ──────────────────────────────────
        self.detalle_lbl = QLabel("Fijo: Bs 0.00  |  Variable: Bs 0.00")
        self.detalle_lbl.setFixedHeight(18)
        self.detalle_lbl.setStyleSheet("font-size: 11px; color: #6B7280;")
        layout.addWidget(self.detalle_lbl)

        layout.addStretch()

        # ── Botones al pie ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setContentsMargins(0, 0, 0, 0)

        ver_btn = QPushButton("📋 Ver Costos")
        ver_btn.setFixedHeight(32)
        ver_btn.setToolTip("Ver y filtrar costos registrados")
        ver_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E7FF; color: #4F46E5;
                padding: 0px 12px; border-radius: 8px;
                font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background-color: #C7D2FE; }
        """)
        ver_btn.clicked.connect(self._open_ver_dialog)
        btn_row.addWidget(ver_btn)

        add_btn = QPushButton("➕ Agregar")
        add_btn.setFixedHeight(32)
        add_btn.setToolTip("Registrar un nuevo costo")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6; color: white;
                padding: 0px 12px; border-radius: 8px;
                font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background-color: #7C3AED; }
        """)
        add_btn.clicked.connect(self._open_add_dialog)
        btn_row.addWidget(add_btn)

        layout.addLayout(btn_row)

    # ── Carga ─────────────────────────────────────────────────────────

    def load_costs(self, year: int, month: int):
        self._year  = year
        self._month = month
        rows = db.fetch_all(
            "SELECT tipo, COALESCE(SUM(monto),0) as total "
            "FROM gastos WHERE strftime('%Y-%m', fecha_gasto)=? GROUP BY tipo",
            (f"{year}-{month:02d}",)
        )
        self._total_fijo     = 0.0
        self._total_variable = 0.0
        for r in (rows or []):
            if r["tipo"] == "fijo":
                self._total_fijo = float(r["total"])
            elif r["tipo"] == "variable":
                self._total_variable = float(r["total"])
        self._refresh_display()

    def _refresh_display(self):
        total = self._total_fijo + self._total_variable
        self.total_lbl.setText(f"Bs {total:.2f}")
        self.detalle_lbl.setText(
            f"Fijo: Bs {self._total_fijo:.2f}  |  Variable: Bs {self._total_variable:.2f}"
        )

    def get_totals(self) -> tuple:
        return self._total_fijo, self._total_variable

    # ── Acciones ──────────────────────────────────────────────────────

    def _open_add_dialog(self):
        dialog = AddCostDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            # ✅ execute_query es el método correcto del DatabaseManager
            db.execute_query(
                "INSERT INTO gastos "
                "(concepto, monto, tipo, categoria, descripcion, fecha_gasto, usuario_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    data["concepto"],
                    data["monto"],
                    data["tipo"],
                    data["categoria"],
                    data["descripcion"],
                    data["fecha_gasto"],
                    1,
                ),
            )
            self.load_costs(self._year, self._month)
            self._parent.refresh_after_cost_change()

    def _open_ver_dialog(self):
        dialog = VerCostosDialog(self._year, self._month, parent=self._parent)
        dialog.exec()
        # Refrescar por si hubo eliminaciones desde el dialog
        self.load_costs(self._year, self._month)
        self._parent.refresh_after_cost_change()


# ──────────────────────────────────────────────────────────────────────────────
# FinanceWidget
# ──────────────────────────────────────────────────────────────────────────────

class FinanceWidget(QWidget):
    """Complete financial analysis widget"""

    def __init__(self):
        super().__init__()
        self.current_month = datetime.now().month
        self.current_year  = datetime.now().year
        self.init_ui()
        self.update_stats()

    def init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(40, 30, 40, 40)
        main_layout.setSpacing(30)

        self._create_header(main_layout)

        # Fila 1: 4 stat cards dinámicas (Ingresos / Gastos / Ganancia / Margen)
        self.main_stats_layout = QHBoxLayout()
        self.main_stats_layout.setSpacing(20)
        main_layout.addLayout(self.main_stats_layout)

        # Fila 2: CostosCard alineada bajo "Ingresos del Mes" y "Gastos del Mes"
        self.costos_row_layout = QHBoxLayout()
        self.costos_row_layout.setSpacing(20)
        self.costos_card = CostosCard(parent_widget=self)
        self.costos_card.load_costs(self.current_year, self.current_month)
        self.costos_row_layout.addWidget(self.costos_card)
        self.costos_row_layout.addStretch()
        main_layout.addLayout(self.costos_row_layout)

        self._create_analysis_section(main_layout)

        scroll.setWidget(content)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    # ── Header ────────────────────────────────────────────────────────

    def _create_header(self, layout):
        vl = QVBoxLayout()
        vl.setSpacing(8)
        title = QLabel("Finanzas")
        title.setStyleSheet("font-size: 32px; font-weight: 700; color: #1F2937;")
        vl.addWidget(title)
        sub = QLabel("Análisis financiero completo y control de gastos")
        sub.setStyleSheet("font-size: 14px; color: #6B7280;")
        vl.addWidget(sub)
        layout.addLayout(vl)

    # ── Sección análisis ──────────────────────────────────────────────

    def _create_analysis_section(self, layout):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        al = QVBoxLayout(frame)
        al.setSpacing(20)

        # Header con controles
        hl = QHBoxLayout()

        title = QLabel("📊 Análisis Financiero")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1F2937;")
        hl.addWidget(title)
        hl.addStretch()

        hl.addWidget(self._lbl("Mes:"))
        self.month_combo = SmartComboBox()
        for i, m in enumerate(MESES_ES, 1):
            self.month_combo.addItem(m, i)
        self.month_combo.setCurrentIndex(self.current_month - 1)
        self.month_combo.currentIndexChanged.connect(self.on_month_changed)
        hl.addWidget(self.month_combo)

        hl.addWidget(self._lbl("Año:"))
        self.year_spin = SmartSpinBox()
        self.year_spin.setRange(2020, 2030)
        self.year_spin.setValue(self.current_year)
        self.year_spin.valueChanged.connect(self.on_year_changed)
        hl.addWidget(self.year_spin)

        excel_btn = QPushButton("📊 Excel")
        excel_btn.setStyleSheet("""
            QPushButton {
                background-color:#10B981;color:white;
                padding:10px 20px;border-radius:8px;font-weight:600;
            }
            QPushButton:hover{background-color:#059669;}
        """)
        excel_btn.clicked.connect(self.export_excel)
        hl.addWidget(excel_btn)

        pdf_btn = QPushButton("📄 PDF")
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color:#EF4444;color:white;
                padding:10px 20px;border-radius:8px;font-weight:600;
            }
            QPushButton:hover{background-color:#DC2626;}
        """)
        pdf_btn.clicked.connect(self.export_pdf)
        hl.addWidget(pdf_btn)

        al.addLayout(hl)

        # Filtros: categoría + día
        fl = QHBoxLayout()
        fl.setSpacing(12)

        fl.addWidget(self._lbl("Categoría:"))
        self.category_combo = SmartComboBox()
        self.category_combo.addItem("Todas las categorías", None)
        self._load_categories()
        self.category_combo.currentIndexChanged.connect(self.on_category_changed)
        fl.addWidget(self.category_combo)

        fl.addWidget(self._lbl("Día:"))
        self.day_combo = SmartComboBox()
        self.day_combo.addItem("Todos los días", 0)
        for d in range(1, 32):
            self.day_combo.addItem(str(d), d)
        self.day_combo.currentIndexChanged.connect(self.on_day_changed)
        fl.addWidget(self.day_combo)

        fl.addStretch()
        al.addLayout(fl)

        # Tabla
        self.analysis_table = QTableWidget()
        self.analysis_table.setColumnCount(5)
        self.analysis_table.setHorizontalHeaderLabels(
            ["Mes/Producto", "Ingresos (Bs)", "Gastos (Bs)",
             "Ganancia Neta (Bs)", "Margen (%)"]
        )
        self.analysis_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.analysis_table.setAlternatingRowColors(True)
        self.analysis_table.setMinimumHeight(500)
        self.analysis_table.setStyleSheet("""
            QTableWidget {
                border: none; gridline-color: #E5E7EB;
                font-size: 13px; background-color: white;
            }
            QTableWidget::item {
                padding: 10px; border-bottom: 1px solid #E5E7EB;
            }
            QTableWidget::item:alternate { background-color: #F9FAFB; }
        """)

        hdr = self.analysis_table.horizontalHeader()
        hdr.setStyleSheet("""
            QHeaderView {
                background-color: white; color: white;
                font-weight: bold; font-size: 20px;
                padding: 10px; border: none;
            }
        """)
        hdr.setMinimumHeight(65)
        hdr.setMaximumHeight(65)
        hdr.setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        hdr.setStretchLastSection(True)
        for col in range(5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.analysis_table.setColumnWidth(1, 160)
        self.analysis_table.setColumnWidth(2, 150)
        self.analysis_table.setColumnWidth(3, 190)
        self.analysis_table.setColumnWidth(4, 130)

        al.addWidget(self.analysis_table)
        layout.addWidget(frame)

    def _lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet("font-weight: 600; color: #4B5563;")
        return l

    def _load_categories(self):
        cats = db.fetch_all(
            "SELECT id, nombre FROM categorias WHERE activo=1 ORDER BY nombre")
        if cats:
            for cat in cats:
                self.category_combo.addItem(cat['nombre'], cat['id'])

    # ── Stats principales ─────────────────────────────────────────────

    def update_stats(self):
        """Reconstruye las 4 stat cards de la fila 1."""
        while self.main_stats_layout.count():
            item = self.main_stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        month_str = f"{self.current_year}-{self.current_month:02d}"

        inc = db.fetch_one(
            "SELECT COALESCE(SUM(total),0) as total FROM ventas "
            "WHERE strftime('%Y-%m',fecha_venta)=? AND estado='completada'",
            (month_str,)
        )
        ingresos = float(inc['total']) if inc else 0.0

        cst = db.fetch_one(
            "SELECT COALESCE(SUM(dv.cantidad*p.costo),0) as total_costo "
            "FROM detalle_ventas dv "
            "JOIN productos p ON dv.producto_id=p.id "
            "JOIN ventas v    ON dv.venta_id=v.id "
            "WHERE strftime('%Y-%m',v.fecha_venta)=? AND v.estado='completada'",
            (month_str,)
        )
        gastos_prod = float(cst['total_costo']) if cst else 0.0

        costo_fijo, costo_variable = self.costos_card.get_totals()
        gastos_total = gastos_prod + costo_fijo + costo_variable

        ganancia = ingresos - gastos_total
        margen   = (ganancia / ingresos * 100) if ingresos > 0 else 0.0

        cards = [
            StatCard("💰", f"Bs {ingresos:.2f}",     "Ingresos del Mes",  "#10B981"),
            StatCard("💸", f"Bs {gastos_total:.2f}", "Gastos del Mes",    "#EF4444"),
            StatCard("📈", f"Bs {ganancia:.2f}",      "Ganancia Neta",
                     "#10B981" if ganancia >= 0 else "#EF4444"),
            StatCard("📊", f"{margen:.1f}%",           "Margen de Ganancia",
                     "#10B981" if margen >= 0 else "#EF4444"),
        ]
        for card in cards:
            self.main_stats_layout.addWidget(card)

        self.update_analysis_table()

    # ── Tabla de análisis ─────────────────────────────────────────────

    def update_analysis_table(self):
        month_str   = f"{self.current_year}-{self.current_month:02d}"
        selected_day = self.day_combo.currentData()

        # Filtro dinámico según día seleccionado
        if selected_day and selected_day > 0:
            day_str     = f"{self.current_year}-{self.current_month:02d}-{selected_day:02d}"
            date_filter = f"strftime('%Y-%m-%d', fecha_venta)='{day_str}'"
            date_filter_v = f"strftime('%Y-%m-%d', v.fecha_venta)='{day_str}'"
            label_periodo = f"📅 {selected_day:02d}/{self.current_month:02d}/{self.current_year}"
        else:
            date_filter   = f"strftime('%Y-%m', fecha_venta)='{month_str}'"
            date_filter_v = f"strftime('%Y-%m', v.fecha_venta)='{month_str}'"
            label_periodo = f"📅 {MESES_ES[self.current_month-1]} {self.current_year}"

        inc = db.fetch_one(
            f"SELECT COALESCE(SUM(total),0) as total FROM ventas "
            f"WHERE {date_filter} AND estado='completada'", ()
        )
        ingresos_mes = float(inc['total']) if inc else 0.0

        cst = db.fetch_one(
            f"SELECT COALESCE(SUM(dv.cantidad*p.costo),0) as total_costo "
            f"FROM detalle_ventas dv "
            f"JOIN productos p ON dv.producto_id=p.id "
            f"JOIN ventas v    ON dv.venta_id=v.id "
            f"WHERE {date_filter_v} AND v.estado='completada'", ()
        )
        gastos_mes   = float(cst['total_costo']) if cst else 0.0
        ganancia_mes = ingresos_mes - gastos_mes
        margen_mes   = (ganancia_mes / ingresos_mes * 100) if ingresos_mes > 0 else 0.0

        selected_cat = self.category_combo.currentData()
        selected_day = self.day_combo.currentData()   # 0 = todos

        # Base del WHERE según si hay filtro de día o solo de mes
        if selected_day and selected_day > 0:
            date_filter = f"strftime('%Y-%m-%d', v.fecha_venta) = '{self.current_year}-{self.current_month:02d}-{selected_day:02d}'"
        else:
            date_filter = f"strftime('%Y-%m', v.fecha_venta) = '{self.current_year}-{self.current_month:02d}'"

        query = (
            "SELECT c.nombre as categoria, p.nombre as producto, "
            "p.costo as costo_unitario, "
            "SUM(dv.cantidad) as unidades_vendidas, "
            "SUM(dv.subtotal) as ingresos, "
            "SUM(dv.cantidad*p.costo) as gastos "
            "FROM detalle_ventas dv "
            "JOIN productos p  ON dv.producto_id=p.id "
            "JOIN categorias c ON p.categoria_id=c.id "
            "JOIN ventas v     ON dv.venta_id=v.id "
            f"WHERE {date_filter} AND v.estado='completada'"
        )
        params = []
        if selected_cat is not None:
            query += " AND c.id=?"
            params.append(selected_cat)
        query += " GROUP BY p.id ORDER BY c.nombre, ingresos DESC"

        product_results = db.fetch_all(query, tuple(params))

        self.analysis_table.setRowCount(0)
        row = 0

        self._add_table_row(
            row,
            label_periodo,
            ingresos_mes, gastos_mes, ganancia_mes, margen_mes,
            is_summary=True
        )
        row += 1

        if product_results:
            current_cat = None
            cat_ing = cat_gas = 0.0

            for p in product_results:
                cat = p['categoria']
                if cat != current_cat:
                    if current_cat is not None:
                        cg = cat_ing - cat_gas
                        cm = (cg / cat_ing * 100) if cat_ing > 0 else 0.0
                        self._add_table_row(
                            row, f"📁 {current_cat}", cat_ing, cat_gas, cg, cm)
                        row += 1

                    current_cat = cat
                    cat_ing = cat_gas = 0.0

                    self.analysis_table.insertRow(row)
                    ch = QTableWidgetItem(f"  📂 {cat}")
                    ch.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
                    ch.setBackground(QColor("#F3F4F6"))
                    self.analysis_table.setItem(row, 0, ch)
                    for col in range(1, 5):
                        e = QTableWidgetItem("")
                        e.setBackground(QColor("#F3F4F6"))
                        self.analysis_table.setItem(row, col, e)
                    self.analysis_table.setRowHeight(row, 40)
                    row += 1

                ing = float(p['ingresos'] or 0)
                gas = float(p['gastos']   or 0)
                gan = ing - gas
                mar = (gan / ing * 100) if ing > 0 else 0.0
                self._add_table_row(
                    row, f"    {p['producto']}", ing, gas, gan, mar)
                row += 1
                cat_ing += ing
                cat_gas += gas

            if current_cat:
                cg = cat_ing - cat_gas
                cm = (cg / cat_ing * 100) if cat_ing > 0 else 0.0
                self._add_table_row(
                    row, f"📁 {current_cat}", cat_ing, cat_gas, cg, cm)

    def _add_table_row(self, row, label, ingresos, gastos, ganancia, margen,
                       is_summary=False):
        self.analysis_table.insertRow(row)
        is_cat = "📁" in label
        sz     = 15 if is_summary else (13 if is_cat else 12)
        bg_def = "#FFF7ED" if is_summary else ("#F3F4F6" if is_cat else None)
        bg_gan = (("#ECFDF5" if ganancia >= 0 else "#FEE2E2")
                  if is_summary else bg_def)
        bold   = is_summary or is_cat
        green  = "#10B981"
        red    = "#EF4444"

        def cell(text, align=Qt.AlignmentFlag.AlignLeft, color=None, bg=None):
            it = QTableWidgetItem(text)
            it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            it.setFont(QFont("Segoe UI", sz,
                             QFont.Weight.Bold if bold else QFont.Weight.Normal))
            if color: it.setForeground(QColor(color))
            if bg:    it.setBackground(QColor(bg))
            return it

        R = Qt.AlignmentFlag.AlignRight
        self.analysis_table.setItem(row, 0, cell(label,                 bg=bg_def))
        self.analysis_table.setItem(row, 1, cell(f"Bs {ingresos:.2f}", R, green, bg_def))
        self.analysis_table.setItem(row, 2, cell(f"Bs {gastos:.2f}",   R, red,   bg_def))
        self.analysis_table.setItem(row, 3, cell(f"Bs {ganancia:.2f}", R,
            green if ganancia >= 0 else red, bg_gan))
        self.analysis_table.setItem(row, 4, cell(f"{margen:.1f}%",     R,
            green if margen >= 0 else red, bg_gan))
        self.analysis_table.setRowHeight(
            row, 75 if is_summary else (55 if is_cat else 48))

    # ── Callbacks ─────────────────────────────────────────────────────

    def on_month_changed(self):
        self.current_month = self.month_combo.currentData()
        self.day_combo.setCurrentIndex(0)   # resetear día al cambiar mes
        self.costos_card.load_costs(self.current_year, self.current_month)
        self.update_stats()

    def on_year_changed(self):
        self.current_year = self.year_spin.value()
        self.day_combo.setCurrentIndex(0)   # resetear día al cambiar año
        self.costos_card.load_costs(self.current_year, self.current_month)
        self.update_stats()

    def on_category_changed(self):
        self.update_analysis_table()

    def on_day_changed(self):
        self.update_analysis_table()

    def refresh_after_cost_change(self):
        """Llamado por CostosCard o VerCostosDialog tras cambios en gastos."""
        self.costos_card.load_costs(self.current_year, self.current_month)
        self.update_stats()

    # ── Exportar ──────────────────────────────────────────────────────

    def export_excel(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment

            wb = Workbook()
            ws = wb.active
            ws.title = f"Finanzas {self.month_combo.currentText()}"

            headers = ["Mes/Producto", "Ingresos (Bs)", "Gastos (Bs)",
                       "Ganancia Neta (Bs)", "Margen (%)"]
            for col, h in enumerate(headers, 1):
                cell = ws.cell(1, col, h)
                cell.font      = Font(bold=True, color="FFFFFF")
                cell.fill      = PatternFill(
                    start_color="FF6B35", end_color="FF6B35", fill_type="solid")
                cell.alignment = Alignment(
                    horizontal="center", vertical="center")

            for row in range(self.analysis_table.rowCount()):
                for col in range(5):
                    item = self.analysis_table.item(row, col)
                    if item:
                        ws.cell(row + 2, col + 1, item.text())

            for col in ws.columns:
                ml = max(
                    (len(str(c.value)) for c in col if c.value), default=0)
                ws.column_dimensions[col[0].column_letter].width = ml + 2

            filename = (f"finanzas_{self.current_year}"
                        f"_{self.current_month:02d}.xlsx")
            wb.save(filename)
            QMessageBox.information(
                self, "Éxito", f"Excel generado:\n{filename}")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error al generar Excel:\n{str(e)}")

    def export_pdf(self):
        QMessageBox.information(self, "PDF", "Generación de PDF en desarrollo")