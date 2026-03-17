"""
Inventory Widget — La Placita POS
4 pestañas: ⚗️ Insumos | 📋 Recetas | 🧺 Compras | 📊 Historial
"""

import json
from datetime import datetime
from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QComboBox, QHeaderView,
    QFrame, QDoubleSpinBox, QSpinBox, QScrollArea, QTextEdit,
    QSizePolicy, QDateEdit, QCheckBox, QAbstractItemView, QAbstractScrollArea
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from models.inventory import (
    Insumo, Receta,
    registrar_movimiento, get_todos_movimientos,
    get_productos_stock_bajo, get_todos_movimientos_insumos,
)
from models.product import Product
from models.user import get_current_user, User
from database.connection import db


# ─────────────────────────────────────────────────────────────────────────────
# Paleta y constantes
# ─────────────────────────────────────────────────────────────────────────────

C_PRIMARY = "#FF6B35"
C_GREEN   = "#10B981"
C_BLUE    = "#3B82F6"
C_AMBER   = "#F59E0B"
C_RED     = "#EF4444"
C_PURPLE  = "#8B5CF6"
C_BG      = "#F8FAFC"
C_WHITE   = "#FFFFFF"
C_TEXT    = "#1E293B"
C_MUTED   = "#64748B"
C_BORDER  = "#E2E8F0"

TIPO_COLOR = {
    "entrada": C_GREEN, "venta": C_BLUE,
    "ajuste":  C_AMBER, "merma": C_RED, "consumo": C_PURPLE,
}
TIPO_ICONO = {
    "entrada": "📥", "venta": "🛒",
    "ajuste":  "✏️",  "merma": "🗑️", "consumo": "⚗️",
}

# Unidades básicas de medida continua
UNIDADES_BASE   = ["g", "kg", "ml", "litros"]
# Unidades de envase — cuando se seleccionan, aparece el campo "unidades por envase"
UNIDADES_ENVASE = ["caja", "bolsa", "paquete"]
# Todas las unidades del combo (base + envase)
UNIDADES_TODAS  = UNIDADES_BASE + UNIDADES_ENVASE
# Tipos de envase (para compatibilidad con código anterior)
ENVASE_TIPOS    = UNIDADES_ENVASE


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de UI
# ─────────────────────────────────────────────────────────────────────────────

_LE = f"""
    QLineEdit {{ background:{C_WHITE}; border:1px solid {C_BORDER};
                border-radius:6px; padding:5px 10px; font-size:12px; color:{C_TEXT}; }}
    QLineEdit:focus {{ border-color:{C_PRIMARY}; }}
    QLineEdit:disabled {{ background:#F1F5F9; color:{C_MUTED}; }}
"""
_SP = f"""
    QDoubleSpinBox, QSpinBox {{
        background:{C_WHITE}; border:1px solid {C_BORDER};
        border-radius:6px; padding:4px 8px; font-size:12px; color:{C_TEXT}; }}
    QDoubleSpinBox:focus, QSpinBox:focus {{ border-color:{C_PRIMARY}; }}
    QDoubleSpinBox:disabled, QSpinBox:disabled {{ background:#F1F5F9; color:{C_MUTED}; }}
"""
_CB = f"""
    QComboBox {{ background:{C_WHITE}; border:1px solid {C_BORDER};
                border-radius:6px; padding:4px 10px; font-size:12px; color:{C_TEXT}; }}
    QComboBox:focus {{ border-color:{C_PRIMARY}; }}
    QComboBox::drop-down {{ border:none; width:22px; }}
    QComboBox:disabled {{ background:#F1F5F9; color:{C_MUTED}; }}
"""
_TBL = f"""
    QTableWidget {{ background:{C_WHITE}; border:none; font-size:12px;
                   gridline-color:{C_BORDER}; outline:none; color:{C_TEXT}; }}
    QTableWidget::item {{ padding:4px 8px; border-bottom:1px solid {C_BORDER}; }}
    QTableWidget::item:selected {{ background:#FFF0EB; color:{C_TEXT}; }}
    QHeaderView::section {{ background:{C_BG}; font-size:11px; font-weight:700;
                           color:{C_MUTED}; border:none; padding:6px 10px;
                           border-bottom:2px solid {C_BORDER}; }}
    QTableWidget::item:alternate {{ background:#F8FAFC; }}
"""
_CHK = f"""
    QCheckBox {{ font-size:12px; color:{C_TEXT}; spacing:6px; }}
    QCheckBox::indicator {{ width:16px; height:16px; border-radius:4px;
                           border:1.5px solid {C_BORDER}; background:{C_WHITE}; }}
    QCheckBox::indicator:checked {{ background:{C_PRIMARY}; border-color:{C_PRIMARY}; }}
    QCheckBox::indicator:hover {{ border-color:{C_PRIMARY}; }}
"""


def _btn(text, color, small=False):
    b = QPushButton(text)
    pad = "5px 12px" if small else "7px 18px"
    sz  = "11" if small else "12"
    b.setStyleSheet(f"""
        QPushButton {{ background:{color}; color:white; border:none;
                      border-radius:7px; font-size:{sz}px; font-weight:600;
                      padding:{pad}; }}
        QPushButton:hover {{ background:{color}DD; }}
        QPushButton:pressed {{ background:{color}BB; }}
        QPushButton:disabled {{ background:#CBD5E1; color:#94A3B8; }}
    """)
    return b


def _btn_ghost(text):
    b = QPushButton(text)
    b.setStyleSheet(f"""
        QPushButton {{ background:transparent; color:{C_MUTED}; border:1px solid {C_BORDER};
                      border-radius:7px; font-size:11px; font-weight:600; padding:5px 12px; }}
        QPushButton:hover {{ background:{C_BG}; color:{C_TEXT}; border-color:#CBD5E1; }}
    """)
    return b


def _sep():
    s = QFrame(); s.setFrameShape(QFrame.Shape.HLine)
    s.setStyleSheet(f"background:{C_BORDER}; max-height:1px; margin:4px 0;")
    return s


def _sep_v():
    s = QFrame(); s.setFrameShape(QFrame.Shape.VLine)
    s.setStyleSheet(f"background:{C_BORDER}; max-width:1px; margin:3px 6px;")
    return s


def _lbl_section(text):
    l = QLabel(text)
    l.setStyleSheet(
        f"font-size:10px; font-weight:700; color:{C_MUTED}; letter-spacing:0.8px;")
    return l


def _tag(text, bg, fg):
    """Etiqueta de color tipo badge."""
    l = QLabel(f"  {text}  ")
    l.setStyleSheet(
        f"background:{bg}; color:{fg}; border-radius:5px; "
        f"font-size:10px; font-weight:700; padding:2px 0;")
    return l


