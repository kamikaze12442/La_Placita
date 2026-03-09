"""
Main Window
Sidebar colapsable con animación: expandido 260px → colapsado 60px (solo íconos)
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QMessageBox, QStatusBar, QScrollArea
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap
from pathlib import Path
from models.user import get_current_user, logout

SIDEBAR_EXPANDED  = 260
SIDEBAR_COLLAPSED = 62


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.current_user      = get_current_user()
        self._sidebar_expanded = True
        self.init_ui()

    # ── UI principal ──────────────────────────────────────────────────

    def init_ui(self):
        self.setWindowTitle("Cafetería La Placita - Sistema de Punto de Venta")
        self.setMinimumSize(1200, 700)

        central = QWidget()
        self.setCentralWidget(central)
        main_lay = QHBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self.create_sidebar()
        main_lay.addWidget(self.sidebar)

        self.create_content_area()
        main_lay.addWidget(self.content_widget, stretch=1)

        self.create_status_bar()
        self.show_home_page()

    # ── Sidebar ───────────────────────────────────────────────────────

    def create_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(SIDEBAR_EXPANDED)
        self.sidebar.setStyleSheet("QFrame#sidebar{background:#1F2937;}")

        lay = QVBoxLayout(self.sidebar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Franja superior con botón toggle ──────────────────────────
        top_bar = QFrame()
        top_bar.setStyleSheet("background:#111827;")
        top_bar.setFixedHeight(42)
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(8, 1, 8, 1)

        self._toggle_btn = QPushButton("☰")
        self._toggle_btn.setFixedSize(32, 32)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setToolTip("Minimizar/Expandir menú")
        self._toggle_btn.setStyleSheet("""
            QPushButton{background:#374151;border:none;border-radius:7px;
                        color:#9CA3AF;font-size:16px;font-weight: 700;padding:3px 0px 0px 8px}
            QPushButton:hover{background:#4B5563;color:white;}
        """)
        self._toggle_btn.clicked.connect(self._toggle_sidebar)
        tb_lay.addStretch()
        tb_lay.addWidget(self._toggle_btn)
        lay.addWidget(top_bar)

        # ── Logo ──────────────────────────────────────────────────────
        self._logo_frame = QFrame()
        self._logo_frame.setStyleSheet("background:#1F2937;")
        lf_lay = QVBoxLayout(self._logo_frame)
        lf_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lf_lay.setContentsMargins(16, 12, 16, 8)

        self._logo_lbl = QLabel()
        logo_path = Path(__file__).parent.parent / "assets" / "logo_laplacita.png"
        if not logo_path.exists():
            logo_path = Path(__file__).parent.parent.parent / "logo_laplacita.png"
        if logo_path.exists():
            px = QPixmap(str(logo_path)).scaled(
                128, 128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self._logo_lbl.setPixmap(px)
        else:
            self._logo_lbl.setText("☕")
            self._logo_lbl.setStyleSheet("font-size:38px;")
        self._logo_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lf_lay.addWidget(self._logo_lbl)
        lay.addWidget(self._logo_frame)

        # ── Info usuario ──────────────────────────────────────────────
        self._user_frame = QFrame()
        self._user_frame.setStyleSheet("""
            QFrame{background:#374151;border-radius:8px;
                   margin:0px 12px 8px 12px;}
        """)
        uf_lay = QVBoxLayout(self._user_frame)
        uf_lay.setContentsMargins(10, 8, 10, 8)
        uf_lay.setSpacing(2)
        self._user_lbl = QLabel(f"Bienvenido(a):\n{self.current_user.nombre}")
        self._user_lbl.setStyleSheet(
            "color:#F9FAFB;font-size:12px;font-weight:600;")
        self._user_lbl.setWordWrap(True)
        uf_lay.addWidget(self._user_lbl)
        lay.addWidget(self._user_frame)

        # Divisor
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background:#374151;margin:0px 12px;")
        div.setFixedHeight(1)
        lay.addWidget(div)
        lay.addSpacing(4)

        # ── Navegación con scroll ─────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea{background:transparent;border:none;}
            QScrollBar:vertical{background:#374151;width:4px;border-radius:2px;}
            QScrollBar::handle:vertical{background:#6B7280;border-radius:2px;min-height:20px;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0px;}
        """)

        nav_cont = QWidget()
        nav_cont.setStyleSheet("background:transparent;")
        self._nav_lay = QVBoxLayout(nav_cont)
        self._nav_lay.setContentsMargins(8, 4, 8, 4)
        self._nav_lay.setSpacing(2)

        self.nav_buttons = []
        self._nav_data   = []

        def add(icon, text, slot):
            btn = self._make_nav_btn(icon, text)
            btn.clicked.connect(slot)
            self._nav_lay.addWidget(btn)
            self.nav_buttons.append(btn)
            self._nav_data.append((icon, text))

        add("🏠", "Inicio",          self.show_home_page)
        if self.current_user.is_admin():
            add("🛍️", "Productos",   self.show_products_page)
        add("💰", "Punto de Venta",  self.show_pos_page)
        add("🧾", "Ventas",          self.show_sales_page)
        add("🏦", "Arqueo de Caja",  self.show_arqueo_page)
        add("📦", "Inventario",      self.show_inventory_page)
        if self.current_user.is_admin():
            add("📊", "Finanzas",    self.show_finance_page)
            add("👥", "Usuarios",    self.show_users_page)
        add("⚙️", "Configuración",   self.show_settings_page)

        self._nav_lay.addStretch()
        scroll.setWidget(nav_cont)
        lay.addWidget(scroll, stretch=1)

        # Divisor inferior
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet("background:#374151;margin:0px 12px;")
        div2.setFixedHeight(1)
        lay.addWidget(div2)

        # Cerrar sesión
        self._logout_btn = QPushButton("🚪  Cerrar Sesión")
        self._logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._logout_btn.setStyleSheet("""
            QPushButton{text-align:left;padding:14px 20px;border:none;
                        font-size:13px;font-weight:500;
                        color:#EF4444;background:transparent;}
            QPushButton:hover{background:rgba(239,68,68,0.15);}
        """)
        self._logout_btn.clicked.connect(self.handle_logout)
        lay.addWidget(self._logout_btn)

    def _make_nav_btn(self, icon: str, text: str) -> QPushButton:
        label = f"  {icon}   {text}" if self._sidebar_expanded else f"  {icon}"
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(44)
        btn.setToolTip(text)
        btn.setStyleSheet("""
            QPushButton{text-align:left;padding:10px 16px;border:none;
                        border-radius:8px;font-size:14px;font-weight:500;
                        color:#9CA3AF;background:transparent;}
            QPushButton:hover{background:rgba(255,255,255,0.08);color:#F9FAFB;}
            QPushButton:checked{background:rgba(234,179,8,0.2);color:#EAB308;
                font-weight:700;border-left:3px solid #EAB308;}
        """)
        return btn

    def _toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        target_w = SIDEBAR_EXPANDED if self._sidebar_expanded else SIDEBAR_COLLAPSED

        # Animación suave
        self._anim = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self._anim.setDuration(220)
        self._anim.setStartValue(self.sidebar.width())
        self._anim.setEndValue(target_w)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()
        self.sidebar.setMaximumWidth(target_w)

        expanded = self._sidebar_expanded
        self._toggle_btn.setText("☰" if expanded else "☰")
        self._logo_frame.setVisible(expanded)
        self._user_frame.setVisible(expanded)
        self._logout_btn.setText("🚪  Cerrar Sesión" if expanded else "🚪")

        # Actualizar etiquetas de botones
        for btn, (icon, text) in zip(self.nav_buttons, self._nav_data):
            btn.setText(f"  {icon}   {text}" if expanded else f"  {icon}")

    # ── Content area ──────────────────────────────────────────────────

    def create_content_area(self):
        self.content_widget = QWidget()
        cl = QVBoxLayout(self.content_widget)
        cl.setContentsMargins(0, 0, 0, 0)
        self.stacked_widget = QStackedWidget()
        cl.addWidget(self.stacked_widget)
        self.create_pages()

    def create_pages(self):
        self.home_page = self.create_home_page()
        self.stacked_widget.addWidget(self.home_page)

        if self.current_user.is_admin():
            from ui.widgets.products_widget import ProductsWidget
            self.products_page = ProductsWidget()
            self.stacked_widget.addWidget(self.products_page)

        from ui.widgets.pos_widget import POSWidget
        self.pos_page = POSWidget()
        self.stacked_widget.addWidget(self.pos_page)

        from ui.widgets.sales_widget import SalesWidget
        self.sales_page = SalesWidget()
        self.stacked_widget.addWidget(self.sales_page)

        from ui.widgets.arqueo_widget import ArqueoWidget
        self.arqueo_page = ArqueoWidget()
        self.stacked_widget.addWidget(self.arqueo_page)

        from ui.widgets.inventory_widget import InventoryWidget
        self.inventory_page = InventoryWidget()
        self.stacked_widget.addWidget(self.inventory_page)

        if self.current_user.is_admin():
            from ui.widgets.finance_widget import FinanceWidget
            self.finance_page = FinanceWidget()
            self.stacked_widget.addWidget(self.finance_page)

            from ui.widgets.users_widget import UsersWidget
            self.users_page = UsersWidget()
            self.stacked_widget.addWidget(self.users_page)

        
        
    

    def create_home_page(self):
        from ui.widgets.home_widget import HomeWidget
        return HomeWidget()

    # ── Navegación ────────────────────────────────────────────────────

    def _go(self, page, btn_idx: int):
        self.stacked_widget.setCurrentWidget(page)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == btn_idx)

    def show_home_page(self):
        self._go(self.home_page, 0)

    def show_products_page(self):
        if self.current_user.is_admin():
            self._go(self.products_page, 1)

    def show_pos_page(self):
        idx = 2 if self.current_user.is_admin() else 1
        self._go(self.pos_page, idx)

    def show_sales_page(self):
        idx = 3 if self.current_user.is_admin() else 2
        self._go(self.sales_page, idx)

    def show_arqueo_page(self):
        idx = 4 if self.current_user.is_admin() else 3
        self._go(self.arqueo_page, idx)

    def show_inventory_page(self):
        idx = 5 if self.current_user.is_admin() else 4
        self._go(self.inventory_page, idx)

    def show_finance_page(self):
        if self.current_user.is_admin():
            self._go(self.finance_page, 6)

    def show_users_page(self):
        if self.current_user.is_admin():
            self._go(self.users_page, 7)

    def show_settings_page(self):
        self._go(self.settings_page, len(self.nav_buttons) - 1)

    # ── Status bar ────────────────────────────────────────────────────

    def create_status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        db = QLabel("🗄️ Base de datos: Conectada")
        db.setStyleSheet("color:#10B981;font-size:12px;")
        sb.addWidget(db)
        sb.addPermanentWidget(QLabel("|"))
        ul = QLabel(f"👤 {self.current_user.nombre} ({self.current_user.rol})")
        ul.setStyleSheet("font-size:12px;color:#6B7280;")
        sb.addPermanentWidget(ul)

    # ── Logout ────────────────────────────────────────────────────────

    def handle_logout(self):
        r = QMessageBox.question(
            self, "Cerrar Sesión",
            "¿Está seguro que desea cerrar sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            logout()
            self.close()
            from ui.login_window import LoginWindow
            login = LoginWindow()
            if login.exec():
                w = MainWindow()
                w.show()