"""
Inventory Widget — La Placita
Diseño moderno y compacto. Tres pestañas:
  1. Productos  — stock + ajustes
  2. Paquetes   — paquetes de insumos con desglose por ítem + merma
  3. Historial  — movimientos de productos e insumos
"""

from functools import partial
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox, QComboBox, QHeaderView,
    QFrame, QDoubleSpinBox, QSpinBox, QTextEdit, QScrollArea,
    QAbstractItemView, QSizePolicy, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from models.inventory import (
    registrar_movimiento, get_todos_movimientos,
    get_productos_stock_bajo, Insumo, get_todos_movimientos_insumos
)
from models.product import Product
from models.user import get_current_user
from database.connection import db
import json
from datetime import datetime
from models.user import User


# ── Paleta y estilos globales ─────────────────────────────────────────────────
C_BG      = "#F8FAFC"
C_WHITE   = "#FFFFFF"
C_BORDER  = "#E2E8F0"
C_TEXT    = "#1E293B"
C_MUTED   = "#64748B"
C_PRIMARY = "#FF6B35"
C_GREEN   = "#10B981"
C_BLUE    = "#3B82F6"
C_AMBER   = "#F59E0B"
C_RED     = "#EF4444"
C_PURPLE  = "#8B5CF6"

TIPO_COLOR = {
    "entrada": C_GREEN, "venta": C_BLUE, "ajuste": C_AMBER,
    "merma": C_RED, "consumo": C_PURPLE,
}
TIPO_ICONO = {
    "entrada": "📥", "venta": "🛒", "ajuste": "✏️",
    "merma": "🗑️", "consumo": "⚗️",
}

TABLE_STYLE = f"""
    QTableWidget {{
        border: 1px solid {C_BORDER}; border-radius: 8px;
        background: {C_WHITE}; font-size: 11px; gridline-color: {C_BG};
        outline: none;
    }}
    QTableWidget::item {{ padding: 5px 8px; color: {C_TEXT}; }}
    QTableWidget::item:alternate {{ background: {C_BG}; }}
    QTableWidget::item:selected {{ background: #EFF6FF; color: {C_TEXT}; }}
    QHeaderView::section {{
        background: #F1F5F9; color: {C_MUTED}; font-weight: 700;
        font-size: 10px; padding: 6px 8px; border: none;
        border-bottom: 1px solid {C_BORDER};
    }}
    QScrollBar:vertical {{ background:{C_BG}; width:5px; border-radius:3px; }}
    QScrollBar::handle:vertical {{ background:#CBD5E1; border-radius:3px; min-height:20px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
"""

COMBO_STYLE = f"""
    QComboBox {{ background:{C_WHITE}; border:1px solid {C_BORDER};
                border-radius:6px; padding:5px 10px; font-size:11px; color:{C_TEXT}; }}
    QComboBox:focus {{ border-color:{C_PRIMARY}; }}
    QComboBox::drop-down {{ border:none; }}
"""

SPIN_STYLE = f"""
    QDoubleSpinBox, QSpinBox {{
        background:{C_WHITE}; border:1px solid {C_BORDER};
        border-radius:6px; padding:5px 8px; font-size:11px; color:{C_TEXT};
    }}
    QDoubleSpinBox:focus, QSpinBox:focus {{ border-color:{C_PRIMARY}; }}
"""

TEXTEDIT_STYLE = f"""
    QTextEdit {{ background:{C_WHITE}; border:1px solid {C_BORDER};
                border-radius:6px; padding:6px; font-size:11px; color:{C_TEXT}; }}
    QTextEdit:focus {{ border-color:{C_PRIMARY}; }}
"""

LINEEDIT_STYLE = f"""
    QLineEdit {{ background:{C_WHITE}; border:1px solid {C_BORDER};
                border-radius:6px; padding:5px 10px; font-size:11px; color:{C_TEXT}; }}
    QLineEdit:focus {{ border-color:{C_PRIMARY}; }}
"""


def _btn(text, color=C_PRIMARY, small=False):
    b = QPushButton(text)
    pad = "3px 10px" if small else "6px 14px"
    b.setStyleSheet(f"""
        QPushButton {{ background:{color}; color:white; border:none;
                      border-radius:6px; font-size:11px; font-weight:600; padding:{pad}; }}
        QPushButton:hover {{ background:{color}cc; }}
        QPushButton:disabled {{ background:#E2E8F0; color:#94A3B8; }}
    """)
    return b

def _btn_ghost(text):
    b = QPushButton(text)
    b.setStyleSheet(f"""
        QPushButton {{ background:transparent; color:{C_MUTED}; border:1px solid {C_BORDER};
                      border-radius:6px; font-size:11px; font-weight:500; padding:5px 12px; }}
        QPushButton:hover {{ background:{C_BG}; border-color:{C_MUTED}; color:{C_TEXT}; }}
    """)
    return b

def _section_lbl(text):
    l = QLabel(text)
    l.setStyleSheet(f"font-size:10px; font-weight:700; color:{C_MUTED}; letter-spacing:0.6px;")
    return l

def _search(placeholder):
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setStyleSheet(LINEEDIT_STYLE)
    return e


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Ajuste de stock de producto
# ──────────────────────────────────────────────────────────────────────────────

class AjusteStockDialog(QDialog):
    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle(f"Ajustar Stock — {product.nombre}")
        self.setFixedWidth(400)
        self.setStyleSheet(f"QDialog {{ background:{C_BG}; }} QLabel {{ background:transparent; }}")
        self._init_ui()

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        info = QFrame()
        info.setStyleSheet(f"QFrame {{ background:{C_WHITE}; border:1px solid {C_BORDER}; border-radius:8px; }}")
        il = QHBoxLayout(info)
        il.setContentsMargins(14, 10, 14, 10)
        nm = QLabel(f"<b>{self.product.nombre}</b>")
        nm.setTextFormat(Qt.TextFormat.RichText)
        il.addWidget(nm)
        il.addStretch()
        sk = QLabel(f"Stock actual: <b>{self.product.stock}</b>")
        sk.setTextFormat(Qt.TextFormat.RichText)
        sk.setStyleSheet(f"font-size:11px; color:{C_MUTED};")
        il.addWidget(sk)
        lay.addWidget(info)

        lay.addWidget(_section_lbl("TIPO DE MOVIMIENTO"))
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("📥  Entrada — suma stock", "entrada")
        self.tipo_combo.addItem("✏️  Ajuste manual",        "ajuste")
        self.tipo_combo.addItem("🗑️  Merma / Pérdida",      "merma")
        self.tipo_combo.setStyleSheet(COMBO_STYLE)
        lay.addWidget(self.tipo_combo)

        lay.addWidget(_section_lbl("CANTIDAD"))
        self.cantidad_spin = QSpinBox()
        self.cantidad_spin.setRange(1, 99999)
        self.cantidad_spin.setStyleSheet(SPIN_STYLE)
        lay.addWidget(self.cantidad_spin)

        lay.addWidget(_section_lbl("MOTIVO (opcional)"))
        self.motivo_input = QTextEdit()
        self.motivo_input.setPlaceholderText("Describe el motivo...")
        self.motivo_input.setFixedHeight(64)
        self.motivo_input.setStyleSheet(TEXTEDIT_STYLE)
        lay.addWidget(self.motivo_input)

        note = QLabel("🔒 Se registrará con tu usuario y fecha.")
        note.setStyleSheet(f"color:{C_MUTED}; font-size:10px;")
        lay.addWidget(note)

        row = QHBoxLayout()
        c = _btn_ghost("Cancelar")
        c.clicked.connect(self.reject)
        ok = _btn("Registrar", C_PRIMARY)
        ok.clicked.connect(self.accept)
        row.addWidget(c)
        row.addStretch()
        row.addWidget(ok)
        lay.addLayout(row)

    def get_data(self):
        tipo  = self.tipo_combo.currentData()
        cant  = self.cantidad_spin.value()
        mot   = self.motivo_input.toPlainText().strip()
        delta = cant if tipo == "entrada" else -cant
        return tipo, delta, mot or None


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Nuevo Paquete de Insumos
# ──────────────────────────────────────────────────────────────────────────────

