"""
Users Widget
User management with CRUD operations
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QComboBox, QHeaderView
)
from PySide6.QtCore import Qt
from models.user import User


class UserDialog(QDialog):
    """Dialog for adding/editing users"""
    
    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Editar Usuario" if user else "Agregar Usuario")
        self.setMinimumWidth(400)
        self.init_ui()
        
        if user:
            self.load_user_data()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Form
        form_layout = QFormLayout()
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre completo")
        form_layout.addRow("Nombre:*", self.name_input)
        
        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("correo@ejemplo.com")
        form_layout.addRow("Email:*", self.email_input)
        
        # Password
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Contraseña" if not self.user else "Dejar vacío para no cambiar")
        form_layout.addRow("Contraseña:", self.password_input)
        
        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItem("👨‍💼 Administrador", "admin")
        self.role_combo.addItem("👨‍💻 Cajero", "cajero")
        form_layout.addRow("Rol:*", self.role_combo)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_user_data(self):
        """Load user data into form"""
        self.name_input.setText(self.user.nombre)
        self.email_input.setText(self.user.email)
        
        # Set role
        if self.user.rol == "admin":
            self.role_combo.setCurrentIndex(0)
        else:
            self.role_combo.setCurrentIndex(1)
    
    def get_user_data(self):
        """Get user data from form"""
        data = {
            'nombre': self.name_input.text().strip(),
            'email': self.email_input.text().strip(),
            'rol': self.role_combo.currentData()
        }
        
        # Only include password if it's set
        password = self.password_input.text().strip()
        if password:
            data['password'] = password
        
        return data
    
    def validate(self):
        """Validate form"""
        data = self.get_user_data()
        
        if not data['nombre']:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio")
            return False
        
        if not data['email']:
            QMessageBox.warning(self, "Error", "El email es obligatorio")
            return False
        
        if '@' not in data['email']:
            QMessageBox.warning(self, "Error", "Email inválido")
            return False
        
        # Password required for new users
        if not self.user and 'password' not in data:
            QMessageBox.warning(self, "Error", "La contraseña es obligatoria")
            return False
        
        return True
    
    def accept(self):
        """Accept dialog"""
        if self.validate():
            super().accept()


class UsersWidget(QWidget):
    """Users management widget"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_users()
    
    def init_ui(self):
        """Initialize user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("👥 Gestión de Usuarios")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Add button
        add_btn = QPushButton("➕ Agregar Usuario")
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
        add_btn.clicked.connect(self.add_user)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Users table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Email", "Rol", "Estado", "Acciones"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(150)
        self.table.setColumnWidth(5, 150)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table)
        
        # Stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #6B7280; font-size: 14px;")
        layout.addWidget(self.stats_label)
    
    def load_users(self):
        """Load users into table"""
        users = User.get_all()
        
        # Clear table
        self.table.setRowCount(0)
        
        # Populate table
        activos = 0
        
        for user in users:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # ID
            id_item = QTableWidgetItem(str(user.id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, id_item)
            
            # Name
            name_item = QTableWidgetItem(user.nombre)
            if not user.activo:
                name_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 1, name_item)
            
            # Email
            email_item = QTableWidgetItem(user.email)
            if not user.activo:
                email_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 2, email_item)
            
            # Role
            role_icons = {
                'admin': '👨‍💼',
                'cajero': '👨‍💻'
            }
            icon = role_icons.get(user.rol, '👤')
            role_item = QTableWidgetItem(f"{icon} {user.rol.title()}")
            role_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, role_item)
            
            # Status
            status_item = QTableWidgetItem("✅ Activo" if user.activo else "❌ Inactivo")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if user.activo:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
                activos += 1
            else:
                status_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 4, status_item)
            
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
            edit_btn.clicked.connect(lambda checked=False, u=user: self.edit_user(u))
            actions_layout.addWidget(edit_btn)
            
            # Toggle status button
            toggle_btn = QPushButton("🔄")
            toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F59E0B;
                    color: white;
                    border-radius: 4px;
                    padding: 5px 10px;
                }
                QPushButton:hover { background-color: #D97706; }
            """)
            toggle_btn.clicked.connect(lambda checked=False, u=user: self.toggle_user_status(u))
            actions_layout.addWidget(toggle_btn)
            
            self.table.setCellWidget(row, 5, actions_widget)
        
        # Update stats
        total = len(users)
        inactivos = total - activos
        
        self.stats_label.setText(
            f"Total: {total} usuarios | Activos: {activos} | Inactivos: {inactivos}"
        )
    
    def add_user(self):
        """Add new user"""
        dialog = UserDialog(parent=self)
        
        if dialog.exec():
            data = dialog.get_user_data()
            user_id = User.create(**data)
            
            if user_id:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Usuario '{data['nombre']}' agregado correctamente"
                )
                self.load_users()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo agregar el usuario.\nPosiblemente el email ya existe."
                )
    
    def edit_user(self, user: User):
        """Edit user"""
        dialog = UserDialog(user=user, parent=self)
        
        if dialog.exec():
            data = dialog.get_user_data()
            success = User.update(user.id, **data)
            
            if success:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Usuario '{data['nombre']}' actualizado correctamente"
                )
                self.load_users()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo actualizar el usuario"
                )
    
    def toggle_user_status(self, user: User):
        """Toggle user active status"""
        new_status = not user.activo
        status_text = "activar" if new_status else "desactivar"
        
        reply = QMessageBox.question(
            self,
            "Confirmar Cambio",
            f"¿Está seguro de {status_text} el usuario '{user.nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = User.update(user.id, activo=new_status)
            
            if success:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Usuario {'activado' if new_status else 'desactivado'} correctamente"
                )
                self.load_users()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo cambiar el estado del usuario"
                )
