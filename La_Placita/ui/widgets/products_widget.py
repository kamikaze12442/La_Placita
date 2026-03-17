"""
Products Widget — La Placita POS
CRUD de productos + subida de imagen desde archivo local (jpg/png)
Columna "Control Stock" visible solo para admin
"""

import os, shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit,
    QHeaderView, QFrame, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QPixmap, QColor
from models.product import Product, Category
from models.user    import get_current_user

# Carpeta donde se copian las imágenes de productos
_IMG_DIR = os.path.join(
    os.path.expanduser("~"), ".restaurant_pos", "images", "productos")
os.makedirs(_IMG_DIR, exist_ok=True)


def _load_pixmap(imagen: str, w: int, h: int) -> QPixmap:
    """Carga y recorta un pixmap a w×h. Devuelve placeholder gris si falla."""
    pm = QPixmap()
    if imagen:
        pm.load(imagen)
    if pm.isNull():
        pm = QPixmap(w, h)
        pm.fill(QColor("#F1F5F9"))
        return pm
    pm = pm.scaled(w, h,
                   Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                   Qt.TransformationMode.SmoothTransformation)
    if pm.width() > w or pm.height() > h:
        pm = pm.copy((pm.width() - w) // 2, (pm.height() - h) // 2, w, h)
    return pm


# ─────────────────────────────────────────────────────────────────────────────
# Selector de imagen
# ─────────────────────────────────────────────────────────────────────────────

class ImagePickerWidget(QWidget):
    """
    Preview 120×120 + botones  📁 Subir imagen  /  🗑 Quitar
    """
    W, H = 120, 120

    def __init__(self, imagen_actual: str = None, read_only: bool = False, parent=None):
        super().__init__(parent)
        self._imagen = imagen_actual
        self._read_only = read_only
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Preview
        self._preview = QLabel()
        self._preview.setFixedSize(self.W, self.H)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._refresh_preview()
        lay.addWidget(self._preview, alignment=Qt.AlignmentFlag.AlignCenter)

        # Botones
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_upload = QPushButton("📁  Subir imagen")
        self._btn_upload.setStyleSheet("""
            QPushButton {
                background: #3B82F6; color: white;
                border: none; border-radius: 7px;
                padding: 6px 14px; font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background: #2563EB; }
            QPushButton:disabled { background: #9CA3AF; }
        """)
        self._btn_upload.clicked.connect(self._pick_file)
        self._btn_upload.setEnabled(not self._read_only)

        self._btn_del = QPushButton("🗑")
        self._btn_del.setStyleSheet("""
            QPushButton {
                background: #FEE2E2; color: #EF4444;
                border: none; border-radius: 7px;
                padding: 6px 10px; font-size: 11px; font-weight: 700;
            }
            QPushButton:hover { background: #EF4444; color: white; }
            QPushButton:disabled { background: #E5E7EB; color: #9CA3AF; }
        """)
        self._btn_del.clicked.connect(self._remove)
        self._btn_del.setVisible(bool(self._imagen))
        self._btn_del.setEnabled(not self._read_only)

        btn_row.addWidget(self._btn_upload)
        btn_row.addWidget(self._btn_del)
        lay.addLayout(btn_row)

    def _refresh_preview(self):
        if self._imagen:
            pm = _load_pixmap(self._imagen, self.W, self.H)
            self._preview.setPixmap(pm)
            self._preview.setText("")
            self._preview.setStyleSheet(
                "border: 2px solid #E5E7EB; border-radius: 10px;")
        else:
            self._preview.clear()
            self._preview.setText("Sin imagen")
            self._preview.setStyleSheet(
                "border: 2px dashed #D1D5DB; border-radius: 10px;"
                "background: #F8FAFC; color: #9CA3AF; font-size: 11px;")

    def _pick_file(self):
        if self._read_only:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen",
            os.path.expanduser("~"),
            "Imágenes (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if not path:
            return
        ext  = os.path.splitext(path)[1].lower() or ".jpg"
        dest = os.path.join(_IMG_DIR, f"prod_{abs(hash(path))}{ext}")
        shutil.copy2(path, dest)
        self._imagen = dest
        self._refresh_preview()
        self._btn_del.setVisible(True)

    def _remove(self):
        if self._read_only:
            return
        self._imagen = None
        self._refresh_preview()
        self._btn_del.setVisible(False)

    def get_imagen(self) -> str:
        return self._imagen


# ─────────────────────────────────────────────────────────────────────────────
# Diálogo de producto
# ─────────────────────────────────────────────────────────────────────────────

class ProductDialog(QDialog):

    def __init__(self, product=None, read_only: bool = False, parent=None):
        super().__init__(parent)
        self.product = product
        self.read_only = read_only
        self.setWindowTitle("Ver Producto" if read_only else ("Editar Producto" if product else "Agregar Producto"))
        self.setMinimumWidth(580)
        self.init_ui()
        if product:
            self.load_product_data()
        if read_only:
            self.setWindowTitle("Editar Stock" if product else "Ver Producto")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(22, 20, 22, 18)

        # ── Cuerpo: formulario izquierda | imagen derecha ─────────────
        body = QHBoxLayout()
        body.setSpacing(20)

        # Columna izquierda
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Café Espresso")
        self.name_input.setReadOnly(self.read_only)
        form.addRow("Nombre: *", self.name_input)

        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(68)
        self.description_input.setPlaceholderText("Descripción opcional…")
        self.description_input.setReadOnly(self.read_only)
        form.addRow("Descripción:", self.description_input)

        self.category_combo = QComboBox()
        self.load_categories()
        self.category_combo.setEnabled(not self.read_only)
        form.addRow("Categoría: *", self.category_combo)

        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.01, 99999.99)
        self.price_input.setDecimals(2)
        self.price_input.setPrefix("Bs ")
        self.price_input.setReadOnly(self.read_only)
        self.price_input.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons if self.read_only else QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        form.addRow("Precio: *", self.price_input)

        self.cost_input = QDoubleSpinBox()
        self.cost_input.setRange(0.00, 99999.99)
        self.cost_input.setDecimals(2)
        self.cost_input.setPrefix("Bs ")
        self.cost_input.setReadOnly(self.read_only)
        self.cost_input.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons if self.read_only else QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        form.addRow("Costo:", self.cost_input)

        self.stock_input = QSpinBox()
        self.stock_input.setRange(0, 99999)
        # El stock siempre es editable (incluso en modo read_only para cajeros)
        # Pero si es read_only y no es admin, solo permitimos editar stock
        form.addRow("Stock: *", self.stock_input)

        left = QWidget()
        left.setLayout(form)
        body.addWidget(left, stretch=3)

        # Columna derecha — imagen
        right = QFrame()
        right.setStyleSheet(
            "QFrame { background: #F8FAFC; border: 1px solid #E5E7EB;"
            " border-radius: 12px; }"
            "QLabel { background: transparent; border: none; }")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 16, 16, 16)
        rl.setSpacing(6)
        rl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        img_title = QLabel("Imagen del producto")
        img_title.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #6B7280;")
        img_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(img_title)

        self.img_picker = ImagePickerWidget(
            imagen_actual=self.product.imagen if self.product else None,
            read_only=self.read_only)
        rl.addWidget(self.img_picker)

        hint = QLabel("jpg · png · webp")
        hint.setStyleSheet("font-size: 10px; color: #9CA3AF;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(hint)

        body.addWidget(right, stretch=2)
        layout.addLayout(body)

        # Botones
        buttons = QDialogButtonBox()
        if self.read_only:
            # En modo solo lectura (cajero editando solo stock), mostramos Guardar y Cancelar
            buttons.setStandardButtons(
                QDialogButtonBox.StandardButton.Save |
                QDialogButtonBox.StandardButton.Cancel
            )
        else:
            buttons.setStandardButtons(
                QDialogButtonBox.StandardButton.Save |
                QDialogButtonBox.StandardButton.Cancel
            )
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_categories(self):
        for cat in Category.get_all():
            self.category_combo.addItem(
                f"{cat.icono} {cat.nombre}", cat.id)

    def load_product_data(self):
        self.name_input.setText(self.product.nombre)
        self.description_input.setPlainText(self.product.descripcion or "")
        self.price_input.setValue(self.product.precio)
        self.cost_input.setValue(self.product.costo)
        self.stock_input.setValue(self.product.stock)
        for i in range(self.category_combo.count()):
            if self.category_combo.itemData(i) == self.product.categoria_id:
                self.category_combo.setCurrentIndex(i)
                break

    def get_product_data(self):
        return {
            'nombre':       self.name_input.text().strip(),
            'descripcion':  self.description_input.toPlainText().strip(),
            'categoria_id': self.category_combo.currentData(),
            'precio':       self.price_input.value(),
            'costo':        self.cost_input.value(),
            'stock':        self.stock_input.value(),
            'imagen':       self.img_picker.get_imagen(),
        }

    def validate(self):
        d = self.get_product_data()
        if not d['nombre']:
            QMessageBox.warning(self, "Campo requerido", "El nombre es obligatorio.")
            return False
        if d['precio'] <= 0:
            QMessageBox.warning(self, "Campo requerido", "El precio debe ser mayor a 0.")
            return False
        if not d['categoria_id']:
            QMessageBox.warning(self, "Campo requerido", "Selecciona una categoría.")
            return False
        return True

    def accept(self):
        if self.read_only:
            # En modo solo lectura (cajero), solo validamos que el stock sea válido
            if self.stock_input.value() < 0:
                QMessageBox.warning(self, "Campo requerido", "El stock no puede ser negativo.")
                return
            super().accept()
        else:
            if self.validate():
                super().accept()


# ─────────────────────────────────────────────────────────────────────────────
# Widget principal
# ─────────────────────────────────────────────────────────────────────────────

class ProductsWidget(QWidget):

    def __init__(self):
        super().__init__()
        u = get_current_user()
        self._es_admin = u.is_admin() if u else False
        self.init_ui()
        self.load_products()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title = QLabel("📦 Gestión de Productos")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")
        header.addWidget(title)
        header.addStretch()
        
        self.add_btn = QPushButton("➕ Agregar Producto")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35; color: white;
                padding: 10px 20px; border-radius: 8px; font-weight: 600;
            }
            QPushButton:hover { background-color: #E55A2B; }
            QPushButton:disabled { background-color: #9CA3AF; }
        """)
        self.add_btn.clicked.connect(self.add_product)
        self.add_btn.setEnabled(self._es_admin)  # Solo admin puede agregar
        header.addWidget(self.add_btn)
        layout.addLayout(header)

        # Filtros
        flay = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar productos...")
        self.search_input.textChanged.connect(self.search_products)
        flay.addWidget(self.search_input)
        self.category_filter = QComboBox()
        self.category_filter.setMinimumWidth(200)
        self.load_category_filter()
        self.category_filter.currentIndexChanged.connect(self.filter_by_category)
        flay.addWidget(self.category_filter)
        layout.addLayout(flay)

        # Tabla
        self.table = QTableWidget()
        if self._es_admin:
            self.table.setColumnCount(9)
            self.table.setHorizontalHeaderLabels([
                "Imagen", "ID", "Nombre", "Categoría",
                "Precio", "Costo", "Stock", "Control Stock", "Acciones"
            ])
        else:
            self.table.setColumnCount(8)
            self.table.setHorizontalHeaderLabels([
                "Imagen", "ID", "Nombre", "Categoría",
                "Precio", "Costo", "Stock", "Acciones"
            ])

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 74)                          # imagen
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        if self._es_admin:
            hh.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(7, 130)                     # control stock
            hh.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(8, 110)                     # acciones
        else:
            hh.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(7, 110)                     # acciones

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(70)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #6B7280; font-size: 14px;")
        layout.addWidget(self.stats_label)

    def load_category_filter(self):
        self.category_filter.clear()
        self.category_filter.addItem("📦 Todas las categorías", None)
        for cat in Category.get_all():
            self.category_filter.addItem(f"{cat.icono} {cat.nombre}", cat.id)

    def load_products(self, category_id=None):
        prods = (Product.get_by_category(category_id)
                 if category_id else Product.get_all(activo_only=True))
        self.table.setRowCount(0)
        self._fill(prods)

    def _fill(self, products):
        for product in products:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Imagen
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_lbl.setStyleSheet("background: transparent;")
            img_lbl.setPixmap(_load_pixmap(product.imagen, 56, 56))
            self.table.setCellWidget(row, 0, img_lbl)

            # ID
            id_i = QTableWidgetItem(str(product.id))
            id_i.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, id_i)

            # Nombre
            self.table.setItem(row, 2, QTableWidgetItem(product.nombre))

            # Categoría
            cat = Category.get_by_id(product.categoria_id)
            self.table.setItem(row, 3, QTableWidgetItem(
                f"{cat.icono} {cat.nombre}" if cat else "Sin categoría"))

            # Precio
            p_i = QTableWidgetItem(f"Bs {product.precio:.2f}")
            p_i.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, p_i)

            # Costo
            c_i = QTableWidgetItem(f"Bs {product.costo:.2f}")
            c_i.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, c_i)

            # Stock
            s_i = QTableWidgetItem(str(product.stock))
            s_i.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if product.stock == 0:
                s_i.setForeground(QColor("#EF4444"))
            self.table.setItem(row, 6, s_i)

            # Control Stock (solo admin)
            if self._es_admin:
                disp = getattr(product, 'disponible', 1)
                sb = QPushButton("✅ Con stock" if disp else "🔓 Sin stock")
                sb.setCheckable(True)
                sb.setChecked(bool(disp))
                sb.setStyleSheet("""
                    QPushButton {
                        background: #D1FAE5; color: #065F46;
                        border: 1px solid #6EE7B7; border-radius: 6px;
                        padding: 4px 8px; font-size: 11px; font-weight: 600;
                    }
                    QPushButton:!checked {
                        background: #FEF3C7; color: #92400E;
                        border-color: #FCD34D;
                    }
                    QPushButton:disabled {
                        background: #E5E7EB; color: #9CA3AF;
                        border-color: #D1D5DB;
                    }
                """)
                def _make_toggle(p, btn):
                    def _t(checked):
                        Product.set_disponible(p.id, checked)
                        btn.setText("✅ Con stock" if checked else "🔓 Sin stock")
                    return _t
                sb.toggled.connect(_make_toggle(product, sb))
                sb.setEnabled(self._es_admin)  # Solo admin puede usar el toggle
                self.table.setCellWidget(row, 7, sb)
                ac = 8
            else:
                ac = 7

            # Acciones
            aw = QWidget(); aw.setStyleSheet("background: transparent;")
            al = QHBoxLayout(aw)
            al.setContentsMargins(4, 2, 4, 2); al.setSpacing(4)

            # Botón Editar
            eb = QPushButton("✏️")
            eb.setStyleSheet("""
                QPushButton { background: #3B82F6; color: white; border: none;
                    border-radius: 5px; padding: 5px 10px; }
                QPushButton:hover { background: #2563EB; }
                QPushButton:disabled { background: #9CA3AF; }
            """)
            eb.clicked.connect(lambda checked=False, p=product: self.edit_product(p))
            eb.setEnabled(True)  # Todos pueden editar (con restricciones)
            al.addWidget(eb)

            # Botón Eliminar (solo admin)
            db_ = QPushButton("🗑️")
            db_.setStyleSheet("""
                QPushButton { background: #EF4444; color: white; border: none;
                    border-radius: 5px; padding: 5px 10px; }
                QPushButton:hover { background: #DC2626; }
                QPushButton:disabled { background: #9CA3AF; }
            """)
            db_.clicked.connect(lambda checked=False, p=product: self.delete_product(p))
            db_.setEnabled(self._es_admin)  # Solo admin puede eliminar
            al.addWidget(db_)

            self.table.setCellWidget(row, ac, aw)

        total     = len(products)
        activos   = sum(1 for p in products if p.activo)
        sin_stock = sum(1 for p in products if p.stock == 0 and p.activo)
        self.stats_label.setText(
            f"Total: {total} productos  |  Activos: {activos}  |  Sin stock: {sin_stock}")

    # ── CRUD ──────────────────────────────────────────────────────────

    def add_product(self):
        if not self._es_admin:
            QMessageBox.warning(self, "Acceso denegado", "Solo los administradores pueden agregar productos.")
            return
        dlg = ProductDialog(parent=self)
        if dlg.exec():
            data = dlg.get_product_data()
            pid  = Product.create(**data)
            if pid:
                QMessageBox.information(
                    self, "Éxito",
                    f"Producto '{data['nombre']}' agregado correctamente.")
                self.load_products()
            else:
                QMessageBox.critical(self, "Error", "No se pudo agregar el producto.")

    def edit_product(self, product: Product):
        if self._es_admin:
            # Admin puede editar todo
            dlg = ProductDialog(product=product, parent=self)
        else:
            # Cajero solo puede editar stock (modo solo lectura para el resto)
            dlg = ProductDialog(product=product, read_only=True, parent=self)
        
        if dlg.exec():
            data = dlg.get_product_data()
            if self._es_admin:
                # Admin actualiza todo
                if Product.update(product.id, **data):
                    QMessageBox.information(
                        self, "Éxito",
                        f"Producto '{data['nombre']}' actualizado correctamente.")
                    self.load_products()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo actualizar el producto.")
            else:
                # Cajero solo actualiza el stock
                if Product.update_stock(product.id, data['stock']):
                    QMessageBox.information(
                        self, "Éxito",
                        f"Stock del producto '{product.nombre}' actualizado correctamente.")
                    self.load_products()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo actualizar el stock.")

    def delete_product(self, product: Product):
        if not self._es_admin:
            QMessageBox.warning(self, "Acceso denegado", "Solo los administradores pueden eliminar productos.")
            return
        reply = QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Eliminar '{product.nombre}'?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if Product.delete(product.id):
                QMessageBox.information(self, "Éxito", "Producto eliminado.")
                self.load_products(self.category_filter.currentData())
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el producto.")

    def filter_by_category(self, index):
        self.load_products(self.category_filter.itemData(index))

    def search_products(self, text):
        if not text:
            self.load_products(self.category_filter.currentData())
            return
        self.table.setRowCount(0)
        self._fill(Product.search(text))