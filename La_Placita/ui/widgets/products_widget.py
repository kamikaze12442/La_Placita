"""
Products Widget
Complete product management with CRUD operations
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit,
    QHeaderView
)
from PySide6.QtCore import Qt
from models.product import Product, Category


class ProductDialog(QDialog):
    """Dialog for adding/editing products"""
    
    def __init__(self, product=None, parent=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle("Editar Producto" if product else "Agregar Producto")
        self.setMinimumWidth(500)
        self.init_ui()
        
        if product:
            self.load_product_data()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Form
        form_layout = QFormLayout()
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Hamburguesa Clásica")
        form_layout.addRow("Nombre:*", self.name_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("Descripción del producto...")
        form_layout.addRow("Descripción:", self.description_input)
        
        # Category
        self.category_combo = QComboBox()
        self.load_categories()
        form_layout.addRow("Categoría:*", self.category_combo)
        
        # Price
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.01, 99999.99)
        self.price_input.setDecimals(2)
        self.price_input.setPrefix("Bs ")
        form_layout.addRow("Precio:*", self.price_input)
        
        # Cost
        self.cost_input = QDoubleSpinBox()
        self.cost_input.setRange(0.00, 99999.99)
        self.cost_input.setDecimals(2)
        self.cost_input.setPrefix("Bs ")
        form_layout.addRow("Costo:", self.cost_input)
        
        # Stock
        self.stock_input = QSpinBox()
        self.stock_input.setRange(0, 99999)
        form_layout.addRow("Stock:*", self.stock_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_categories(self):
        """Load categories"""
        categories = Category.get_all()
        for category in categories:
            self.category_combo.addItem(
                f"{category.icono} {category.nombre}",
                category.id
            )
    
    def load_product_data(self):
        """Load product data into form"""
        self.name_input.setText(self.product.nombre)
        self.description_input.setPlainText(self.product.descripcion or "")
        self.price_input.setValue(self.product.precio)
        self.cost_input.setValue(self.product.costo)
        self.stock_input.setValue(self.product.stock)
        
        # Set category
        for i in range(self.category_combo.count()):
            if self.category_combo.itemData(i) == self.product.categoria_id:
                self.category_combo.setCurrentIndex(i)
                break
    
    def get_product_data(self):
        """Get product data from form"""
        return {
            'nombre': self.name_input.text().strip(),
            'descripcion': self.description_input.toPlainText().strip(),
            'categoria_id': self.category_combo.currentData(),
            'precio': self.price_input.value(),
            'costo': self.cost_input.value(),
            'stock': self.stock_input.value()
        }
    
    def validate(self):
        """Validate form"""
        data = self.get_product_data()
        
        if not data['nombre']:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio")
            return False
        
        if data['precio'] <= 0:
            QMessageBox.warning(self, "Error", "El precio debe ser mayor a 0")
            return False
        
        if not data['categoria_id']:
            QMessageBox.warning(self, "Error", "Debe seleccionar una categoría")
            return False
        
        return True
    
    def accept(self):
        """Accept dialog"""
        if self.validate():
            super().accept()


class ProductsWidget(QWidget):
    """Products management widget"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_products()
    
    def init_ui(self):
        """Initialize user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("📦 Gestión de Productos")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Add button
        add_btn = QPushButton("➕ Agregar Producto")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #E55A2B;
            }
        """)
        add_btn.clicked.connect(self.add_product)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Search and filters
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar productos...")
        self.search_input.textChanged.connect(self.search_products)
        filter_layout.addWidget(self.search_input)
        
        self.category_filter = QComboBox()
        self.category_filter.setMinimumWidth(200)
        self.load_category_filter()
        self.category_filter.currentIndexChanged.connect(self.filter_by_category)
        filter_layout.addWidget(self.category_filter)
        
        layout.addLayout(filter_layout)
        
        # Products table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Categoría", "Precio", "Costo", "Stock", "Acciones"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 150)
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(100)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table)
        
        # Stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #6B7280; font-size: 14px;")
        layout.addWidget(self.stats_label)
    
    def load_category_filter(self):
        """Load categories into filter"""
        self.category_filter.clear()
        
        self.category_filter.addItem("📦 Todas las categorías", None)
        
        categories = Category.get_all()
        for category in categories:
            self.category_filter.addItem(
                f"{category.icono} {category.nombre}",
                category.id
            )
    
    def load_products(self, category_id=None):
        """Load products into table"""
        # Get products
        if category_id:
            products = Product.get_by_category(category_id)
        else:
            products = Product.get_all(activo_only=True)
        
        # Clear table
        self.table.setRowCount(0)
        
        # Populate table
        for product in products:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # ID
            id_item = QTableWidgetItem(str(product.id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, id_item)
            
            # Name
            name_item = QTableWidgetItem(product.nombre)
            if not product.activo:
                name_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 1, name_item)
            
            # Category
            category = Category.get_by_id(product.categoria_id)
            cat_name = f"{category.icono} {category.nombre}" if category else "Sin categoría"
            cat_item = QTableWidgetItem(cat_name)
            self.table.setItem(row, 2, cat_item)
            
            # Price
            price_item = QTableWidgetItem(f"Bs {product.precio:.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, price_item)
            
            # Cost
            cost_item = QTableWidgetItem(f"Bs {product.costo:.2f}")
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, cost_item)
            
            # Stock
            stock_item = QTableWidgetItem(str(product.stock))
            stock_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if product.stock == 0:
                stock_item.setForeground(Qt.GlobalColor.red)
            elif product.stock < 10:
                stock_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                stock_item.setForeground(Qt.GlobalColor.darkGreen)
            self.table.setItem(row, 5, stock_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 2, 5, 2)
            actions_layout.setSpacing(5)
            
            # Edit button
            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3B82F6;
                    color: white;
                    border-radius: 4px;
                    padding: 5px 10px;
                }
                QPushButton:hover { background-color: #2563EB; }
            """)
            edit_btn.clicked.connect(lambda checked=False, p=product: self.edit_product(p))
            actions_layout.addWidget(edit_btn)
            
            # Delete button
            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #EF4444;
                    color: white;
                    border-radius: 4px;
                    padding: 5px 10px;
                }
                QPushButton:hover { background-color: #DC2626; }
            """)
            delete_btn.clicked.connect(lambda checked=False, p=product: self.delete_product(p))
            actions_layout.addWidget(delete_btn)
            
            self.table.setCellWidget(row, 6, actions_widget)
        
        # Update stats
        total = len(products)
        activos = sum(1 for p in products if p.activo)
        sin_stock = sum(1 for p in products if p.stock == 0 and p.activo)
        
        self.stats_label.setText(
            f"Total: {total} productos | Activos: {activos} | Sin stock: {sin_stock}"
        )
    
    def filter_by_category(self, index):
        """Filter products by category"""
        category_id = self.category_filter.itemData(index)
        self.load_products(category_id)
    
    def search_products(self, text):
        """Search products"""
        if not text:
            category_id = self.category_filter.currentData()
            self.load_products(category_id)
            return
        
        products = Product.search(text)
        
        # Clear table
        self.table.setRowCount(0)
        
        # Show results (simplified, reuse load_products logic)
        for product in products:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(product.id)))
            self.table.setItem(row, 1, QTableWidgetItem(product.nombre))
            
            category = Category.get_by_id(product.categoria_id)
            cat_name = f"{category.icono} {category.nombre}" if category else "Sin categoría"
            self.table.setItem(row, 2, QTableWidgetItem(cat_name))
            self.table.setItem(row, 3, QTableWidgetItem(f"Bs {product.precio:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"Bs {product.costo:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(str(product.stock)))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 2, 5, 2)
            
            edit_btn = QPushButton("✏️")
            edit_btn.clicked.connect(lambda checked=False, p=product: self.edit_product(p))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.clicked.connect(lambda checked=False, p=product: self.delete_product(p))
            actions_layout.addWidget(delete_btn)
            
            self.table.setCellWidget(row, 6, actions_widget)
    
    def add_product(self):
        """Add new product"""
        dialog = ProductDialog(parent=self)
        
        if dialog.exec():
            data = dialog.get_product_data()
            product_id = Product.create(**data)
            
            if product_id:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Producto '{data['nombre']}' agregado correctamente"
                )
                self.load_products()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo agregar el producto"
                )
    
    def edit_product(self, product: Product):
        """Edit product"""
        dialog = ProductDialog(product=product, parent=self)
        
        if dialog.exec():
            data = dialog.get_product_data()
            success = Product.update(product.id, **data)
            
            if success:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Producto '{data['nombre']}' actualizado correctamente"
                )
                self.load_products()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo actualizar el producto"
                )
    
    def delete_product(self, product: Product):
        """Delete product"""
        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar el producto '{product.nombre}'?\n\n"
            f"Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = Product.delete(product.id)
            
            if success:
                QMessageBox.information(
                    self,
                    "Éxito",
                    "Producto eliminado correctamente"
                )
                category_id = self.category_filter.currentData()
                self.load_products(category_id)
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo eliminar el producto"
                )