class NuevoPaqueteDialog(QDialog):
    UNIDADES = ["kg","g","litros","ml","unidades","porciones","cajas","bolsas"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Paquete de Insumos")
        self.setMinimumWidth(620)
        self.setMinimumHeight(540)
        self.setStyleSheet(f"QDialog {{ background:{C_BG}; }} QLabel {{ background:transparent; }}")
        self._items = []
        self._init_ui()

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 24, 24, 24)

        # ── Nombre del paquete ─────────────────────────────────────────
        lay.addWidget(_section_lbl("NOMBRE DEL PAQUETE"))
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Ej: Café del mes, Lácteos semana 1...")
        self.nombre_input.setStyleSheet(f"""
            QLineEdit {{ background:{C_WHITE}; border:1.5px solid {C_BORDER};
                        border-radius:7px; padding:7px 12px; font-size:13px; font-weight:600; }}
            QLineEdit:focus {{ border-color:{C_PRIMARY}; }}
        """)
        lay.addWidget(self.nombre_input)

        # ── Proveedor y nota ───────────────────────────────────────────
        row2 = QHBoxLayout(); row2.setSpacing(12)
        c1 = QVBoxLayout(); c1.setSpacing(4)
        c1.addWidget(_section_lbl("PROVEEDOR"))
        self.proveedor_input = QLineEdit()
        self.proveedor_input.setPlaceholderText("Nombre del proveedor")
        self.proveedor_input.setStyleSheet(LINEEDIT_STYLE)
        c1.addWidget(self.proveedor_input)
        row2.addLayout(c1)
        c2 = QVBoxLayout(); c2.setSpacing(4)
        c2.addWidget(_section_lbl("NOTA"))
        self.nota_input = QLineEdit()
        self.nota_input.setPlaceholderText("Observación opcional")
        self.nota_input.setStyleSheet(LINEEDIT_STYLE)
        c2.addWidget(self.nota_input)
        row2.addLayout(c2)
        lay.addLayout(row2)

        # ── Separador ─────────────────────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{C_BORDER}; max-height:1px; margin:2px 0;")
        lay.addWidget(sep)

        # ── Cabecera de columnas de entrada ───────────────────────────
        lay.addWidget(_section_lbl("INSUMOS DEL PAQUETE"))

        col_hdr = QHBoxLayout(); col_hdr.setSpacing(6)
        for txt, stretch, fixed in [
            ("Nombre del insumo", 3, None),
            ("Cantidad",          0, 82),
            ("Unidad",            0, 90),
            ("Precio unit.",      0, 96),
            ("Total",             0, 90),
            ("",                  0, 34),
        ]:
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"font-size:10px; font-weight:700; color:{C_MUTED}; letter-spacing:0.4px;")
            if fixed:
                lbl.setFixedWidth(fixed)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                col_hdr.addWidget(lbl)
            else:
                col_hdr.addWidget(lbl, stretch=stretch)
        lay.addLayout(col_hdr)

        # ── Fila de entrada ────────────────────────────────────────────
        add_row = QHBoxLayout(); add_row.setSpacing(6)

        self._item_nombre = QLineEdit()
        self._item_nombre.setPlaceholderText("Ej: Leche entera, Azúcar...")
        self._item_nombre.setStyleSheet(LINEEDIT_STYLE)

        self._item_cant = QDoubleSpinBox()
        self._item_cant.setRange(0.001, 99999); self._item_cant.setDecimals(3)
        self._item_cant.setFixedWidth(82); self._item_cant.setStyleSheet(SPIN_STYLE)
        self._item_cant.valueChanged.connect(self._recalc_preview)

        self._item_unidad = QComboBox()
        for u in self.UNIDADES: self._item_unidad.addItem(u)
        self._item_unidad.setFixedWidth(90); self._item_unidad.setStyleSheet(COMBO_STYLE)

        self._item_precio = QDoubleSpinBox()
        self._item_precio.setRange(0, 999999); self._item_precio.setDecimals(2)
        self._item_precio.setPrefix("Bs "); self._item_precio.setFixedWidth(96)
        self._item_precio.setStyleSheet(SPIN_STYLE)
        self._item_precio.valueChanged.connect(self._recalc_preview)

        # Preview del total de esta fila (solo lectura)
        self._item_preview = QLabel("Bs 0.00")
        self._item_preview.setFixedWidth(90)
        self._item_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._item_preview.setStyleSheet(f"""
            background:{C_WHITE}; border:1px solid {C_BORDER}; border-radius:6px;
            padding:5px 6px; font-size:11px; font-weight:700; color:{C_GREEN};
        """)

        add_btn = _btn("＋ Agregar", C_GREEN, small=True)
        add_btn.setFixedWidth(84)
        add_btn.clicked.connect(self._agregar_item)

        add_row.addWidget(self._item_nombre, stretch=3)
        add_row.addWidget(self._item_cant)
        add_row.addWidget(self._item_unidad)
        add_row.addWidget(self._item_precio)
        add_row.addWidget(self._item_preview)
        add_row.addWidget(add_btn)
        lay.addLayout(add_row)

        # ── Tabla de ítems ─────────────────────────────────────────────
        # Cols: Insumo | Cant. | Unidad | P.Unit | Costo Total | ✕
        self._items_table = QTableWidget(0, 6)
        self._items_table.setHorizontalHeaderLabels(
            ["Insumo", "Cantidad", "Unidad", "P. Unit.", "Total", ""])
        self._items_table.setFixedHeight(160)
        hh = self._items_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, w in [(1,72),(2,72),(3,82),(4,82),(5,32)]:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self._items_table.setColumnWidth(col, w)
        self._items_table.verticalHeader().setVisible(False)
        self._items_table.verticalHeader().setDefaultSectionSize(28)
        self._items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._items_table.setAlternatingRowColors(True)
        self._items_table.setShowGrid(False)
        self._items_table.setStyleSheet(TABLE_STYLE)
        lay.addWidget(self._items_table)

        # ── Totalizador ────────────────────────────────────────────────
        total_row = QHBoxLayout()
        total_row.addStretch()
        self._total_lbl = QLabel("Costo total del paquete:  <b style='color:{C_PRIMARY}'>Bs 0.00</b>")
        self._total_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._total_lbl.setStyleSheet(f"font-size:12px; color:{C_MUTED};")
        total_row.addWidget(self._total_lbl)
        lay.addLayout(total_row)

        # ── Botones ────────────────────────────────────────────────────
        lay.addSpacing(4)
        btn_row = QHBoxLayout()
        c = _btn_ghost("Cancelar"); c.clicked.connect(self.reject)
        ok = _btn("💾  Guardar Paquete", C_PRIMARY); ok.clicked.connect(self._on_accept)
        btn_row.addWidget(c); btn_row.addStretch(); btn_row.addWidget(ok)
        lay.addLayout(btn_row)

    def _recalc_preview(self):
        total = self._item_cant.value() * self._item_precio.value()
        self._item_preview.setText(f"Bs {total:.2f}")

    def _agregar_item(self):
        nombre = self._item_nombre.text().strip()
        if not nombre:
            self._item_nombre.setFocus()
            return
        precio_unit = self._item_precio.value()
        cantidad    = self._item_cant.value()
        costo_total = round(cantidad * precio_unit, 2)
        self._items.append({
            "nombre":       nombre,
            "cantidad":     cantidad,
            "unidad":       self._item_unidad.currentText(),
            "precio_unit":  precio_unit,
            "costo":        costo_total,
        })
        # Reset fila
        self._item_nombre.clear()
        self._item_cant.setValue(1.0)
        self._item_precio.setValue(0.0)
        self._item_preview.setText("Bs 0.00")
        self._item_nombre.setFocus()
        self._refresh_table()

    def _refresh_table(self):
        self._items_table.setRowCount(len(self._items))
        total_pkg = 0.0
        for r, it in enumerate(self._items):
            self._items_table.setItem(r, 0, QTableWidgetItem(it["nombre"]))

            ci = QTableWidgetItem(f"{it['cantidad']:.3g}")
            ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._items_table.setItem(r, 1, ci)

            ui = QTableWidgetItem(it["unidad"])
            ui.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._items_table.setItem(r, 2, ui)

            pu = QTableWidgetItem(f"Bs {it['precio_unit']:.2f}")
            pu.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            pu.setForeground(QColor(C_MUTED))
            self._items_table.setItem(r, 3, pu)

            tc = QTableWidgetItem(f"Bs {it['costo']:.2f}")
            tc.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tc.setForeground(QColor(C_GREEN))
            self._items_table.setItem(r, 4, tc)

            total_pkg += it["costo"]

            qw = QWidget(); qw.setStyleSheet("background:transparent;")
            ql = QHBoxLayout(qw); ql.setContentsMargins(3,2,3,2)
            qb = QPushButton("✕"); qb.setFixedSize(22,22)
            qb.setStyleSheet(f"""
                QPushButton {{ background:#FEE2E2; color:{C_RED}; border:none;
                              border-radius:4px; font-size:10px; font-weight:700; }}
                QPushButton:hover {{ background:{C_RED}; color:white; }}
            """)
            qb.clicked.connect(partial(self._quitar_item, r))
            ql.addWidget(qb)
            self._items_table.setCellWidget(r, 5, qw)

        self._total_lbl.setText(
            f"Costo total del paquete:  "
            f"<b style='color:{C_PRIMARY}; font-size:14px;'>Bs {total_pkg:.2f}</b>")

    def _quitar_item(self, idx):
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._refresh_table()

    def _on_accept(self):
        if not self.nombre_input.text().strip():
            QMessageBox.warning(self, "Error", "El nombre del paquete es obligatorio.")
            return
        if not self._items:
            QMessageBox.warning(self, "Error", "Agrega al menos un insumo al paquete.")
            return
        self.accept()

    def get_data(self):
        return {
            "nombre":      self.nombre_input.text().strip(),
            "proveedor":   self.proveedor_input.text().strip() or None,
            "nota":        self.nota_input.text().strip() or None,
            "items":       self._items,
            "costo_total": sum(i["costo"] for i in self._items),
        }


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Ajuste de paquete (merma/pérdida)
# ──────────────────────────────────────────────────────────────────────────────

