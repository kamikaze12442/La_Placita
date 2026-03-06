"""
Inventory Widget
Gestión completa de inventario: productos, insumos e historial de movimientos.
Accesible para admin y cajero. Todos los cambios quedan registrados con usuario y fecha.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox, QComboBox, QHeaderView,
    QFrame, QDoubleSpinBox, QSpinBox, QScrollArea, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from models.inventory import (
    registrar_movimiento, get_todos_movimientos,
    get_productos_stock_bajo, Insumo, get_todos_movimientos_insumos
)
from models.product import Product
from models.user import get_current_user
from database.connection import db


# ──────────────────────────────────────────────────────────────────────────────
# Helpers visuales
# ──────────────────────────────────────────────────────────────────────────────

TIPO_COLOR = {
    'entrada':  '#10B981',  # verde
    'venta':    '#3B82F6',  # azul
    'ajuste':   '#F59E0B',  # amarillo
    'merma':    '#EF4444',  # rojo
    'consumo':  '#8B5CF6',  # morado
}

TIPO_ICONO = {
    'entrada': '📥', 'venta': '🛒', 'ajuste': '✏️',
    'merma': '🗑️', 'consumo': '⚗️'
}


def _badge(text: str, color: str) -> QLabel:
    lbl = QLabel(f" {TIPO_ICONO.get(text, '')} {text.title()} ")
    lbl.setStyleSheet(f"""
        background-color: {color}22;
        color: {color};
        border: 1px solid {color}55;
        border-radius: 10px;
        padding: 2px 8px;
        font-weight: 600;
        font-size: 12px;
    """)
    return lbl


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Ajuste de stock de producto
# ──────────────────────────────────────────────────────────────────────────────

class AjusteStockDialog(QDialog):
    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle(f"Ajustar Stock — {product.nombre}")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(f"Stock actual: <b>{self.product.stock} unidades</b>")
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("📥 Entrada (suma stock)",  'entrada')
        self.tipo_combo.addItem("✏️ Ajuste manual",         'ajuste')
        self.tipo_combo.addItem("🗑️ Merma / Pérdida",       'merma')
        form.addRow("Tipo de movimiento:*", self.tipo_combo)

        self.cantidad_spin = QSpinBox()
        self.cantidad_spin.setRange(1, 99999)
        self.cantidad_spin.setValue(1)
        form.addRow("Cantidad:*", self.cantidad_spin)

        self.motivo_input = QTextEdit()
        self.motivo_input.setPlaceholderText("Describe el motivo del ajuste...")
        self.motivo_input.setMaximumHeight(80)
        form.addRow("Motivo:", self.motivo_input)

        layout.addLayout(form)

        note = QLabel("🔒 Este movimiento quedará registrado con tu usuario y la fecha actual.")
        note.setStyleSheet("color: #6B7280; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Registrar movimiento")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        tipo     = self.tipo_combo.currentData()
        cantidad = self.cantidad_spin.value()
        motivo   = self.motivo_input.toPlainText().strip()
        # Entradas suman, merma y ajuste restan
        delta = cantidad if tipo == 'entrada' else -cantidad
        return tipo, delta, motivo or None


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Crear / Editar Insumo
# ──────────────────────────────────────────────────────────────────────────────

class InsumoDialog(QDialog):
    UNIDADES = ['kg', 'g', 'litros', 'ml', 'unidades', 'porciones', 'cajas', 'bolsas']

    def __init__(self, insumo=None, parent=None):
        super().__init__(parent)
        self.insumo = insumo
        self.setWindowTitle("Editar Insumo" if insumo else "Nuevo Insumo")
        self.setMinimumWidth(420)
        self._init_ui()
        if insumo:
            self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Ej: Leche entera")
        form.addRow("Nombre:*", self.nombre_input)

        self.categoria_input = QLineEdit()
        self.categoria_input.setPlaceholderText("Ej: Lácteos, Granos, Bebidas...")
        form.addRow("Categoría:", self.categoria_input)

        self.unidad_combo = QComboBox()
        for u in self.UNIDADES:
            self.unidad_combo.addItem(u)
        form.addRow("Unidad:*", self.unidad_combo)

        self.stock_minimo_spin = QDoubleSpinBox()
        self.stock_minimo_spin.setRange(0, 99999)
        self.stock_minimo_spin.setDecimals(2)
        self.stock_minimo_spin.setSuffix("  (alerta)")
        form.addRow("Stock mínimo:*", self.stock_minimo_spin)

        self.costo_spin = QDoubleSpinBox()
        self.costo_spin.setRange(0, 99999)
        self.costo_spin.setDecimals(2)
        self.costo_spin.setPrefix("Bs ")
        form.addRow("Costo unitario:", self.costo_spin)

        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(70)
        self.desc_input.setPlaceholderText("Descripción opcional...")
        form.addRow("Descripción:", self.desc_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_data(self):
        self.nombre_input.setText(self.insumo.nombre)
        self.categoria_input.setText(self.insumo.categoria or "")
        idx = self.unidad_combo.findText(self.insumo.unidad)
        if idx >= 0:
            self.unidad_combo.setCurrentIndex(idx)
        self.stock_minimo_spin.setValue(self.insumo.stock_minimo)
        self.costo_spin.setValue(self.insumo.costo_unitario)
        self.desc_input.setPlainText(self.insumo.descripcion or "")

    def get_data(self):
        return {
            'nombre':         self.nombre_input.text().strip(),
            'unidad':         self.unidad_combo.currentText(),
            'categoria':      self.categoria_input.text().strip() or None,
            'stock_minimo':   self.stock_minimo_spin.value(),
            'costo_unitario': self.costo_spin.value(),
            'descripcion':    self.desc_input.toPlainText().strip() or None,
        }

    def accept(self):
        if not self.nombre_input.text().strip():
            QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
            return
        super().accept()


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Movimiento de Insumo
# ──────────────────────────────────────────────────────────────────────────────

class MovimientoInsumoDialog(QDialog):
    def __init__(self, insumo: Insumo, parent=None):
        super().__init__(parent)
        self.insumo = insumo
        self.setWindowTitle(f"Movimiento — {insumo.nombre}")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            f"Stock actual: <b>{self.insumo.stock_actual} {self.insumo.unidad}</b> &nbsp;·&nbsp; "
            f"Mínimo: <b>{self.insumo.stock_minimo} {self.insumo.unidad}</b>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("📥 Entrada (compra/recepción)", 'entrada')
        self.tipo_combo.addItem("⚗️ Consumo (uso en producción)", 'consumo')
        self.tipo_combo.addItem("✏️ Ajuste manual",               'ajuste')
        self.tipo_combo.addItem("🗑️ Merma / Pérdida",             'merma')
        form.addRow("Tipo:*", self.tipo_combo)

        self.cantidad_spin = QDoubleSpinBox()
        self.cantidad_spin.setRange(0.001, 99999)
        self.cantidad_spin.setDecimals(3)
        self.cantidad_spin.setSuffix(f"  {self.insumo.unidad}")
        form.addRow("Cantidad:*", self.cantidad_spin)

        self.motivo_input = QTextEdit()
        self.motivo_input.setPlaceholderText("Motivo del movimiento...")
        self.motivo_input.setMaximumHeight(70)
        form.addRow("Motivo:", self.motivo_input)

        layout.addLayout(form)

        note = QLabel("🔒 Registrado con tu usuario y la fecha actual.")
        note.setStyleSheet("color: #6B7280; font-size: 11px;")
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Registrar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        tipo     = self.tipo_combo.currentData()
        cantidad = self.cantidad_spin.value()
        motivo   = self.motivo_input.toPlainText().strip()
        delta    = cantidad if tipo == 'entrada' else -cantidad
        return tipo, delta, motivo or None


# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: Stock de Productos
# ──────────────────────────────────────────────────────────────────────────────

class ProductosStockTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Barra superior
        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar producto...")
        self.search_input.textChanged.connect(self.load_data)
        top.addWidget(self.search_input)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Todos los productos", None)
        self.filter_combo.addItem("⚠️ Stock bajo (≤ 5)", "bajo")
        self.filter_combo.currentIndexChanged.connect(self.load_data)
        top.addWidget(self.filter_combo)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_data)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Producto", "Categoría", "Stock actual", "Estado", "Precio", "Acción"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def load_data(self):
        term   = self.search_input.text().strip()
        filtro = self.filter_combo.currentData()

        products = Product.search(term) if term else Product.get_all()

        if filtro == "bajo":
            products = [p for p in products if p.stock <= 5]

        # Enriquecer con nombre de categoría
        cat_cache = {}
        rows = db.fetch_all("SELECT id, nombre FROM categorias")
        for r in rows:
            cat_cache[r['id']] = r['nombre']

        self.table.setRowCount(len(products))
        for row, p in enumerate(products):
            self.table.setItem(row, 0, QTableWidgetItem(p.nombre))
            self.table.setItem(row, 1, QTableWidgetItem(cat_cache.get(p.categoria_id, '—')))
            self.table.setItem(row, 2, QTableWidgetItem(str(p.stock)))
            self.table.setItem(row, 4, QTableWidgetItem(f"Bs {p.precio:.2f}"))

            # Estado visual
            if p.stock == 0:
                estado, color = "❌ Sin stock", "#EF4444"
            elif p.stock <= 5:
                estado, color = "⚠️ Stock bajo", "#F59E0B"
            else:
                estado, color = "✅ OK", "#10B981"

            estado_item = QTableWidgetItem(estado)
            estado_item.setForeground(QColor(color))
            self.table.setItem(row, 3, estado_item)

            # Botón ajustar
            btn = QPushButton("✏️ Ajustar")
            btn.setStyleSheet("padding: 4px 12px; font-size: 12px;")
            btn.clicked.connect(lambda checked=False, prod=p: self.ajustar_stock(prod))
            self.table.setCellWidget(row, 5, btn)

    def ajustar_stock(self, product):
        dialog = AjusteStockDialog(product, self)
        if dialog.exec():
            tipo, delta, motivo = dialog.get_data()
            ok = registrar_movimiento(product.id, tipo, delta, motivo)
            if ok:
                QMessageBox.information(self, "Éxito", "✅ Movimiento registrado correctamente.")
                self.load_data()
            else:
                QMessageBox.warning(self, "Error",
                    "No se pudo registrar el movimiento.\n"
                    "Verifica que el stock no quede negativo.")


# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: Insumos
# ──────────────────────────────────────────────────────────────────────────────

class InsumosTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar insumo...")
        self.search_input.textChanged.connect(self.load_data)
        top.addWidget(self.search_input)

        add_btn = QPushButton("➕ Nuevo Insumo")
        add_btn.clicked.connect(self.nuevo_insumo)
        top.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_data)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Insumo", "Categoría", "Stock actual", "Mínimo", "Unidad", "Estado", "Acciones"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def load_data(self):
        term    = self.search_input.text().strip().lower()
        insumos = Insumo.get_all()
        if term:
            insumos = [i for i in insumos if term in i.nombre.lower()]

        self.table.setRowCount(len(insumos))
        for row, ins in enumerate(insumos):
            self.table.setItem(row, 0, QTableWidgetItem(ins.nombre))
            self.table.setItem(row, 1, QTableWidgetItem(ins.categoria or '—'))
            self.table.setItem(row, 2, QTableWidgetItem(f"{ins.stock_actual:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{ins.stock_minimo:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(ins.unidad))

            if ins.stock_actual == 0:
                estado, color = "❌ Sin stock", "#EF4444"
            elif ins.stock_bajo:
                estado, color = "⚠️ Stock bajo", "#F59E0B"
            else:
                estado, color = "✅ OK", "#10B981"

            estado_item = QTableWidgetItem(estado)
            estado_item.setForeground(QColor(color))
            self.table.setItem(row, 5, estado_item)

            # Acciones
            actions = QWidget()
            a_layout = QHBoxLayout(actions)
            a_layout.setContentsMargins(2, 2, 2, 2)
            a_layout.setSpacing(4)

            mov_btn = QPushButton("📥 Movimiento")
            mov_btn.setStyleSheet("padding: 3px 8px; font-size: 11px;")
            mov_btn.clicked.connect(lambda checked=False, i=ins: self.registrar_movimiento(i))
            a_layout.addWidget(mov_btn)

            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet("padding: 3px 8px; font-size: 11px;")
            edit_btn.clicked.connect(lambda checked=False, i=ins: self.editar_insumo(i))
            a_layout.addWidget(edit_btn)

            self.table.setCellWidget(row, 6, actions)

    def nuevo_insumo(self):
        dialog = InsumoDialog(parent=self)
        if dialog.exec():
            data = dialog.get_data()
            Insumo.create(**data)
            self.load_data()

    def editar_insumo(self, insumo: Insumo):
        dialog = InsumoDialog(insumo=insumo, parent=self)
        if dialog.exec():
            data = dialog.get_data()
            Insumo.update(insumo.id, **data)
            self.load_data()

    def registrar_movimiento(self, insumo: Insumo):
        # Recargar para tener stock actualizado
        insumo = Insumo.get_by_id(insumo.id)
        dialog = MovimientoInsumoDialog(insumo, self)
        if dialog.exec():
            tipo, delta, motivo = dialog.get_data()
            ok = insumo.registrar_movimiento_insumo(tipo, delta, motivo)
            if ok:
                QMessageBox.information(self, "Éxito", "✅ Movimiento registrado correctamente.")
                self.load_data()
            else:
                QMessageBox.warning(self, "Error",
                    "No se pudo registrar el movimiento.\n"
                    "Verifica que el stock no quede negativo.")


# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: Historial de Movimientos
# ──────────────────────────────────────────────────────────────────────────────

class HistorialTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        top = QHBoxLayout()

        self.vista_combo = QComboBox()
        self.vista_combo.addItem("📦 Productos", "productos")
        self.vista_combo.addItem("⚗️ Insumos", "insumos")
        self.vista_combo.currentIndexChanged.connect(self.load_data)
        top.addWidget(QLabel("Ver:"))
        top.addWidget(self.vista_combo)
        top.addStretch()

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_data)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

    def load_data(self):
        vista = self.vista_combo.currentData()

        if vista == "productos":
            movs = get_todos_movimientos()
            self.table.setColumnCount(8)
            self.table.setHorizontalHeaderLabels(
                ["#", "Producto", "Tipo", "Cantidad", "Stock anterior", "Stock nuevo", "Usuario", "Fecha"]
            )
            self.table.setRowCount(len(movs))
            for row, m in enumerate(movs):
                self.table.setItem(row, 0, QTableWidgetItem(str(m['id'])))
                self.table.setItem(row, 1, QTableWidgetItem(m['producto']))
                tipo_item = QTableWidgetItem(f"{TIPO_ICONO.get(m['tipo'],'')} {m['tipo'].title()}")
                tipo_item.setForeground(QColor(TIPO_COLOR.get(m['tipo'], '#6B7280')))
                self.table.setItem(row, 2, tipo_item)
                self.table.setItem(row, 3, QTableWidgetItem(str(m['cantidad'])))
                self.table.setItem(row, 4, QTableWidgetItem(str(m['stock_anterior'])))
                self.table.setItem(row, 5, QTableWidgetItem(str(m['stock_nuevo'])))
                self.table.setItem(row, 6, QTableWidgetItem(m['usuario']))
                fecha = m['fecha'][:16].replace('T', ' ') if m['fecha'] else '—'
                self.table.setItem(row, 7, QTableWidgetItem(fecha))
        else:
            movs = get_todos_movimientos_insumos()
            self.table.setColumnCount(9)
            self.table.setHorizontalHeaderLabels(
                ["#", "Insumo", "Unidad", "Tipo", "Cantidad", "Stock ant.", "Stock nuevo", "Usuario", "Fecha"]
            )
            self.table.setRowCount(len(movs))
            for row, m in enumerate(movs):
                self.table.setItem(row, 0, QTableWidgetItem(str(m['id'])))
                self.table.setItem(row, 1, QTableWidgetItem(m['insumo']))
                self.table.setItem(row, 2, QTableWidgetItem(m['unidad']))
                tipo_item = QTableWidgetItem(f"{TIPO_ICONO.get(m['tipo'],'')} {m['tipo'].title()}")
                tipo_item.setForeground(QColor(TIPO_COLOR.get(m['tipo'], '#6B7280')))
                self.table.setItem(row, 3, tipo_item)
                self.table.setItem(row, 4, QTableWidgetItem(str(m['cantidad'])))
                self.table.setItem(row, 5, QTableWidgetItem(str(m['stock_anterior'])))
                self.table.setItem(row, 6, QTableWidgetItem(str(m['stock_nuevo'])))
                self.table.setItem(row, 7, QTableWidgetItem(m['usuario']))
                fecha = m['fecha'][:16].replace('T', ' ') if m['fecha'] else '—'
                self.table.setItem(row, 8, QTableWidgetItem(fecha))


# ──────────────────────────────────────────────────────────────────────────────
# WIDGET PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

class InventoryWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header con alertas
        header = QHBoxLayout()
        title = QLabel("📦 Inventario")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #1F2937;")
        header.addWidget(title)
        header.addStretch()

        # Alerta rápida de stock bajo
        bajos_prod  = len(get_productos_stock_bajo())
        bajos_insum = len(Insumo.get_stock_bajo())
        total_bajos = bajos_prod + bajos_insum

        if total_bajos > 0:
            alerta = QLabel(f"⚠️  {total_bajos} ítem(s) con stock bajo")
            alerta.setStyleSheet("""
                background-color: #FEF3C7;
                color: #92400E;
                border: 1px solid #FCD34D;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
            """)
            header.addWidget(alerta)

        layout.addLayout(header)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(ProductosStockTab(), "📦 Productos")
        tabs.addTab(InsumosTab(),        "⚗️ Insumos")
        tabs.addTab(HistorialTab(),      "📋 Historial de Movimientos")
        layout.addWidget(tabs)
