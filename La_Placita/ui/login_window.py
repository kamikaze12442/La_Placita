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
from models.user import User, login


class LoginWindow(QDialog):
    """Login dialog window"""
    
    login_successful = Signal(object)  # Emits User object
    
    def __init__(self):
        super().__init__()
        self.user = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Restaurant POS - Login")
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
        logo_label = QLabel("🍽️")
        logo_font = QFont()
        logo_font.setPointSize(48)
        logo_label.setFont(logo_font)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(logo_label)
        
        # Title
        title = QLabel("Restaurant POS")
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
        form_layout.setSpacing(15)
        
        # Email field
        email_label = QLabel("Correo Electrónico")
        email_label.setStyleSheet("font-weight: 600; color: #4B5563;")
        form_layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Ingrese su correo")
        self.email_input.setText("admin@restaurant.com")  # Default for testing
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
        
        # Footer
        layout.addStretch()
        footer = QLabel("© 2025 Restaurant POS - Versión 1.0")
        footer.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
        
        self.setLayout(layout)
        
        # Apply card style to dialog
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 16px;
            }
        """)
    def toggle_password_visibility(self, state):
        """Show/Hide password text"""
        if state == Qt.CheckState.Checked.value:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def handle_login(self):
        """Handle login button click"""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        # Validate inputs
        if not email or not password:
            QMessageBox.warning(
                self,
                "Error de Login",
                "Por favor ingrese su correo y contraseña"
            )
            return
        
        # Attempt authentication
        user = login(email, password)
        
        if user:
            self.user = user
            self.login_successful.emit(user)
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Error de Login",
                "Correo o contraseña incorrectos.\n"
                "Por favor intente nuevamente."
            )
            self.password_input.clear()
            self.password_input.setFocus()
    
    def get_user(self):
        """Get authenticated user"""
        return self.user


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    from pathlib import Path
    import sys
    
    app = QApplication(sys.argv)
    
    # Load stylesheet with correct path
    style_path = Path(__file__).parent / 'styles' / 'material_style.qss'
    if style_path.exists():
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
        print("✓ Styles loaded")
    
    login_window = LoginWindow()
    if login_window.exec() == QDialog.DialogCode.Accepted:
        user = login_window.get_user()
        print(f"✓ Login successful: {user.nombre} ({user.rol})")
    else:
        print("Login cancelled")
    
    sys.exit()
