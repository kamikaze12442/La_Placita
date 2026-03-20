"""
Users Widget
User management with CRUD operations
SEGURIDAD: Verificación de contraseña actual + confirmación + longitud mínima
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QComboBox, QHeaderView, QFrame
)
from PySide6.QtCore import Qt
from database.connection import db
from models.user import User, _verify_password


class UserDialog(QDialog):
    """Diálogo para agregar o editar usuarios"""

    MIN_PASSWORD_LENGTH = 8

    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = user  # None = nuevo usuario, User = edición
        self.setWindowTitle("Editar Usuario" if user else "Agregar Usuario")
        self.setMinimumWidth(440)
        self.init_ui()

        if user:
            self.load_user_data()

    def init_ui(self):
        """Inicializar interfaz"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # ── Datos generales ────────────────────────────────────────────
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre completo")
        form_layout.addRow("Nombre:*", self.name_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("usuario123")
        form_layout.addRow("Usuario:*", self.email_input)

        self.role_combo = QComboBox()
        self.role_combo.addItem("👨‍💼 Administrador", "admin")
        self.role_combo.addItem("👨‍💻 Cajero", "cajero")
        form_layout.addRow("Rol:*", self.role_combo)

        layout.addLayout(form_layout)

        # ── Sección contraseña ─────────────────────────────────────────
        pwd_frame = QFrame()
        pwd_frame.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        pwd_layout = QFormLayout(pwd_frame)
        pwd_layout.setSpacing(10)

        if self.user:
            # En edición: pedir contraseña actual primero
            section_label = QLabel("🔑 Cambio de contraseña (opcional)")
            section_label.setStyleSheet("font-weight: 600; color: #374151; font-size: 12px;")
            pwd_layout.addRow(section_label)

            self.current_password_input = QLineEdit()
            self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.current_password_input.setPlaceholderText("Ingrese contraseña actual para confirmar")
            pwd_layout.addRow("Contraseña actual:", self.current_password_input)

            hint = QLabel("Deja los tres campos vacíos si no deseas cambiar la contraseña.")
            hint.setStyleSheet("color: #9CA3AF; font-size: 11px;")
            hint.setWordWrap(True)
            pwd_layout.addRow(hint)
        else:
            self.current_password_input = None
            section_label = QLabel("🔑 Contraseña")
            section_label.setStyleSheet("font-weight: 600; color: #374151; font-size: 12px;")
            pwd_layout.addRow(section_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(
            "Mínimo 8 caracteres" if not self.user else "Nueva contraseña"
        )
        pwd_layout.addRow("Nueva contraseña:" if self.user else "Contraseña:*", self.password_input)

        self.password_confirm_input = QLineEdit()
        self.password_confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_confirm_input.setPlaceholderText("Repetir contraseña")
        pwd_layout.addRow("Confirmar:*", self.password_confirm_input)

        layout.addWidget(pwd_frame)

        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_user_data(self):
        """Cargar datos del usuario en el formulario (modo edición)"""
        self.name_input.setText(self.user.nombre)
        self.email_input.setText(self.user.email)
        self.role_combo.setCurrentIndex(0 if self.user.rol == "admin" else 1)
        # Campos de contraseña vacíos intencionalmente

    def _get_stored_hash(self) -> str:
        """Obtener el hash almacenado del usuario actual desde la BD."""
        result = db.fetch_one(
            "SELECT password FROM usuarios WHERE id = ?", (self.user.id,)
        )
        return result['password'] if result else ""

    def get_user_data(self) -> dict:
        """Construir diccionario con los datos del formulario."""
        data = {
            'nombre': self.name_input.text().strip(),
            'email': self.email_input.text().strip(),
            'rol': self.role_combo.currentData()
        }
        password = self.password_input.text().strip()
        if password:
            data['password'] = password  # User.update hashea internamente
        return data

    def validate(self) -> bool:
        """Validar formulario. Retorna True solo si todo está correcto."""
        data = self.get_user_data()

        # ── Campos obligatorios ────────────────────────────────────────
        if not data['nombre']:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
            self.name_input.setFocus()
            return False

        if not data['email']:
            QMessageBox.warning(self, "Error", "Ingrese un nombre válido.")
            self.email_input.setFocus()
            return False

        # ── Validación de contraseña ───────────────────────────────────
        new_pwd     = self.password_input.text().strip()
        confirm_pwd = self.password_confirm_input.text().strip()
        current_pwd = self.current_password_input.text().strip() if self.current_password_input else None

        # Nuevo usuario: contraseña obligatoria
        if not self.user:
            if not new_pwd:
                QMessageBox.warning(self, "Error", "La contraseña es obligatoria.")
                self.password_input.setFocus()
                return False
            if len(new_pwd) < self.MIN_PASSWORD_LENGTH:
                QMessageBox.warning(
                    self, "Error",
                    f"La contraseña debe tener al menos {self.MIN_PASSWORD_LENGTH} caracteres."
                )
                return False
            if new_pwd != confirm_pwd:
                QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
                self.password_input.clear()
                self.password_confirm_input.clear()
                self.password_input.setFocus()
                return False

        # Edición: si escribió algo en cualquier campo de contraseña, validar todo
        if self.user and (new_pwd or confirm_pwd or current_pwd):

            # 1. Contraseña actual es obligatoria para el cambio
            if not current_pwd:
                QMessageBox.warning(
                    self, "Error",
                    "Debes ingresar tu contraseña actual para poder cambiarla."
                )
                self.current_password_input.setFocus()
                return False

            # 2. Verificar que la contraseña actual sea correcta
            stored_hash = self._get_stored_hash()
            if not _verify_password(current_pwd, stored_hash):
                QMessageBox.critical(
                    self, "Contraseña incorrecta",
                    "La contraseña actual ingresada no es correcta.\nNo se realizaron cambios."
                )
                self.current_password_input.clear()
                self.password_input.clear()
                self.password_confirm_input.clear()
                self.current_password_input.setFocus()
                return False

            # 3. Nueva contraseña con longitud mínima
            if len(new_pwd) < self.MIN_PASSWORD_LENGTH:
                QMessageBox.warning(
                    self, "Error",
                    f"La nueva contraseña debe tener al menos {self.MIN_PASSWORD_LENGTH} caracteres."
                )
                self.password_input.setFocus()
                return False

            # 4. Nueva contraseña y confirmación deben coincidir
            if new_pwd != confirm_pwd:
                QMessageBox.warning(self, "Error", "Las contraseñas nuevas no coinciden.")
                self.password_input.clear()
                self.password_confirm_input.clear()
                self.password_input.setFocus()
                return False

        return True

    def accept(self):
        """Aceptar solo si el formulario es válido."""
        if self.validate():
            super().accept()


# ──────────────────────────────────────────────────────────────────────────────

class UsersWidget(QWidget):
    """Widget de gestión de usuarios"""

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_users()

    def init_ui(self):
        """Inicializar interfaz"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("👥 Gestión de Usuarios")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #1F2937;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        add_btn = QPushButton("➕ Agregar Usuario")
        add_btn.clicked.connect(self.add_user)
        header_layout.addWidget(add_btn)
        layout.addLayout(header_layout)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Email", "Rol", "Estado", "Acciones"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(100)
        layout.addWidget(self.table)

    def load_users(self):
        """Cargar usuarios en la tabla"""
        users = User.get_all()
        self.table.setRowCount(len(users))

        for row, user in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(str(user.id)))
            self.table.setItem(row, 1, QTableWidgetItem(user.nombre))
            self.table.setItem(row, 2, QTableWidgetItem(user.email))
            self.table.setItem(row, 3, QTableWidgetItem(
                "👨‍💼 Admin" if user.rol == "admin" else "👨‍💻 Cajero"
            ))
            self.table.setItem(row, 4, QTableWidgetItem(
                "✅ Activo" if user.activo else "❌ Inactivo"
            ))

            # Botones de acción
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)

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

            toggle_btn = QPushButton("🔴" if user.activo else "🟢")
            toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3B82F6;
                    color: white;
                    border-radius: 4px;
                    padding: 5px 10px;
                }
                QPushButton:hover { background-color: #2563EB; }
            """)
            toggle_btn.clicked.connect(lambda checked=False, u=user: self.toggle_user_status(u))
            actions_layout.addWidget(toggle_btn)

            self.table.setCellWidget(row, 5, actions_widget)

    def add_user(self):
        """Agregar nuevo usuario"""
        dialog = UserDialog(parent=self)
        if dialog.exec():
            data = dialog.get_user_data()
            User.create(
                nombre=data['nombre'],
                email=data['email'],
                password=data['password'],
                rol=data['rol']
            )
            QMessageBox.information(self, "Éxito", f"Usuario '{data['nombre']}' creado correctamente.")
            self.load_users()

    def edit_user(self, user: User):
        """Editar usuario existente"""
        dialog = UserDialog(user=user, parent=self)
        if dialog.exec():
            data = dialog.get_user_data()
            User.update(user.id, **data)
            QMessageBox.information(self, "Éxito", f"Usuario '{data['nombre']}' actualizado correctamente.")
            self.load_users()

    def toggle_user_status(self, user: User):
        """Activar o desactivar usuario"""
        new_status = not user.activo
        action = "activar" if new_status else "desactivar"
        reply = QMessageBox.question(
            self, "Confirmar",
            f"¿Está seguro de {action} al usuario '{user.nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            User.update(user.id, activo=new_status)
            self.load_users()