def _filter_bar():
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{ background:{C_WHITE}; border:1px solid {C_BORDER}; border-radius:10px; }}
        QLabel {{ background:transparent; border:none; color:{C_TEXT}; }}
    """)
    lay = QHBoxLayout(f); lay.setContentsMargins(14, 10, 14, 10); lay.setSpacing(8)
    return f, lay

def _make_btn_icono(emoji, color, color_hover, color_pressed, ancho=32):
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

def _make_table(cols, headers, col_widths=None, stretch_cols=None):
    t = QTableWidget()
    t.setColumnCount(cols)
    t.setHorizontalHeaderLabels(headers)
    hh = t.horizontalHeader()
    for c in (stretch_cols or [0]):
        hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
    if col_widths:
        for col, w in col_widths:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            t.setColumnWidth(col, w)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(34)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setAlternatingRowColors(True)
    t.setShowGrid(False)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.setStyleSheet(_TBL)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    t.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
    
    return t


def _card_frame(color=None):
    """Frame estilo tarjeta con borde izquierdo de color."""
    f = QFrame()
    border = f"border-left:3px solid {color};" if color else ""
    f.setStyleSheet(
        f"QFrame {{ background:#F8FAFC; border-radius:7px; {border} }}"
        f"QLabel {{ background:transparent; border:none; }}")
    return f


# ─────────────────────────────────────────────────────────────────────────────
# Diálogo — Insumo (crear / editar)
# ─────────────────────────────────────────────────────────────────────────────

class InsumoDialog(QDialog):
    """
    Formulario crear/editar insumo.
    Si la unidad elegida es caja/bolsa/paquete, aparece
    debajo el campo 'unidades por envase' y el precio pasa
    a ser por envase (el costo unitario se calcula automáticamente).
    """
    # Unidades que activan el bloque de envase
    _ENVASE_UNITS = {"caja", "bolsa", "paquete"}

    def __init__(self, insumo=None, parent=None):
        super().__init__(parent)
        self.insumo = insumo
        self.setWindowTitle("Editar Insumo" if insumo else "Nuevo Insumo")
        self.setMinimumWidth(480)
        self.setStyleSheet(
            f"QDialog {{ background:{C_BG}; }}"
            f"QLabel {{ background:transparent; }}")
        self._build()
        if insumo:
            self._load()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(14); lay.setContentsMargins(24, 24, 24, 20)

        # Encabezado
        title = QLabel("✏️ Editar Insumo" if self.insumo else "➕ Nuevo Insumo")
        title.setStyleSheet(f"font-size:16px; font-weight:700; color:{C_TEXT};")
        lay.addWidget(title)
        lay.addWidget(_sep())

        lay.addWidget(_lbl_section("INFORMACIÓN BÁSICA"))
        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("Ej: Huevos, Café, Leche…")
        self.nombre.setStyleSheet(_LE)
        form.addRow("Nombre: *", self.nombre)

        self.cat = QLineEdit()
        self.cat.setPlaceholderText("Lácteos, Granos, Carnes…")
        self.cat.setStyleSheet(_LE)
        form.addRow("Categoría:", self.cat)

        # ── Combo unidad — incluye caja/bolsa/paquete ─────────────────────────
        self.unidad = QComboBox()
        self.unidad.setEditable(True)
        self.unidad.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        # Grupo 1: medidas continuas
        for u in UNIDADES_BASE:
            self.unidad.addItem(u)
        # Separador visual
        self.unidad.insertSeparator(len(UNIDADES_BASE))
        # Grupo 2: envases
        for u in UNIDADES_ENVASE:
            self.unidad.addItem(u.capitalize(), u)
        self.unidad.lineEdit().setPlaceholderText(
            "huevos, láminas, panes…  (escribe la tuya)")
        self.unidad.setStyleSheet(_CB)
        self.unidad.currentTextChanged.connect(self._on_unidad_changed)
        form.addRow("Unidad: *", self.unidad)

        lay.addLayout(form)

        # ── Bloque envase — se muestra solo si unidad es caja/bolsa/paquete ───
        self._env_frame = QFrame()
        self._env_frame.setStyleSheet(
            f"QFrame {{ background:#EFF6FF; border:1px solid #BFDBFE; "
            f"border-radius:8px; }}"
            f"QLabel {{ background:transparent; border:none; color:{C_TEXT}; }}")
        env_lay = QVBoxLayout(self._env_frame)
        env_lay.setContentsMargins(14, 12, 14, 12); env_lay.setSpacing(10)

        env_form = QFormLayout(); env_form.setSpacing(10)
        env_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.env_cant = QDoubleSpinBox()
        self.env_cant.setRange(1, 99999); self.env_cant.setDecimals(2)
        self.env_cant.setValue(1); self.env_cant.setStyleSheet(_SP)
        self.env_cant.valueChanged.connect(self._upd_env_preview)
        self._lbl_env_cant = QLabel("Unidades por caja:")
        env_form.addRow(self._lbl_env_cant, self.env_cant)

        self.precio_env = QDoubleSpinBox()
        self.precio_env.setRange(0, 999999); self.precio_env.setDecimals(2)
        self.precio_env.setPrefix("Bs "); self.precio_env.setStyleSheet(_SP)
        self.precio_env.valueChanged.connect(self._upd_env_preview)
        self._lbl_precio_env = QLabel("Precio por caja:")
        env_form.addRow(self._lbl_precio_env, self.precio_env)

        env_lay.addLayout(env_form)

        self._env_preview = QLabel("")
        self._env_preview.setStyleSheet(
            f"font-size:11px; font-weight:700; color:#1D4ED8;")
        self._env_preview_sub = QLabel("")
        self._env_preview_sub.setStyleSheet(
            f"font-size:10px; color:{C_MUTED};")
        env_lay.addWidget(self._env_preview)
        env_lay.addWidget(self._env_preview_sub)
        lay.addWidget(self._env_frame)
        self._env_frame.setVisible(False)

        # ── Resto del formulario ──────────────────────────────────────────────
        form2 = QFormLayout(); form2.setSpacing(10)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        row_s = QHBoxLayout(); row_s.setSpacing(10)
        self.stock_ini = QDoubleSpinBox()
        self.stock_ini.setRange(0, 999999); self.stock_ini.setDecimals(2)
        self.stock_ini.setStyleSheet(_SP); self.stock_ini.setFixedWidth(120)
        row_s.addWidget(self.stock_ini)
        row_s.addWidget(QLabel("  Mínimo:"))
        self.stock_min = QDoubleSpinBox()
        self.stock_min.setRange(0, 999999); self.stock_min.setDecimals(2)
        self.stock_min.setStyleSheet(_SP); self.stock_min.setFixedWidth(120)
        row_s.addWidget(self.stock_min); row_s.addStretch()
        form2.addRow("Stock inicial:", row_s)

        # Costo: si hay envase se calcula automáticamente y se muestra readonly
        self._lbl_costo = QLabel("Costo / unidad:")
        self.costo = QDoubleSpinBox()
        self.costo.setRange(0, 999999); self.costo.setDecimals(4)
        self.costo.setPrefix("Bs "); self.costo.setStyleSheet(_SP)
        form2.addRow(self._lbl_costo, self.costo)

        self.nota = QTextEdit(); self.nota.setMaximumHeight(52)
        self.nota.setPlaceholderText("Nota opcional…")
        self.nota.setStyleSheet(
            f"QTextEdit {{ background:{C_WHITE}; border:1px solid {C_BORDER}; "
            f"border-radius:6px; padding:6px; font-size:12px; color:{C_TEXT}; }}")
        form2.addRow("Nota:", self.nota)
        lay.addLayout(form2)

        br = QHBoxLayout(); br.setContentsMargins(0, 8, 0, 0)
        c = _btn_ghost("Cancelar"); c.clicked.connect(self.reject)
        ok = _btn("💾  Guardar", C_PRIMARY); ok.clicked.connect(self._ok)
        br.addWidget(c); br.addStretch(); br.addWidget(ok)
        lay.addLayout(br)

    # ── Lógica interna ────────────────────────────────────────────────────────

    def _es_envase(self):
        """True si la unidad seleccionada es caja, bolsa o paquete."""
        return self.unidad.currentText().strip().lower() in self._ENVASE_UNITS

    def _on_unidad_changed(self, text):
        es = text.strip().lower() in self._ENVASE_UNITS
        self._env_frame.setVisible(es)
        # Actualizar etiquetas con el nombre de la unidad
        u = text.strip().lower() or "envase"
        self._lbl_env_cant.setText(f"Unidades por {u}:")
        self._lbl_precio_env.setText(f"Precio por {u}:")
        # Campo costo: editable solo si NO es envase
        self.costo.setEnabled(not es)
        if es:
            self._lbl_costo.setText("Costo / unidad (calc.):")
        else:
            self._lbl_costo.setText("Costo / unidad:")
            self._env_preview.setText("")
            self._env_preview_sub.setText("")
        self._upd_env_preview()

    def _upd_env_preview(self):
        if not self._es_envase():
            return
        u     = self.unidad.currentText().strip().lower() or "envase"
        cant  = self.env_cant.value()
        prec  = self.precio_env.value()
        n     = int(cant) if cant == int(cant) else cant
        p_uni = prec / cant if cant > 0 else 0
        # Actualizar costo unitario calculado
        self.costo.setValue(p_uni)
        self._env_preview.setText(f"1 {u} = {n} unidades")
        if prec > 0:
            self._env_preview_sub.setText(
                f"Bs {prec:.2f} ÷ {n} = Bs {p_uni:.4f} / unidad")
        else:
            self._env_preview_sub.setText("")

    def _load(self):
        i = self.insumo
        self.nombre.setText(i.nombre)
        self.cat.setText(i.categoria or "")

        # Bloquear señales mientras cargamos para no disparar _on_unidad_changed
        self.unidad.blockSignals(True)
        idx = self.unidad.findText(i.unidad, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.unidad.setCurrentIndex(idx)
        else:
            # unidad personalizada (ej: "huevos")
            self.unidad.setCurrentText(i.unidad)
        self.unidad.blockSignals(False)

        self.stock_ini.setValue(i.stock_actual)
        self.stock_min.setValue(i.stock_minimo)
        self.nota.setPlainText(i.descripcion or "")

        if i.tiene_envase:
            self.env_cant.setValue(i.envase_cantidad)
            # Recalcular precio de envase desde costo unitario guardado
            self.precio_env.setValue(i.costo_unitario * i.envase_cantidad)
        else:
            self.costo.setValue(i.costo_unitario)

        # Disparar manualmente para que aparezca el frame si corresponde
        self._on_unidad_changed(self.unidad.currentText())

    def _ok(self):
        nombre = self.nombre.text().strip()
        unidad = self.unidad.currentText().strip()
        if not nombre:
            QMessageBox.warning(self, "Campo requerido",
                                "El nombre del insumo es obligatorio.")
            return
        if not unidad:
            QMessageBox.warning(self, "Campo requerido",
                                "Selecciona o escribe la unidad del insumo.")
            return
        if self._es_envase() and self.env_cant.value() < 1:
            QMessageBox.warning(self, "Campo requerido",
                                "Indica cuántas unidades trae el envase.")
            return
        self.accept()

    def get_data(self):
        unidad = self.unidad.currentText().strip() or "unidades"
        es_env = self._es_envase()
        return {
            "nombre":          self.nombre.text().strip(),
            "categoria":       self.cat.text().strip() or None,
            "unidad":          unidad,
            "stock_actual":    self.stock_ini.value(),
            "stock_minimo":    self.stock_min.value(),
            # Si es envase: costo ya fue calculado automáticamente en _upd_env_preview
            "costo_unitario":  self.costo.value(),
            "descripcion":     self.nota.toPlainText().strip() or None,
            # Campos envase: se guardan si la unidad es caja/bolsa/paquete
            "envase_tipo":     unidad.lower() if es_env else None,
            "envase_cantidad": self.env_cant.value() if es_env else 1.0,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Diálogo — Movimiento de insumo
# ─────────────────────────────────────────────────────────────────────────────

class MovimientoDialog(QDialog):
    """
    Registra una entrada, ajuste o merma de un insumo.
    Si el insumo tiene envase configurado, en modo Entrada aparece
    el bloque de conversión automática (N envases → unidades).
    """
    def __init__(self, insumo, parent=None):
        super().__init__(parent)
        self.insumo = insumo
        self.setWindowTitle(f"Movimiento — {insumo.nombre}")
        self.setMinimumWidth(430)
        self.setStyleSheet(
            f"QDialog {{ background:{C_BG}; }}"
            f"QLabel {{ background:transparent; }}")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(14); lay.setContentsMargins(24, 22, 24, 20)

        # ── Info actual ───────────────────────────────────────────────────────
        info_frame = _card_frame()
        il = QHBoxLayout(info_frame)
        il.setContentsMargins(14, 10, 14, 10); il.setSpacing(20)

        def _info_col(label, value, color=C_TEXT):
            col = QVBoxLayout(); col.setSpacing(1)
            lv = QLabel(value)
            lv.setStyleSheet(
                f"font-size:14px; font-weight:700; color:{color};")
            ll = QLabel(label)
            ll.setStyleSheet(f"font-size:10px; color:{C_MUTED};")
            col.addWidget(lv); col.addWidget(ll)
            return col

        stock_color = (C_RED if self.insumo.stock_actual <= 0
                       else C_AMBER if self.insumo.stock_bajo else C_GREEN)
        # Stock mostrado en la unidad del insumo (siempre)
        il.addLayout(_info_col(
            "Stock actual",
            f"{self.insumo.stock_actual:.2f} {self.insumo.unidad}",
            stock_color))
        if self.insumo.tiene_envase:
            # Para envases mostramos precio por envase + equivalencia
            precio_env = self.insumo.costo_unitario * self.insumo.envase_cantidad
            il.addLayout(_info_col(
                f"Precio / {self.insumo.envase_tipo}",
                f"Bs {precio_env:.2f}", C_BLUE))
            il.addLayout(_info_col(
                "Equivalencia",
                self.insumo.envase_label, C_MUTED))
        else:
            il.addLayout(_info_col(
                f"Precio / {self.insumo.unidad}",
                f"Bs {self.insumo.costo_unitario:.4f}"))
        il.addStretch()
        lay.addWidget(info_frame)

        # ── Tipo ──────────────────────────────────────────────────────────────
        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.tipo = QComboBox(); self.tipo.setStyleSheet(_CB)
        self.tipo.addItem("📥  Entrada  (compra / reposición)", "entrada")
        self.tipo.addItem("🗑️  Merma / Pérdida",                "merma")
        self.tipo.currentIndexChanged.connect(self._on_tipo)
        form.addRow("Tipo: *", self.tipo)
        lay.addLayout(form)

        # ── Bloque Entrada ────────────────────────────────────────────────────
        self._entrada_frame = QFrame()
        self._entrada_frame.setStyleSheet(
            f"QFrame {{ background:transparent; }}"
            f"QLabel {{ background:transparent; border:none; }}")
        ef_lay = QVBoxLayout(self._entrada_frame)
        ef_lay.setContentsMargins(0, 4, 0, 0); ef_lay.setSpacing(10)

        ef_form = QFormLayout(); ef_form.setSpacing(10)
        ef_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Modo envase (solo si tiene envase configurado)
        # Si la unidad del insumo ES un envase (caja/bolsa/paquete),
        # el modo envase está siempre activo y se puede desactivar manualmente
        _u = self.insumo.unidad.lower()
        self._es_unidad_envase = _u in {"caja", "bolsa", "paquete"}

        self._chk_envase = None

        if self.insumo.tiene_envase or self._es_unidad_envase:

            n = int(self.insumo.envase_cantidad or 1)

            lbl_env = (
                self.insumo.envase_label
                if self.insumo.tiene_envase
                else f"1 {_u} = {n} unidades"
            )

            self._chk_envase = QCheckBox()
            self._chk_envase.setStyleSheet(_CHK)
            self._chk_envase.setChecked(True)

            self._lbl_env = lbl_env

            self._chk_envase.toggled.connect(self._on_modo)

            self._actualizar_texto_chk()

            ef_lay.addWidget(self._chk_envase)
        # Frame modo ENVASE
        self._modo_env = _card_frame(C_BLUE)
        me_lay = QFormLayout(self._modo_env)
        me_lay.setSpacing(10); me_lay.setContentsMargins(14, 12, 14, 12)
        me_lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._n_env = QDoubleSpinBox()
        self._n_env.setRange(1, 9999); self._n_env.setDecimals(0)
        self._n_env.setValue(1); self._n_env.setStyleSheet(_SP)
        tipo_env = self.insumo.unidad  # la unidad ES el envase (caja/bolsa/paquete)
        self._n_env.setSuffix(f"  {tipo_env}(s)")
        self._n_env.valueChanged.connect(self._upd_preview)
        me_lay.addRow(f"Cantidad de {tipo_env}s:", self._n_env)

        self._precio_env = QDoubleSpinBox()
        self._precio_env.setRange(0, 999999); self._precio_env.setDecimals(2)
        self._precio_env.setPrefix("Bs ")
        # Precio sugerido = costo_unitario × envase_cantidad
        self._precio_env.setValue(
            self.insumo.costo_unitario * self.insumo.envase_cantidad)
        self._precio_env.setStyleSheet(_SP)
        self._precio_env.valueChanged.connect(self._upd_preview)
        me_lay.addRow(f"Precio por {tipo_env}:", self._precio_env)

        ef_lay.addWidget(self._modo_env)

        # Frame modo DIRECTO
        self._modo_dir = _card_frame(C_BLUE)
        md_lay = QFormLayout(self._modo_dir)
        md_lay.setSpacing(10); md_lay.setContentsMargins(14, 12, 14, 12)
        md_lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        unidad_txt= "unidades" if self.insumo.unidad in {"Paquete","Caja","Bolsa"} else self.insumo.unidad

        self._cant_dir = QDoubleSpinBox()
        self._cant_dir.setRange(0.000, 999999); self._cant_dir.setDecimals(3)
        self._cant_dir.setSuffix(f"  {unidad_txt}")
        self._cant_dir.setStyleSheet(_SP)
        self._cant_dir.valueChanged.connect(self._upd_preview)
        md_lay.addRow(f"Cantidad ({unidad_txt}):", self._cant_dir)

        self._precio_dir = QDoubleSpinBox()
        self._precio_dir.setRange(0, 999999); self._precio_dir.setDecimals(2)
        self._precio_dir.setPrefix("Bs ")
        self._precio_dir.setValue(self.insumo.costo_unitario)
        self._precio_dir.setStyleSheet(_SP)
        self._precio_dir.valueChanged.connect(self._upd_preview)
        md_lay.addRow(f"Precio / {unidad_txt}:", self._precio_dir)

        ef_lay.addWidget(self._modo_dir)

        # Preview resultado
        self._preview = QLabel("")
        self._preview.setStyleSheet(
            f"font-size:12px; font-weight:700; color:{C_GREEN}; padding:4px 0;")
        self._preview_sub = QLabel("")
        self._preview_sub.setStyleSheet(
            f"font-size:10px; color:{C_MUTED};")
        ef_lay.addWidget(self._preview)
        ef_lay.addWidget(self._preview_sub)

        lay.addWidget(self._entrada_frame)

       # Solo unidades mínimas — registrar merma en cajas no tiene sentido
        self._otro_frame = _card_frame()
        of = QFormLayout(self._otro_frame)
        of.setSpacing(10); of.setContentsMargins(14, 12, 14, 12)
        of.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._cant_otro = QDoubleSpinBox()
        self._cant_otro.setRange(0.000, 999999); self._cant_otro.setDecimals(3)
        self._cant_otro.setSuffix(f"  {unidad_txt}")
        self._cant_otro.setStyleSheet(_SP)
        of.addRow(f"Cantidad ({unidad_txt}):", self._cant_otro)
        lay.addWidget(self._otro_frame)

        # ── Motivo ────────────────────────────────────────────────────────────
        lbl_mot = QLabel("Motivo:")
        lbl_mot.setStyleSheet(f"font-size:12px; color:{C_TEXT};")
        lay.addWidget(lbl_mot)
        self.motivo = QTextEdit(); self.motivo.setMaximumHeight(52)
        self.motivo.setPlaceholderText("Motivo del movimiento (opcional)…")
        self.motivo.setStyleSheet(
            f"QTextEdit {{ background:{C_WHITE}; border:1px solid {C_BORDER}; "
            f"border-radius:6px; padding:6px; font-size:12px; color:{C_TEXT}; }}")
        lay.addWidget(self.motivo)

        nota = QLabel(
            "🔒  Este movimiento quedará registrado con tu usuario y la fecha actual.")
        nota.setStyleSheet(f"font-size:10px; color:{C_MUTED};")
        lay.addWidget(nota)

        # ── Botones ───────────────────────────────────────────────────────────
        br = QHBoxLayout()
        c = _btn_ghost("Cancelar"); c.clicked.connect(self.reject)
        self._btn_ok = _btn("✅  Registrar", C_GREEN)
        self._btn_ok.clicked.connect(self.accept)
        br.addWidget(c); br.addStretch(); br.addWidget(self._btn_ok)
        lay.addLayout(br)

        # Estado inicial
        self._on_tipo()

    # ── lógica interna ────────────────────────────────────────────────────────
    def _actualizar_texto_chk(self):
        if not self._chk_envase:
            return
        
        if self._chk_envase.isChecked():
            self._chk_envase.setText(
                f"Ingresar por {self.insumo.unidad} ({self._lbl_env})"
            )
        else:
            self._chk_envase.setText(
                f"Ingresar por unidades ({self._lbl_env})")
            

        """def _on_modo_otro(self):

        if not self._chk_envase_otro:
            return

        if self._chk_envase_otro.isChecked():
            self._modo_env_otro.setVisible(True)
            self._modo_dir_otro.setVisible(False)
        else:
            self._modo_env_otro.setVisible(False)
            self._modo_dir_otro.setVisible(True)
      
        self._upd_preview()"""

        
    def _on_tipo(self):
        es_entrada = self.tipo.currentData() == "entrada"
        self._entrada_frame.setVisible(es_entrada)
        self._otro_frame.setVisible(not es_entrada)
        if es_entrada:
            self._on_modo(self._chk_envase.isChecked()
                          if self._chk_envase else False)
        self._upd_preview()

    def _on_modo(self, use_env):
        self._modo_env.setVisible(use_env)
        self._modo_dir.setVisible(not use_env)
        self._actualizar_texto_chk()
        self._upd_preview()

    def _upd_preview(self):
        if self.tipo.currentData() != "entrada":
            self._preview.setText(""); self._preview_sub.setText(""); return

        use_env = (self._chk_envase is not None
                   and self._chk_envase.isChecked())

        if use_env:
            n        = self._n_env.value()
            uds_env  = self.insumo.envase_cantidad
            total_u  = n * uds_env
            precio_e = self._precio_env.value()
            precio_u = precio_e / uds_env if uds_env > 0 else 0
            tipo_env = self.insumo.unidad
            self._preview.setText(
                f"Stock: +{total_u:.3g} unidades   ·   "
                f"Total: Bs {n * precio_e:.2f}")
            self._preview_sub.setText(
                f"Bs {precio_e:.2f} / {tipo_env} ÷ {int(uds_env)} unidades "
                f"= Bs {precio_u:.4f} / unidad")
        else:
            cant   = self._cant_dir.value()
            precio = self._precio_dir.value()
            if precio > 0:
                self._preview.setText(
                    f"Stock: +{cant:.3g} {self.insumo.unidad}   ·   "
                    f"Total: Bs {cant * precio:.2f}")
            else:
                self._preview.setText(
                    f"Stock: +{cant:.3g} {self.insumo.unidad}")
            self._preview_sub.setText("")

    def get_data(self):
        """Devuelve (tipo, delta, motivo, precio_unitario)."""
        tipo = self.tipo.currentData()
        mot  = self.motivo.toPlainText().strip() or None

        if tipo != "entrada":
            return tipo, -self._cant_otro.value(), mot, None

        use_env = (self._chk_envase is not None
                   and self._chk_envase.isChecked())

        if use_env:
            n        = self._n_env.value()
            uds_env  = self.insumo.envase_cantidad
            delta    = n * uds_env           # stock sube en unidades mínimas
            precio_e = self._precio_env.value()
            precio_u = precio_e / uds_env if uds_env > 0 else 0
            tipo_env = self.insumo.unidad    # "caja", "bolsa", etc.
            mot_auto = (f"{int(n)} {tipo_env}(s) × "
                        f"{int(uds_env)} unidades/envase = {int(delta)} unidades")
            mot = f"{mot_auto}  —  {mot}" if mot else mot_auto
        else:
            delta    = self._cant_dir.value()
            precio_u = self._precio_dir.value()

        return tipo, delta, mot, precio_u


# ─────────────────────────────────────────────────────────────────────────────
# Diálogo — Receta de un producto
# ─────────────────────────────────────────────────────────────────────────────

class RecetaDialog(QDialog):
    def __init__(self, producto, parent=None):
        super().__init__(parent)
        self.producto = producto
        self._items   = []
        self._insumos = Insumo.get_all()
        self.setWindowTitle(f"Receta — {producto.nombre}")
        self.setMinimumWidth(560); self.setMinimumHeight(440)
        self.setStyleSheet(
            f"QDialog {{ background:{C_BG}; }}"
            f"QLabel {{ background:transparent; }}")
        self._build(); self._cargar()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12); lay.setContentsMargins(24, 22, 24, 20)

        title = QLabel(f"📋  Receta de <b>{self.producto.nombre}</b>")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setStyleSheet(f"font-size:15px; color:{C_TEXT};")
        lay.addWidget(title)
        sub = QLabel(
            "Define qué insumos se descuentan automáticamente al vender "
            "una unidad de este producto.")
        sub.setStyleSheet(f"font-size:11px; color:{C_MUTED};")
        sub.setWordWrap(True); lay.addWidget(sub)
        lay.addWidget(_sep())

        lay.addWidget(_lbl_section("AGREGAR INSUMO"))
        add_row = QHBoxLayout(); add_row.setSpacing(8)

        self.ins_cb = QComboBox(); self.ins_cb.setStyleSheet(_CB)
        self.ins_cb.addItem("— Seleccionar insumo —", None)
        for ins in self._insumos:
            UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
            unidad = ins.unidad
            unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
            self.ins_cb.addItem(f"{ins.nombre}  ({unidad_txt})", ins.id)

        self.cant_sp = QDoubleSpinBox()
        self.cant_sp.setRange(0.000, 99999); self.cant_sp.setDecimals(3)
        self.cant_sp.setFixedWidth(100); self.cant_sp.setStyleSheet(_SP)

        self._uni_lbl = QLabel("—")
        self._uni_lbl.setStyleSheet(
            f"font-size:11px; color:{C_MUTED}; min-width:55px;")
        self.ins_cb.currentIndexChanged.connect(self._upd_uni)
        self._upd_uni()

        add_b = _btn("＋ Agregar", C_GREEN, small=True)
        add_b.clicked.connect(self._agregar)
        add_row.addWidget(self.ins_cb, stretch=3)
        add_row.addWidget(self.cant_sp)
        add_row.addWidget(self._uni_lbl)
        add_row.addWidget(add_b)
        lay.addLayout(add_row)

        self._tbl = _make_table(
            4, ["Insumo", "Cantidad", "Unidad", ""],
            col_widths=[(1, 85), (2, 85), (3, 36)])
        self._tbl.setFixedHeight(180)
        lay.addWidget(self._tbl)

        self._empty = QLabel(
            "Sin insumos — este producto no descuenta inventario al venderse.")
        self._empty.setStyleSheet(
            f"font-size:11px; color:{C_MUTED}; padding:8px 0;")
        lay.addWidget(self._empty)

        br = QHBoxLayout()
        c = _btn_ghost("Cancelar"); c.clicked.connect(self.reject)
        ok = _btn("💾  Guardar Receta", C_PRIMARY); ok.clicked.connect(self.accept)
        br.addWidget(c); br.addStretch(); br.addWidget(ok)
        lay.addLayout(br)

    def _upd_uni(self):
        ins = next(
            (i for i in self._insumos if i.id == self.ins_cb.currentData()),
            None
        )

        if not ins:
            self._uni_lbl.setText("—")
            return

        UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}

        unidad = ins.unidad
        unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad

        self._uni_lbl.setText(unidad_txt)

    def _cargar(self):
        items = Receta.get_por_producto(self.producto.id)
        UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
        self._items = [
            {"insumo_id": ri.insumo_id, "insumo_nombre": ri.insumo_nombre,
             "cantidad": ri.cantidad, "unidad": 'unidades' if ri.insumo_unidad in UNIDADES_A_UNIDADES else ri.insumo_unidad}
            for ri in items]
        self._refresh()

    def _agregar(self):
        ins_id = self.ins_cb.currentData()
        if ins_id is None:
            QMessageBox.warning(self, "Falta insumo",
                                "Selecciona un insumo de la lista."); return
        ins = next((i for i in self._insumos if i.id == ins_id), None)
        UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
        unidad = ins.unidad
        unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
        if not ins: return
        for it in self._items:
            if it["insumo_id"] == ins_id:
                it["cantidad"] = self.cant_sp.value()
                self._refresh(); return
        self._items.append({
            "insumo_id": ins_id, "insumo_nombre": ins.nombre,
            "cantidad": self.cant_sp.value(), "unidad": unidad_txt})
        self.cant_sp.setValue(1.0); self._refresh()

    def _quitar(self, idx):
        if 0 <= idx < len(self._items):
            self._items.pop(idx); self._refresh()

    def _refresh(self):
        tiene = bool(self._items)
        self._tbl.setVisible(tiene); self._empty.setVisible(not tiene)
        self._tbl.setRowCount(len(self._items))
        for r, it in enumerate(self._items):
            self._tbl.setItem(r, 0, QTableWidgetItem(it["insumo_nombre"]))
            ci = QTableWidgetItem(f"{it['cantidad']:.3g}")
            ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tbl.setItem(r, 1, ci)
            ui = QTableWidgetItem(it["unidad"])
            ui.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tbl.setItem(r, 2, ui)
            qw = QWidget(); qw.setStyleSheet("background:transparent;")
            ql = QHBoxLayout(qw); ql.setContentsMargins(3, 2, 3, 2)
            qb = QPushButton("✕"); qb.setFixedSize(24, 24)
            qb.setStyleSheet(
                f"QPushButton {{ background:#FEE2E2; color:{C_RED}; border:none; "
                f"border-radius:4px; font-size:10px; font-weight:700; }}"
                f"QPushButton:hover {{ background:{C_RED}; color:white; }}")
            qb.clicked.connect(partial(self._quitar, r))
            ql.addWidget(qb)
            self._tbl.setCellWidget(r, 3, qw)

    def get_data(self):
        return [{"insumo_id": it["insumo_id"], "cantidad": it["cantidad"]}
                for it in self._items]


# ─────────────────────────────────────────────────────────────────────────────
# Diálogo — Nueva compra
# ─────────────────────────────────────────────────────────────────────────────

class NuevaCompraDialog(QDialog):
    """
    Panel izq: 3 pasos (datos, selector, cantidad/precio)
    Panel der: lista de ítems en tiempo real con scroll y total
    """
    _ENVASE_U = {"caja", "bolsa", "paquete"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Compra")
        self.setMinimumWidth(900)
        self.setMinimumHeight(640)
        self.setStyleSheet(
            f"QDialog {{ background:{C_BG}; }}"
            f"QLabel {{ background:transparent; }}")
        self._insumos = Insumo.get_all()
        self._items   = []
        self._build()

    # ──────────────────────────────────────────────────────────────────────
    # BUILD
    # ──────────────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet(f"QFrame{{background:{C_WHITE};border-bottom:1px solid {C_BORDER};}}"
                          f"QLabel{{background:transparent;border:none;}}")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(28,18,28,18); hl.setSpacing(14)
        ico = QLabel("🧺"); ico.setStyleSheet("font-size:26px;")
        hl.addWidget(ico)
        tv = QVBoxLayout(); tv.setSpacing(2)
        t1 = QLabel("Registrar Compra de Insumos")
        t1.setStyleSheet(f"font-size:17px; font-weight:700; color:{C_TEXT};")
        t2 = QLabel("Selecciona los insumos comprados y el sistema actualizará el stock automáticamente.")
        t2.setStyleSheet(f"font-size:11px; color:{C_MUTED};")
        tv.addWidget(t1); tv.addWidget(t2)
        hl.addLayout(tv); hl.addStretch()
        root.addWidget(hdr)

        # ── Body ──────────────────────────────────────────────────────────
        body = QHBoxLayout(); body.setContentsMargins(0,0,0,0); body.setSpacing(0)

        # ══ Panel izquierdo ═══════════════════════════════════════════════
        # Scroll propio para que nunca se corte
        left_scroll = QScrollArea(); left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        left_scroll.setStyleSheet(f"""
            QScrollArea{{background:{C_BG};border:none;}}
            QScrollBar:vertical{{width:6px;background:transparent;}}
            QScrollBar::handle:vertical{{background:#CBD5E1;border-radius:3px;min-height:24px;}}
            QScrollBar::handle:vertical:hover{{background:#94A3B8;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
        """)
        left_inner = QWidget(); left_inner.setStyleSheet(f"background:{C_BG};")
        left_lay = QVBoxLayout(left_inner)
        left_lay.setContentsMargins(28,24,24,24); left_lay.setSpacing(18)

        # ─ Paso 1: datos ──────────────────────────────────────────────────
        left_lay.addWidget(self._step_header("1", "Datos de la compra"))

        f1 = QFrame(); f1.setStyleSheet(
            f"QFrame{{background:{C_WHITE};border:1px solid {C_BORDER};border-radius:10px;}}"
            f"QLabel{{background:transparent;border:none;}}")
        f1l = QFormLayout(f1); f1l.setContentsMargins(18,16,18,16); f1l.setSpacing(12)
        f1l.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("Ej: Compra semanal, Lunes 14 marzo…")
        self.nombre.setStyleSheet(_LE)
        f1l.addRow("Referencia: *", self.nombre)

        self.proveedor = QLineEdit()
        self.proveedor.setPlaceholderText("Nombre del proveedor (opcional)")
        self.proveedor.setStyleSheet(_LE)
        f1l.addRow("Proveedor:", self.proveedor)

        self.nota_input = QTextEdit(); self.nota_input.setMaximumHeight(52)
        self.nota_input.setPlaceholderText("Observación (opcional)…")
        self.nota_input.setStyleSheet(
            f"QTextEdit{{background:{C_WHITE};border:1px solid {C_BORDER};"
            f"border-radius:6px;padding:6px 10px;font-size:12px;color:{C_TEXT};}}")
        f1l.addRow("Nota:", self.nota_input)
        left_lay.addWidget(f1)

        # ─ Paso 2: seleccionar insumo ─────────────────────────────────────
        left_lay.addWidget(self._step_header("2", "Seleccionar insumo"))

        self.ins_cb = QComboBox(); self.ins_cb.setStyleSheet(_CB)
        self.ins_cb.addItem("— Elige un insumo de la lista —", None)
        for ins in self._insumos:
            UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
            unidad = ins.unidad
            unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
            lbl = f"{ins.nombre}  ({unidad_txt})"
            self.ins_cb.addItem(lbl, ins)
        self.ins_cb.currentIndexChanged.connect(self._on_insumo_sel)
        left_lay.addWidget(self.ins_cb)

        # Info pills del insumo seleccionado
        self._info_frame = QFrame()
        self._info_frame.setStyleSheet(
            f"QFrame{{background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;}}"
            f"QLabel{{background:transparent;border:none;}}")
        ifl = QHBoxLayout(self._info_frame)
        ifl.setContentsMargins(18,14,18,14); ifl.setSpacing(28)

        self._pill_stock  = self._make_pill("Stock actual", "—")
        self._pill_envase = self._make_pill("Envase", "—")
        self._pill_precio = self._make_pill("Precio actual", "—")
        ifl.addLayout(self._pill_stock)
        ifl.addLayout(self._pill_envase)
        ifl.addLayout(self._pill_precio)
        ifl.addStretch()
        left_lay.addWidget(self._info_frame)
        self._info_frame.setVisible(False)

        # ─ Paso 3: cantidad y precio ───────────────────────────────────────
        left_lay.addWidget(self._step_header("3", "Cantidad y precio"))

        # Toggle modo envase — solo texto, sin checkbox feo
        self._toggle_frame = QFrame()
        self._toggle_frame.setStyleSheet(
            f"QFrame{{background:{C_WHITE};border:1px solid {C_BORDER};border-radius:8px;}}"
            f"QLabel{{background:transparent;border:none;}}")
        tfl = QHBoxLayout(self._toggle_frame)
        tfl.setContentsMargins(16,12,16,12); tfl.setSpacing(12)
        self._toggle_lbl = QLabel("Modo de ingreso:")
        self._toggle_lbl.setStyleSheet(f"font-size:11px;color:{C_MUTED};font-weight:600;")
        tfl.addWidget(self._toggle_lbl)
        self._btn_modo_env = QPushButton()
        self._btn_modo_env.setCheckable(True)
        self._btn_modo_env.setChecked(False)
        self._btn_modo_env.clicked.connect(self._on_modo_toggle)
        self._btn_modo_dir = QPushButton()
        self._btn_modo_dir.setCheckable(True)
        self._btn_modo_dir.setChecked(True)
        self._btn_modo_dir.clicked.connect(self._on_modo_toggle)
        for b in [self._btn_modo_env, self._btn_modo_dir]:
            b.setStyleSheet(f"""
                QPushButton{{border:1px solid {C_BORDER};border-radius:6px;
                    font-size:11px;font-weight:600;padding:5px 14px;
                    background:{C_WHITE};color:{C_MUTED};}}
                QPushButton:checked{{background:{C_PRIMARY};color:white;border-color:{C_PRIMARY};}}
                QPushButton:hover:!checked{{background:{C_BG};color:{C_TEXT};}}
            """)
        tfl.addWidget(self._btn_modo_env)
        tfl.addWidget(self._btn_modo_dir)
        tfl.addStretch()
        left_lay.addWidget(self._toggle_frame)
        self._toggle_frame.setVisible(False)

        # Frame ENVASE
        self._frame_env = QFrame()
        self._frame_env.setStyleSheet(
            f"QFrame{{background:{C_WHITE};border:1px solid {C_BORDER};border-radius:10px;}}"
            f"QLabel{{background:transparent;border:none;}}")
        fel = QVBoxLayout(self._frame_env)
        fel.setContentsMargins(18,16,18,16); fel.setSpacing(14)

        row_env = QHBoxLayout(); row_env.setSpacing(16)
        c1 = QVBoxLayout(); c1.setSpacing(6)
        self._lbl_n_env = QLabel("Cantidad")
        self._lbl_n_env.setStyleSheet(f"font-size:11px;font-weight:600;color:{C_MUTED};")
        self._n_env_c = QDoubleSpinBox()
        self._n_env_c.setRange(1,9999); self._n_env_c.setDecimals(0)
        self._n_env_c.setValue(1); self._n_env_c.setStyleSheet(_SP)
        self._n_env_c.valueChanged.connect(self._upd_preview)
        c1.addWidget(self._lbl_n_env); c1.addWidget(self._n_env_c)

        c2 = QVBoxLayout(); c2.setSpacing(6)
        self._lbl_precio_env = QLabel("Precio")
        self._lbl_precio_env.setStyleSheet(f"font-size:11px;font-weight:600;color:{C_MUTED};")
        self._precio_env_c = QDoubleSpinBox()
        self._precio_env_c.setRange(0,999999); self._precio_env_c.setDecimals(2)
        self._precio_env_c.setPrefix("Bs "); self._precio_env_c.setStyleSheet(_SP)
        self._precio_env_c.valueChanged.connect(self._upd_preview)
        c2.addWidget(self._lbl_precio_env); c2.addWidget(self._precio_env_c)

        row_env.addLayout(c1,1); row_env.addLayout(c2,2)
        fel.addLayout(row_env)
        left_lay.addWidget(self._frame_env)

        # Frame DIRECTO
        self._frame_dir = QFrame()
        self._frame_dir.setStyleSheet(
            f"QFrame{{background:{C_WHITE};border:1px solid {C_BORDER};border-radius:10px;}}"
            f"QLabel{{background:transparent;border:none;}}")
        fdl = QVBoxLayout(self._frame_dir)
        fdl.setContentsMargins(18,16,18,16); fdl.setSpacing(14)

        row_dir = QHBoxLayout(); row_dir.setSpacing(16)
        d1 = QVBoxLayout(); d1.setSpacing(6)
        self._lbl_cant_dir = QLabel("Cantidad")
        self._lbl_cant_dir.setStyleSheet(f"font-size:11px;font-weight:600;color:{C_MUTED};")
        self._cant_dir_c = QDoubleSpinBox()
        self._cant_dir_c.setRange(0.000,999999); self._cant_dir_c.setDecimals(3)
        self._cant_dir_c.setStyleSheet(_SP)
        self._cant_dir_c.valueChanged.connect(self._upd_preview)
        d1.addWidget(self._lbl_cant_dir); d1.addWidget(self._cant_dir_c)

        d2 = QVBoxLayout(); d2.setSpacing(6)
        self._lbl_precio_dir = QLabel("Precio por unidad")
        self._lbl_precio_dir.setStyleSheet(f"font-size:11px;font-weight:600;color:{C_MUTED};")
        self._precio_dir_c = QDoubleSpinBox()
        self._precio_dir_c.setRange(0,999999); self._precio_dir_c.setDecimals(4)
        self._precio_dir_c.setPrefix("Bs "); self._precio_dir_c.setStyleSheet(_SP)
        self._precio_dir_c.valueChanged.connect(self._upd_preview)
        d2.addWidget(self._lbl_precio_dir); d2.addWidget(self._precio_dir_c)

        row_dir.addLayout(d1,1); row_dir.addLayout(d2,2)
        fdl.addLayout(row_dir)
        left_lay.addWidget(self._frame_dir)

        # Preview resultado
        self._prev_frame = QFrame()
        self._prev_frame.setStyleSheet(
            f"QFrame{{background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;}}"
            f"QLabel{{background:transparent;border:none;}}")
        pvl = QVBoxLayout(self._prev_frame)
        pvl.setContentsMargins(16,12,16,12); pvl.setSpacing(3)
        self._prev_main = QLabel("")
        self._prev_main.setStyleSheet("font-size:13px;font-weight:700;color:#15803D;")
        self._prev_sub = QLabel("")
        self._prev_sub.setStyleSheet(f"font-size:10px;color:{C_MUTED};")
        pvl.addWidget(self._prev_main); pvl.addWidget(self._prev_sub)
        left_lay.addWidget(self._prev_frame)
        self._prev_frame.setVisible(False)

        # Botón agregar
        self._btn_add = _btn("＋  Agregar a la lista", C_PRIMARY)
        self._btn_add.setEnabled(False)
        self._btn_add.clicked.connect(self._agregar_item)
        left_lay.addWidget(self._btn_add)
        left_lay.addStretch()

        left_scroll.setWidget(left_inner)
        body.addWidget(left_scroll, stretch=5)

        # ── Separador ────────────────────────────────────────────────────────
        vsep = QFrame(); vsep.setFrameShape(QFrame.Shape.VLine)
        vsep.setStyleSheet(f"background:{C_BORDER};max-width:1px;")
        body.addWidget(vsep)

        # ══ Panel derecho: lista ══════════════════════════════════════════════
        right = QWidget(); right.setStyleSheet(f"background:{C_WHITE};")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0,0,0,0); right_lay.setSpacing(0)

        # Header derecho fijo
        rh_frame = QFrame()
        rh_frame.setStyleSheet(
            f"QFrame{{background:{C_WHITE};border-bottom:1px solid {C_BORDER};}}"
            f"QLabel{{background:transparent;border:none;}}")
        rhl = QHBoxLayout(rh_frame); rhl.setContentsMargins(20,14,20,14)
        rl = QLabel("Lista de compra")
        rl.setStyleSheet(f"font-size:13px;font-weight:700;color:{C_TEXT};")
        self._total_lbl = QLabel("Total:  Bs 0.00")
        self._total_lbl.setStyleSheet(f"font-size:14px;font-weight:700;color:{C_PRIMARY};")
        rhl.addWidget(rl); rhl.addStretch(); rhl.addWidget(self._total_lbl)
        right_lay.addWidget(rh_frame)

        # Scroll de la lista
        rscroll = QScrollArea(); rscroll.setWidgetResizable(True)
        rscroll.setFrameShape(QFrame.Shape.NoFrame)
        rscroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rscroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        rscroll.setStyleSheet(f"""
            QScrollArea{{background:{C_WHITE};border:none;}}
            QScrollBar:vertical{{width:8px;background:#F8FAFC;
                border-radius:4px;margin:4px 2px;}}
            QScrollBar::handle:vertical{{background:#CBD5E1;border-radius:4px;min-height:28px;}}
            QScrollBar::handle:vertical:hover{{background:#94A3B8;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
            QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:transparent;}}
        """)
        self._lista_widget = QWidget(); self._lista_widget.setStyleSheet("background:transparent;")
        self._lista_lay = QVBoxLayout(self._lista_widget)
        self._lista_lay.setContentsMargins(16,16,16,16); self._lista_lay.setSpacing(10)

        self._empty_lbl = QLabel("Aún no hay insumos en la lista.\nSelecciona uno a la izquierda y presiona Agregar.")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(f"font-size:11px;color:{C_MUTED};padding:40px 16px;")
        self._empty_lbl.setWordWrap(True)
        self._lista_lay.addWidget(self._empty_lbl)
        self._lista_lay.addStretch()

        rscroll.setWidget(self._lista_widget)
        right_lay.addWidget(rscroll)
        body.addWidget(right, stretch=4)
        root.addLayout(body)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QFrame()
        footer.setStyleSheet(
            f"QFrame{{background:{C_WHITE};border-top:1px solid {C_BORDER};}}"
            f"QLabel{{background:transparent;border:none;}}")
        fl = QHBoxLayout(footer); fl.setContentsMargins(28,16,28,16); fl.setSpacing(12)
        fl.addStretch()
        btn_c = _btn_ghost("Cancelar"); btn_c.clicked.connect(self.reject)
        btn_ok = _btn("✅  Confirmar compra", C_PRIMARY); btn_ok.clicked.connect(self._ok)
        fl.addWidget(btn_c); fl.addWidget(btn_ok)
        root.addWidget(footer)

        self._on_insumo_sel()

    # ──────────────────────────────────────────────────────────────────────
    # Helpers de UI
    # ──────────────────────────────────────────────────────────────────────
    def _step_header(self, num, txt):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)
        badge = QLabel(num); badge.setFixedSize(24,24)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"background:{C_PRIMARY};color:white;border-radius:12px;"
                            f"font-size:12px;font-weight:700;")
        lbl = QLabel(txt)
        lbl.setStyleSheet(f"font-size:13px;font-weight:700;color:{C_TEXT};")
        lay.addWidget(badge); lay.addWidget(lbl); lay.addStretch()
        return w

    def _make_pill(self, label, value):
        col = QVBoxLayout(); col.setSpacing(4)
        col._v = QLabel(value)
        col._v.setStyleSheet(f"font-size:14px;font-weight:700;color:{C_TEXT};")
        col._l = QLabel(label)
        col._l.setStyleSheet(f"font-size:9px;color:{C_MUTED};font-weight:600;letter-spacing:0.5px;")
        col.addWidget(col._v); col.addWidget(col._l)
        return col

    def _set_pill(self, col, val, color=None):
        col._v.setText(val)
        if color:
            col._v.setStyleSheet(f"font-size:14px;font-weight:700;color:{color};")

    # ──────────────────────────────────────────────────────────────────────
    # Lógica
    # ──────────────────────────────────────────────────────────────────────
    def _ins(self):
        """Insumo actualmente seleccionado o None."""
        return self.ins_cb.currentData()

    def _es_envase(self, ins=None):
        ins = ins or self._ins()
        UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
        unidad = ins.unidad
        unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
        if ins is None: return False
        return unidad_txt.lower() in self._ENVASE_U or ins.tiene_envase

    def _modo_env_activo(self):
        return self._btn_modo_env.isChecked()

    def _on_insumo_sel(self):
        ins = self._ins()
        
        if ins is None:
            self._info_frame.setVisible(False)
            self._toggle_frame.setVisible(False)
            self._frame_env.setVisible(False)
            self._frame_dir.setVisible(False)
            self._prev_frame.setVisible(False)
            self._btn_add.setEnabled(False)
            return
        UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
        unidad = ins.unidad
        unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
        # Pills de info
        sc = (C_RED if ins.stock_actual <= 0
              else C_AMBER if ins.stock_bajo else C_GREEN)
        self._set_pill(self._pill_stock,
                       f"{ins.stock_actual:.2f} {unidad_txt}", sc)

        if ins.tiene_envase:
            n = int(ins.envase_cantidad) if ins.envase_cantidad == int(ins.envase_cantidad) else ins.envase_cantidad
            env_txt = f"1 {ins.envase_tipo} = {n} {unidad_txt}"
        elif unidad_txt.lower() in self._ENVASE_U:
            n = int(ins.envase_cantidad) if ins.envase_cantidad == int(ins.envase_cantidad) else ins.envase_cantidad
            env_txt = f"1 {unidad_txt} = {n} unidades"
        else:
            env_txt = "Sin envase"
        self._set_pill(self._pill_envase, env_txt,
                       C_BLUE if self._es_envase(ins) else C_MUTED)

        p_unit = ins.costo_unitario
        self._set_pill(self._pill_precio, f"Bs {p_unit:.4f} / {unidad_txt}", C_TEXT)
        self._info_frame.setVisible(True)

        es_env = self._es_envase(ins)
        # Toggle modo
        if es_env:
            tipo = ins.envase_tipo or unidad_txt
            n = int(ins.envase_cantidad) if ins.envase_cantidad == int(ins.envase_cantidad) else ins.envase_cantidad
            self._btn_modo_env.setText(f"Por {tipo}  ({n} und.)")
            self._btn_modo_dir.setText("Por unidad")
            self._btn_modo_env.setChecked(True)
            self._btn_modo_dir.setChecked(False)
            self._toggle_frame.setVisible(True)
        else:
            self._btn_modo_env.setChecked(False)
            self._btn_modo_dir.setChecked(True)
            self._toggle_frame.setVisible(False)

        # Labels dinámicos
        tipo_env = ins.envase_tipo or unidad_txt
        self._lbl_n_env.setText(f"Cantidad de {tipo_env}s")
        self._lbl_precio_env.setText(f"Precio por {tipo_env}")
        self._lbl_cant_dir.setText(f"Cantidad  ({unidad_txt})")
        self._lbl_precio_dir.setText(f"Precio por {unidad_txt}")
        self._n_env_c.setSuffix(f"  {tipo_env}(s)")
        self._cant_dir_c.setSuffix(f"  {unidad_txt}")

        # Precios sugeridos
        precio_env_sug = ins.costo_unitario * ins.envase_cantidad
        self._precio_env_c.setValue(max(precio_env_sug, 0))
        self._precio_dir_c.setValue(ins.costo_unitario)
        self._n_env_c.setValue(1)
        self._cant_dir_c.setValue(1)

        self._btn_add.setEnabled(True)
        self._aplicar_modo()

    def _on_modo_toggle(self):
        sender = self.sender()
        # Solo un botón activo a la vez
        self._btn_modo_env.setChecked(sender is self._btn_modo_env)
        self._btn_modo_dir.setChecked(sender is self._btn_modo_dir)
        self._aplicar_modo()

    def _aplicar_modo(self):
        modo_env = self._modo_env_activo() and self._es_envase()
        self._frame_env.setVisible(modo_env)
        self._frame_dir.setVisible(not modo_env)
        self._upd_preview()

    def _upd_preview(self):
        ins = self._ins()
        if ins is None:
            self._prev_frame.setVisible(False); return

        if self._modo_env_activo() and self._es_envase(ins):
            UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
            unidad = ins.unidad
            unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
            n       = self._n_env_c.value()
            uds     = ins.envase_cantidad
            total_u = n * uds
            prec_e  = self._precio_env_c.value()
            prec_u  = prec_e / uds if uds > 0 else 0
            tipo    = ins.envase_tipo or unidad_txt
            self._prev_main.setText(
                f"+{total_u:.3g} {unidad_txt}  ·  Total  Bs {n * prec_e:.2f}")
            self._prev_sub.setText(
                f"Bs {prec_e:.2f} por {tipo} ÷ {int(uds)} unidades = Bs {prec_u:.4f} / {unidad_txt}")
        else:
            cant  = self._cant_dir_c.value()
            prec  = self._precio_dir_c.value()
            self._prev_main.setText(
                f"+{cant:.3g} {unidad_txt}"
                + (f"  ·  Total  Bs {cant*prec:.2f}" if prec > 0 else ""))
            self._prev_sub.setText("")

        self._prev_frame.setVisible(True)

    def _agregar_item(self):
        ins = self._ins()
        if ins is None: return

        if self._modo_env_activo() and self._es_envase(ins):
            UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
            unidad = ins.unidad
            unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
            n_env    = self._n_env_c.value()
            uds      = ins.envase_cantidad
            cantidad = n_env * uds
            prec_e   = self._precio_env_c.value()
            precio_u = prec_e / uds if uds > 0 else 0
            tipo_env = ins.envase_tipo or unidad_txt
            nota_env = f"{int(n_env)} {tipo_env}(s)  ×  {int(uds)} unidades = {int(cantidad)} unidades"
        else:
            cantidad = self._cant_dir_c.value()
            precio_u = self._precio_dir_c.value()
            nota_env = None

        # Actualizar si ya existe
        for it in self._items:
            if it["insumo_id"] == ins.id:
                it["cantidad"] = cantidad
                it["precio_unit"] = precio_u
                it["nota_env"] = nota_env
                self._refresh_lista(); return

        self._items.append({
            "insumo_id":   ins.id,
            "insumo":      ins,
            "cantidad":    cantidad,
            "precio_unit": precio_u,
            "nota_env":    nota_env,
        })
        # Reset
        self._n_env_c.setValue(1); self._precio_env_c.setValue(0)
        self._cant_dir_c.setValue(1); self._precio_dir_c.setValue(0)
        self._prev_frame.setVisible(False)
        self.ins_cb.setCurrentIndex(0)
        self._refresh_lista()

    def _quitar_item(self, insumo_id):
        self._items = [i for i in self._items if i["insumo_id"] != insumo_id]
        self._refresh_lista()

    def _refresh_lista(self):
        while self._lista_lay.count():
            it = self._lista_lay.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        if not self._items:
            # Crear nuevo label cada vez (el anterior fue destruido por deleteLater)
            lbl = QLabel("Aún no hay insumos en la lista.\nSelecciona uno a la izquierda y presiona Agregar.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"font-size:11px;color:{C_MUTED};padding:40px 16px;")
            lbl.setWordWrap(True)
            self._lista_lay.addWidget(lbl)
            self._lista_lay.addStretch()
            self._total_lbl.setText("Total:  Bs 0.00")
            return

        total_general = 0.0
        for it in self._items:
            ins      = it["insumo"]
            subtotal = it["precio_unit"] * it["cantidad"]
            total_general += subtotal

            card = QFrame()
            card.setStyleSheet(
                f"QFrame{{background:{C_BG};border:1px solid {C_BORDER};"
                f"border-radius:10px;}}"
                f"QLabel{{background:transparent;border:none;}}")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16,14,16,14); cl.setSpacing(8)

            # Fila 1: nombre + quitar
            r1 = QHBoxLayout(); r1.setSpacing(8)
            nm = QLabel(ins.nombre)
            nm.setStyleSheet(f"font-size:13px;font-weight:700;color:{C_TEXT};")
            qb = QPushButton("✕"); qb.setFixedSize(24,24)
            qb.setStyleSheet(
                f"QPushButton{{background:#FEE2E2;color:{C_RED};border:none;"
                f"border-radius:5px;font-size:10px;font-weight:700;}}"
                f"QPushButton:hover{{background:{C_RED};color:white;}}")
            qb.clicked.connect(partial(self._quitar_item, ins.id))
            r1.addWidget(nm); r1.addStretch(); r1.addWidget(qb)
            cl.addLayout(r1)

            # Detalle envase
            if it.get("nota_env"):
                nd = QLabel(it["nota_env"])
                nd.setStyleSheet(f"font-size:10px;color:{C_BLUE};")
                cl.addWidget(nd)

            # Fila 2: cantidad · precio · subtotal
            r2 = QHBoxLayout(); r2.setSpacing(6)

            def chip(txt, color=C_MUTED, bg="#F1F5F9"):
                l = QLabel(txt)
                l.setStyleSheet(f"font-size:11px;color:{color};background:{bg};"
                                f"border-radius:5px;padding:3px 8px;")
                return l

            r2.addWidget(chip(f"{it['cantidad']:.3g} und."))
            sep_lbl = QLabel("·"); sep_lbl.setStyleSheet(f"color:{C_MUTED};")
            r2.addWidget(sep_lbl)
            r2.addWidget(chip(f"Bs {it['precio_unit']:.4f}/und."))
            r2.addStretch()
            r2.addWidget(chip(f"Bs {subtotal:.2f}", "#15803D", "#DCFCE7"))
            cl.addLayout(r2)
            self._lista_lay.addWidget(card)

        self._lista_lay.addStretch()
        self._total_lbl.setText(f"Total:  Bs {total_general:.2f}")

    # ──────────────────────────────────────────────────────────────────────
    # Validación
    # ──────────────────────────────────────────────────────────────────────
    def _ok(self):
        if not self.nombre.text().strip():
            QMessageBox.warning(self, "Campo requerido",
                                "Escribe una referencia para esta compra.")
            return
        if not self._items:
            QMessageBox.warning(self, "Lista vacía",
                                "Agrega al menos un insumo a la lista.")
            return
        self.accept()

    def get_data(self):
        return {
            "nombre":    self.nombre.text().strip(),
            "proveedor": self.proveedor.text().strip() or None,
            "nota":      self.nota_input.toPlainText().strip() or None,
            "items":     self._items,
        }



# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Insumos
# ─────────────────────────────────────────────────────────────────────────────

class InsumosTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build(); self._refresh_cats()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10); lay.setContentsMargins(0, 8, 0, 0)

        bar, bl = _filter_bar()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Buscar insumo…")
        self.search.setStyleSheet(_LE); self.search.setFixedWidth(200)
        self.search.textChanged.connect(self.load_data); bl.addWidget(self.search)

        self.filtro = QComboBox()
        self.filtro.addItem("Todos",          None)
        self.filtro.addItem("⚠️ Stock bajo",  "bajo")
        self.filtro.addItem("❌ Sin stock",   "cero")
        self.filtro.setStyleSheet(_CB); self.filtro.setFixedWidth(130)
        self.filtro.currentIndexChanged.connect(self.load_data)
        bl.addWidget(self.filtro)

        self.cat_cb = QComboBox()
        self.cat_cb.addItem("Todas las categorías", None)
        self.cat_cb.setStyleSheet(_CB); self.cat_cb.setFixedWidth(170)
        self.cat_cb.currentIndexChanged.connect(self.load_data)
        bl.addWidget(self.cat_cb)

        bl.addStretch()
        nb = _btn("➕ Nuevo Insumo", C_PRIMARY, small=True)
        nb.clicked.connect(self._nuevo); bl.addWidget(nb)
        rf = _btn_ghost("🔄"); rf.setFixedWidth(36)
        rf.clicked.connect(self._refresh_cats); bl.addWidget(rf)
        lay.addWidget(bar)

        # 8 columnas: Insumo | Categoría | Stock | Mínimo | Unidad | Envase | Estado | Acciones
        self.table = _make_table(
            8,
            ["Insumo", "Categoría", "Stock", "Mínimo",
             "Unidad", "Envase", "Estado", "Acciones"],
            col_widths=[(2, 80), (3, 70), (4, 70), (6, 95), (7, 90)],
            stretch_cols=[0, 1, 5]
        )
        lay.addWidget(self.table)

    def _refresh_cats(self):
        cat_sel = self.cat_cb.currentData()
        self.cat_cb.blockSignals(True)
        self.cat_cb.clear()
        self.cat_cb.addItem("Todas las categorías", None)
        rows = db.fetch_all(
            "SELECT DISTINCT categoria FROM insumos "
            "WHERE activo=1 AND categoria IS NOT NULL ORDER BY categoria")
        for r in rows:
            self.cat_cb.addItem(r["categoria"], r["categoria"])
        idx = self.cat_cb.findData(cat_sel)
        self.cat_cb.setCurrentIndex(idx if idx >= 0 else 0)
        self.cat_cb.blockSignals(False)
        self.load_data()

    def load_data(self):
        term   = self.search.text().strip().lower()
        filtro = self.filtro.currentData()
        cat    = self.cat_cb.currentData()
        ins    = Insumo.get_all()
        if term:   ins = [i for i in ins if term in i.nombre.lower()]
        if cat:    ins = [i for i in ins if (i.categoria or "") == cat]
        if filtro == "bajo":  ins = [i for i in ins if i.stock_bajo]
        elif filtro == "cero": ins = [i for i in ins if i.stock_actual <= 0]

        self.table.setRowCount(len(ins))

        
        for r, i in enumerate(ins):
            UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
            unidad = i.unidad
            unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
            self.table.setItem(r, 0, QTableWidgetItem(i.nombre))
            self.table.setItem(r, 1, QTableWidgetItem(i.categoria or "—"))

            sa = QTableWidgetItem(f"{i.stock_actual:.2f}")
            sa.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            sa.setForeground(QColor(
                C_RED if i.stock_actual <= 0
                else C_AMBER if i.stock_bajo else C_GREEN))
            self.table.setItem(r, 2, sa)

            sm = QTableWidgetItem(f"{i.stock_minimo:.2f}")
            sm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 3, sm)

            un = QTableWidgetItem(unidad_txt)
            un.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 4, un)

            # Columna envase
            env_txt = i.envase_label if i.tiene_envase else "—"
            ev = QTableWidgetItem(env_txt)
            ev.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            ev.setForeground(QColor(C_BLUE if i.tiene_envase else C_MUTED))
            self.table.setItem(r, 5, ev)

            if i.stock_actual <= 0: est, ecol = "❌ Sin stock",  C_RED
            elif i.stock_bajo:      est, ecol = "⚠️ Stock bajo", C_AMBER
            else:                   est, ecol = "✅ OK",          C_GREEN
            ei = QTableWidgetItem(est)
            ei.setForeground(QColor(ecol))
            self.table.setItem(r, 6, ei)

            # Acciones
            aw = QWidget()
            aw.setStyleSheet("background: transparent;")
            al = QHBoxLayout(aw)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)
            al.setAlignment(Qt.AlignmentFlag.AlignCenter)

            mb_w, mb = _make_btn_icono("📥", "#27ae60", "#2ecc71", "#1e8449")
            mb.setCursor(Qt.CursorShape.PointingHandCursor)
            mb.clicked.connect(partial(self._movimiento, i))

            eb_w, eb = _make_btn_icono("✏️", "#e67e22", "#f39c12", "#ca6f1e")
            eb.setCursor(Qt.CursorShape.PointingHandCursor)
            eb.clicked.connect(partial(self._editar, i))

            al.addWidget(mb_w)
            al.addWidget(eb_w)
            #self.table.setColumnWidth(7, 190)  # columna Acciones más ancha
            self.table.setCellWidget(r, 7, aw)
            self.table.setColumnWidth(7, 90)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(42)

    def _nuevo(self):
        dlg = InsumoDialog(parent=self)
        if dlg.exec():
            Insumo.create(**dlg.get_data()); self._refresh_cats()

    def _editar(self, ins):
        dlg = InsumoDialog(insumo=Insumo.get_by_id(ins.id), parent=self)
        if dlg.exec():
            Insumo.update(ins.id, **dlg.get_data()); self._refresh_cats()

    def _movimiento(self, ins):
        fresh = Insumo.get_by_id(ins.id)
        dlg = MovimientoDialog(fresh, self)
        if dlg.exec():
            tipo, delta, mot, precio_u = dlg.get_data()
            u  = get_current_user()
            ok = fresh.registrar_movimiento(
                tipo, delta, mot, usuario_id=u.id if u else None)
            if ok:
                if tipo == "entrada" and precio_u and precio_u > 0:
                    Insumo.update(fresh.id, costo_unitario=precio_u)
                QMessageBox.information(
                    self, "Éxito", "✅ Movimiento registrado correctamente.")
            else:
                QMessageBox.warning(
                    self, "Error", "No se pudo registrar el movimiento.")
            self.load_data()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Recetas
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Diálogo — Calcular costo de un producto (solo admin)
# ─────────────────────────────────────────────────────────────────────────────

class CostoDialog(QDialog):
    """
    Calcula el precio de venta sugerido de un producto con receta.
    Factores: costo de insumos + otros costos extra + margen de ganancia %.
    Solo visible para administradores.
    """
    def __init__(self, producto, parent=None):
        super().__init__(parent)
        self.producto = producto
        self.setWindowTitle(f"💰 Calcular costo — {producto.nombre}")
        self.setMinimumWidth(480)
        self.setStyleSheet(
            f"QDialog {{ background:{C_BG}; }}"
            f"QLabel {{ background:transparent; }}")
        self._receta = Receta.get_por_producto(producto.id)
        self._costo_insumos = sum(
            ri.cantidad * (Insumo.get_by_id(ri.insumo_id).costo_unitario
                           if Insumo.get_by_id(ri.insumo_id) else 0)
            for ri in self._receta
        )
        self._build()
        self._calcular()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(14); lay.setContentsMargins(24, 22, 24, 20)

        title = QLabel("💰  Calcular precio de venta")
        title.setStyleSheet(f"font-size:16px; font-weight:700; color:{C_TEXT};")
        lay.addWidget(title)
        sub = QLabel(f"Producto: <b>{self.producto.nombre}</b>")
        sub.setTextFormat(Qt.TextFormat.RichText)
        sub.setStyleSheet(f"font-size:12px; color:{C_MUTED};")
        lay.addWidget(sub)
        lay.addWidget(_sep())

        # ── Costo de insumos (readonly) ───────────────────────────────────────
        lay.addWidget(_lbl_section("COSTO DE INSUMOS  (según receta)"))
        ins_frame = _card_frame()
        ifl = QVBoxLayout(ins_frame)
        ifl.setContentsMargins(14, 10, 14, 10); ifl.setSpacing(4)

        UNIDADES_ENVASE = {"Paquete", "Caja", "Bolsa"}
        if self._receta:
            for ri in self._receta:
                ins = Insumo.get_by_id(ri.insumo_id)
                costo_ri = ri.cantidad * (ins.costo_unitario if ins else 0)
                unidad_txt = ("unidades" if ins and ins.unidad in UNIDADES_ENVASE
                              else (ins.unidad if ins else ""))
                row_w = QWidget(); row_w.setStyleSheet("background:transparent;")
                rl = QHBoxLayout(row_w); rl.setContentsMargins(0, 2, 0, 2)
                nm = QLabel(f"{ri.insumo_nombre}  ×  {ri.cantidad:.3g} {unidad_txt}")
                nm.setStyleSheet(f"font-size:11px; color:{C_TEXT};")
                ct = QLabel(f"Bs {costo_ri:.4f}")
                ct.setStyleSheet(f"font-size:11px; font-weight:600; color:{C_AMBER};")
                rl.addWidget(nm); rl.addStretch(); rl.addWidget(ct)
                ifl.addWidget(row_w)
            sep_w = QFrame(); sep_w.setFrameShape(QFrame.Shape.HLine)
            sep_w.setStyleSheet(f"background:{C_BORDER}; max-height:1px;")
            ifl.addWidget(sep_w)
        else:
            nl = QLabel("Sin receta — no hay insumos registrados.")
            nl.setStyleSheet(f"font-size:11px; color:{C_MUTED};")
            ifl.addWidget(nl)

        total_row = QWidget(); total_row.setStyleSheet("background:transparent;")
        trl = QHBoxLayout(total_row); trl.setContentsMargins(0, 4, 0, 0)
        tl = QLabel("Total insumos:")
        tl.setStyleSheet(f"font-size:12px; font-weight:700; color:{C_TEXT};")
        self._lbl_insumos = QLabel(f"Bs {self._costo_insumos:.4f}")
        self._lbl_insumos.setStyleSheet(
            f"font-size:13px; font-weight:700; color:{C_AMBER};")
        trl.addWidget(tl); trl.addStretch(); trl.addWidget(self._lbl_insumos)
        ifl.addWidget(total_row)
        lay.addWidget(ins_frame)

        # ── Factores adicionales ──────────────────────────────────────────────
        lay.addWidget(_lbl_section("FACTORES ADICIONALES"))
        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.extras = QDoubleSpinBox()
        self.extras.setRange(0, 999999); self.extras.setDecimals(2)
        self.extras.setPrefix("Bs ")
        self.extras.setToolTip("Empaque, transporte, gas, electricidad, etc.")
        self.extras.setStyleSheet(_SP)
        self.extras.valueChanged.connect(self._calcular)
        form.addRow("Otros costos (Bs):", self.extras)

        self.margen = QDoubleSpinBox()
        self.margen.setRange(0, 1000); self.margen.setDecimals(1)
        self.margen.setSuffix("  %"); self.margen.setValue(30.0)
        self.margen.setStyleSheet(_SP)
        self.margen.valueChanged.connect(self._calcular)
        form.addRow("Margen de ganancia:", self.margen)
        lay.addLayout(form)

        # ── Resultado ─────────────────────────────────────────────────────────
        lay.addWidget(_sep())
        res_frame = QFrame()
        res_frame.setStyleSheet(
            f"QFrame {{ background:#F0FDF4; border:1px solid #86EFAC; "
            f"border-radius:10px; }}"
            f"QLabel {{ background:transparent; border:none; }}")
        rl2 = QVBoxLayout(res_frame)
        rl2.setContentsMargins(18, 14, 18, 14); rl2.setSpacing(8)

        def _res_row(label, attr, color=C_TEXT, bold=False):
            w = QWidget(); w.setStyleSheet("background:transparent;")
            wl = QHBoxLayout(w); wl.setContentsMargins(0, 0, 0, 0)
            k = QLabel(label)
            k.setStyleSheet(f"font-size:11px; color:{C_MUTED};")
            v = QLabel("—")
            sz = "14" if bold else "12"
            v.setStyleSheet(
                f"font-size:{sz}px; font-weight:{'700' if bold else '600'}; "
                f"color:{color};")
            wl.addWidget(k); wl.addStretch(); wl.addWidget(v)
            setattr(self, attr, v)
            return w

        rl2.addWidget(_res_row("Costo total (insumos + extras):",
                               "_lbl_costo_total", C_TEXT))
        rl2.addWidget(_res_row("Margen aplicado:",
                               "_lbl_margen_bs", C_AMBER))

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background:#86EFAC; max-height:1px;")
        rl2.addWidget(sep2)

        rl2.addWidget(_res_row("💰 Precio sugerido de venta:",
                               "_lbl_precio_final", "#15803D", bold=True))
        lay.addWidget(res_frame)

        nota = QLabel(
            "ℹ️ Este cálculo es orientativo. El precio final lo define el negocio.")
        nota.setStyleSheet(f"font-size:10px; color:{C_MUTED};")
        nota.setWordWrap(True); lay.addWidget(nota)

        br = QHBoxLayout()
        c = _btn_ghost("Cerrar"); c.clicked.connect(self.reject)
        br.addWidget(c); br.addStretch()
        lay.addLayout(br)

    def _calcular(self):
        costo_base = self._costo_insumos + self.extras.value()
        margen_pct = self.margen.value() / 100.0
        margen_bs  = costo_base * margen_pct
        precio_sug = costo_base + margen_bs

        self._lbl_costo_total.setText(f"Bs {costo_base:.4f}")
        self._lbl_margen_bs.setText(
            f"Bs {margen_bs:.4f}  ({self.margen.value():.1f}%)")
        self._lbl_precio_final.setText(f"Bs {precio_sug:.2f}")



class RecetasTab(QWidget):
    def __init__(self):
        super().__init__()
        u = get_current_user()
        self._es_admin = u.is_admin() if u else False
        self._build(); self.load_data()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10); lay.setContentsMargins(0, 8, 0, 0)

        bar, bl = _filter_bar()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Buscar producto…")
        self.search.setStyleSheet(_LE); self.search.setFixedWidth(200)
        self.search.textChanged.connect(self.load_data); bl.addWidget(self.search)

        self.filtro = QComboBox()
        self.filtro.addItem("Todos los productos", None)
        self.filtro.addItem("✅ Con receta",        "con")
        self.filtro.addItem("🔲 Sin receta",        "sin")
        self.filtro.setStyleSheet(_CB); self.filtro.setFixedWidth(160)
        self.filtro.currentIndexChanged.connect(self.load_data)
        bl.addWidget(self.filtro)

        bl.addStretch()
        nota = QLabel("💡 Sin receta = no descuenta inventario al venderse.")
        nota.setStyleSheet(f"font-size:10px; color:{C_MUTED};")
        bl.addWidget(nota)
        rf = _btn_ghost("🔄"); rf.setFixedWidth(36)
        rf.clicked.connect(self.load_data); bl.addWidget(rf)
        lay.addWidget(bar)

        self.table = _make_table(
            4, ["Producto", "Categoría", "Receta (insumos)", ""],
            col_widths=[(3, 150)], stretch_cols=[0, 1, 2])
        lay.addWidget(self.table)

    def load_data(self):
        term   = self.search.text().strip().lower()
        filtro = self.filtro.currentData()
        prods  = Product.get_all()
        if term: prods = [p for p in prods if term in p.nombre.lower()]

        con_receta = Receta.productos_con_receta()
        if filtro == "con":  prods = [p for p in prods if p.id in con_receta]
        elif filtro == "sin": prods = [p for p in prods if p.id not in con_receta]

        cats = {r["id"]: r["nombre"]
                for r in db.fetch_all("SELECT id, nombre FROM categorias")}

        self.table.setRowCount(len(prods))
        for r, p in enumerate(prods):
            self.table.setItem(r, 0, QTableWidgetItem(p.nombre))
            self.table.setItem(r, 1, QTableWidgetItem(
                cats.get(p.categoria_id, "—")))
            UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
            tiene = p.id in con_receta
            if tiene:
                items_r = Receta.get_por_producto(p.id)
                resumen = ", ".join(
                    
                    f"{ri.insumo_nombre} {ri.cantidad:.3g} {'unidades' if ri.insumo_unidad in UNIDADES_A_UNIDADES else ri.insumo_unidad}"
                    for ri in items_r)
                ri_item = QTableWidgetItem(f"✅  {resumen}")
                ri_item.setForeground(QColor(C_GREEN))
            else:
                ri_item = QTableWidgetItem("🔲  Sin receta")
                ri_item.setForeground(QColor(C_MUTED))
            self.table.setItem(r, 2, ri_item)

            """ aw = QWidget(); aw.setStyleSheet("background:transparent;")
            al = QHBoxLayout(aw); al.setContentsMargins(4, 3, 4, 3); al.setSpacing(4)
            lbl = "✏️ Editar" if tiene else "➕ Crear receta"
            eb  = _btn(lbl, C_BLUE if tiene else C_PRIMARY, small=True)
            eb.clicked.connect(partial(self._editar, p))
            al.addWidget(eb)
            # Botón calcular costo — solo visible para admin y si tiene receta
            if self._es_admin and tiene:
                cb = _btn("💰", C_AMBER, small=True); cb.setFixedWidth(30)
                cb.setToolTip("Calcular precio de venta sugerido")
                cb.clicked.connect(partial(self._calcular_costo, p))
                al.addWidget(cb)
            self.table.setCellWidget(r, 3, aw) """


            # Acciones
            aw = QWidget()
            aw.setStyleSheet("background: transparent;")
            al = QHBoxLayout(aw)
            al.setContentsMargins(2, 0, 2, 0)
            al.setSpacing(2)
            al.setAlignment(Qt.AlignmentFlag.AlignCenter)

            tiene_dos_botones = self._es_admin and tiene
            eb_w, eb = _make_btn_icono("✏️" if tiene else "➕", "#27ae60", "#2ecc71", "#1e8449",
                            ancho=56 if not tiene_dos_botones else 28)
            eb.setCursor(Qt.CursorShape.PointingHandCursor)
            eb.clicked.connect(partial(self._editar, p))
            al.addWidget(eb_w)

            if self._es_admin and tiene:
                cb_w, cb = _make_btn_icono("💰", "#e67e22", "#f39c12", "#ca6f1e")
                cb.setCursor(Qt.CursorShape.PointingHandCursor)
                cb.clicked.connect(partial(self._calcular_costo, p))
                al.addWidget(cb_w)

            self.table.setCellWidget(r, 3, aw)
            #self.table.setColumnWidth(7, 190)  # columna Acciones más ancha
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(42)

            

    def _editar(self, producto):
        dlg = RecetaDialog(producto, self)
        if dlg.exec():
            ok = Receta.set_receta(producto.id, dlg.get_data())
            if ok: self.load_data()
            else: QMessageBox.warning(
                self, "Error", "No se pudo guardar la receta.")

    def _calcular_costo(self, producto):
        dlg = CostoDialog(producto, self)
        dlg.exec()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Compras
# ─────────────────────────────────────────────────────────────────────────────

class ComprasTab(QWidget):
    def __init__(self):
        self._es_admin       = False
        self._usuario_id_own = None
        super().__init__()
        self._build()
        self._init_usuarios()
        self.load_data()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10); lay.setContentsMargins(0, 8, 0, 0)

        bar, bl = _filter_bar()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Buscar compra…")
        self.search.setStyleSheet(_LE); self.search.setFixedWidth(180)
        self.search.textChanged.connect(self.load_data); bl.addWidget(self.search)

        bl.addWidget(_sep_v())
        bl.addWidget(QLabel("Desde:"))
        self.desde = QDateEdit(QDate.currentDate().addMonths(-1))
        self.desde.setCalendarPopup(True); self.desde.setStyleSheet(_CB)
        self.desde.dateChanged.connect(self.load_data); bl.addWidget(self.desde)

        bl.addWidget(QLabel("Hasta:"))
        self.hasta = QDateEdit(QDate.currentDate())
        self.hasta.setCalendarPopup(True); self.hasta.setStyleSheet(_CB)
        self.hasta.dateChanged.connect(self.load_data); bl.addWidget(self.hasta)

        bl.addWidget(_sep_v())
        bl.addWidget(QLabel("Usuario:"))
        self.usuario_cb = QComboBox(); self.usuario_cb.setStyleSheet(_CB)
        self.usuario_cb.setFixedWidth(140)
        self.usuario_cb.currentIndexChanged.connect(self.load_data)
        bl.addWidget(self.usuario_cb)

        bl.addStretch()
        limpiar = _btn_ghost("↺"); limpiar.setFixedWidth(32)
        limpiar.setToolTip("Limpiar filtros")
        limpiar.clicked.connect(self._limpiar); bl.addWidget(limpiar)
        nb = _btn("➕ Nueva Compra", C_PRIMARY, small=True)
        nb.clicked.connect(self._nueva); bl.addWidget(nb)
        rf = _btn_ghost("🔄"); rf.setFixedWidth(36)
        rf.clicked.connect(self.load_data); bl.addWidget(rf)
        lay.addWidget(bar)

        self.table = _make_table(
            6,
            ["Compra / Referencia", "Proveedor", "Ítems",
             "Total Bs", "Usuario", "Fecha"],
            col_widths=[(1, 110), (2, 50), (3, 85), (4, 100)],
            stretch_cols=[0, 5])
        self.table.doubleClicked.connect(self._ver_detalle)
        lay.addWidget(self.table)

        hint = QLabel(
            "💡 Doble clic en una fila para ver el detalle completo.")
        hint.setStyleSheet(f"font-size:10px; color:{C_MUTED}; padding:2px 0;")
        lay.addWidget(hint)

    def _init_usuarios(self):
        u = get_current_user()
        self._es_admin       = u.is_admin() if u else False
        self._usuario_id_own = u.id if u else None
        if self._es_admin:
            self.usuario_cb.addItem("Todos", None)
            for usr in User.get_all():
                self.usuario_cb.addItem(f"👤 {usr.nombre}", usr.id)
        else:
            self.usuario_cb.addItem(
                f"👤 {u.nombre if u else '—'}", self._usuario_id_own)
            self.usuario_cb.setEnabled(False)

    def _limpiar(self):
        self.search.clear()
        self.desde.setDate(QDate.currentDate().addMonths(-1))
        self.hasta.setDate(QDate.currentDate())
        if self._es_admin: self.usuario_cb.setCurrentIndex(0)
        self.load_data()

    def load_data(self):
        term  = self.search.text().strip().lower()
        desde = self.desde.date().toString("yyyy-MM-dd")
        hasta = self.hasta.date().toString("yyyy-MM-dd") + " 23:59:59"
        uid   = self.usuario_cb.currentData()

        q = """SELECT p.*, u.nombre as usuario_nombre
               FROM paquetes_insumos p
               LEFT JOIN usuarios u ON p.usuario_id = u.id
               WHERE p.fecha_registro >= ? AND p.fecha_registro <= ?"""
        params = [desde, hasta]

        # Cajero solo ve sus propias compras
        if uid:
            q += " AND p.usuario_id = ?"; params.append(uid)
        elif not self._es_admin:
            q += " AND p.usuario_id = ?"; params.append(self._usuario_id_own)

        q += " ORDER BY p.fecha_registro DESC LIMIT 200"
        rows = db.fetch_all(q, tuple(params))
        if term:
            rows = [r for r in rows
                    if term in (r["nombre"] or "").lower()
                    or term in (r["proveedor"] or "").lower()]
        self._rows = [dict(r) for r in rows]
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(row["nombre"] or "—"))
            self.table.setItem(r, 1, QTableWidgetItem(row["proveedor"] or "—"))
            items = json.loads(row["items_json"] or "[]")
            ni = QTableWidgetItem(f"{len(items)}")
            ni.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, ni)
            costo = row["costo_total"] or 0
            ci = QTableWidgetItem(f"Bs {costo:.2f}")
            ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            ci.setForeground(QColor(C_GREEN if costo > 0 else C_MUTED))
            self.table.setItem(r, 3, ci)
            self.table.setItem(r, 4, QTableWidgetItem(
                row["usuario_nombre"] or "—"))
            fecha = (row["fecha_registro"] or "")[:16].replace("T", " ")
            self.table.setItem(r, 5, QTableWidgetItem(fecha))

    def _nueva(self):
        dlg = NuevaCompraDialog(self)
        if not dlg.exec(): return
        data  = dlg.get_data()
        u     = get_current_user()
        uid   = u.id if u else None
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        items_json  = []
        costo_total = 0.0
        for it in data["items"]:
            ins        = it["insumo"]
            fresh      = Insumo.get_by_id(ins.id)
            precio_u   = it["precio_unit"]
            subtotal   = precio_u * it["cantidad"]
            costo_total += subtotal

            fresh.registrar_movimiento(
                "entrada", it["cantidad"],
                motivo=(f"Compra: {data['nombre']}"
                        + (f" — {it['nota_env']}" if it.get("nota_env") else "")),
                usuario_id=uid)

            if precio_u > 0:
                Insumo.update(ins.id, costo_unitario=precio_u)

            items_json.append({
                "insumo_id":   ins.id,
                "insumo":      ins.nombre,
                "cantidad":    it["cantidad"],
                "unidad":      ins.unidad,
                "precio_unit": precio_u,
                "subtotal":    subtotal,
                "nota_env":    it.get("nota_env"),
            })

        db.execute_query(
            """INSERT INTO paquetes_insumos
               (nombre, proveedor, nota, items_json, costo_total, usuario_id, fecha_registro)
               VALUES (?,?,?,?,?,?,?)""",
            (data["nombre"], data["proveedor"], data["nota"],
             json.dumps(items_json, ensure_ascii=False),
             costo_total, uid, ahora))

        QMessageBox.information(
            self, "Compra registrada",
            f"✅ Compra registrada correctamente.\n"
            f"Total: Bs {costo_total:.2f}  ·  "
            f"{len(data['items'])} insumo(s) actualizado(s).")
        self.load_data()

    def _ver_detalle(self):
        idx = self.table.currentRow()
        if idx < 0 or idx >= len(self._rows): return
        row   = self._rows[idx]
        items = json.loads(row["items_json"] or "[]")

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detalle — {row['nombre']}")
        dlg.setMinimumWidth(480)
        dlg.setStyleSheet(
            f"QDialog {{ background:{C_BG}; }}"
            f"QLabel {{ background:transparent; }}")

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(22, 20, 22, 20); lay.setSpacing(10)

        title = QLabel(f"🧺  {row['nombre']}")
        title.setStyleSheet(f"font-size:15px; font-weight:700; color:{C_TEXT};")
        lay.addWidget(title)

        meta = QLabel(
            f"Proveedor: <b>{row['proveedor'] or '—'}</b>  ·  "
            f"Usuario: <b>{row['usuario_nombre'] or '—'}</b>  ·  "
            f"Fecha: <b>{(row['fecha_registro'] or '')[:16]}</b>")
        meta.setTextFormat(Qt.TextFormat.RichText)
        meta.setStyleSheet(f"font-size:11px; color:{C_MUTED};")
        meta.setWordWrap(True); lay.addWidget(meta)

        costo = row["costo_total"] or 0
        total_lbl = QLabel(f"Total compra: Bs {costo:.2f}")
        total_lbl.setStyleSheet(
            f"font-size:14px; font-weight:700; color:{C_GREEN};")
        lay.addWidget(total_lbl); lay.addWidget(_sep())

        tbl = _make_table(
            4, ["Insumo / Envase", "Cantidad", "Precio unit.", "Subtotal", ""],
            col_widths=[(1, 110), (3, 80)],
            stretch_cols=[0,2])
        tbl.setFixedHeight(min(46 + len(items) * 34, 600))
        tbl.setRowCount(len(items))
        for r, it in enumerate(items):
            UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
            unidad = it.get("unidad", "")
            unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
            nombre = it.get("insumo", "—")
            if it.get("nota_env"):
                nombre += f"\n({it['nota_env']})"
            tbl.setItem(r, 0, QTableWidgetItem(nombre))

            cant = it.get("cantidad", 0)
            uni  = unidad_txt
            ci = QTableWidgetItem(f"{cant:.3g} {uni}")
            ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tbl.setItem(r, 1, ci)

            pu = it.get("precio_unit", 0)
            pi = QTableWidgetItem(
                f"Bs {pu:.2f}/{uni}" if pu else "—")
            pi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tbl.setItem(r, 2, pi)

            sub = it.get("subtotal") or (pu * cant)
            si = QTableWidgetItem(f"Bs {sub:.2f}" if sub else "—")
            si.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            si.setForeground(QColor(C_AMBER))
            tbl.setItem(r, 3, si)

        lay.addWidget(tbl)

        if row.get("nota"):
            nl = QLabel(f"📝  {row['nota']}")
            nl.setStyleSheet(f"font-size:11px; color:{C_MUTED};")
            nl.setWordWrap(True); lay.addWidget(nl)

        ok = _btn("Cerrar", C_MUTED); ok.clicked.connect(dlg.accept)
        lay.addWidget(ok, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — Historial  (Ventas | Insumos | Compras) con panel lateral
# ─────────────────────────────────────────────────────────────────────────────

class HistorialTab(QWidget):
    def __init__(self):
        self._es_admin        = False
        self._usuario_id_own  = None
        self._ventas_rows     = []
        self._insumos_rows    = []
        self._paquetes_rows   = []
        super().__init__()
        self._build()
        self._init_usuarios()
        self.load_data()

    def _build(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 8, 0, 0); outer.setSpacing(10)

        # ── Izquierda ─────────────────────────────────────────────────────────
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0); left_lay.setSpacing(10)

        bar, bl = _filter_bar()
        bl.addWidget(QLabel("Ver:"))
        self.vista = QComboBox()
        self.vista.addItem("🛒 Ventas (por producto)", "ventas")
        self.vista.addItem("⚗️ Insumos",               "insumos")
        self.vista.addItem("🧺 Compras",               "compras")
        self.vista.setStyleSheet(_CB); self.vista.setFixedWidth(185)
        self.vista.currentIndexChanged.connect(self._on_vista)
        bl.addWidget(self.vista); bl.addWidget(_sep_v())

        bl.addWidget(QLabel("Desde:"))
        self.desde = QDateEdit(QDate.currentDate().addMonths(-1))
        self.desde.setCalendarPopup(True); self.desde.setStyleSheet(_CB)
        self.desde.dateChanged.connect(self.load_data); bl.addWidget(self.desde)

        bl.addWidget(QLabel("Hasta:"))
        self.hasta = QDateEdit(QDate.currentDate())
        self.hasta.setCalendarPopup(True); self.hasta.setStyleSheet(_CB)
        self.hasta.dateChanged.connect(self.load_data); bl.addWidget(self.hasta)

        bl.addWidget(_sep_v()); bl.addWidget(QLabel("Usuario:"))
        self.usuario_cb = QComboBox(); self.usuario_cb.setStyleSheet(_CB)
        self.usuario_cb.setFixedWidth(140)
        self.usuario_cb.currentIndexChanged.connect(self.load_data)
        bl.addWidget(self.usuario_cb)

        bl.addStretch()
        limpiar = _btn_ghost("↺"); limpiar.setFixedWidth(32)
        limpiar.setToolTip("Limpiar filtros")
        limpiar.clicked.connect(self._limpiar); bl.addWidget(limpiar)
        """ rf = _btn_ghost("🔄"); rf.setFixedWidth(32)
        rf.clicked.connect(self.load_data); bl.addWidget(rf) """
        left_lay.addWidget(bar)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(_TBL)
        self.table.itemSelectionChanged.connect(self._on_select)
        left_lay.addWidget(self.table)
        outer.addWidget(left, stretch=3)

        # ── Panel derecho ─────────────────────────────────────────────────────
        self._detail_frame = QFrame()
        self._detail_frame.setFixedWidth(270)
        self._detail_frame.setStyleSheet(
            f"QFrame {{ background:{C_WHITE}; border:1px solid {C_BORDER}; "
            f"border-radius:10px; }}"
            f"QLabel {{ background:transparent; border:none; }}")
        df_lay = QVBoxLayout(self._detail_frame)
        df_lay.setContentsMargins(0, 0, 0, 0); df_lay.setSpacing(0)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setStyleSheet(
            "QScrollBar:vertical{width:4px;background:transparent;}"
            "QScrollBar::handle:vertical{background:#CBD5E1;border-radius:2px;}"
            "QScrollBar::add-line:vertical,"
            "QScrollBar::sub-line:vertical{height:0;}")

        self._detail_inner = QWidget()
        self._detail_inner.setStyleSheet("background:transparent;")
        self._detail_lay = QVBoxLayout(self._detail_inner)
        self._detail_lay.setContentsMargins(16, 16, 16, 16)
        self._detail_lay.setSpacing(6)
        self._detail_lay.addWidget(self._placeholder())
        self._detail_lay.addStretch()

        scroll.setWidget(self._detail_inner)
        df_lay.addWidget(scroll)
        outer.addWidget(self._detail_frame, stretch=0)

    # ── helpers panel ─────────────────────────────────────────────────────────

    def _placeholder(self):
        lbl = QLabel("Selecciona una fila\npara ver el detalle")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"font-size:11px; color:{C_MUTED}; padding:20px;")
        lbl.setWordWrap(True)
        return lbl

    def _clear_detail(self):
        while self._detail_lay.count():
            item = self._detail_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _det_title(self, text):
        l = QLabel(text); l.setWordWrap(True)
        l.setStyleSheet(f"font-size:13px; font-weight:700; color:{C_TEXT};")
        return l

    def _det_kv(self, key, val, val_color=None):
        row = QHBoxLayout(); row.setSpacing(4)
        k = QLabel(key); k.setStyleSheet(f"font-size:10px; color:{C_MUTED};")
        v = QLabel(str(val)); v.setWordWrap(True)
        v.setStyleSheet(
            f"font-size:11px; font-weight:600; color:{val_color or C_TEXT};")
        row.addWidget(k); row.addStretch(); row.addWidget(v)
        w = QWidget(); w.setStyleSheet("background:transparent;")
        w.setLayout(row)
        return w

    def _det_sep(self):
        s = QFrame(); s.setFrameShape(QFrame.Shape.HLine)
        s.setStyleSheet(f"background:{C_BORDER}; max-height:1px; margin:4px 0;")
        return s

    def _det_insumo_card(self, nombre, cantidad_str, detalle_str,
                          color_cant=C_RED):
        iw = QWidget()
        iw.setStyleSheet("background:#F8FAFC; border-radius:6px;")
        il = QVBoxLayout(iw); il.setContentsMargins(8, 6, 8, 6); il.setSpacing(2)
        top = QHBoxLayout()
        nm = QLabel(nombre)
        nm.setStyleSheet(f"font-size:11px; font-weight:600; color:{C_TEXT};")
        ct = QLabel(cantidad_str)
        ct.setStyleSheet(f"font-size:11px; font-weight:700; color:{color_cant};")
        top.addWidget(nm); top.addStretch(); top.addWidget(ct)
        sub = QLabel(detalle_str)
        sub.setStyleSheet(f"font-size:10px; color:{C_MUTED};")
        il.addLayout(top); il.addWidget(sub)
        return iw

    # ── inicialización ────────────────────────────────────────────────────────

    def _init_usuarios(self):
        u = get_current_user()
        self._es_admin       = u.is_admin() if u else False
        self._usuario_id_own = u.id if u else None
        if self._es_admin:
            self.usuario_cb.addItem("Todos", None)
            for usr in User.get_all():
                self.usuario_cb.addItem(f"👤 {usr.nombre}", usr.id)
        else:
            self.usuario_cb.addItem(
                f"👤 {u.nombre if u else '—'}", self._usuario_id_own)
            self.usuario_cb.setEnabled(False)

    def _on_vista(self):
        self._clear_detail()
        self._detail_lay.addWidget(self._placeholder())
        self._detail_lay.addStretch()
        self.load_data()

    def _limpiar(self):
        self.desde.setDate(QDate.currentDate().addMonths(-1))
        self.hasta.setDate(QDate.currentDate())
        if self._es_admin: self.usuario_cb.setCurrentIndex(0)
        self.load_data()

    def _filtros(self):
        desde = self.desde.date().toString("yyyy-MM-dd")
        hasta = self.hasta.date().toString("yyyy-MM-dd") + " 23:59:59"
        uid   = self.usuario_cb.currentData()
        return desde, hasta, uid

    # ── carga de datos ────────────────────────────────────────────────────────

    def load_data(self):
        vista          = self.vista.currentData()
        desde, hasta, uid = self._filtros()
        self._clear_detail()
        self._detail_lay.addWidget(self._placeholder())
        self._detail_lay.addStretch()

        if vista == "ventas":   self._load_ventas(desde, hasta, uid)
        elif vista == "insumos": self._load_insumos(desde, hasta, uid)
        else:                    self._load_compras(desde, hasta)

    def _load_ventas(self, desde, hasta, uid):
        q = """
            SELECT dv.producto_id,
                   p.nombre   AS producto,
                   SUM(dv.cantidad) AS total_uds,
                   SUM(dv.subtotal) AS total_bs,
                   u.nombre   AS usuario,
                   MAX(v.fecha_venta) AS ultima_venta
            FROM detalle_ventas dv
            JOIN ventas    v ON dv.venta_id    = v.id
            JOIN productos p ON dv.producto_id = p.id
            LEFT JOIN usuarios u ON v.usuario_id = u.id
            WHERE DATE(v.fecha_venta) >= ? AND DATE(v.fecha_venta) <= ?
              AND v.estado = 'completada'
        """
        params = [desde, hasta[:10]]
        if uid:
            q += " AND v.usuario_id = ?"; params.append(uid)
        elif not self._es_admin:
            q += " AND v.usuario_id = ?"; params.append(self._usuario_id_own)
        q += " GROUP BY dv.producto_id, p.nombre ORDER BY total_uds DESC"

        rows = db.fetch_all(q, tuple(params))
        self._ventas_rows = [dict(r) for r in rows]

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Producto", "Unidades vendidas", "Total Bs",
             "Usuario", "Última venta"])
        self.table.setRowCount(len(self._ventas_rows))
        for r, m in enumerate(self._ventas_rows):
            self.table.setItem(r, 0, QTableWidgetItem(m["producto"]))
            ud = QTableWidgetItem(str(int(m["total_uds"])))
            ud.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 1, ud)
            bs = QTableWidgetItem(f"Bs {m['total_bs']:.2f}")
            bs.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, bs)
            self.table.setItem(r, 3, QTableWidgetItem(m.get("usuario") or "—"))
            fecha = (m["ultima_venta"] or "")[:16].replace("T", " ")
            self.table.setItem(r, 4, QTableWidgetItem(fecha))

    def _load_insumos(self, desde, hasta, uid):
        fuid = uid if uid else (None if self._es_admin else self._usuario_id_own)
        movs = get_todos_movimientos_insumos(
            desde=desde, hasta=hasta, usuario_id=fuid)
        self._insumos_rows = movs

        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Insumo", "Tipo", "Cantidad", "Stock ant.",
             "Stock nuevo", "Usuario", "Fecha"])
        self.table.setRowCount(len(movs))
        for r, m in enumerate(movs):
            UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
            unidad = m.get("unidad", "")
            unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
            self.table.setItem(r, 0, QTableWidgetItem(m["insumo"]))
            ti = QTableWidgetItem(
                f"{TIPO_ICONO.get(m['tipo'],'')} {m['tipo'].title()}")
            ti.setForeground(QColor(TIPO_COLOR.get(m["tipo"], C_MUTED)))
            self.table.setItem(r, 1, ti)
            cant = m["cantidad"]
            ci = QTableWidgetItem(f"{abs(cant):.3g} {unidad_txt}")
            ci.setForeground(QColor(C_GREEN if cant > 0 else C_RED))
            ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, ci)
            self.table.setItem(r, 3, QTableWidgetItem(
                f"{m['stock_anterior']:.2f}"))
            nv = QTableWidgetItem(f"{m['stock_nuevo']:.2f}")
            nv.setForeground(QColor(
                C_RED if m["stock_nuevo"] <= 0 else C_TEXT))
            self.table.setItem(r, 4, nv)
            self.table.setItem(r, 5, QTableWidgetItem(
                m.get("usuario") or "—"))
            self.table.setItem(r, 6, QTableWidgetItem(
                (m["fecha"] or "")[:16].replace("T", " ")))

    def _load_compras(self, desde, hasta):
        rows = db.fetch_all(
            """SELECT p.*, u.nombre as usuario_nombre
               FROM paquetes_insumos p
               LEFT JOIN usuarios u ON p.usuario_id = u.id
               WHERE DATE(p.fecha_registro) >= ?
                 AND DATE(p.fecha_registro) <= ?
               ORDER BY p.fecha_registro DESC""",
            (desde, hasta[:10]))
        self._paquetes_rows = [dict(r) for r in rows]

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Compra / Referencia", "Proveedor", "Total Bs",
             "Usuario", "Fecha"])
        self.table.setRowCount(len(self._paquetes_rows))
        for r, row in enumerate(self._paquetes_rows):
            self.table.setItem(r, 0, QTableWidgetItem(row["nombre"] or "—"))
            self.table.setItem(r, 1, QTableWidgetItem(row["proveedor"] or "—"))
            costo = row.get("costo_total") or 0
            ci = QTableWidgetItem(f"Bs {costo:.2f}" if costo else "—")
            ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            ci.setForeground(QColor(C_GREEN if costo > 0 else C_MUTED))
            self.table.setItem(r, 2, ci)
            self.table.setItem(r, 3, QTableWidgetItem(
                row["usuario_nombre"] or "—"))
            fecha = (row["fecha_registro"] or "")[:16].replace("T", " ")
            self.table.setItem(r, 4, QTableWidgetItem(fecha))

    # ── panel derecho ─────────────────────────────────────────────────────────

    def _on_select(self):
        row   = self.table.currentRow()
        if row < 0: return
        vista = self.vista.currentData()
        if vista == "ventas":    self._show_venta(row)
        elif vista == "insumos": self._show_insumo(row)
        else:                    self._show_compra(row)

    def _show_venta(self, row):
        if row >= len(self._ventas_rows): 
            return

        m = self._ventas_rows[row]
        self._clear_detail()
        lay = self._detail_lay

        lay.addWidget(self._det_title(f"🛒 {m['producto']}"))
        lay.addWidget(self._det_sep())

        lay.addWidget(self._det_kv("Unidades vendidas", int(m["total_uds"])))
        lay.addWidget(self._det_kv(
            "Total recaudado", f"Bs {m['total_bs']:.2f}", C_GREEN))

        lay.addWidget(self._det_kv("Usuario", m.get("usuario") or "—"))

        lay.addWidget(self._det_kv(
            "Última venta",
            (m["ultima_venta"] or "")[:16].replace("T", " "))
        )

        receta = Receta.get_por_producto(m["producto_id"])

        if receta:
            lay.addWidget(self._det_sep())

            cap = QLabel("INSUMOS CONSUMIDOS")
            cap.setStyleSheet(
                f"font-size:9px; font-weight:700; color:{C_MUTED}; "
                f"letter-spacing:0.8px;"
            )
            lay.addWidget(cap)

            uds = int(m["total_uds"])
            UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}

            for ri in receta:
                total_c = ri.cantidad * uds

                unidad = ri.insumo_unidad
                unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad

                lay.addWidget(self._det_insumo_card(
                    ri.insumo_nombre,
                    f"{total_c:.3g} {unidad_txt}",
                    f"{ri.cantidad:.3g} {unidad_txt} × {uds} uds",
                    C_RED
                ))

        else:
            lay.addWidget(self._det_sep())

            nl = QLabel("Sin receta — no descuenta insumos")
            nl.setStyleSheet(
                f"font-size:10px; color:{C_MUTED}; padding:4px 0;"
            )
            lay.addWidget(nl)

        lay.addStretch()

    def _show_insumo(self, row):
        if row >= len(self._insumos_rows): return
        m     = self._insumos_rows[row]
        self._clear_detail()
        lay   = self._detail_lay
        tipo  = m["tipo"]
        icono = TIPO_ICONO.get(tipo, "")
        color = TIPO_COLOR.get(tipo, C_MUTED)
        UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
        unidad = m.get("unidad", "")
        unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad


        lay.addWidget(self._det_title(f"{icono} {m['insumo']}"))
        lay.addWidget(self._det_sep())
        ti = QLabel(f"{icono}  {tipo.title()}")
        ti.setStyleSheet(f"font-size:12px; font-weight:700; color:{color};")
        lay.addWidget(ti)
        lay.addWidget(self._det_kv(
            "Cantidad",
            f"{abs(m['cantidad']):.3g} {unidad_txt}",
            C_GREEN if m["cantidad"] > 0 else C_RED))
        lay.addWidget(self._det_kv(
            "Stock anterior",
            f"{m['stock_anterior']:.2f} {unidad_txt}"))
        lay.addWidget(self._det_kv(
            "Stock nuevo",
            f"{m['stock_nuevo']:.2f} {unidad_txt}",
            C_RED if m["stock_nuevo"] <= 0 else C_GREEN))
        if m.get("motivo"):
            lay.addWidget(self._det_sep())
            ml = QLabel(f"📝  {m['motivo']}")
            ml.setStyleSheet(f"font-size:11px; color:{C_MUTED};")
            ml.setWordWrap(True); lay.addWidget(ml)
        lay.addWidget(self._det_sep())
        lay.addWidget(self._det_kv("Usuario", m.get("usuario") or "—"))
        lay.addWidget(self._det_kv(
            "Fecha", (m["fecha"] or "")[:16].replace("T", " ")))
        lay.addStretch()

    def _show_compra(self, row):
        if row >= len(self._paquetes_rows): return
        data  = self._paquetes_rows[row]
        items = json.loads(data.get("items_json") or "[]")
        self._clear_detail()
        lay   = self._detail_lay

        lay.addWidget(self._det_title(f"🧺 {data['nombre']}"))
        lay.addWidget(self._det_sep())
        lay.addWidget(self._det_kv("Proveedor", data.get("proveedor") or "—"))
        lay.addWidget(self._det_kv("Usuario",   data.get("usuario_nombre") or "—"))
        lay.addWidget(self._det_kv(
            "Fecha", (data.get("fecha_registro") or "")[:16]))

        costo = data.get("costo_total") or 0
        lay.addWidget(self._det_kv(
            "TOTAL COMPRA",
            f"Bs {costo:.2f}",
            C_GREEN if costo > 0 else C_MUTED))

        if items:
            lay.addWidget(self._det_sep())
            cap = QLabel("DESGLOSE POR INSUMO")
            cap.setStyleSheet(
                f"font-size:9px; font-weight:700; color:{C_MUTED}; "
                f"letter-spacing:0.8px;")
            lay.addWidget(cap)
            for it in items:
                precio  = it.get("precio_unit", 0) or 0
                cant    = it.get("cantidad", 0) or 0
                subtotal = it.get("subtotal") or (precio * cant)
                det_txt = (
    f"{cant:.3g} {'unidades' if it.get('unidad') in ['Paquete','Caja','Bolsa'] else it.get('unidad','')}"
).strip() + (f"  ×  Bs {precio:.4f}" if precio else "")
                
                lay.addWidget(self._det_insumo_card(
                    it.get("insumo", "—"),
                    f"Bs {subtotal:.2f}" if subtotal else "—",
                    det_txt,
                    C_AMBER))

        if data.get("nota"):
            lay.addWidget(self._det_sep())
            nl = QLabel(f"📝  {data['nota']}")
            nl.setStyleSheet(f"font-size:11px; color:{C_MUTED};")
            nl.setWordWrap(True); lay.addWidget(nl)

        lay.addStretch()


# ─────────────────────────────────────────────────────────────────────────────
# WIDGET PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class InventoryWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 22, 28, 22); lay.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("📦  Inventario")
        title.setStyleSheet(f"font-size:20px; font-weight:700; color:{C_TEXT};")
        hdr.addWidget(title); hdr.addStretch()

        bajos = len(Insumo.get_stock_bajo())
        if bajos > 0:
            alerta = QLabel(f"⚠️  {bajos} insumo(s) con stock bajo")
            alerta.setStyleSheet(f"""
                background:#FEF3C7; color:#92400E; border:1px solid #FCD34D;
                border-radius:7px; padding:4px 14px;
                font-size:11px; font-weight:600;
            """)
            hdr.addWidget(alerta)
        lay.addLayout(hdr)

        sub = QLabel(
            "Gestión de insumos, recetas, compras e historial de movimientos.")
        sub.setStyleSheet(f"font-size:11px; color:{C_MUTED}; margin-top:-4px;")
        lay.addWidget(sub)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border:1px solid {C_BORDER}; border-radius:10px;
                background:{C_WHITE}; padding:16px; }}
            QTabBar::tab {{
                padding:7px 22px; font-size:11px; font-weight:600;
                color:{C_MUTED}; border:none; margin-right:3px; }}
            QTabBar::tab:selected {{
                color:{C_PRIMARY}; border-bottom:2px solid {C_PRIMARY}; }}
            QTabBar::tab:hover:!selected {{ color:{C_TEXT}; }}
        """)
        tabs.addTab(InsumosTab(),   "⚗️  Insumos")
        tabs.addTab(RecetasTab(),   "📋  Recetas")
        tabs.addTab(ComprasTab(),   "🧺  Compras")
        tabs.addTab(HistorialTab(), "📊  Historial")
        lay.addWidget(tabs)