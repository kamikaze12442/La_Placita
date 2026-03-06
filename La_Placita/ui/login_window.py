"""
Login Window
Authentication interface for the application
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from models.user import login
from ui.reset_password_dialog import (
    ResetPasswordDialog,
    SetupMasterPasswordDialog,
    master_password_configured
)
from pathlib import Path


class LoginWindow(QDialog):
    """Login dialog window"""
    
    login_successful = Signal(object)  # Emits User object
    
    def __init__(self):
        super().__init__()
        self.user = None
        self.init_ui()
        """self._ensure_master_password()"""
    
    def _ensure_master_password(self):
        """
        Si no existe contraseña maestra, solicitar configurarla al arrancar.
        Esto ocurre solo la primera vez que se abre el sistema.
        """
        if not master_password_configured():
            QMessageBox.information(
                self,
                "Configuración inicial",
                "👋 Bienvenido.\n\n"
                "Para proteger el sistema, debes configurar una "
                "contraseña maestra antes de continuar.\n\n"
                "Esta contraseña te permitirá resetear el acceso de "
                "cualquier usuario si alguna vez olvidas tu contraseña.",
                QMessageBox.StandardButton.Ok
            )
            setup = SetupMasterPasswordDialog(self)
            setup.exec()  # No bloqueamos si cancela — puede configurarla después


    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Cafetería La Placita - Login")
        self.setFixedSize(450, 750)
        self.setModal(True)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Logo/Title section
        title_layout = QVBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.setSpacing(10)
        
        # App icon/logo
        logo_label = QLabel()
        logo_font = QFont()
        logo_font.setPointSize(48)
        logo_label.setFont(logo_font)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = Path(__file__).parent.parent / "assets" / "logo_laplacita.png"
        # Fallback: buscar en la carpeta del ejecutable también
        if not logo_path.exists():
            logo_path = Path(__file__).parent.parent.parent / "logo_laplacita.png"

        if logo_path.exists():
            pixmap = QPixmap(str(logo_path)).scaled(
                140, 140,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
        else:
            # Fallback texto si no encuentra la imagen
            logo_label.setText("☕")
            logo_label.setStyleSheet("font-size: 48px;")

        logo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_layout.addWidget(logo_label)



        # Title
        title = QLabel("Cafetería La Placita")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Sistema de Punto de Venta")
        subtitle.setStyleSheet("color: #6B7280; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(subtitle)
        
        layout.addLayout(title_layout)
        layout.addSpacing(20)
        
        # Login form
        form_layout = QVBoxLayout()
        form_layout.setSpacing(13)
        
        # Email field
        email_label = QLabel("Correo Electrónico")
        email_label.setStyleSheet("font-weight: 600; color: #4B5563;")
        form_layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Ingrese su correo")
        self.email_input.setText("gabi193@restaurant.com")  # Default for testing
        self.email_input.returnPressed.connect(self.handle_login)
        form_layout.addWidget(self.email_input)
        
       # Password field
        password_label = QLabel("Contraseña")
        password_label.setStyleSheet("font-weight: 600; color: #4B5563;")
        form_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Ingrese su contraseña")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setText("admin123")  # Default for testing
        self.password_input.returnPressed.connect(self.handle_login)
        form_layout.addWidget(self.password_input)

        show_pass_layout = QHBoxLayout()
        show_pass_layout.setContentsMargins(0, 4, 0, 0)
        show_pass_layout.setSpacing(6)

        self.show_password_cb = QCheckBox("Mostrar contraseña")
        self.show_password_cb.setStyleSheet("color: #6B7280; font-size: 11px;")
        self.show_password_cb.stateChanged.connect(self.toggle_password_visibility)

        show_pass_layout.addWidget(self.show_password_cb)
        show_pass_layout.addStretch()
        form_layout.addLayout(show_pass_layout)
        
        layout.addLayout(form_layout)
        layout.addSpacing(10)
        
        # Login button
        self.login_btn = QPushButton("Iniciar Sesión")
        self.login_btn.setObjectName("login_btn")
        self.login_btn.setStyleSheet("""
            QPushButton#login_btn {
                background-color: #FF6B35;
                color: white;
                padding: 12px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
                min-height: 45px;
            }
            QPushButton#login_btn:hover {
                background-color: #E55A2B;
            }
            QPushButton#login_btn:pressed {
                background-color: #CC4E24;
            }
        """)
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)
        
        # Info section
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #F3F4F6;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        # ── Botón ¿Olvidaste tu contraseña? ───────────────────────────
        forgot_btn = QPushButton("¿Olvidaste tu contraseña?")
        forgot_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6B7280;
                border: none;
                font-size: 12px;
                text-decoration: underline;
                padding: 4px;
            }
            QPushButton:hover  { color: #FF6B35; }
            QPushButton:pressed { color: #CC4E24; }
        """)
        forgot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_btn.clicked.connect(self.handle_forgot_password)
        layout.addWidget(forgot_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Footer ────────────────────────────────────────────────────
        layout.addStretch()
        footer = QLabel("© 2025 Cafetería La Placita - v1.0")
        footer.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        self.setLayout(layout)
        self.setStyleSheet("QDialog { background-color: white; border-radius: 16px; }")

        # ── Handlers ──────────────────────────────────────────────────────

    def toggle_password_visibility(self, state):
        if state == Qt.CheckState.Checked.value:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

    def handle_login(self):
        """Intentar autenticación con email y contraseña."""
        email    = self.email_input.text().strip()
        password = self.password_input.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Error", "Por favor ingrese su correo y contraseña.")
            return

        user = login(email, password)

        if user:
            self.user = user
            self.login_successful.emit(user)
            self.accept()
        else:
            QMessageBox.critical(
                self, "Error de Login",
                "Correo o contraseña incorrectos.\nPor favor intente nuevamente."
            )
            self.password_input.clear()
            self.password_input.setFocus()

    def handle_forgot_password(self):
        """Abrir diálogo de reseteo de contraseña."""
        if not master_password_configured():
            reply = QMessageBox.question(
                self,
                "Contraseña maestra no configurada",
                "Aún no tienes una contraseña maestra configurada.\n"
                "¿Deseas configurarla ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                setup = SetupMasterPasswordDialog(self)
                setup.exec()
            return

        dialog = ResetPasswordDialog(self)
        dialog.exec()

    def get_user(self):
        return self.user


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    from pathlib import Path
    import sys

    app = QApplication(sys.argv)

    style_path = Path(__file__).parent / 'styles' / 'material_style.qss'
    if style_path.exists():
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    login_window = LoginWindow()
    if login_window.exec() == QDialog.DialogCode.Accepted:
        user = login_window.get_user()
        print(f"✓ Login exitoso: {user.nombre} ({user.rol})")
    else:
        print("Login cancelado")

    sys.exit()