class AjustePaqueteDialog(QDialog):
    def __init__(self, paquete, parent=None):
        super().__init__(parent)
        self.paquete = paquete
        self.setWindowTitle(f"Ajustar — {paquete['nombre']}")
        self.setFixedWidth(440)
        self.setStyleSheet(f"QDialog {{ background:{C_BG}; }} QLabel {{ background:transparent; }}")
        self._init_ui()

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        info = QFrame()
        info.setStyleSheet(f"QFrame {{ background:{C_WHITE}; border:1px solid {C_BORDER}; border-radius:8px; }}")
        il = QHBoxLayout(info)
        il.setContentsMargins(14,10,14,10)
        nm = QLabel(f"<b>{self.paquete['nombre']}</b>")
        nm.setTextFormat(Qt.TextFormat.RichText)
        il.addWidget(nm)
        il.addStretch()
        ct = QLabel(f"Total: Bs {self.paquete['costo_total']:.2f}")
        ct.setStyleSheet(f"font-size:11px; color:{C_MUTED};")
        il.addWidget(ct)
        lay.addWidget(info)

        lay.addWidget(_section_lbl("INSUMO AFECTADO"))
        self.insumo_combo = QComboBox()
        for it in self.paquete.get("items", []):
            self.insumo_combo.addItem(
                f"{it['nombre']}  ·  {it['cantidad']} {it['unidad']}  ·  Bs {it['costo']:.2f}", it)
        self.insumo_combo.setStyleSheet(COMBO_STYLE)
        lay.addWidget(self.insumo_combo)

        lay.addWidget(_section_lbl("TIPO DE AJUSTE"))
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("🗑️  Merma / Pérdida", "merma")
        self.tipo_combo.addItem("✏️  Ajuste manual",    "ajuste")
        self.tipo_combo.setStyleSheet(COMBO_STYLE)
        lay.addWidget(self.tipo_combo)

        lay.addWidget(_section_lbl("COSTO AJUSTADO"))
        self.costo_spin = QDoubleSpinBox()
        self.costo_spin.setRange(0, 999999)
        self.costo_spin.setDecimals(2)
        self.costo_spin.setPrefix("Bs ")
        self.costo_spin.setStyleSheet(SPIN_STYLE)
        lay.addWidget(self.costo_spin)

        lay.addWidget(_section_lbl("MOTIVO"))
        self.motivo_input = QTextEdit()
        self.motivo_input.setPlaceholderText("Describe brevemente el ajuste...")
        self.motivo_input.setFixedHeight(56)
        self.motivo_input.setStyleSheet(TEXTEDIT_STYLE)
        lay.addWidget(self.motivo_input)

        note = QLabel("🔒 El ajuste quedará registrado en el historial.")
        note.setStyleSheet(f"color:{C_MUTED}; font-size:10px;")
        lay.addWidget(note)

        row = QHBoxLayout()
        c = _btn_ghost("Cancelar"); c.clicked.connect(self.reject)
        ok = _btn("Registrar ajuste", C_AMBER); ok.clicked.connect(self.accept)
        row.addWidget(c); row.addStretch(); row.addWidget(ok)
        lay.addLayout(row)

    def accept(self):
        tipo   = self.tipo_combo.currentData()
        motivo = self.motivo_input.toPlainText().strip()
        if tipo == "merma" and not motivo:
            QMessageBox.warning(self, "Motivo requerido",
                "El motivo es obligatorio para registrar una merma.")
            return
        super().accept()

    def get_data(self):
        return {
            "insumo": self.insumo_combo.currentData(),
            "tipo":   self.tipo_combo.currentData(),
            "costo":  self.costo_spin.value(),
            "motivo": self.motivo_input.toPlainText().strip() or None,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Detalle de paquete
# ──────────────────────────────────────────────────────────────────────────────

class DetallePaqueteDialog(QDialog):
    def __init__(self, paquete, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Detalle — {paquete['nombre']}")
        self.setMinimumWidth(460)
        self.setStyleSheet(f"QDialog {{ background:{C_BG}; }} QLabel {{ background:transparent; }}")
        self._init_ui(paquete)

    def _init_ui(self, p):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet(f"QFrame {{ background:{C_WHITE}; border:1px solid {C_BORDER}; border-radius:10px; }}")
        hl = QVBoxLayout(hdr)
        hl.setContentsMargins(16,12,16,12)
        hl.setSpacing(4)
        nm = QLabel(f"<b>{p['nombre']}</b>")
        nm.setStyleSheet(f"font-size:14px; color:{C_TEXT};")
        nm.setTextFormat(Qt.TextFormat.RichText)
        hl.addWidget(nm)
        meta = QHBoxLayout()
        fecha = (p.get("fecha_registro") or "")[:10]
        for txt in [f"📅 {fecha}", f"🏪 {p.get('proveedor') or '—'}", f"💬 {p.get('nota') or '—'}"]:
            l = QLabel(txt); l.setStyleSheet(f"font-size:10px; color:{C_MUTED};")
            meta.addWidget(l)
        meta.addStretch()
        hl.addLayout(meta)
        lay.addWidget(hdr)

        lay.addWidget(_section_lbl("INSUMOS"))
        items = p.get("items", [])
        tbl = QTableWidget(len(items), 4)
        tbl.setHorizontalHeaderLabels(["Insumo","Cantidad","Unidad","Costo"])
        hh = tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, w in [(1,80),(2,72),(3,80)]:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            tbl.setColumnWidth(col, w)
        tbl.verticalHeader().setVisible(False)
        tbl.verticalHeader().setDefaultSectionSize(26)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        tbl.setStyleSheet(TABLE_STYLE)
        tbl.setFixedHeight(min(200, 38 + len(items)*26))
        for r, it in enumerate(items):
            tbl.setItem(r,0,QTableWidgetItem(it["nombre"]))
            tbl.setItem(r,1,QTableWidgetItem(str(it["cantidad"])))
            tbl.setItem(r,2,QTableWidgetItem(it["unidad"]))
            ci = QTableWidgetItem(f"Bs {it['costo']:.2f}")
            ci.setForeground(QColor(C_GREEN))
            tbl.setItem(r,3,ci)
        lay.addWidget(tbl)

        total_row = QHBoxLayout()
        total_row.addStretch()
        tl = QLabel(f"Costo total: <b style='color:{C_PRIMARY}'>Bs {p['costo_total']:.2f}</b>")
        tl.setTextFormat(Qt.TextFormat.RichText)
        tl.setStyleSheet("font-size:12px;")
        total_row.addWidget(tl)
        lay.addLayout(total_row)

        ajustes = p.get("ajustes", [])
        if ajustes:
            lay.addWidget(_section_lbl("AJUSTES / MERMAS"))
            for aj in ajustes:
                af = QFrame()
                af.setStyleSheet(f"QFrame {{ background:#FFF7ED; border:1px solid #FED7AA; border-radius:7px; }}")
                al = QHBoxLayout(af)
                al.setContentsMargins(12,7,12,7)
                tip = QLabel(f"{TIPO_ICONO.get(aj.get('tipo','ajuste'),'✏️')} {aj.get('tipo','—').title()}")
                tip.setStyleSheet(f"font-size:11px; font-weight:600; color:{C_AMBER};")
                al.addWidget(tip)
                al.addWidget(QLabel(f"· {aj.get('insumo_nombre','—')}"))
                al.addStretch()
                cl = QLabel(f"–Bs {aj.get('costo',0):.2f}")
                cl.setStyleSheet(f"font-size:11px; font-weight:700; color:{C_RED};")
                al.addWidget(cl)
                lay.addWidget(af)

        row = QHBoxLayout()
        row.addStretch()
        c = _btn_ghost("Cerrar"); c.clicked.connect(self.accept)
        row.addWidget(c)
        lay.addLayout(row)


# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: Productos
# ──────────────────────────────────────────────────────────────────────────────

class ProductosStockTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(0, 8, 0, 0)

        top = QHBoxLayout(); top.setSpacing(8)
        self.search_input = _search("🔍 Buscar producto...")
        self.search_input.textChanged.connect(self.load_data)
        top.addWidget(self.search_input)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Todos los productos", None)
        self.filter_combo.addItem("⚠️ Stock bajo (≤ 5)", "bajo")
        self.filter_combo.setStyleSheet(COMBO_STYLE)
        self.filter_combo.setFixedWidth(160)
        self.filter_combo.currentIndexChanged.connect(self.load_data)
        top.addWidget(self.filter_combo)

        rf = _btn_ghost("🔄")
        rf.setFixedWidth(36)
        rf.clicked.connect(self.load_data)
        top.addWidget(rf)
        lay.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Producto","Categoría","Stock","Estado","Precio",""])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, w in [(2,60),(3,100),(4,80),(5,84)]:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(TABLE_STYLE)
        lay.addWidget(self.table)

    def load_data(self):
        term   = self.search_input.text().strip()
        filtro = self.filter_combo.currentData()
        prods  = Product.search(term) if term else Product.get_all()
        if filtro == "bajo":
            prods = [p for p in prods if p.stock <= 5]
        cat_cache = {r["id"]: r["nombre"]
                     for r in db.fetch_all("SELECT id,nombre FROM categorias")}

        self.table.setRowCount(len(prods))
        for row, p in enumerate(prods):
            self.table.setItem(row, 0, QTableWidgetItem(p.nombre))
            self.table.setItem(row, 1, QTableWidgetItem(cat_cache.get(p.categoria_id,"—")))

            si = QTableWidgetItem(str(p.stock))
            si.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, si)

            if p.stock == 0:      estado, color = "❌ Sin stock", C_RED
            elif p.stock <= 5:    estado, color = "⚠️ Bajo",     C_AMBER
            else:                 estado, color = "✅ OK",        C_GREEN
            ei = QTableWidgetItem(estado)
            ei.setForeground(QColor(color))
            self.table.setItem(row, 3, ei)

            pi = QTableWidgetItem(f"Bs {p.precio:.2f}")
            pi.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, pi)

            btn = _btn("Ajustar", C_PRIMARY, small=True)
            btn.clicked.connect(partial(self.ajustar_stock, p))
            cw = QWidget(); cw.setStyleSheet("background:transparent;")
            cl = QHBoxLayout(cw); cl.setContentsMargins(4,3,4,3)
            cl.addWidget(btn)
            self.table.setCellWidget(row, 5, cw)

    def ajustar_stock(self, product):
        dlg = AjusteStockDialog(product, self)
        if dlg.exec():
            tipo, delta, motivo = dlg.get_data()
            ok = registrar_movimiento(product.id, tipo, delta, motivo)
            if ok:
                self.load_data()
            else:
                QMessageBox.warning(self, "Error",
                    "No se pudo registrar. Verifica que el stock no quede negativo.")


# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: Paquetes de Insumos
# ──────────────────────────────────────────────────────────────────────────────

class PaquetesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._paquetes = []
        self._init_ui()
        self.load_data()

    def _stat_card(self, parent_layout, label, value_text, color):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        wl = QVBoxLayout(w); wl.setContentsMargins(0,0,0,0); wl.setSpacing(1)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size:10px; color:{C_MUTED}; font-weight:600;")
        val = QLabel(value_text)
        val.setStyleSheet(f"font-size:16px; font-weight:800; color:{color};")
        wl.addWidget(lbl); wl.addWidget(val)
        parent_layout.addWidget(w)
        return val

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(0, 8, 0, 0)

        # Fila 1: búsqueda + botón nuevo
        top = QHBoxLayout(); top.setSpacing(8)
        self.search_input = _search("🔍 Buscar paquete...")
        self.search_input.textChanged.connect(self.load_data)
        top.addWidget(self.search_input)

        nuevo_btn = _btn("+ Nuevo Paquete", C_PRIMARY)
        nuevo_btn.clicked.connect(self._nuevo_paquete)
        top.addWidget(nuevo_btn)

        rf = _btn_ghost("🔄"); rf.setFixedWidth(36)
        rf.clicked.connect(self.load_data)
        top.addWidget(rf)
        lay.addLayout(top)

        # ── Fila combinada: filtro mes/año + tarjetas de resumen ─────────
        combo_row = QFrame()
        combo_row.setStyleSheet("""
            QFrame { background:white; border:1px solid #E5E7EB; border-radius:12px; }
            QLabel { background:transparent; border:none; }
        """)
        cl = QHBoxLayout(combo_row)
        cl.setContentsMargins(16, 10, 16, 10)
        cl.setSpacing(8)

        # Filtros
        cl.addWidget(_section_lbl("MES:"))
        self.mes_combo = QComboBox()
        meses = ["Todos","Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        for i, m in enumerate(meses):
            self.mes_combo.addItem(m, i)
        self.mes_combo.setStyleSheet(COMBO_STYLE)
        self.mes_combo.setFixedWidth(115)
        self.mes_combo.currentIndexChanged.connect(self.load_data)
        cl.addWidget(self.mes_combo)

        cl.addWidget(_section_lbl("AÑO:"))
        self.anio_spin = QSpinBox()
        self.anio_spin.setRange(2020, 2099)
        self.anio_spin.setValue(datetime.now().year)
        self.anio_spin.setStyleSheet(SPIN_STYLE)
        self.anio_spin.setFixedWidth(78)
        self.anio_spin.valueChanged.connect(self.load_data)
        cl.addWidget(self.anio_spin)

        mes_actual_btn = _btn_ghost("📅 Hoy")
        mes_actual_btn.setFixedWidth(68)
        mes_actual_btn.clicked.connect(self._ir_mes_actual)
        cl.addWidget(mes_actual_btn)

        # Separador vertical
        sv = QFrame(); sv.setFrameShape(QFrame.Shape.VLine)
        sv.setStyleSheet("background:#E5E7EB; max-width:1px; margin:4px 8px;")
        cl.addWidget(sv)

        # Tarjetas de stats inline
        def _card(icon, label, color):
            w = QWidget(); w.setStyleSheet("background:transparent;")
            wl = QVBoxLayout(w); wl.setContentsMargins(8,0,8,0); wl.setSpacing(1)
            lbl = QLabel(f"{icon}  {label}")
            lbl.setStyleSheet("font-size:10px; color:#64748B; font-weight:600;")
            val = QLabel("—")
            val.setStyleSheet(f"font-size:16px; font-weight:800; color:{color};")
            wl.addWidget(lbl); wl.addWidget(val)
            cl.addWidget(w)
            return val

        # Stretch empuja las tarjetas hacia la derecha
        cl.addStretch()

        self._stat_total    = _card("💰", "Costo del mes",  "#FF6B35")

        sv2 = QFrame(); sv2.setFrameShape(QFrame.Shape.VLine)
        sv2.setStyleSheet("background:#E5E7EB; max-width:1px; margin:4px 4px;")
        cl.addWidget(sv2)

        self._stat_paquetes = _card("📦", "Paquetes",        "#3B82F6")

        sv3 = QFrame(); sv3.setFrameShape(QFrame.Shape.VLine)
        sv3.setStyleSheet("background:#E5E7EB; max-width:1px; margin:4px 4px;")
        cl.addWidget(sv3)

        self._stat_merma    = _card("🗑️", "Mermas",          "#EF4444")
        lay.addWidget(combo_row)

        # ── Tabla ──────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Nombre del paquete", "Proveedor", "Fecha", "Insumos",
             "Costo total", "Acciones"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, w in [(2,90),(3,62),(4,96),(5,150)]:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.doubleClicked.connect(self._ver_detalle_doble)
        lay.addWidget(self.table)

    def _ir_mes_actual(self):
        now = datetime.now()
        self.mes_combo.setCurrentIndex(now.month)   # índice = mes (1-12)
        self.anio_spin.setValue(now.year)
        self.load_data()

    def load_data(self):
        term = self.search_input.text().strip().lower()
        mes  = self.mes_combo.currentData()   # 0=todos, 1-12
        anio = self.anio_spin.value()

        query  = "SELECT * FROM paquetes_insumos WHERE 1=1"
        params = []
        if mes and mes > 0:
            # filtrar por mes y año usando strftime sobre fecha_registro
            query += " AND strftime('%m', fecha_registro) = ?"
            query += " AND strftime('%Y', fecha_registro) = ?"
            params += [f"{mes:02d}", str(anio)]
        else:
            # solo filtrar por año
            query += " AND strftime('%Y', fecha_registro) = ?"
            params.append(str(anio))

        query += " ORDER BY fecha_registro DESC LIMIT 500"
        rows   = db.fetch_all(query, tuple(params))

        self._paquetes = []
        for r in rows:
            p = dict(r)
            try:    p["items"]   = json.loads(p.get("items_json","[]"))
            except: p["items"]   = []
            try:    p["ajustes"] = json.loads(p.get("ajustes_json","[]"))
            except: p["ajustes"] = []
            if term and term not in p["nombre"].lower():
                continue
            self._paquetes.append(p)

        total_costo = sum(p["costo_total"] for p in self._paquetes)
        total_merma = sum(sum(aj.get("costo",0) for aj in p["ajustes"]) for p in self._paquetes)
        self._stat_total.setText(f"Bs {total_costo:.2f}")
        self._stat_paquetes.setText(str(len(self._paquetes)))
        self._stat_merma.setText(f"Bs {total_merma:.2f}")

        self.table.setRowCount(len(self._paquetes))
        for row, p in enumerate(self._paquetes):
            self.table.setItem(row, 0, QTableWidgetItem(p["nombre"]))
            self.table.setItem(row, 1, QTableWidgetItem(p.get("proveedor") or "—"))
            self.table.setItem(row, 2, QTableWidgetItem((p.get("fecha_registro") or "")[:10]))
            ni = QTableWidgetItem(str(len(p["items"])))
            ni.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, ni)
            ci = QTableWidgetItem(f"Bs {p['costo_total']:.2f}")
            ci.setForeground(QColor(C_PRIMARY))
            ci.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, ci)

            cw = QWidget(); cw.setStyleSheet("background:transparent;")
            cl = QHBoxLayout(cw); cl.setContentsMargins(4,3,4,3); cl.setSpacing(4)
            ver = _btn("👁", C_BLUE, small=True)
            ver.clicked.connect(partial(self._abrir_detalle, p))
            ajustar = _btn("✏️", C_MUTED, small=True)
            ajustar.clicked.connect(partial(self._ajustar_paquete, p))
            cl.addWidget(ver); cl.addWidget(ajustar)
            self.table.setCellWidget(row, 5, cw)

    def _nuevo_paquete(self):
        dlg = NuevoPaqueteDialog(self)
        if dlg.exec():
            data    = dlg.get_data()
            usuario = get_current_user()
            db.execute_query(
                """INSERT INTO paquetes_insumos
                   (nombre, proveedor, nota, items_json, ajustes_json,
                    costo_total, usuario_id, fecha_registro)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (data["nombre"], data["proveedor"], data["nota"],
                 json.dumps(data["items"]), json.dumps([]),
                 data["costo_total"], usuario.id, datetime.now().isoformat())
            )
            self.load_data()

    def _abrir_detalle(self, p):
        DetallePaqueteDialog(p, self).exec()

    def _ver_detalle_doble(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._paquetes):
            self._abrir_detalle(self._paquetes[row])

    def _ajustar_paquete(self, paquete):
        if not paquete.get("items"):
            QMessageBox.information(self, "Sin insumos",
                "Este paquete no tiene insumos registrados.")
            return
        dlg = AjustePaqueteDialog(paquete, self)
        if dlg.exec():
            aj      = dlg.get_data()
            ajustes = paquete.get("ajustes", [])
            ajustes.append({
                "insumo_nombre": aj["insumo"]["nombre"],
                "tipo":          aj["tipo"],
                "costo":         aj["costo"],
                "motivo":        aj["motivo"],
                "fecha":         datetime.now().isoformat()[:16],
            })
            db.execute_query(
                "UPDATE paquetes_insumos SET ajustes_json=? WHERE id=?",
                (json.dumps(ajustes), paquete["id"])
            )
            self.load_data()


# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: Historial
# ──────────────────────────────────────────────────────────────────────────────

class HistorialTab(QWidget):
    def __init__(self):
        super().__init__()
        self._rows_paquetes = []
        self._es_admin = False
        self._usuario_id_propio = None
        self._init_ui()   # crea fecha_desde, usuario_combo, etc.
        self.load_data()  # ahora los atributos ya existen

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(0, 8, 0, 0)

        # ── Barra de filtros ───────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame { background:white; border:1px solid #E5E7EB; border-radius:10px; }
            QLabel { background:transparent; border:none; }
        """)
        ff = QHBoxLayout(filter_frame)
        ff.setContentsMargins(14, 10, 14, 10)
        ff.setSpacing(10)

        # Vista
        ff.addWidget(_section_lbl("VER:"))
        self.vista_combo = QComboBox()
        self.vista_combo.addItem("📦 Productos", "productos")
        self.vista_combo.addItem("🧺 Paquetes",  "paquetes")
        self.vista_combo.setStyleSheet(COMBO_STYLE)
        self.vista_combo.setFixedWidth(140)
        self.vista_combo.currentIndexChanged.connect(self._on_vista_changed)
        ff.addWidget(self.vista_combo)

        _sv = QFrame(); _sv.setFrameShape(QFrame.Shape.VLine)
        _sv.setStyleSheet("background:#E5E7EB; max-width:1px; margin:3px 4px;")
        ff.addWidget(_sv)

        # Fecha desde
        ff.addWidget(_section_lbl("DESDE:"))
        self.fecha_desde = QDateEdit()
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_desde.setDisplayFormat("dd/MM/yyyy")
        self.fecha_desde.setStyleSheet("""
            QDateEdit { background:white; border:1px solid #E2E8F0;
                        border-radius:6px; padding:4px 8px; font-size:11px; }
            QDateEdit:focus { border-color:#FF6B35; }
            QDateEdit::drop-down { border:none; width:18px; }
        """)
        self.fecha_desde.setFixedWidth(110)
        self.fecha_desde.dateChanged.connect(self.load_data)
        ff.addWidget(self.fecha_desde)

        # Fecha hasta
        ff.addWidget(_section_lbl("HASTA:"))
        self.fecha_hasta = QDateEdit()
        self.fecha_hasta.setCalendarPopup(True)
        self.fecha_hasta.setDate(QDate.currentDate().addDays(1))
        self.fecha_hasta.setDisplayFormat("dd/MM/yyyy")
        self.fecha_hasta.setStyleSheet("""
            QDateEdit { background:white; border:1px solid #E2E8F0;
                        border-radius:6px; padding:4px 8px; font-size:11px; }
            QDateEdit:focus { border-color:#FF6B35; }
            QDateEdit::drop-down { border:none; width:18px; }
        """)
        self.fecha_hasta.setFixedWidth(110)
        self.fecha_hasta.dateChanged.connect(self.load_data)
        ff.addWidget(self.fecha_hasta)

        _sv2 = QFrame(); _sv2.setFrameShape(QFrame.Shape.VLine)
        _sv2.setStyleSheet("background:#E5E7EB; max-width:1px; margin:3px 4px;")
        ff.addWidget(_sv2)

        # Filtro de usuario
        ff.addWidget(_section_lbl("USUARIO:"))
        self.usuario_combo = QComboBox()
        self.usuario_combo.setStyleSheet(COMBO_STYLE)
        self.usuario_combo.setFixedWidth(150)
        self.usuario_combo.currentIndexChanged.connect(self.load_data)
        ff.addWidget(self.usuario_combo)

        # Cargar usuarios según rol
        usuario_actual = get_current_user()
        self._es_admin = usuario_actual.is_admin() if usuario_actual else False
        self._usuario_id_propio = usuario_actual.id if usuario_actual else None

        if self._es_admin:
            self.usuario_combo.addItem("Todos los usuarios", None)
            for u in User.get_all():
                self.usuario_combo.addItem(f"👤 {u.nombre}", u.id)
        else:
            self.usuario_combo.addItem(
                f"👤 {usuario_actual.nombre if usuario_actual else '—'}",
                self._usuario_id_propio
            )
            self.usuario_combo.setEnabled(False)
            self.usuario_combo.setStyleSheet(COMBO_STYLE + """
                QComboBox:disabled { background:#F1F5F9; color:#94A3B8; }
            """)

        ff.addStretch()

        limpiar_btn = _btn_ghost("🔄")
        limpiar_btn.clicked.connect(self._limpiar_filtros)
        ff.addWidget(limpiar_btn)

        """ rf = _btn_ghost("🔄")
        rf.setFixedWidth(36)
        rf.clicked.connect(self.load_data)
        ff.addWidget(rf) """

        lay.addWidget(filter_frame)

        # ── Cuerpo: tabla + panel detalle ─────────────────────────────
        body = QHBoxLayout(); body.setSpacing(10)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        body.addWidget(self.table, stretch=3)

        # Panel lateral de detalle — estilo arqueo con scroll
        self._detail_panel = QFrame()
        self._detail_panel.setFixedWidth(270)
        self._detail_panel.setStyleSheet("""
            QFrame#detailOuter { background:white; border:1px solid #E5E7EB;
                                 border-radius:12px; }
            QLabel { background:transparent; border:none; }
        """)
        self._detail_panel.setObjectName("detailOuter")
        self._detail_panel.setVisible(False)
        outer_lay = QVBoxLayout(self._detail_panel)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)

        # ScrollArea interior
        _scroll = QScrollArea()
        _scroll.setWidgetResizable(True)
        _scroll.setFrameShape(QFrame.Shape.NoFrame)
        _scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        _scroll.setStyleSheet("""
            QScrollArea { background:transparent; border:none; }
            QScrollBar:vertical { background:#F8FAFC; width:4px; border-radius:2px; }
            QScrollBar::handle:vertical { background:#CBD5E1; border-radius:2px; min-height:20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)

        _scroll_content = QWidget()
        _scroll_content.setStyleSheet("background:transparent;")
        _scroll.setWidget(_scroll_content)
        outer_lay.addWidget(_scroll)

        dp = QVBoxLayout(_scroll_content)
        dp.setContentsMargins(18, 16, 18, 16)
        dp.setSpacing(0)

        det_cap = QLabel("DETALLE DEL PAQUETE")
        det_cap.setStyleSheet(
            "font-size:10px; font-weight:700; color:#94A3B8; letter-spacing:1px;")
        dp.addWidget(det_cap)
        dp.addSpacing(12)

        # Nombre del paquete
        self._det_nombre = QLabel("—")
        self._det_nombre.setStyleSheet(
            "font-size:13px; font-weight:700; color:#1E293B;")
        self._det_nombre.setWordWrap(True)
        dp.addWidget(self._det_nombre)
        dp.addSpacing(4)

        # Meta: fecha · cajero · proveedor (filas clave/valor estilo arqueo)
        self._det_meta_rows = {}
        for key, emoji, label in [
            ("fecha",     "📅", "Fecha"),
            ("cajero",    "👤", "Cajero"),
            ("proveedor", "🏪", "Proveedor"),
        ]:
            rw = QWidget(); rw.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(rw); rl.setContentsMargins(0,4,0,4); rl.setSpacing(6)
            k = QLabel(f"{emoji}  {label}")
            k.setStyleSheet("font-size:12px; color:#64748B;")
            rl.addWidget(k); rl.addStretch()
            v = QLabel("—")
            v.setStyleSheet("font-size:12px; font-weight:700; color:#1E293B;")
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            rl.addWidget(v)
            self._det_meta_rows[key] = v
            dp.addWidget(rw)

        # Sep
        s1 = QFrame(); s1.setFrameShape(QFrame.Shape.HLine)
        s1.setStyleSheet("background:#F1F5F9; max-height:1px; margin:8px 0;")
        dp.addWidget(s1)

        # Insumos caption
        ins_cap = QLabel("INSUMOS")
        ins_cap.setStyleSheet(
            "font-size:10px; font-weight:700; color:#94A3B8; letter-spacing:1px;")
        dp.addWidget(ins_cap)
        dp.addSpacing(6)

        self._det_insumos_layout = QVBoxLayout()
        self._det_insumos_layout.setSpacing(2)
        dp.addLayout(self._det_insumos_layout)
        dp.addSpacing(6)

        # Costo total
        s2 = QFrame(); s2.setFrameShape(QFrame.Shape.HLine)
        s2.setStyleSheet("background:#F1F5F9; max-height:1px; margin:4px 0;")
        dp.addWidget(s2)

        cw = QWidget(); cw.setStyleSheet("background:transparent;")
        cl = QHBoxLayout(cw); cl.setContentsMargins(0,5,0,5)
        ck = QLabel("💰  Costo total")
        ck.setStyleSheet("font-size:12px; color:#64748B;")
        cl.addWidget(ck); cl.addStretch()
        self._det_costo = QLabel("Bs 0.00")
        self._det_costo.setStyleSheet(
            "font-size:12px; font-weight:700; color:#FF6B35;")
        self._det_costo.setAlignment(Qt.AlignmentFlag.AlignRight)
        cl.addWidget(self._det_costo)
        dp.addWidget(cw)

        # Ajustes caption
        s3 = QFrame(); s3.setFrameShape(QFrame.Shape.HLine)
        s3.setStyleSheet("background:#F1F5F9; max-height:1px; margin:8px 0;")
        dp.addWidget(s3)

        aj_cap = QLabel("AJUSTES / MERMAS")
        aj_cap.setStyleSheet(
            "font-size:10px; font-weight:700; color:#94A3B8; letter-spacing:1px;")
        dp.addWidget(aj_cap)
        dp.addSpacing(6)

        self._det_ajustes_layout = QVBoxLayout()
        self._det_ajustes_layout.setSpacing(4)
        dp.addLayout(self._det_ajustes_layout)

        # Costo neto
        dp.addSpacing(6)
        s4 = QFrame(); s4.setFrameShape(QFrame.Shape.HLine)
        s4.setStyleSheet("background:#F1F5F9; max-height:1px; margin:4px 0;")
        dp.addWidget(s4)

        nw = QWidget(); nw.setStyleSheet("background:transparent;")
        nl = QHBoxLayout(nw); nl.setContentsMargins(0,5,0,5)
        nk = QLabel("📊  Costo neto")
        nk.setStyleSheet("font-size:12px; color:#64748B;")
        nl.addWidget(nk); nl.addStretch()
        self._det_neto = QLabel("Bs 0.00")
        self._det_neto.setStyleSheet(
            "font-size:12px; font-weight:700; color:#1E293B;")
        self._det_neto.setAlignment(Qt.AlignmentFlag.AlignRight)
        nl.addWidget(self._det_neto)
        dp.addWidget(nw)
        dp.addStretch()

        body.addWidget(self._detail_panel, stretch=0)
        # guardamos referencia al scroll para poder refrescar tamaño
        self._detail_scroll = _scroll
        lay.addLayout(body)

    def _limpiar_filtros(self):
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_hasta.setDate(QDate.currentDate().addDays(1))
        if self._es_admin:
            self.usuario_combo.setCurrentIndex(0)
        self._detail_panel.setVisible(False)
        self.load_data()

    def _on_vista_changed(self):
        self._detail_panel.setVisible(False)
        self.load_data()

    def _get_filtros(self):
        desde = self.fecha_desde.date().toString("yyyy-MM-dd")
        hasta = self.fecha_hasta.date().toString("yyyy-MM-dd") + " 23:59:59"
        uid   = self.usuario_combo.currentData()
        return desde, hasta, uid

    def _limpiar_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_row_selected(self):
        if self.vista_combo.currentData() != "paquetes":
            return
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows_paquetes):
            self._detail_panel.setVisible(False)
            return
        r = self._rows_paquetes[row]

        # ── Nombre y meta ──────────────────────────────────────────────
        self._det_nombre.setText(r["nombre"])
        self._det_meta_rows["fecha"].setText(
            (r.get("fecha_registro") or "")[:10] or "—")
        self._det_meta_rows["cajero"].setText(r.get("cajero") or "—")
        self._det_meta_rows["proveedor"].setText(r.get("proveedor") or "—")

        # ── Insumos ────────────────────────────────────────────────────
        self._limpiar_layout(self._det_insumos_layout)
        try:
            items = json.loads(r.get("items_json") or "[]")
        except Exception:
            items = []

        for it in items:
            rw = QWidget(); rw.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(rw)
            rl.setContentsMargins(0, 3, 0, 3); rl.setSpacing(4)
            # Nombre insumo
            nm = QLabel(f"•  {it.get('nombre','—')}")
            nm.setStyleSheet("font-size:12px; color:#1E293B;")
            nm.setWordWrap(True)
            rl.addWidget(nm, stretch=2)
            # Cantidad + unidad
            cant = it.get("cantidad", 0)
            uni  = it.get("unidad", "")
            pu   = it.get("precio_unit", it.get("costo", 0))   # compat. datos viejos
            cu   = QLabel(f"{cant:.3g} {uni}")
            cu.setStyleSheet("font-size:11px; color:#64748B;")
            cu.setAlignment(Qt.AlignmentFlag.AlignRight)
            rl.addWidget(cu, stretch=1)
            self._det_insumos_layout.addWidget(rw)
            # Sub-fila: precio unit → costo
            sw = QWidget(); sw.setStyleSheet("background:transparent;")
            sl = QHBoxLayout(sw); sl.setContentsMargins(12, 0, 0, 4); sl.setSpacing(4)
            pu_lbl = QLabel(f"Bs {pu:.2f} c/u")
            pu_lbl.setStyleSheet("font-size:10px; color:#94A3B8;")
            sl.addWidget(pu_lbl); sl.addStretch()
            total_it = it.get("costo", 0)
            cv = QLabel(f"Bs {total_it:.2f}")
            cv.setStyleSheet("font-size:12px; font-weight:700; color:#10B981;")
            cv.setAlignment(Qt.AlignmentFlag.AlignRight)
            sl.addWidget(cv)
            self._det_insumos_layout.addWidget(sw)

        if not items:
            vl = QLabel("Sin insumos registrados")
            vl.setStyleSheet("font-size:12px; color:#94A3B8;")
            self._det_insumos_layout.addWidget(vl)

        # ── Costo total ────────────────────────────────────────────────
        costo_total = float(r.get("costo_total") or 0)
        self._det_costo.setText(f"Bs {costo_total:.2f}")

        # ── Ajustes ────────────────────────────────────────────────────
        self._limpiar_layout(self._det_ajustes_layout)
        try:
            ajustes = json.loads(r.get("ajustes_json") or "[]")
        except Exception:
            ajustes = []

        total_ajuste = 0.0
        for aj in ajustes:
            af = QFrame()
            af.setStyleSheet("""
                QFrame { background:#FFF7ED; border:1px solid #FED7AA;
                         border-radius:6px; }
                QLabel { background:transparent; border:none; }
            """)
            al = QVBoxLayout(af)
            al.setContentsMargins(10, 7, 10, 7); al.setSpacing(2)

            # Tipo + costo
            hr = QHBoxLayout(); hr.setSpacing(4)
            tipo_lbl = QLabel(
                f"{TIPO_ICONO.get(aj.get('tipo','ajuste'),'✏️')}  "
                f"{aj.get('tipo','—').title()}")
            tipo_lbl.setStyleSheet("font-size:12px; font-weight:700; color:#F59E0B;")
            hr.addWidget(tipo_lbl); hr.addStretch()
            costo_aj = float(aj.get("costo", 0))
            cl = QLabel(f"–Bs {costo_aj:.2f}")
            cl.setStyleSheet("font-size:12px; font-weight:700; color:#EF4444;")
            hr.addWidget(cl)
            al.addLayout(hr)

            # Insumo afectado
            ins_lbl = QLabel(aj.get("insumo_nombre", "—"))
            ins_lbl.setStyleSheet("font-size:12px; color:#1E293B;")
            al.addWidget(ins_lbl)

            # Motivo (ahora siempre se muestra)
            motivo = (aj.get("motivo") or "").strip()
            mot_lbl = QLabel(f"💬  {motivo}" if motivo else "💬  Sin motivo")
            mot_lbl.setStyleSheet(
                f"font-size:11px; color:{'#64748B' if motivo else '#94A3B8'};")
            mot_lbl.setWordWrap(True)
            al.addWidget(mot_lbl)

            # Fecha
            fecha_aj = aj.get("fecha", "")
            if fecha_aj:
                fl = QLabel(f"📅  {fecha_aj[:10]}")
                fl.setStyleSheet("font-size:11px; color:#94A3B8;")
                al.addWidget(fl)

            self._det_ajustes_layout.addWidget(af)
            total_ajuste += costo_aj

        if not ajustes:
            nl = QLabel("Sin ajustes registrados")
            nl.setStyleSheet("font-size:12px; color:#94A3B8;")
            self._det_ajustes_layout.addWidget(nl)

        # ── Costo neto ─────────────────────────────────────────────────
        neto = costo_total - total_ajuste
        self._det_neto.setText(f"Bs {neto:.2f}")
        self._detail_panel.setVisible(True)

    def load_data(self):
        vista  = self.vista_combo.currentData()
        desde, hasta, uid = self._get_filtros()
        self._detail_panel.setVisible(False)

        if vista == "productos":
            q = (
                "SELECT mi.*, p.nombre as producto, u.nombre as usuario "
                "FROM movimientos_inventario mi "
                "JOIN productos p ON mi.producto_id = p.id "
                "JOIN usuarios u ON mi.usuario_id = u.id "
                "WHERE mi.fecha >= ? AND mi.fecha <= ?"
            )
            params = [desde, hasta]
            if uid:
                q += " AND mi.usuario_id = ?"
                params.append(uid)
            elif not self._es_admin:
                q += " AND mi.usuario_id = ?"
                params.append(self._usuario_id_propio)
            q += " ORDER BY mi.fecha DESC LIMIT 500"

            movs = db.fetch_all(q, tuple(params))
            self.table.setColumnCount(7)
            self.table.setHorizontalHeaderLabels(
                ["Producto","Tipo","Cantidad","Stock ant.","Stock nuevo","Usuario","Fecha"])
            self.table.setRowCount(len(movs))
            for row, m in enumerate(movs):
                self.table.setItem(row,0,QTableWidgetItem(m["producto"]))
                ti = QTableWidgetItem(
                    f"{TIPO_ICONO.get(m['tipo'],'')} {m['tipo'].title()}")
                ti.setForeground(QColor(TIPO_COLOR.get(m["tipo"], C_MUTED)))
                self.table.setItem(row,1,ti)
                self.table.setItem(row,2,QTableWidgetItem(str(m["cantidad"])))
                self.table.setItem(row,3,QTableWidgetItem(str(m["stock_anterior"])))
                self.table.setItem(row,4,QTableWidgetItem(str(m["stock_nuevo"])))
                self.table.setItem(row,5,QTableWidgetItem(m["usuario"]))
                self.table.setItem(row,6,QTableWidgetItem(
                    (m["fecha"] or "")[:16].replace("T"," ")))
        else:
            q = (
                "SELECT p.*, u.nombre as cajero "
                "FROM paquetes_insumos p "
                "LEFT JOIN usuarios u ON p.usuario_id = u.id "
                "WHERE p.fecha_registro >= ? AND p.fecha_registro <= ?"
            )
            params = [desde, hasta]
            if uid:
                q += " AND p.usuario_id = ?"
                params.append(uid)
            elif not self._es_admin:
                q += " AND p.usuario_id = ?"
                params.append(self._usuario_id_propio)
            q += " ORDER BY p.fecha_registro DESC LIMIT 500"

            rows = db.fetch_all(q, tuple(params))
            self._rows_paquetes = [dict(r) for r in rows]
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(
                ["Paquete","Fecha","Costo total","Ajustes","Registrado por"])
            self.table.setRowCount(len(self._rows_paquetes))
            for row, r in enumerate(self._rows_paquetes):
                self.table.setItem(row,0,QTableWidgetItem(r["nombre"]))
                self.table.setItem(row,1,QTableWidgetItem((r["fecha_registro"] or "")[:10]))
                ci = QTableWidgetItem(f"Bs {r['costo_total']:.2f}")
                ci.setForeground(QColor(C_PRIMARY))
                self.table.setItem(row,2,ci)
                try:    n = len(json.loads(r.get("ajustes_json") or "[]"))
                except: n = 0
                ni = QTableWidgetItem(str(n) if n else "—")
                ni.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if n > 0:
                    ni.setForeground(QColor(C_AMBER))
                self.table.setItem(row,3,ni)
                self.table.setItem(row,4,QTableWidgetItem(r.get("cajero") or "—"))


# ──────────────────────────────────────────────────────────────────────────────
# WIDGET PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

class InventoryWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 22, 28, 22)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("📦 Inventario")
        title.setStyleSheet(f"font-size:20px; font-weight:700; color:{C_TEXT};")
        hdr.addWidget(title)
        hdr.addStretch()

        bajos = len(get_productos_stock_bajo())
        if bajos > 0:
            alerta = QLabel(f"⚠️  {bajos} producto(s) con stock bajo")
            alerta.setStyleSheet(f"""
                background:#FEF3C7; color:#92400E; border:1px solid #FCD34D;
                border-radius:7px; padding:4px 12px; font-size:11px; font-weight:600;
            """)
            hdr.addWidget(alerta)
        lay.addLayout(hdr)

        sub = QLabel("Gestión de productos, paquetes de insumos e historial de movimientos.")
        sub.setStyleSheet(f"font-size:11px; color:{C_MUTED}; margin-top:-4px;")
        lay.addWidget(sub)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border:1px solid {C_BORDER}; border-radius:10px;
                               background:{C_WHITE}; padding:16px; }}
            QTabBar::tab {{ padding:6px 18px; font-size:11px; font-weight:600;
                           color:{C_MUTED}; border:none; margin-right:3px; }}
            QTabBar::tab:selected {{ color:{C_PRIMARY}; border-bottom:2px solid {C_PRIMARY}; }}
            QTabBar::tab:hover:!selected {{ color:{C_TEXT}; }}
        """)
        tabs.addTab(ProductosStockTab(), "📦  Productos")
        tabs.addTab(PaquetesTab(),       "🧺  Paquetes de Insumos")
        tabs.addTab(HistorialTab(),      "📋  Historial")
        lay.addWidget(tabs)