"""
Main Window
Main application window with sidebar navigation
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QMessageBox, QStatusBar
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon
from models.user import get_current_user, logout


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.current_user = get_current_user()
        self.init_ui()
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Restaurant POS - Sistema de Punto de Venta")
        self.setMinimumSize(1400, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.create_sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Content area
        self.create_content_area()
        main_layout.addWidget(self.content_widget, stretch=1)
        
        # Status bar
        self.create_status_bar()
        
        # Show home page by default
        self.show_home_page()
    
    def create_sidebar(self):
        """Create sidebar with navigation"""
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280)
        self.sidebar.setStyleSheet("""
            QFrame#sidebar {
                background-color: white;
                border-right: 1px solid #E5E7EB;
            }
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)
        
        # Logo/Brand
        brand_layout = QVBoxLayout()
        brand_layout.setContentsMargins(20, 10, 20, 20)
        
        logo_label = QLabel("MR. SALES V")
        logo_font = QFont()
        logo_font.setPointSize(18)
        logo_font.setBold(True)
        logo_label.setFont(logo_font)
        logo_label.setStyleSheet("color: #FF6B35;")
        brand_layout.addWidget(logo_label)
        
        # User info
        user_label = QLabel(f"👤 {self.current_user.nombre}")
        user_label.setStyleSheet("color: #6B7280; font-size: 13px; margin-top: 5px;")
        brand_layout.addWidget(user_label)
        
        role_label = QLabel(f"Rol: {self.current_user.rol.title()}")
        role_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        brand_layout.addWidget(role_label)
        
        sidebar_layout.addLayout(brand_layout)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #E5E7EB;")
        sidebar_layout.addWidget(divider)
        
        sidebar_layout.addSpacing(10)
        
        # Navigation buttons
        self.nav_buttons = []
        
        # Home
        home_btn = self.create_nav_button("🏠", "Inicio")
        home_btn.clicked.connect(self.show_home_page)
        sidebar_layout.addWidget(home_btn)
        self.nav_buttons.append(home_btn)
        
        # Products (Admin only)
        if self.current_user.is_admin():
            products_btn = self.create_nav_button("📦", "Productos")
            products_btn.clicked.connect(self.show_products_page)
            sidebar_layout.addWidget(products_btn)
            self.nav_buttons.append(products_btn)
        
        # POS
        pos_btn = self.create_nav_button("💰", "Punto de Venta")
        pos_btn.clicked.connect(self.show_pos_page)
        sidebar_layout.addWidget(pos_btn)
        self.nav_buttons.append(pos_btn)
        
        # Sales
        sales_btn = self.create_nav_button("🧾", "Ventas")
        sales_btn.clicked.connect(self.show_sales_page)
        sidebar_layout.addWidget(sales_btn)
        self.nav_buttons.append(sales_btn)
        
        # Finance (Admin only)
        if self.current_user.is_admin():
            finance_btn = self.create_nav_button("📊", "Finanzas")
            finance_btn.clicked.connect(self.show_finance_page)
            sidebar_layout.addWidget(finance_btn)
            self.nav_buttons.append(finance_btn)
        
        # Users (Admin only)
        if self.current_user.is_admin():
            users_btn = self.create_nav_button("👥", "Usuarios")
            users_btn.clicked.connect(self.show_users_page)
            sidebar_layout.addWidget(users_btn)
            self.nav_buttons.append(users_btn)
        
        # Settings
        settings_btn = self.create_nav_button("⚙️", "Configuración")
        settings_btn.clicked.connect(self.show_settings_page)
        sidebar_layout.addWidget(settings_btn)
        self.nav_buttons.append(settings_btn)
        
        sidebar_layout.addStretch()
        
        # Logout button
        logout_btn = QPushButton("🚪 Cerrar Sesión")
        logout_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 15px 20px;
                border: none;
                border-radius: 8px;
                margin: 5px 10px;
                font-size: 14px;
                font-weight: 500;
                color: #EF4444;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.1);
            }
        """)
        logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_btn)
    
    def create_nav_button(self, icon: str, text: str) -> QPushButton:
        """Create navigation button"""
        btn = QPushButton(f"{icon}  {text}")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn
    
    def create_content_area(self):
        """Create main content area"""
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Stacked widget for pages
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)
        
        # Create pages
        self.create_pages()
    
    def create_pages(self):
        """Create all pages"""
        # Home page
        self.home_page = self.create_home_page()
        self.stacked_widget.addWidget(self.home_page)
        
        # Products page (Admin only)
        if self.current_user.is_admin():
            from ui.widgets.products_widget import ProductsWidget
            self.products_page = ProductsWidget()
            self.stacked_widget.addWidget(self.products_page)
        
        # POS page
        from ui.widgets.pos_widget import POSWidget
        self.pos_page = POSWidget()
        self.stacked_widget.addWidget(self.pos_page)
        
        # Sales page
        from ui.widgets.sales_widget import SalesWidget
        self.sales_page = SalesWidget()
        self.stacked_widget.addWidget(self.sales_page)
        
        # Finance page (Admin only)
        if self.current_user.is_admin():
            from ui.widgets.finance_widget import FinanceWidget
            self.finance_page = FinanceWidget()
            self.stacked_widget.addWidget(self.finance_page)
        
        # Users page (Admin only)
        if self.current_user.is_admin():
            from ui.widgets.users_widget import UsersWidget
            self.users_page = UsersWidget()
            self.stacked_widget.addWidget(self.users_page)
        
        # Settings page
        self.settings_page = self.create_settings_page()
        self.stacked_widget.addWidget(self.settings_page)
    
    def create_home_page(self) -> QWidget:
        """Create home page with dashboard"""
        from ui.widgets.home_widget import HomeWidget
        return HomeWidget()
    
    def create_settings_page(self) -> QWidget:
        """Create settings page"""
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
    
    def create_status_bar(self):
        """Create status bar"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Left side info
        db_label = QLabel("🗄️ Base de datos: Conectada")
        db_label.setStyleSheet("color: #10B981; font-size: 12px;")
        status_bar.addWidget(db_label)
        
        status_bar.addPermanentWidget(QLabel("|"))
        
        # User info
        user_status = QLabel(f"👤 {self.current_user.nombre} ({self.current_user.rol})")
        user_status.setStyleSheet("font-size: 12px; color: #6B7280;")
        status_bar.addPermanentWidget(user_status)
    
    def set_active_nav_button(self, button: QPushButton):
        """Set active navigation button"""
        for btn in self.nav_buttons:
            btn.setChecked(False)
        button.setChecked(True)
    
    def show_home_page(self):
        """Show home page"""
        self.stacked_widget.setCurrentWidget(self.home_page)
        if self.nav_buttons:
            self.set_active_nav_button(self.nav_buttons[0])
    
    def show_products_page(self):
        """Show products page"""
        if hasattr(self, 'products_page'):
            self.stacked_widget.setCurrentWidget(self.products_page)
            self.set_active_nav_button(self.nav_buttons[1])
    
    def show_pos_page(self):
        """Show POS page"""
        self.stacked_widget.setCurrentWidget(self.pos_page)
        idx = 2 if self.current_user.is_admin() else 1
        self.set_active_nav_button(self.nav_buttons[2])
    
    def show_sales_page(self):
        """Show sales page"""
        self.stacked_widget.setCurrentWidget(self.sales_page)
        idx = 3 if self.current_user.is_admin() else 2
        self.set_active_nav_button(self.nav_buttons[idx])
    
    def show_finance_page(self):
        """Show finance page"""
        if hasattr(self, 'finance_page'):
            self.stacked_widget.setCurrentWidget(self.finance_page)
            self.set_active_nav_button(self.nav_buttons[4])
    
    def show_users_page(self):
        """Show users page"""
        if hasattr(self, 'users_page'):
            self.stacked_widget.setCurrentWidget(self.users_page)
            self.set_active_nav_button(self.nav_buttons[5])
    
    def show_settings_page(self):
        """Show settings page"""
        self.stacked_widget.setCurrentWidget(self.settings_page)
        self.set_active_nav_button(self.nav_buttons[-1])
    
    def handle_logout(self):
        """Handle logout"""
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Está seguro que desea cerrar sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logout()
            self.close()
            
            # Show login window again
            from ui.login_window import LoginWindow
            login_window = LoginWindow()
            if login_window.exec():
                # Create new main window with new user
                new_window = MainWindow()
                new_window.show()
