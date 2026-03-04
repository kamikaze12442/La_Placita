"""
POS Widget
Complete Point of Sale interface
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QSpinBox, QMessageBox, QFrame, QScrollArea, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from models.product import Product, Category
from models.sale import Sale, SaleDetail
from models.user import get_current_user


class ProductCard(QFrame):
    """Product card button"""
    
    clicked = Signal(object)  # Emits Product object
    
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
        
        # Product name
        name_label = QLabel(self.product.nombre)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #1F2937;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        # Price
        price_label = QLabel(f"Bs {self.product.precio:.2f}")
        price_label.setStyleSheet("color: #FF6B35; font-size: 14px; font-weight: 700;")
        price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(price_label)
        
        # Stock
        stock_label = QLabel(f"Stock: {self.product.stock}")
        stock_color = "#10B981" if self.product.stock > 10 else "#F59E0B" if self.product.stock > 0 else "#EF4444"
        stock_label.setStyleSheet(f"color: {stock_color}; font-size: 11px;")
        stock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(stock_label)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.product)


class POSWidget(QWidget):
    """Complete POS interface"""
    
    def __init__(self):
        super().__init__()
        self.cart_items = []  # List of SaleDetail objects
        self.current_user = get_current_user()
        self.init_ui()
        self.load_categories()
        self.load_products()
    
    def init_ui(self):
        """Initialize user interface"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Left side - Products
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # Header
        header = QLabel("💰 Punto de Venta")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")
        left_layout.addWidget(header)
        
        # Search and filters
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar producto...")
        self.search_input.textChanged.connect(self.search_products)
        filter_layout.addWidget(self.search_input)
        
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(150)
        self.category_combo.currentIndexChanged.connect(self.filter_by_category)
        filter_layout.addWidget(self.category_combo)
        
        left_layout.addLayout(filter_layout)
        
        # Products grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.products_container = QWidget()
        self.products_layout = QGridLayout(self.products_container)
        self.products_layout.setSpacing(15)
        scroll.setWidget(self.products_container)
        
        left_layout.addWidget(scroll)
        
        main_layout.addWidget(left_widget, stretch=2)
        
        # Right side - Cart
        right_widget = QWidget()
        right_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }
        """)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)
        
        # Cart header
        cart_header = QLabel("🛒 Carrito de Compra")
        cart_header.setStyleSheet("font-size: 18px; font-weight: 600; color: #1F2937;")
        right_layout.addWidget(cart_header)
        
        # Cart table
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
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
        
        # Client info
        client_layout = QHBoxLayout()
        client_layout.addWidget(QLabel("Cliente:"))
        self.client_input = QLineEdit()
        self.client_input.setPlaceholderText("Cliente General")
        client_layout.addWidget(self.client_input)
        right_layout.addLayout(client_layout)
        
        # Payment method
        payment_layout = QHBoxLayout()
        payment_layout.addWidget(QLabel("Pago:"))
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Efectivo", "QR"])
        payment_layout.addWidget(self.payment_combo)
        right_layout.addLayout(payment_layout)
        
        # Totals
        totals_frame = QFrame()
        totals_frame.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        totals_layout = QVBoxLayout(totals_frame)
        
        self.subtotal_label = QLabel("Subtotal: Bs 0.00")
        self.subtotal_label.setStyleSheet("font-size: 14px; color: #6B7280;")
        totals_layout.addWidget(self.subtotal_label)
        
        self.total_label = QLabel("TOTAL: Bs 0.00")
        self.total_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FF6B35;")
        totals_layout.addWidget(self.total_label)
        
        right_layout.addWidget(totals_frame)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ Limpiar")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B7280;
                color: white;
                padding: 12px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #4B5563; }
        """)
        clear_btn.clicked.connect(self.clear_cart)
        buttons_layout.addWidget(clear_btn)
        
        self.checkout_btn = QPushButton("✅ Completar Venta")
        self.checkout_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                padding: 12px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #059669; }
            QPushButton:disabled {
                background-color: #D1D5DB;
                color: #9CA3AF;
            }
        """)
        self.checkout_btn.clicked.connect(self.complete_sale)
        self.checkout_btn.setEnabled(False)
        buttons_layout.addWidget(self.checkout_btn)
        
        right_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(right_widget, stretch=1)
    
    def load_categories(self):
        """Load categories into combo"""
        self.category_combo.clear()
        self.category_combo.addItem("📦 Todas las categorías", None)
        
        categories = Category.get_all()
        for category in categories:
            self.category_combo.addItem(
                f"{category.icono} {category.nombre}",
                category.id
            )
    
    def load_products(self, category_id=None):
        """Load products into grid"""
        # Clear existing products
        while self.products_layout.count():
            item = self.products_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get products
        if category_id:
            products = Product.get_by_category(category_id)
        else:
            products = Product.get_all()
        
        # Display products in grid
        row, col = 0, 0
        max_cols = 4
        
        for product in products:
            if product.stock > 0:  # Only show products in stock
                card = ProductCard(product)
                card.clicked.connect(self.add_to_cart)
                self.products_layout.addWidget(card, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
    
    def filter_by_category(self, index):
        """Filter products by category"""
        category_id = self.category_combo.currentData()
        self.load_products(category_id)
    
    def search_products(self, text):
        """Search products"""
        if not text:
            category_id = self.category_combo.currentData()
            self.load_products(category_id)
            return
        
        # Clear grid
        while self.products_layout.count():
            item = self.products_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Search and display
        products = Product.search(text)
        row, col = 0, 0
        max_cols = 4
        
        for product in products:
            if product.stock > 0:
                card = ProductCard(product)
                card.clicked.connect(self.add_to_cart)
                self.products_layout.addWidget(card, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
    
    def add_to_cart(self, product: Product):
        """Add product to cart"""
        # Check if product already in cart
        for item in self.cart_items:
            if item.producto_id == product.id:
                if item.cantidad < product.stock:
                    item.cantidad += 1
                    item.calculate_subtotal()
                    self.update_cart_display()
                else:
                    QMessageBox.warning(
                        self,
                        "Stock Insuficiente",
                        f"No hay más stock disponible de {product.nombre}"
                    )
                return
        
        # Add new item
        item = SaleDetail(
            producto_id=product.id,
            producto_nombre=product.nombre,
            cantidad=1,
            precio_unitario=product.precio
        )
        item.calculate_subtotal()
        self.cart_items.append(item)
        self.update_cart_display()
    
    def update_cart_display(self):
        """Update cart table"""
        self.cart_table.setRowCount(len(self.cart_items))
        
        for i, item in enumerate(self.cart_items):
            # Product name
            self.cart_table.setItem(i, 0, QTableWidgetItem(item.producto_nombre))
            
            # Quantity spinbox
            qty_spin = QSpinBox()
            qty_spin.setMinimum(1)
            qty_spin.setMaximum(100)
            qty_spin.setValue(item.cantidad)
            qty_spin.valueChanged.connect(lambda val, idx=i: self.update_quantity(idx, val))
            self.cart_table.setCellWidget(i, 1, qty_spin)
            
            # Price
            price_item = QTableWidgetItem(f"Bs {item.precio_unitario:.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.cart_table.setItem(i, 2, price_item)
            
            # Subtotal
            subtotal_item = QTableWidgetItem(f"Bs {item.subtotal:.2f}")
            subtotal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.cart_table.setItem(i, 3, subtotal_item)
            
            # Remove button
            remove_btn = QPushButton("🗑️")
            remove_btn.setStyleSheet("background-color: #EF4444; color: white; border-radius: 4px;")
            remove_btn.clicked.connect(lambda checked=False, idx=i: self.remove_from_cart(idx))
            self.cart_table.setCellWidget(i, 4, remove_btn)
        
        self.update_totals()
    
    def update_quantity(self, index: int, quantity: int):
        """Update item quantity"""
        if 0 <= index < len(self.cart_items):
            self.cart_items[index].cantidad = quantity
            self.cart_items[index].calculate_subtotal()
            self.update_cart_display()
    
    def remove_from_cart(self, index: int):
        """Remove item from cart"""
        if 0 <= index < len(self.cart_items):
            self.cart_items.pop(index)
            self.update_cart_display()
    
    def update_totals(self):
        """Update total labels"""
        subtotal = sum(item.subtotal for item in self.cart_items)
        total = subtotal
        
        self.subtotal_label.setText(f"Subtotal: Bs {subtotal:.2f}")
        self.total_label.setText(f"TOTAL: Bs {total:.2f}")
        
        self.checkout_btn.setEnabled(len(self.cart_items) > 0)
    
    def clear_cart(self):
        """Clear cart"""
        if self.cart_items:
            reply = QMessageBox.question(
                self,
                "Limpiar Carrito",
                "¿Está seguro de limpiar el carrito?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.cart_items.clear()
                self.update_cart_display()
    
    def complete_sale(self):
        """Complete sale"""
        if not self.cart_items:
            return
        
        # Get client name
        cliente = self.client_input.text().strip() or "Cliente General"
        
        # Get payment method
        metodo_pago = self.payment_combo.currentText().lower()
        
        # Create sale
        sale_id = Sale.create(
            usuario_id=self.current_user.id,
            items=self.cart_items,
            cliente=cliente,
            metodo_pago=metodo_pago
        )
        
        if sale_id:
            # Get sale details
            sale = Sale.get_by_id(sale_id)
            
            # Show success message
            QMessageBox.information(
                self,
                "Venta Completada",
                f"✅ Venta completada exitosamente!\n\n"
                f"Factura: {sale.numero_factura}\n"
                f"Total: Bs {sale.total:.2f}\n"
                f"Método: {sale.metodo_pago.title()}\n\n"
                f"¿Desea imprimir la factura?"
            )
            
            # Clear cart
            self.cart_items.clear()
            self.client_input.clear()
            self.update_cart_display()
            
            # Reload products (stock updated)
            self.load_products()
        else:
            QMessageBox.critical(
                self,
                "Error",
                "No se pudo completar la venta.\nIntente nuevamente."
            )
