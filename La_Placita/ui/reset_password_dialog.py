"""
Reset Password Dialog
Permite resetear la contraseña de cualquier usuario usando una contraseña maestra.
La contraseña maestra se guarda hasheada en la tabla configuracion.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QLabel, QPushButton, QDialogButtonBox, QMessageBox,
    QComboBox, QFrame
)
from PySide6.QtCore import Qt
import bcrypt
from typing import Optional
from database.connection import db
from models.user import User, _hash_password, _verify_password

# ── Clave usada en la tabla configuracion ─────────────────────────────────────
_MASTER_KEY = "master_reset_password"


def get_master_hash() -> Optional[str]:
    """Obtener el hash de la contraseña maestra desde configuracion."""
    result = db.fetch_one(
        "SELECT valor FROM configuracion WHERE clave = ?", (_MASTER_KEY,)
    )
    return result['valor'] if result else None


def set_master_password(plain: str):
    """Guardar o actualizar la contraseña maestra (hasheada) en configuracion."""
    hashed = _hash_password(plain)
    existing = db.fetch_one(
        "SELECT clave FROM configuracion WHERE clave = ?", (_MASTER_KEY,)
    )
    if existing:
        db.execute_query(
            "UPDATE configuracion SET valor = ? WHERE clave = ?",
            (hashed, _MASTER_KEY)
        )
    else:
        db.execute_query(
            "INSERT INTO configuracion (clave, valor, descripcion) VALUES (?, ?, ?)",
            (_MASTER_KEY, hashed, "Hash de contraseña maestra para reseteo de acceso")
        )


def master_password_configured() -> bool:
    """Indica si ya existe una contraseña maestra configurada."""
    return get_master_hash() is not None


# ──────────────────────────────────────────────────────────────────────────────

class SetupMasterPasswordDialog(QDialog):
    """
    Diálogo para configurar la contraseña maestra por primera vez.
    Se muestra automáticamente si aún no existe.
    """

    MIN_LENGTH = 10  # Más larga que las normales por ser la "llave maestra"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Configurar Contraseña Maestra")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Aviso informativo
        info = QFrame()
        info.setStyleSheet("""
            QFrame {
                background-color: #FFF7ED;
                border: 1px solid #FDBA74;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        info_layout = QVBoxLayout(info)
        info_lbl = QLabel(
            "🔑 <b>Contraseña Maestra</b><br>"
            "Esta contraseña permite resetear el acceso de cualquier usuario "
            "en caso de olvido. Guárdala en un lugar seguro — "
            "<b>no se puede recuperar si la pierdes.</b>"
        )
        info_lbl.setWordWrap(True)
        info_lbl.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(info_lbl)
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        self.master_input = QLineEdit()
        self.master_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.master_input.setPlaceholderText(f"Mínimo {self.MIN_LENGTH} caracteres")
        form.addRow("Contraseña maestra:*", self.master_input)

        self.master_confirm = QLineEdit()
        self.master_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.master_confirm.setPlaceholderText("Repetir contraseña maestra")
        form.addRow("Confirmar:*", self.master_confirm)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        pwd     = self.master_input.text().strip()
        confirm = self.master_confirm.text().strip()

        if len(pwd) < self.MIN_LENGTH:
            QMessageBox.warning(
                self, "Error",
                f"La contraseña maestra debe tener al menos {self.MIN_LENGTH} caracteres."
            )
            return
        if pwd != confirm:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
            self.master_input.clear()
            self.master_confirm.clear()
            self.master_input.setFocus()
            return

        set_master_password(pwd)
        QMessageBox.information(
            self, "Listo",
            "✅ Contraseña maestra configurada correctamente.\n"
            "Guárdala en un lugar seguro."
        )
        super().accept()


# ──────────────────────────────────────────────────────────────────────────────

class ResetPasswordDialog(QDialog):
    """
    Diálogo de reseteo de contraseña accesible desde el login.
    Flujo:
      1. Usuario selecciona su cuenta.
      2. Ingresa la contraseña maestra.
      3. Ingresa y confirma la nueva contraseña.
    """

    MIN_LENGTH = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔓 Resetear Contraseña")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Título
        title = QLabel("Resetear contraseña de usuario")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1F2937;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        # Selector de usuario
        self.user_combo = QComboBox()
        self._load_users()
        form.addRow("Usuario:", self.user_combo)

        layout.addLayout(form)

        # Sección contraseña maestra
        master_frame = QFrame()
        master_frame.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        master_layout = QFormLayout(master_frame)
        master_layout.setSpacing(10)

        master_lbl = QLabel("🔑 Verificación")
        master_lbl.setStyleSheet("font-weight: 600; color: #374151;")
        master_layout.addRow(master_lbl)

        self.master_input = QLineEdit()
        self.master_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.master_input.setPlaceholderText("Contraseña maestra del sistema")
        master_layout.addRow("Contraseña maestra:*", self.master_input)

        layout.addWidget(master_frame)

        # Sección nueva contraseña
        new_frame = QFrame()
        new_frame.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        new_layout = QFormLayout(new_frame)
        new_layout.setSpacing(10)

        new_lbl = QLabel("🔒 Nueva contraseña")
        new_lbl.setStyleSheet("font-weight: 600; color: #374151;")
        new_layout.addRow(new_lbl)

        self.new_pwd_input = QLineEdit()
        self.new_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pwd_input.setPlaceholderText(f"Mínimo {self.MIN_LENGTH} caracteres")
        new_layout.addRow("Nueva contraseña:*", self.new_pwd_input)

        self.confirm_pwd_input = QLineEdit()
        self.confirm_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pwd_input.setPlaceholderText("Repetir nueva contraseña")
        new_layout.addRow("Confirmar:*", self.confirm_pwd_input)

        layout.addWidget(new_frame)

        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Resetear contraseña")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_users(self):
        """Cargar usuarios activos en el combo."""
        users = User.get_all()
        for u in users:
            label = f"{'👨‍💼' if u.rol == 'admin' else '👨‍💻'} {u.nombre} ({u.email})"
            self.user_combo.addItem(label, u.id)

    def accept(self):
        master  = self.master_input.text().strip()
        new_pwd = self.new_pwd_input.text().strip()
        confirm = self.confirm_pwd_input.text().strip()

        # 1. Verificar contraseña maestra
        stored_hash = get_master_hash()
        if not stored_hash or not _verify_password(master, stored_hash):
            QMessageBox.critical(
                self, "Acceso denegado",
                "❌ La contraseña maestra es incorrecta."
            )
            self.master_input.clear()
            self.master_input.setFocus()
            return

        # 2. Validar nueva contraseña
        if len(new_pwd) < self.MIN_LENGTH:
            QMessageBox.warning(
                self, "Error",
                f"La nueva contraseña debe tener al menos {self.MIN_LENGTH} caracteres."
            )
            self.new_pwd_input.setFocus()
            return

        if new_pwd != confirm:
            QMessageBox.warning(self, "Error", "Las contraseñas nuevas no coinciden.")
            self.new_pwd_input.clear()
            self.confirm_pwd_input.clear()
            self.new_pwd_input.setFocus()
            return

        # 3. Actualizar contraseña — User.update hashea internamente
        user_id = self.user_combo.currentData()
        User.update(user_id, password=new_pwd)

        QMessageBox.information(
            self, "Éxito",
            "✅ Contraseña reseteada correctamente.\nYa puedes iniciar sesión con la nueva contraseña."
        )
        super().accept()