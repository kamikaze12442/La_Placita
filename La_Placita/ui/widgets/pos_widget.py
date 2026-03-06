"""
POS Widget
ACTUALIZADO: Bloquea "Completar Venta" si no hay caja abierta para el usuario actual
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QSpinBox, QMessageBox, QFrame, QScrollArea, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from models.product import Product, Category
from models.sale import Sale, SaleDetail
from models.user import get_current_user
from models.arqueo import ArqueoCaja


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

        # Verificar estado de caja cada 20 segundos
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

        # ── Lado izquierdo: productos ──────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(15)

        header = QLabel("💰 Punto de Venta")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")
        left_layout.addWidget(header)

        # Banner de estado de caja
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

        # ── Lado derecho: carrito ──────────────────────────────────────
        right = QWidget()
        right.setFixedWidth(380)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(10)

        cart_title = QLabel("🛒 Carrito")
        cart_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1F2937;")
        right_layout.addWidget(cart_title)

        self.cart_table = QTableWidget(0, 5)
        self.cart_table.setHorizontalHeaderLabels(["Producto", "Cant.", "Precio", "Total", ""])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cart_table.setColumnWidth(1, 50)
        self.cart_table.setColumnWidth(2, 80)
        self.cart_table.setColumnWidth(3, 80)
        self.cart_table.setColumnWidth(4, 40)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.verticalHeader().setDefaultSectionSize(100)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.cart_table)

        client_layout = QHBoxLayout()
        client_layout.addWidget(QLabel("Cliente:"))
        self.client_input = QLineEdit()
        self.client_input.setPlaceholderText("Cliente General")
        client_layout.addWidget(self.client_input)
        right_layout.addLayout(client_layout)

        payment_layout = QHBoxLayout()
        payment_layout.addWidget(QLabel("Pago:"))
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Efectivo", "QR", "Tarjeta"])
        payment_layout.addWidget(self.payment_combo)
        right_layout.addLayout(payment_layout)

        totals_frame = QFrame()
        totals_frame.setStyleSheet("QFrame{background-color:#F9FAFB;border-radius:8px;padding:15px;}")
        totals_layout = QVBoxLayout(totals_frame)
        self.subtotal_label = QLabel("Subtotal: Bs 0.00")
        self.subtotal_label.setStyleSheet("font-size: 14px; color: #6B7280;")
        totals_layout.addWidget(self.subtotal_label)
        self.total_label = QLabel("TOTAL: Bs 0.00")
        self.total_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FF6B35;")
        totals_layout.addWidget(self.total_label)
        right_layout.addWidget(totals_frame)

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

        # Hint cuando la caja está cerrada
        self._hint = QLabel("")
        self._hint.setStyleSheet("color: #EF4444; font-size: 11px;")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)
        right_layout.addWidget(self._hint)

        main_layout.addWidget(right, stretch=1)

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

            rm_btn = QPushButton("🗑️")
            rm_btn.setStyleSheet("background-color: #EF4444; color: white; border-radius: 4px;")
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

    def update_totals(self):
        subtotal = sum(item.subtotal for item in self.cart_items)
        self.subtotal_label.setText(f"Subtotal: Bs {subtotal:.2f}")
        self.total_label.setText(f"TOTAL: Bs {subtotal:.2f}")

        hay_items = len(self.cart_items) > 0
        # Solo habilitar si hay items Y la caja está abierta
        self.checkout_btn.setEnabled(hay_items and self._caja_abierta)

        if hay_items and not self._caja_abierta:
            self._hint.setText(
                "⚠️ Abre la caja primero en Arqueo de Caja\npara poder completar una venta."
            )
        else:
            self._hint.setText("")

    def clear_cart(self):
        if self.cart_items:
            reply = QMessageBox.question(
                self, "Limpiar Carrito", "¿Está seguro de limpiar el carrito?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.cart_items.clear()
                self.update_cart_display()

    def complete_sale(self):
        if not self.cart_items:
            return

        # Doble verificación en el momento de completar
        arqueo = ArqueoCaja.get_abierto_por_usuario(self.current_user.id)
        if not arqueo:
            QMessageBox.warning(
                self, "Caja cerrada",
                "No hay caja abierta.\nVe a Arqueo de Caja y abre la caja primero."
            )
            self._caja_abierta = False
            self.update_totals()
            return

        cliente     = self.client_input.text().strip() or "Cliente General"
        metodo_pago = self.payment_combo.currentText().lower()

        sale_id = Sale.create(
            usuario_id=self.current_user.id,
            items=self.cart_items,
            cliente=cliente,
            metodo_pago=metodo_pago
        )

        if sale_id:
            sale = Sale.get_by_id(sale_id)
            QMessageBox.information(
                self, "Venta Completada",
                f"✅ Venta completada exitosamente!\n\n"
                f"Factura: {sale.numero_factura}\n"
                f"Total: Bs {sale.total:.2f}\n"
                f"Método: {sale.metodo_pago.title()}"
            )
            self.cart_items.clear()
            self.client_input.clear()
            self.update_cart_display()
            self.load_products()
        else:
            QMessageBox.critical(self, "Error", "No se pudo completar la venta. Intente nuevamente.")