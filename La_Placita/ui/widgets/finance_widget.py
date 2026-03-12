"""
Finance Widget - Complete Financial Analysis
Monthly revenue, expenses, profit margin, and detailed product analysis
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
    QScrollArea, QHeaderView, QDialog, QDialogButtonBox,
    QLineEdit, QDoubleSpinBox, QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor
from datetime import datetime
from database.connection import db
from utils.excel_exporter import ExcelExporter
from utils.pdf_generator import InvoiceGenerator
import calendar


class StatCard(QFrame):
    """Financial stat card"""
    
    def __init__(self, icon, value, label, color="#FF6B35", editable=False, on_edit=None):
        super().__init__()
        self.value_text = value
        self.editable = editable
        self.on_edit = on_edit
        
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
        
        # Top row: Icon + Edit button
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
                    min-width: 26px;
                    max-width: 26px;
                    min-height: 26px;
                    max-height: 26px;
                    margin: 0px 0px 0px 80px;
                }
                QPushButton:hover { background-color: #2563EB; }
            """)
            edit_btn.clicked.connect(self.on_edit)
            top_layout.addWidget(edit_btn)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #1F2937;
        """)
        layout.addWidget(self.value_label)
        
        # Label
        label_label = QLabel(label)
        label_label.setStyleSheet("""
            font-size: 14px;
            color: black; 
            font-weight: 500;
        """)
        layout.addWidget(label_label)
        
        layout.addStretch()
    
    def update_value(self, value):
        """Update the displayed value"""
        self.value_text = value
        self.value_label.setText(value)


class CostDialog(QDialog):
    """Dialog for editing costs"""
    
    def __init__(self, cost_type, current_value=0, parent=None):
        super().__init__(parent)
        self.cost_type = cost_type
        self.setWindowTitle(f"Editar {cost_type}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Title
        title = QLabel(f"💰 Configurar {cost_type}")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1F2937;")
        layout.addWidget(title)
        
        # Value input
        value_layout = QVBoxLayout()
        value_label = QLabel(f"Monto mensual de {cost_type.lower()}:")
        value_label.setStyleSheet("font-weight: 600; color: #4B5563;")
        value_layout.addWidget(value_label)
        
        self.value_input = QDoubleSpinBox()
        self.value_input.setPrefix("Bs ")
        self.value_input.setMaximum(999999.99)
        self.value_input.setDecimals(2)
        self.value_input.setValue(current_value)
        self.value_input.setStyleSheet("font-size: 16px; padding: 8px;")
        value_layout.addWidget(self.value_input)
        
        layout.addLayout(value_layout)
        
        # Info text
        info_text = f"""
        <b>Ejemplos de {cost_type.lower()}:</b><br>
        {'• Alquiler<br>• Salarios<br>• Servicios básicos<br>• Seguros' if 'Fijo' in cost_type else '• Materia prima<br>• Comisiones<br>• Marketing<br>• Mantenimiento'}
        """
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #6B7280; font-size: 13px; padding: 12px; background-color: #F9FAFB; border-radius: 8px;")
        layout.addWidget(info_label)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_value(self):
        return self.value_input.value()


class FinanceWidget(QWidget):
    """Complete financial analysis widget"""
    
    def __init__(self):
        super().__init__()
        self.costo_fijo = 0
        self.costo_variable = 0
        self.current_month = datetime.now().month
        self.current_year = datetime.now().year
        self.load_costs()
        self.init_ui()
        self.update_stats()
    
    def init_ui(self):
        """Initialize UI"""
        # Main scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        # Content
        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(40, 30, 40, 40)
        main_layout.setSpacing(30)
        
        # Header
        self._create_header(main_layout)
        
        # Main stats (4 cards)
        self.main_stats_layout = QHBoxLayout()
        self.main_stats_layout.setSpacing(20)
        main_layout.addLayout(self.main_stats_layout)
        
        # Cost stats (2 cards)
        self.cost_stats_layout = QHBoxLayout()
        self.cost_stats_layout.setSpacing(20)
        main_layout.addLayout(self.cost_stats_layout)
        
        # Create costs cards
        self._create_cost_cards()
        
        # Financial analysis section
        self._create_analysis_section(main_layout)
        
        scroll.setWidget(content)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
    
    def _create_header(self, layout):
        """Create header"""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel("Finanzas")
        title.setStyleSheet("font-size: 32px; font-weight: 700; color: #1F2937;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("Análisis financiero completo y control de gastos")
        subtitle.setStyleSheet("font-size: 14px; color: #6B7280;")
        header_layout.addWidget(subtitle)
        
        layout.addLayout(header_layout)
    
    def _create_cost_cards(self):
        """Create editable cost cards"""
        self.costo_fijo_card = StatCard(
            "🏢",
            f"Bs {self.costo_fijo:.2f}",
            "Costo Fijo Mensual",
            "#3B82F6",
            editable=True,
            on_edit=self.edit_costo_fijo
        )
        self.cost_stats_layout.addWidget(self.costo_fijo_card)
        
        self.costo_variable_card = StatCard(
            "📊",
            f"Bs {self.costo_variable:.2f}",
            "Costo Variable Mensual",
            "#F59E0B",
            editable=True,
            on_edit=self.edit_costo_variable
        )
        self.cost_stats_layout.addWidget(self.costo_variable_card)
        
        # Delete button
        delete_btn = QPushButton("🗑️ Eliminar Costos")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                padding: 16px 24px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                min-width: 200px;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        delete_btn.clicked.connect(self.delete_costs)
        self.cost_stats_layout.addWidget(delete_btn)
        
        self.cost_stats_layout.addStretch()
    
    def _create_analysis_section(self, layout):
        """Create financial analysis table section"""
        # Section frame
        analysis_frame = QFrame()
        analysis_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        analysis_layout = QVBoxLayout(analysis_frame)
        analysis_layout.setSpacing(20)
        
        # Header with controls
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("📊 Análisis Financiero")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1F2937;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Month selector
        month_label = QLabel("Mes:")
        month_label.setStyleSheet("font-weight: 600; color: #4B5563;")
        header_layout.addWidget(month_label)
        
        self.month_combo = QComboBox()
        months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        for i, month in enumerate(months, 1):
            self.month_combo.addItem(month, i)
        self.month_combo.setCurrentIndex(self.current_month - 1)
        self.month_combo.currentIndexChanged.connect(self.on_month_changed)
        header_layout.addWidget(self.month_combo)
        
        # Year selector
        year_label = QLabel("Año:")
        year_label.setStyleSheet("font-weight: 600; color: #4B5563;")
        header_layout.addWidget(year_label)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2020, 2030)
        self.year_spin.setValue(self.current_year)
        self.year_spin.valueChanged.connect(self.on_year_changed)
        header_layout.addWidget(self.year_spin)
        
        # Export buttons
        excel_btn = QPushButton("📊 Excel")
        excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        excel_btn.clicked.connect(self.export_excel)
        header_layout.addWidget(excel_btn)
        
        pdf_btn = QPushButton("📄 PDF")
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        pdf_btn.clicked.connect(self.export_pdf)
        header_layout.addWidget(pdf_btn)
        
        analysis_layout.addLayout(header_layout)

        # Category filter row (separate row below)
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        category_label = QLabel("Filtrar por categoría:")
        category_label.setStyleSheet("font-weight: 600; color: #4B5563; font-size: 14px;")
        filter_layout.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Todas las categorías", None)

        # Load categories from database
        query_categories = "SELECT id, nombre FROM categorias WHERE activo = 1 ORDER BY nombre"
        categories = db.fetch_all(query_categories)
        for cat in categories:
            self.category_combo.addItem(cat['nombre'], cat['id'])

        self.category_combo.currentIndexChanged.connect(self.on_category_changed)
        self.category_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                background-color: white;
                min-width: 220px;
                font-size: 14px;
            }
            QComboBox:hover {
                border-color: #FF6B35;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        filter_layout.addWidget(self.category_combo)

        filter_layout.addStretch()

        analysis_layout.addLayout(filter_layout)
        
        # Table
        self.analysis_table = QTableWidget()
        self.analysis_table.setColumnCount(5)
        self.analysis_table.setHorizontalHeaderLabels([
            "Mes/Producto", "Ingresos (Bs)", "Gastos (Bs)", 
            "Ganancia Neta (Bs)", "Margen (%)"
        ])
        
        self.analysis_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.analysis_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.analysis_table.setAlternatingRowColors(True)
        self.analysis_table.verticalHeader().setVisible(False)
        self.analysis_table.setMinimumHeight(500)
        
        # Style the table
        self.analysis_table.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #E5E7EB;
                font-size: 13px;
                background-color: white;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #E5E7EB;
            }
            QTableWidget::item:alternate {
                background-color: #F9FAFB;
            }
            
        """)
        
        # Configure header
        header = self.analysis_table.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView {
                background-color: white;
                color: white;
                font-weight: bold;
                font-size: 20px;
                padding: 10px 10px;
                border: none;
                text-align: center;
            }

        """)
        
        # Set header properties
        header.setMinimumHeight(65)
        header.setMaximumHeight(65)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        header.setStretchLastSection(True)
        
        # Column widths
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # Set fixed widths for columns
        self.analysis_table.setColumnWidth(1, 160)
        self.analysis_table.setColumnWidth(2, 150)
        self.analysis_table.setColumnWidth(3, 190)
        self.analysis_table.setColumnWidth(4, 130)
        
        analysis_layout.addWidget(self.analysis_table)
        
        layout.addWidget(analysis_frame)
    
    def load_costs(self):
        """Load costs from database"""
        # Check if gastos table has data for this month
        query = """
            SELECT tipo, SUM(monto) as total
            FROM gastos
            WHERE strftime('%Y-%m', fecha_gasto) = ?
            GROUP BY tipo
        """
        month_str = f"{self.current_year}-{self.current_month:02d}"
        results = db.fetch_all(query, (month_str,))
        
        for row in results:
            if row['tipo'] == 'fijo':
                self.costo_fijo = float(row['total'])
            elif row['tipo'] == 'variable':
                self.costo_variable = float(row['total'])
    
    def save_costs(self):
        """Save costs to database"""
        # Delete existing costs for current month
        delete_query = "DELETE FROM gastos WHERE strftime('%Y-%m', fecha_gasto) = ?"
        month_str = f"{self.current_year}-{self.current_month:02d}"
        db.execute(delete_query, (month_str,))
        
        # Insert new costs
        fecha_gasto = f"{self.current_year}-{self.current_month:02d}-01"
        
        if self.costo_fijo > 0:
            query = """
                INSERT INTO gastos (concepto, monto, tipo, fecha_gasto, usuario_id)
                VALUES (?, ?, ?, ?, ?)
            """
            db.execute(query, ('Costos Fijos Mensuales', self.costo_fijo, 'fijo', fecha_gasto, 1))
        
        if self.costo_variable > 0:
            query = """
                INSERT INTO gastos (concepto, monto, tipo, fecha_gasto, usuario_id)
                VALUES (?, ?, ?, ?, ?)
            """
            db.execute(query, ('Costos Variables Mensuales', self.costo_variable, 'variable', fecha_gasto, 1))
    
    def edit_costo_fijo(self):
        """Edit fixed cost"""
        dialog = CostDialog("Costo Fijo", self.costo_fijo, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.costo_fijo = dialog.get_value()
            self.save_costs()
            self.costo_fijo_card.update_value(f"Bs {self.costo_fijo:.2f}")
            self.update_stats()
            self.update_analysis_table()
    
    def edit_costo_variable(self):
        """Edit variable cost"""
        dialog = CostDialog("Costo Variable", self.costo_variable, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.costo_variable = dialog.get_value()
            self.save_costs()
            self.costo_variable_card.update_value(f"Bs {self.costo_variable:.2f}")
            self.update_stats()
            self.update_analysis_table()
    
    def delete_costs(self):
        """Delete all costs"""
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            "¿Está seguro de eliminar todos los costos del mes actual?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.costo_fijo = 0
            self.costo_variable = 0
            self.save_costs()
            self.costo_fijo_card.update_value(f"Bs {self.costo_fijo:.2f}")
            self.costo_variable_card.update_value(f"Bs {self.costo_variable:.2f}")
            self.update_stats()
            self.update_analysis_table()
            QMessageBox.information(self, "Éxito", "Costos eliminados correctamente")
    
    def update_stats(self):
        """Update main stat cards"""
        # Clear existing
        while self.main_stats_layout.count():
            child = self.main_stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Get current month data
        month_str = f"{self.current_year}-{self.current_month:02d}"
        
        # Ingresos del mes
        query_income = """
            SELECT COALESCE(SUM(total), 0) as total
            FROM ventas
            WHERE strftime('%Y-%m', fecha_venta) = ? AND estado = 'completada'
        """
        income_result = db.fetch_one(query_income, (month_str,))
        ingresos = float(income_result['total']) if income_result else 0
        
        # Gastos del mes
        

        # Get total product costs ONLY (sum of all product costs)
        query_costs = """
            SELECT COALESCE(SUM(dv.cantidad * p.costo), 0) as total_costo
            FROM detalle_ventas dv
            JOIN productos p ON dv.producto_id = p.id
            JOIN ventas v ON dv.venta_id = v.id
            WHERE strftime('%Y-%m', v.fecha_venta) = ? AND v.estado = 'completada'
        """
        costs_result = db.fetch_one(query_costs, (month_str,))
        gastos = float(costs_result['total_costo']) if costs_result else 0
        
        # Ganancia neta
        ganancia = ingresos - gastos
        
        # Margen de ganancia
        margen = (ganancia / ingresos * 100) if ingresos > 0 else 0
        
        # Card 1: Ingresos
        card1 = StatCard("💰", f"Bs {ingresos:.2f}", "Ingresos del Mes", "#10B981")
        self.main_stats_layout.addWidget(card1)
        
        # Card 2: Gastos
        card2 = StatCard("💸", f"Bs {gastos:.2f}", "Gastos del Mes", "#EF4444")
        self.main_stats_layout.addWidget(card2)
        
        # Card 3: Ganancia Neta
        color_ganancia = "#10B981" if ganancia >= 0 else "#EF4444"
        card3 = StatCard("📈", f"Bs {ganancia:.2f}", "Ganancia Neta", color_ganancia)
        self.main_stats_layout.addWidget(card3)
        
        # Card 4: Margen
        color_margen = "#10B981" if margen >= 0 else "#EF4444"
        card4 = StatCard("📊", f"{margen:.1f}%", "Margen de Ganancia", color_margen)
        self.main_stats_layout.addWidget(card4)
        
        # Update table
        self.update_analysis_table()
    
    def update_analysis_table(self):
        """Update analysis table with monthly data and product breakdown"""
        month_str = f"{self.current_year}-{self.current_month:02d}"
        
        # Get monthly totals
        query_income = """
            SELECT COALESCE(SUM(total), 0) as total
            FROM ventas
            WHERE strftime('%Y-%m', fecha_venta) = ? AND estado = 'completada'
        """
        income_result = db.fetch_one(query_income, (month_str,))
        ingresos_mes = float(income_result['total']) if income_result else 0
        
        # Get total product costs ONLY (sum of all product costs)
        query_costs = """
            SELECT COALESCE(SUM(dv.cantidad * p.costo), 0) as total_costo
            FROM detalle_ventas dv
            JOIN productos p ON dv.producto_id = p.id
            JOIN ventas v ON dv.venta_id = v.id
            WHERE strftime('%Y-%m', v.fecha_venta) = ? AND v.estado = 'completada'
        """
        costs_result = db.fetch_one(query_costs, (month_str,))
        gastos_productos_mes = float(costs_result['total_costo']) if costs_result else 0
        
        # For summary row: show only product costs (NOT including fixed/variable)
        ganancia_mes = ingresos_mes - gastos_productos_mes
        margen_mes = (ganancia_mes / ingresos_mes * 100) if ingresos_mes > 0 else 0
        
        # Get product details grouped by category with optional filter
        selected_category_id = self.category_combo.currentData()
        
        query_products = """
            SELECT 
                c.nombre as categoria,
                p.nombre as producto,
                p.costo as costo_unitario,
                SUM(dv.cantidad) as unidades_vendidas,
                SUM(dv.subtotal) as ingresos,
                SUM(dv.cantidad * p.costo) as gastos
            FROM detalle_ventas dv
            JOIN productos p ON dv.producto_id = p.id
            JOIN categorias c ON p.categoria_id = c.id
            JOIN ventas v ON dv.venta_id = v.id
            WHERE strftime('%Y-%m', v.fecha_venta) = ? AND v.estado = 'completada'
        """

        # Add category filter if selected
        params = [month_str]
        if selected_category_id is not None:
            query_products += " AND c.id = ?"
            params.append(selected_category_id)

        query_products += """
            GROUP BY c.nombre, p.nombre, p.costo
            ORDER BY c.nombre, ingresos DESC
        """
        
        products = db.fetch_all(query_products, tuple(params))
        
        # Build rows with category headers
        rows_to_add = []
        current_category = None
        
        for product in products:
            categoria = product['categoria']
            
            # Add category header row if new category
            if categoria != current_category:
                current_category = categoria
                rows_to_add.append({
                    'type': 'category',
                    'label': f" {categoria}"
                })
            
            # Add product row
            ingresos_prod = float(product['ingresos'])
            gastos_prod = float(product['gastos'])
            ganancia_prod = ingresos_prod - gastos_prod
            margen_prod = (ganancia_prod / ingresos_prod * 100) if ingresos_prod > 0 else 0
            unidades = int(product['unidades_vendidas'])
            
            rows_to_add.append({
                'type': 'product',
                'label': f"  └─ {product['producto']}",
                'ingresos': ingresos_prod,
                'gastos': gastos_prod,
                'ganancia': ganancia_prod,
                'margen': margen_prod,
                'unidades': unidades
            })
        
        # Calculate total rows: 1 summary + category headers + products
        total_rows = 1 + len(rows_to_add)
        self.analysis_table.setRowCount(total_rows)
        
        # Row 0: Monthly summary
        month_name = self.month_combo.currentText()
        self._set_table_row(
            row=0,
            label=f" {month_name} {self.current_year}",
            ingresos=ingresos_mes,
            gastos=gastos_productos_mes,
            ganancia=ganancia_mes,
            margen=margen_mes,
            unidades=None,
            is_summary=True
        )
        
        # Add all rows (category headers + products)
        for i, row_data in enumerate(rows_to_add, 1):
            if row_data['type'] == 'category':
                # Category header row - only label, no numbers
                self._set_category_row(i, row_data['label'])
            else:
                # Product row with all data
                self._set_table_row(
                    row=i,
                    label=row_data['label'],
                    ingresos=row_data['ingresos'],
                    gastos=row_data['gastos'],
                    ganancia=row_data['ganancia'],
                    margen=row_data['margen'],
                    unidades=row_data['unidades'],
                    is_summary=False
                )
    
    def _set_category_row(self, row, label):
        """Set category header row (only label, no numbers)"""
        # Label only
        label_item = QTableWidgetItem(label)
        label_item.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        label_item.setForeground(QColor("#1F2937"))
        label_item.setBackground(QColor("#F3F4F6"))
        self.analysis_table.setItem(row, 0, label_item)
        
        # Empty cells for other columns with same background
        for col in range(1, 5):
            empty_item = QTableWidgetItem("")
            empty_item.setBackground(QColor("#F3F4F6"))
            self.analysis_table.setItem(row, col, empty_item)
        
        # Set row height
        self.analysis_table.setRowHeight(row, 45)
    
    
    def _set_table_row(self, row, label, ingresos, gastos, ganancia, margen, unidades, is_summary=False):
        """Set table row data with optional units sold"""
        # Column 0: Label (Mes/Producto) with units
        if unidades is not None:
            label_text = f"{label}  ({unidades} unidades)"
        else:
            label_text = label
        
        label_item = QTableWidgetItem(label_text)
        
        if is_summary:
            # Summary row (header row for month)
            font = QFont("Segoe UI", 16, QFont.Weight.Bold)
            label_item.setFont(font)
            label_item.setBackground(QColor("#F9FAFB"))
            label_item.setForeground(QColor("#1F2937"))
        else:
            # Product rows
            if "📁" in label:
                # Category header
                font = QFont("Segoe UI", 13, QFont.Weight.Bold)
                label_item.setFont(font)
                label_item.setForeground(QColor("#1F2937"))
                label_item.setBackground(QColor("#F3F4F6"))
            else:
                # Regular product
                font = QFont("Segoe UI", 13)
                label_item.setFont(font)
                label_item.setForeground(QColor("#4B5563"))
        
        self.analysis_table.setItem(row, 0, label_item)
        
        # Column 1: Ingresos
        ing_item = QTableWidgetItem(f"Bs {ingresos:,.2f}")
        ing_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ing_item.setForeground(QColor("#10B981"))
        
        if is_summary:
            ing_item.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            ing_item.setBackground(QColor("#ECFDF5"))
        elif "📁" in label:
            ing_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            ing_item.setBackground(QColor("#F3F4F6"))
        else:
            ing_item.setFont(QFont("Segoe UI", 12))
        
        self.analysis_table.setItem(row, 1, ing_item)
        
        # Column 2: Gastos
        gas_item = QTableWidgetItem(f"Bs {gastos:,.2f}")
        gas_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        gas_item.setForeground(QColor("#EF4444"))
        
        if is_summary:
            gas_item.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            gas_item.setBackground(QColor("#FEE2E2"))
        elif "📁" in label:
            gas_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            gas_item.setBackground(QColor("#F3F4F6"))
        else:
            gas_item.setFont(QFont("Segoe UI", 12))
        
        self.analysis_table.setItem(row, 2, gas_item)
        
        # Column 3: Ganancia Neta
        gan_item = QTableWidgetItem(f"Bs {ganancia:,.2f}")
        gan_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        gan_item.setForeground(QColor("#10B981" if ganancia >= 0 else "#EF4444"))
        
        if is_summary:
            gan_item.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            color_bg = "#ECFDF5" if ganancia >= 0 else "#FEE2E2"
            gan_item.setBackground(QColor(color_bg))
        elif "📁" in label:
            gan_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            gan_item.setBackground(QColor("#F3F4F6"))
        else:
            gan_item.setFont(QFont("Segoe UI", 12))
        
        self.analysis_table.setItem(row, 3, gan_item)
        
        # Column 4: Margen
        mar_item = QTableWidgetItem(f"{margen:.1f}%")
        mar_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        mar_item.setForeground(QColor("#10B981" if margen >= 0 else "#EF4444"))
        
        if is_summary:
            mar_item.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            color_bg = "#ECFDF5" if margen >= 0 else "#FEE2E2"
            mar_item.setBackground(QColor(color_bg))
        elif "📁" in label:
            mar_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            mar_item.setBackground(QColor("#F3F4F6"))
        else:
            mar_item.setFont(QFont("Segoe UI", 12))
        
        self.analysis_table.setItem(row, 4, mar_item)
        
        # Set row height
        if is_summary:
            self.analysis_table.setRowHeight(row, 75)
        elif "📁" in label:
            self.analysis_table.setRowHeight(row, 55)
        else:
            self.analysis_table.setRowHeight(row, 48)
    
    def on_month_changed(self):
        """Handle month change"""
        self.current_month = self.month_combo.currentData()
        self.load_costs()
        self.costo_fijo_card.update_value(f"Bs {self.costo_fijo:.2f}")
        self.costo_variable_card.update_value(f"Bs {self.costo_variable:.2f}")
        self.update_stats()
    
    def on_year_changed(self):
        """Handle year change"""
        self.current_year = self.year_spin.value()
        self.load_costs()
        self.costo_fijo_card.update_value(f"Bs {self.costo_fijo:.2f}")
        self.costo_variable_card.update_value(f"Bs {self.costo_variable:.2f}")
        self.update_stats()
    def on_category_changed(self):
        """Handle category filter change"""
        self.update_analysis_table()
    
    def export_excel(self):
        """Export to Excel"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            
            wb = Workbook()
            ws = wb.active
            ws.title = f"Finanzas {self.month_combo.currentText()}"
            
            # Header
            headers = ["Mes/Producto", "Ingresos (Bs)", "Gastos (Bs)", "Ganancia Neta (Bs)", "Margen (%)"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(1, col, header)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="FF6B35", end_color="FF6B35", fill_type="solid")
                cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Data
            for row in range(self.analysis_table.rowCount()):
                for col in range(5):
                    item = self.analysis_table.item(row, col)
                    if item:
                        ws.cell(row + 2, col + 1, item.text())
            
            # Auto-width
            for col in ws.columns:
                max_length = 0
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                ws.column_dimensions[col[0].column_letter].width = max_length + 2
            
            # Save
            filename = f"finanzas_{self.current_year}_{self.current_month:02d}.xlsx"
            filepath = f"{filename}"
            wb.save(filepath)
            
            QMessageBox.information(self, "Éxito", f"Excel generado:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar Excel:\n{str(e)}")
    
    def export_pdf(self):
        """Export to PDF"""
        QMessageBox.information(self, "PDF", "Generación de PDF en desarrollo")