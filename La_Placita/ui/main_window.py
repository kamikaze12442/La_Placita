"""
Main Window
Main application window with sidebar navigation
ACTUALIZADO: Pestaña Inventario disponible para admin y cajero
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QMessageBox, QStatusBar, QScrollArea
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap
from pathlib import Path
from models.user import get_current_user, logout


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.current_user = get_current_user()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Cafetería La Placita - Sistema de Punto de Venta")
        self.setMinimumSize(1400, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.create_sidebar()
        main_layout.addWidget(self.sidebar)

        self.create_content_area()
        main_layout.addWidget(self.content_widget, stretch=1)

        self.create_status_bar()
        self.show_home_page()

    # ── Sidebar ───────────────────────────────────────────────────────

    def create_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(260)
        self.sidebar.setStyleSheet("QFrame#sidebar { background-color: #1F2937; }")

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # ── Logo ──────────────────────────────────────────────────────
        logo_frame = QFrame()
        logo_frame.setStyleSheet("background-color: #1F2937; padding: 16px 0px 10px 0px;")
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        logo_layout.setSpacing(10)
        logo_layout.setContentsMargins(16, 16, 16, 10)

        logo_lbl = QLabel()
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
            logo_lbl.setPixmap(pixmap)
        else:
            # Fallback texto si no encuentra la imagen
            logo_lbl.setText("☕")
            logo_lbl.setStyleSheet("font-size: 48px;")

        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        logo_layout.addWidget(logo_lbl)

        sidebar_layout.addWidget(logo_frame)

        # ── Info del usuario ──────────────────────────────────────────
        user_frame = QFrame()
        user_frame.setStyleSheet("""
            QFrame {
                background-color: #374151;
                border-radius: 8px;
                margin: 0px 12px 8px 12px;
                padding: 8px 12px;
            }
        """)
        user_layout = QVBoxLayout(user_frame)
        user_layout.setSpacing(2)
        user_layout.setContentsMargins(8, 8, 8, 8)

        user_lbl = QLabel(f"Bienvenido(a): {self.current_user.nombre}")
        user_lbl.setStyleSheet("color: #F9FAFB; font-size: 13px; font-weight: 600;")
        user_layout.addWidget(user_lbl)

        """ rol_icon = "👑" if self.current_user.rol == "admin" else "🧑‍💼"
        role_lbl = QLabel(f"{rol_icon}  {self.current_user.rol.title()}")
        role_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        user_layout.addWidget(role_lbl)"""

        sidebar_layout.addWidget(user_frame)

        # Divisor
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background-color: #374151; margin: 0px 12px;")
        div.setFixedHeight(1)
        sidebar_layout.addWidget(div)
        sidebar_layout.addSpacing(6)

        # ── Área scrollable de botones de navegación ──────────────────
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #374151;
                width: 4px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #6B7280;
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        nav_layout.setSpacing(2)

        self.nav_buttons = []

        def add_btn(icon, text, slot):
            btn = self.create_nav_button(icon, text)
            btn.clicked.connect(slot)
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        add_btn("🏠",  "Inicio",         self.show_home_page)
        if self.current_user.is_admin():
            add_btn("🛍️", "Productos",   self.show_products_page)
        add_btn("💰",  "Punto de Venta", self.show_pos_page)
        add_btn("🧾",  "Ventas",         self.show_sales_page)
        add_btn("🏦",  "Arqueo de Caja", self.show_arqueo_page)
        if self.current_user.is_admin():
            add_btn("📊", "Finanzas",    self.show_finance_page)
            add_btn("👥", "Usuarios",    self.show_users_page)
        add_btn("⚙️",  "Configuración",  self.show_settings_page)

        nav_layout.addStretch()
        scroll_area.setWidget(nav_container)
        sidebar_layout.addWidget(scroll_area, stretch=1)

        # ── Divisor inferior ──────────────────────────────────────────
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet("background-color: #374151; margin: 0px 12px;")
        div2.setFixedHeight(1)
        sidebar_layout.addWidget(div2)

        # ── Botón Cerrar Sesión (fijo abajo) ──────────────────────────
        logout_btn = QPushButton("🚪  Cerrar Sesión")
        logout_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 14px 20px;
                border: none;
                border-radius: 0px;
                font-size: 13px;
                font-weight: 500;
                color: #EF4444;
                background-color: transparent;
            }
            QPushButton:hover { background-color: rgba(239, 68, 68, 0.15); }
        """)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_btn)

    def create_nav_button(self, icon: str, text: str) -> QPushButton:
        btn = QPushButton(f"  {icon}   {text}")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(44)
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 16px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                color: #9CA3AF;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: #F9FAFB;
            }
            QPushButton:checked {
                background-color: rgba(234, 179, 8, 0.2);
                color: #EAB308;
                font-weight: 700;
                border-left: 3px solid #EAB308;
            }
        """)
        return btn

    # ── Content area ──────────────────────────────────────────────────

    def create_content_area(self):
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)

        self.create_pages()

    def create_pages(self):
        # Home
        self.home_page = self.create_home_page()
        self.stacked_widget.addWidget(self.home_page)

        # Products (admin only)
        if self.current_user.is_admin():
            from ui.widgets.products_widget import ProductsWidget
            self.products_page = ProductsWidget()
            self.stacked_widget.addWidget(self.products_page)

        # POS
        from ui.widgets.pos_widget import POSWidget
        self.pos_page = POSWidget()
        self.stacked_widget.addWidget(self.pos_page)

        # Sales
        from ui.widgets.sales_widget import SalesWidget
        self.sales_page = SalesWidget()
        self.stacked_widget.addWidget(self.sales_page)

        # ── Inventario (admin y cajero) ────────────────────────────
        from ui.widgets.inventory_widget import InventoryWidget
        self.inventory_page = InventoryWidget()
        self.stacked_widget.addWidget(self.inventory_page)

        # ── Arqueo de Caja (admin y cajero) ────────────────────────
        from ui.widgets.arqueo_widget import ArqueoWidget
        self.arqueo_page = ArqueoWidget()
        self.stacked_widget.addWidget(self.arqueo_page)

        # Finance (admin only)
        if self.current_user.is_admin():
            from ui.widgets.finance_widget import FinanceWidget
            self.finance_page = FinanceWidget()
            self.stacked_widget.addWidget(self.finance_page)

        # Users (admin only)
        if self.current_user.is_admin():
            from ui.widgets.users_widget import UsersWidget
            self.users_page = UsersWidget()
            self.stacked_widget.addWidget(self.users_page)

        # Settings
        self.settings_page = self.create_settings_page()
        self.stacked_widget.addWidget(self.settings_page)

    # ── Page factories ────────────────────────────────────────────────

    def create_home_page(self) -> QWidget:
        from ui.widgets.home_widget import HomeWidget
        return HomeWidget()

    def create_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("⚙️ Configuración")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")
        layout.addWidget(title)
        layout.addStretch()
        info = QLabel("Página de configuración en desarrollo...")
        info.setStyleSheet("color: #6B7280;")
        layout.addWidget(info)
        layout.addStretch()
        return page

    # ── Navigation ────────────────────────────────────────────────────

    def _nav_index(self, page_name: str) -> int:
        """Calcula el índice dinámico de cada página según el rol."""
        is_admin = self.current_user.is_admin()
        order = ['home']
        if is_admin:
            order.append('products')
        order += ['pos', 'sales', 'arqueo']
        if is_admin:
            order += ['finance', 'users']
        order.append('settings')
        return order.index(page_name) if page_name in order else 0

    def set_active_nav_button(self, button: QPushButton):
        for btn in self.nav_buttons:
            btn.setChecked(False)
        button.setChecked(True)

    def show_home_page(self):
        self.stacked_widget.setCurrentWidget(self.home_page)
        self.set_active_nav_button(self.nav_buttons[0])

    def show_products_page(self):
        if hasattr(self, 'products_page'):
            self.stacked_widget.setCurrentWidget(self.products_page)
            self.set_active_nav_button(self.nav_buttons[1])

    def show_pos_page(self):
        self.stacked_widget.setCurrentWidget(self.pos_page)
        idx = 2 if self.current_user.is_admin() else 1
        self.set_active_nav_button(self.nav_buttons[idx])

    def show_sales_page(self):
        self.stacked_widget.setCurrentWidget(self.sales_page)
        idx = 3 if self.current_user.is_admin() else 2
        self.set_active_nav_button(self.nav_buttons[idx])

    """ def show_inventory_page(self):
        self.stacked_widget.setCurrentWidget(self.inventory_page)
        idx = 4 if self.current_user.is_admin() else 3
        self.set_active_nav_button(self.nav_buttons[idx]) """

    def show_arqueo_page(self):
        self.stacked_widget.setCurrentWidget(self.arqueo_page)
        idx = 4 if self.current_user.is_admin() else 3
        self.set_active_nav_button(self.nav_buttons[idx])

    def show_finance_page(self):
        if hasattr(self, 'finance_page'):
            self.stacked_widget.setCurrentWidget(self.finance_page)
            self.set_active_nav_button(self.nav_buttons[5])

    def show_users_page(self):
        if hasattr(self, 'users_page'):
            self.stacked_widget.setCurrentWidget(self.users_page)
            self.set_active_nav_button(self.nav_buttons[6])

    def show_settings_page(self):
        self.stacked_widget.setCurrentWidget(self.settings_page)
        self.set_active_nav_button(self.nav_buttons[-1])

    # ── Status bar ────────────────────────────────────────────────────

    def create_status_bar(self):
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        db_label = QLabel("🗄️ Base de datos: Conectada")
        db_label.setStyleSheet("color: #10B981; font-size: 12px;")
        status_bar.addWidget(db_label)
        status_bar.addPermanentWidget(QLabel("|"))

        user_status = QLabel(f"👤 {self.current_user.nombre} ({self.current_user.rol})")
        user_status.setStyleSheet("font-size: 12px; color: #6B7280;")
        status_bar.addPermanentWidget(user_status)

    # ── Logout ────────────────────────────────────────────────────────

    def handle_logout(self):
        reply = QMessageBox.question(
            self, "Cerrar Sesión",
            "¿Está seguro que desea cerrar sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            logout()
            self.close()
            from ui.login_window import LoginWindow
            login_window = LoginWindow()
            if login_window.exec():
                new_window = MainWindow()
                new_window.show()