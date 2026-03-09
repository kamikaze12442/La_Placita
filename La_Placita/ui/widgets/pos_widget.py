"""
POS Widget
ACTUALIZADO:
  - Impresión térmica al completar venta
  - Pago Efectivo / QR / Tarjeta / Mixto (Efectivo + QR)
  - Cálculo de cambio a dar
  - Sin subtotal, solo TOTAL
  - Bloquea "Completar Venta" si no hay caja abierta
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox, QFrame,
    QScrollArea, QHeaderView, QButtonGroup, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from models.product import Product, Category
from models.sale import Sale, SaleDetail
from models.user import get_current_user
from models.arqueo import ArqueoCaja

try:
    from utils.printer import imprimir_recibo
    PRINTER_OK = True
except ImportError:
    PRINTER_OK = False


class ProductCard(QFrame):
    clicked = Signal(object)

    def __init__(self, product: Product):
        super().__init__()
        self.product = product
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(140, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            ProductCard {
                background-color: white;
                border: 2px solid #E5E7EB;
                border-radius: 10px;
                padding: 10px;
            }
            ProductCard:hover {
                border-color: #FF6B35;
                background-color: #FFF5F2;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        name_label = QLabel(self.product.nombre)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #1F2937;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        price_label = QLabel(f"Bs {self.product.precio:.2f}")
        price_label.setStyleSheet("color: #FF6B35; font-size: 14px; font-weight: 700;")
        price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(price_label)

        stock_color = "#10B981" if self.product.stock > 10 else "#F59E0B" if self.product.stock > 0 else "#EF4444"
        stock_label = QLabel(f"Stock: {self.product.stock}")
        stock_label.setStyleSheet(f"color: {stock_color}; font-size: 11px;")
        stock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(stock_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.product)


class POSWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.cart_items = []
        self.current_user = get_current_user()
        self._caja_abierta = False
        self.init_ui()
        self.load_categories()
        self.load_products()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_caja)
        self._timer.start(20000)
        self._check_caja()

    # ── Estado de caja ────────────────────────────────────────────────

    def _check_caja(self):
        arqueo = ArqueoCaja.get_abierto_por_usuario(self.current_user.id)
        self._caja_abierta = arqueo is not None

        if self._caja_abierta:
            inicio = arqueo.fecha_inicio[:16].replace('T', ' ')
            self._banner.setText(f"🟢  Caja abierta desde {inicio}")
            self._banner.setStyleSheet("""
                background-color: #D1FAE5; color: #065F46;
                border: 1px solid #6EE7B7; border-radius: 8px;
                padding: 6px 14px; font-weight: 600; font-size: 12px;
            """)
        else:
            self._banner.setText("🔴  No hay caja abierta — ve a Arqueo de Caja para abrir la caja")
            self._banner.setStyleSheet("""
                background-color: #FEE2E2; color: #991B1B;
                border: 1px solid #FCA5A5; border-radius: 8px;
                padding: 6px 14px; font-weight: 600; font-size: 12px;
            """)

        self.update_totals()

    # ── UI ────────────────────────────────────────────────────────────

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ── Lado izquierdo: productos ─────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(15)

        header = QLabel("💰 Punto de Venta")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")
        left_layout.addWidget(header)

        self._banner = QLabel("")
        self._banner.setWordWrap(True)
        left_layout.addWidget(self._banner)

        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar producto...")
        self.search_input.textChanged.connect(self.search_products)
        filter_layout.addWidget(self.search_input)

        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(180)
        self.category_combo.currentIndexChanged.connect(
            lambda: self.load_products(self.category_combo.currentData())
        )
        filter_layout.addWidget(self.category_combo)
        left_layout.addLayout(filter_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.products_container = QWidget()
        self.products_grid = QGridLayout(self.products_container)
        self.products_grid.setSpacing(10)
        scroll.setWidget(self.products_container)
        left_layout.addWidget(scroll)

        main_layout.addWidget(left, stretch=2)

        # ── Lado derecho: carrito ─────────────────────────────────────
        right = QWidget()
        right.setFixedWidth(400)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        cart_title = QLabel("🛒 Carrito")
        cart_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1F2937;")
        right_layout.addWidget(cart_title)

        # Tabla carrito — ocupa todo el espacio vertical disponible
        self.cart_table = QTableWidget(0, 5)
        self.cart_table.setHorizontalHeaderLabels(["Producto", "Cant.", "Precio", "Total", ""])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cart_table.setColumnWidth(1, 50)
        self.cart_table.setColumnWidth(2, 75)
        self.cart_table.setColumnWidth(3, 75)
        self.cart_table.setColumnWidth(4, 36)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.verticalHeader().setDefaultSectionSize(46)
        self.cart_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.cart_table.setStyleSheet("""
            QTableWidget { border: 1px solid #E5E7EB; border-radius: 8px;
                           background: white; font-size: 12px; }
            QHeaderView::section { background: #F9FAFB; color: #6B7280;
                font-weight: 600; padding: 6px; border: none;
                border-bottom: 1px solid #E5E7EB; }
        """)
        right_layout.addWidget(self.cart_table, stretch=1)

        # ── Panel de pago ──────────────────────────────────────────────
        pay_frame = QFrame()
        pay_frame.setStyleSheet("""
            QFrame { background: #F9FAFB; border: 1px solid #E5E7EB;
                     border-radius: 10px; }
        """)
        pay_layout = QVBoxLayout(pay_frame)
        pay_layout.setContentsMargins(12, 10, 12, 10)
        pay_layout.setSpacing(7)

        # Cliente
        client_row = QHBoxLayout()
        client_lbl = QLabel("Cliente:")
        client_lbl.setFixedWidth(72)
        client_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#6B7280;")
        self.client_input = QLineEdit()
        self.client_input.setPlaceholderText("Cliente General")
        self.client_input.setStyleSheet("""
            QLineEdit { background:white; border:1px solid #E5E7EB;
                        border-radius:6px; padding:4px 8px; font-size:12px; }
            QLineEdit:focus { border-color:#FF6B35; }
        """)
        client_row.addWidget(client_lbl)
        client_row.addWidget(self.client_input)
        pay_layout.addLayout(client_row)

        # Método de pago: chips
        method_row = QHBoxLayout()
        method_row.setSpacing(5)
        method_lbl = QLabel("Pago:")
        method_lbl.setFixedWidth(72)
        method_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#6B7280;")
        method_row.addWidget(method_lbl)

        self._pay_group = QButtonGroup(self)
        self._pay_group.setExclusive(True)
        chip_style = """
            QPushButton { background:white; border:1.5px solid #E5E7EB;
                          border-radius:6px; font-size:11px; font-weight:600;
                          color:#6B7280; padding:4px 9px; }
            QPushButton:checked { background:#FF6B35; border-color:#FF6B35; color:white; }
            QPushButton:hover:!checked { border-color:#FF6B35; color:#FF6B35; }
        """
        for label, key in [("💵 Efectivo", "efectivo"), ("📱 QR", "qr"),
                            ("💳 Tarjeta", "tarjeta"),  ("⚡ Mixto", "mixto")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("pay_key", key)
            btn.setStyleSheet(chip_style)
            if key == "efectivo":
                btn.setChecked(True)
            btn.toggled.connect(self._on_method_changed)
            self._pay_group.addButton(btn)
            method_row.addWidget(btn)
        method_row.addStretch()
        pay_layout.addLayout(method_row)

        spin_style = """
            QDoubleSpinBox { background:white; border:1px solid #E5E7EB;
                             border-radius:6px; padding:4px 8px; font-size:12px; }
            QDoubleSpinBox:focus { border-color:#10B981; }
        """

        # Fila efectivo recibido
        self._eff_row = QHBoxLayout()
        self._eff_lbl = QLabel("Recibido:")
        self._eff_lbl.setFixedWidth(72)
        self._eff_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#6B7280;")
        self._eff_spin = QDoubleSpinBox()
        self._eff_spin.setRange(0, 999999)
        self._eff_spin.setDecimals(2)
        self._eff_spin.setPrefix("Bs ")
        self._eff_spin.setStyleSheet(spin_style)
        self._eff_spin.valueChanged.connect(self.update_totals)
        self._eff_row.addWidget(self._eff_lbl)
        self._eff_row.addWidget(self._eff_spin)
        pay_layout.addLayout(self._eff_row)

        # Fila QR (solo en modo Mixto)
        self._qr_row = QHBoxLayout()
        self._qr_lbl = QLabel("QR:")
        self._qr_lbl.setFixedWidth(72)
        self._qr_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#6B7280;")
        self._qr_spin = QDoubleSpinBox()
        self._qr_spin.setRange(0, 999999)
        self._qr_spin.setDecimals(2)
        self._qr_spin.setPrefix("Bs ")
        self._qr_spin.setStyleSheet(spin_style.replace("#10B981", "#3B82F6"))
        self._qr_spin.valueChanged.connect(self.update_totals)
        self._qr_row.addWidget(self._qr_lbl)
        self._qr_row.addWidget(self._qr_spin)
        pay_layout.addLayout(self._qr_row)
        self._qr_lbl.setVisible(False)
        self._qr_spin.setVisible(False)

        right_layout.addWidget(pay_frame)

        # ── Totales ────────────────────────────────────────────────────
        totals_frame = QFrame()
        totals_frame.setStyleSheet("""
            QFrame { background: #FFF7ED; border: 1.5px solid #FED7AA;
                     border-radius: 10px; }
        """)
        totals_layout = QVBoxLayout(totals_frame)
        totals_layout.setContentsMargins(14, 10, 14, 10)
        totals_layout.setSpacing(6)

        total_row = QHBoxLayout()
        total_title = QLabel("TOTAL:")
        total_title.setStyleSheet("font-size:15px; font-weight:700; color:#1F2937;")
        total_row.addWidget(total_title)
        self.total_label = QLabel("Bs 0.00")
        self.total_label.setStyleSheet(
            "font-size:22px; font-weight:800; color:#FF6B35;")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        total_row.addWidget(self.total_label)
        totals_layout.addLayout(total_row)

        # Cambio a dar
        self._cambio_frame = QFrame()
        self._cambio_frame.setStyleSheet(
            "QFrame { background:#10B981; border-radius:7px; }")
        cambio_inner = QHBoxLayout(self._cambio_frame)
        cambio_inner.setContentsMargins(10, 6, 10, 6)
        cambio_title = QLabel("💰 Cambio a dar:")
        cambio_title.setStyleSheet("font-size:12px; font-weight:600; color:white;")
        cambio_inner.addWidget(cambio_title)
        cambio_inner.addStretch()
        self._cambio_val = QLabel("Bs 0.00")
        self._cambio_val.setStyleSheet("font-size:16px; font-weight:800; color:white;")
        cambio_inner.addWidget(self._cambio_val)
        totals_layout.addWidget(self._cambio_frame)
        self._cambio_frame.setVisible(False)

        right_layout.addWidget(totals_frame)

        # ── Botones ────────────────────────────────────────────────────
        buttons_layout = QHBoxLayout()

        clear_btn = QPushButton("🗑️ Limpiar")
        clear_btn.setStyleSheet("""
            QPushButton { background-color: #6B7280; color: white; padding: 12px;
                          border-radius: 8px; font-weight: 600; }
            QPushButton:hover { background-color: #4B5563; }
        """)
        clear_btn.clicked.connect(self.clear_cart)
        buttons_layout.addWidget(clear_btn)

        self.checkout_btn = QPushButton("✅ Completar Venta")
        self.checkout_btn.setStyleSheet("""
            QPushButton { background-color: #10B981; color: white; padding: 12px;
                          border-radius: 8px; font-weight: 600; }
            QPushButton:hover { background-color: #059669; }
            QPushButton:disabled { background-color: #D1D5DB; color: #9CA3AF; }
        """)
        self.checkout_btn.clicked.connect(self.complete_sale)
        self.checkout_btn.setEnabled(False)
        buttons_layout.addWidget(self.checkout_btn)
        right_layout.addLayout(buttons_layout)

        self._hint = QLabel("")
        self._hint.setStyleSheet("color: #EF4444; font-size: 11px;")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)
        right_layout.addWidget(self._hint)

        main_layout.addWidget(right, stretch=1)

    # ── Método de pago ────────────────────────────────────────────────

    def _current_method(self) -> str:
        for btn in self._pay_group.buttons():
            if btn.isChecked():
                return btn.property("pay_key")
        return "efectivo"

    def _on_method_changed(self, _=None):
        method = self._current_method()
        show_eff = method in ("efectivo", "mixto")
        self._eff_lbl.setVisible(show_eff)
        self._eff_spin.setVisible(show_eff)
        self._eff_lbl.setText("Efectivo:" if method == "mixto" else "Recibido:")
        self._qr_lbl.setVisible(method == "mixto")
        self._qr_spin.setVisible(method == "mixto")
        self.update_totals()

    # ── Productos ─────────────────────────────────────────────────────

    def load_categories(self):
        self.category_combo.clear()
        self.category_combo.addItem("📦 Todas las categorías", None)
        for cat in Category.get_all():
            self.category_combo.addItem(f"{cat.icono} {cat.nombre}", cat.id)

    def load_products(self, categoria_id=None):
        products = Product.get_by_category(categoria_id) if categoria_id else Product.get_all()
        self._render_products(products)

    def search_products(self, term: str):
        products = Product.search(term) if term else Product.get_all()
        self._render_products(products)

    def _render_products(self, products):
        while self.products_grid.count():
            item = self.products_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cols = 5
        for i, product in enumerate(products):
            card = ProductCard(product)
            card.clicked.connect(self.add_to_cart)
            self.products_grid.addWidget(card, i // cols, i % cols)

    # ── Carrito ───────────────────────────────────────────────────────

    def add_to_cart(self, product: Product):
        for item in self.cart_items:
            if item.producto_id == product.id:
                item.cantidad += 1
                item.calculate_subtotal()
                self.update_cart_display()
                return
        detail = SaleDetail(
            producto_id=product.id,
            producto_nombre=product.nombre,
            cantidad=1,
            precio_unitario=product.precio
        )
        detail.calculate_subtotal()
        self.cart_items.append(detail)
        self.update_cart_display()

    def update_cart_display(self):
        self.cart_table.setRowCount(len(self.cart_items))
        for i, item in enumerate(self.cart_items):
            self.cart_table.setItem(i, 0, QTableWidgetItem(item.producto_nombre))

            qty_spin = QSpinBox()
            qty_spin.setRange(1, 999)
            qty_spin.setValue(item.cantidad)
            qty_spin.valueChanged.connect(lambda val, idx=i: self.update_quantity(idx, val))
            self.cart_table.setCellWidget(i, 1, qty_spin)

            price_item = QTableWidgetItem(f"Bs {item.precio_unitario:.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.cart_table.setItem(i, 2, price_item)

            sub_item = QTableWidgetItem(f"Bs {item.subtotal:.2f}")
            sub_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.cart_table.setItem(i, 3, sub_item)

            rm_btn = QPushButton("✕")
            rm_btn.setStyleSheet("""
                QPushButton { background:#FEE2E2; color:#EF4444; border:none;
                              border-radius:5px; font-weight:700; font-size:11px; }
                QPushButton:hover { background:#EF4444; color:white; }
            """)
            rm_btn.clicked.connect(lambda checked=False, idx=i: self.remove_from_cart(idx))
            self.cart_table.setCellWidget(i, 4, rm_btn)

        self.update_totals()

    def update_quantity(self, index: int, quantity: int):
        if 0 <= index < len(self.cart_items):
            self.cart_items[index].cantidad = quantity
            self.cart_items[index].calculate_subtotal()
            self.update_cart_display()

    def remove_from_cart(self, index: int):
        if 0 <= index < len(self.cart_items):
            self.cart_items.pop(index)
            self.update_cart_display()

    def clear_cart(self):
        if self.cart_items:
            reply = QMessageBox.question(
                self, "Limpiar Carrito", "¿Está seguro de limpiar el carrito?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.cart_items.clear()
                self.update_cart_display()

    # ── Totales ───────────────────────────────────────────────────────

    def update_totals(self):
        total = sum(item.subtotal for item in self.cart_items)
        self.total_label.setText(f"Bs {total:.2f}")

        method   = self._current_method()
        pago_ok  = True
        show_cambio = False

        if method == "efectivo":
            rec = self._eff_spin.value()
            if rec > 0:
                cambio  = max(rec - total, 0)
                pago_ok = rec >= total
                show_cambio = True
                color = "#10B981" if pago_ok else "#EF4444"
                self._cambio_frame.setStyleSheet(
                    f"QFrame {{ background:{color}; border-radius:7px; }}")
                self._cambio_val.setText(f"Bs {cambio:.2f}")

        elif method == "mixto":
            eff  = self._eff_spin.value()
            qr   = self._qr_spin.value()
            suma = eff + qr
            if suma > 0:
                cambio  = max(suma - total, 0)
                pago_ok = suma >= total
                show_cambio = True
                color = "#10B981" if pago_ok else "#EF4444"
                self._cambio_frame.setStyleSheet(
                    f"QFrame {{ background:{color}; border-radius:7px; }}")
                self._cambio_val.setText(f"Bs {cambio:.2f}")

        self._cambio_frame.setVisible(show_cambio)

        hay_items = len(self.cart_items) > 0
        self.checkout_btn.setEnabled(hay_items and self._caja_abierta and pago_ok)

        if hay_items and not self._caja_abierta:
            self._hint.setText(
                "⚠️ Abre la caja primero en Arqueo de Caja\npara poder completar una venta.")
        elif not pago_ok:
            self._hint.setText("⚠️ El monto recibido es menor al total.")
        else:
            self._hint.setText("")

    # ── Completar venta ───────────────────────────────────────────────

    def complete_sale(self):
        if not self.cart_items:
            return

        arqueo = ArqueoCaja.get_abierto_por_usuario(self.current_user.id)
        if not arqueo:
            QMessageBox.warning(
                self, "Caja cerrada",
                "No hay caja abierta.\nVe a Arqueo de Caja y abre la caja primero.")
            self._caja_abierta = False
            self.update_totals()
            return

        cliente     = self.client_input.text().strip() or "Cliente General"
        method      = self._current_method()

        sale_id = Sale.create(
            usuario_id=self.current_user.id,
            items=self.cart_items,
            cliente=cliente,
            metodo_pago=method
        )

        if not sale_id:
            QMessageBox.critical(self, "Error",
                "No se pudo completar la venta. Intente nuevamente.")
            return

        sale  = Sale.get_by_id(sale_id)
        total = sale.total

        msg = (f"✅ Venta completada exitosamente!\n\n"
               f"Factura: {sale.numero_factura}\n"
               f"Total:   Bs {total:.2f}\n")

        if method == "efectivo":
            rec    = self._eff_spin.value()
            cambio = max(rec - total, 0)
            if rec > 0:
                msg += f"Recibido: Bs {rec:.2f}\n"
                msg += f"Cambio:   Bs {cambio:.2f}\n"
        elif method == "mixto":
            eff    = self._eff_spin.value()
            qr     = self._qr_spin.value()
            cambio = max((eff + qr) - total, 0)
            msg += f"Efectivo: Bs {eff:.2f}\n"
            msg += f"QR:       Bs {qr:.2f}\n"
            if cambio > 0:
                msg += f"Cambio:   Bs {cambio:.2f}\n"
        else:
            msg += f"Método:  {method.title()}\n"

        reply = QMessageBox.question(
            self, "Venta Completada",
            msg + "\n🖨️ ¿Desea imprimir el recibo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._print_receipt(sale)

        self.cart_items.clear()
        self.client_input.clear()
        self._eff_spin.setValue(0)
        self._qr_spin.setValue(0)
        self.update_cart_display()
        self.load_products()

    # ── Impresión ─────────────────────────────────────────────────────

    def _print_receipt(self, sale):
        if not PRINTER_OK:
            QMessageBox.warning(self, "Impresora no disponible",
                "El módulo de impresión no está instalado.\n"
                "Ejecuta: pip install pywin32")
            return
        ok, msg = imprimir_recibo(sale)
        if not ok:
            QMessageBox.warning(self, "Error de impresión", msg)