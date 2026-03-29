"""
Settings Widget — Configuración del sistema
Secciones: Negocio · Impresión · Seguridad · Sistema (admin) · Mi Cuenta (ambos)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QCheckBox, QScrollArea,
    QMessageBox, QTabWidget, QFormLayout, QTextEdit,
    QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from database.connection import db
from models.user import get_current_user, _verify_password, _hash_password


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_config(clave: str, default: str = "") -> str:
    row = db.fetch_one(
        "SELECT valor FROM configuracion WHERE clave = ?", (clave,))
    return row['valor'] if row else default


def _set_config(clave: str, valor: str):
    db.execute_query(
        """INSERT INTO configuracion (clave, valor, fecha_actualizacion)
           VALUES (?, ?, datetime('now'))
           ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor,
           fecha_actualizacion = excluded.fecha_actualizacion""",
        (clave, valor)
    )


CARD_STYLE = """
    QFrame {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 14px;
    }
"""

SECTION_TITLE_STYLE = (
    "font-size: 15px; font-weight: 700; color: #1F2937;"
)

INPUT_STYLE = """
    QLineEdit, QTextEdit {
        border: 1px solid #D1D5DB;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        background: white;
        color: #1F2937;
    }
    QLineEdit:focus, QTextEdit:focus {
        border-color: #FF6B35;
    }
"""

BTN_PRIMARY = """
    QPushButton {
        background: #FF6B35; color: white;
        border-radius: 9px; font-weight: 700;
        font-size: 13px; padding: 0 20px;
        min-height: 38px;
    }
    QPushButton:hover { background: #E85D2F; }
"""

BTN_SECONDARY = """
    QPushButton {
        background: #F3F4F6; color: #374151;
        border-radius: 9px; font-weight: 600;
        font-size: 13px; padding: 0 20px;
        min-height: 38px;
        border: 1px solid #E5E7EB;
    }
    QPushButton:hover { background: #E5E7EB; }
"""

BTN_DANGER = """
    QPushButton {
        background: #EF4444; color: white;
        border-radius: 9px; font-weight: 700;
        font-size: 13px; padding: 0 20px;
        min-height: 38px;
    }
    QPushButton:hover { background: #DC2626; }
"""

CHECK_STYLE = """
    QCheckBox {
        font-size: 13px;
        color: #374151;
        spacing: 10px;
    }
    QCheckBox::indicator {
        width: 20px; height: 20px;
        border: 2px solid #D1D5DB;
        border-radius: 5px;
        background: white;
    }
    QCheckBox::indicator:checked {
        background: #FF6B35;
        border-color: #FF6B35;
        image: none;
    }
    QCheckBox::indicator:hover {
        border-color: #FF6B35;
    }
"""


def _card(parent_layout, title: str, spacing: int = 16) -> QVBoxLayout:
    """Crea una card blanca con título y devuelve el layout interno."""
    frame = QFrame()
    frame.setStyleSheet(CARD_STYLE)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(spacing)

    t = QLabel(title)
    t.setStyleSheet(SECTION_TITLE_STYLE)
    lay.addWidget(t)

    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("background: #F3F4F6; max-height: 1px;")
    lay.addWidget(sep)

    parent_layout.addWidget(frame)
    return lay


def _lbl(text: str, hint: bool = False) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        f"font-size: {'11' if hint else '13'}px; "
        f"color: {'#9CA3AF' if hint else '#374151'}; "
        "font-weight: 500; background: transparent; border: none"
    )
    if hint:
        l.setWordWrap(True)
    return l


# ── Tab: Impresión ────────────────────────────────────────────────────────────

class ImpresionTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # ── Card: Tickets ─────────────────────────────────────────────
        c = _card(lay, "🖨️ Tickets de Impresión")

        c.addWidget(_lbl(
            "Seleccioná qué tickets se imprimen automáticamente al completar una venta."))

        self._chk_cliente = QCheckBox("Imprimir ticket para el cliente")
        self._chk_cliente.setStyleSheet(CHECK_STYLE)
        self._chk_cliente.setChecked(
            _get_config("imprimir_ticket_cliente", "1") == "1")
        c.addWidget(self._chk_cliente)

        self._chk_cocina = QCheckBox("Imprimir ticket para cocina")
        self._chk_cocina.setStyleSheet(CHECK_STYLE)
        self._chk_cocina.setChecked(
            _get_config("imprimir_ticket_cocina", "0") == "1")
        c.addWidget(self._chk_cocina)

        c.addWidget(_lbl(
            "El ticket de cocina muestra solo los ítems del pedido sin totales ni precios.",
            hint=True))

        # ── Card: Contenido del ticket ────────────────────────────────
        c2 = _card(lay, "📄 Contenido del Ticket")

        c2.addWidget(_lbl("Mensaje de pie de ticket:"))
        self._pie_input = QTextEdit()
        self._pie_input.setPlaceholderText(
            "Ej: ¡Gracias por su visita! Vuelva pronto.")
        self._pie_input.setFixedHeight(70)
        self._pie_input.setStyleSheet(INPUT_STYLE)
        self._pie_input.setPlainText(
            _get_config("mensaje_pie_ticket", "¡Gracias por su visita!\nVuelva pronto"))
        c2.addWidget(self._pie_input)

        c2.addWidget(_lbl("Número de copias (cliente):"))
        self._copias_input = QLineEdit()
        self._copias_input.setPlaceholderText("1")
        self._copias_input.setFixedHeight(38)
        self._copias_input.setFixedWidth(80)
        self._copias_input.setStyleSheet(INPUT_STYLE)
        self._copias_input.setText(_get_config("copias_ticket_cliente", "1"))
        c2.addWidget(self._copias_input)

        # ── Card: Cajón de dinero ─────────────────────────────────────
        c3 = _card(lay, "💰 Cajón de Dinero")

        self._chk_cajon = QCheckBox("Abrir cajón automáticamente al completar venta en efectivo")
        self._chk_cajon.setStyleSheet(CHECK_STYLE)
        self._chk_cajon.setChecked(
            _get_config("abrir_cajon_auto", "0") == "1")
        c3.addWidget(self._chk_cajon)

        # Botón guardar
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("💾  Guardar Configuración")
        save_btn.setStyleSheet(BTN_PRIMARY)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

        lay.addStretch()
        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _save(self):
        _set_config("imprimir_ticket_cliente",
                    "1" if self._chk_cliente.isChecked() else "0")
        _set_config("imprimir_ticket_cocina",
                    "1" if self._chk_cocina.isChecked() else "0")
        _set_config("abrir_cajon_auto",
                    "1" if self._chk_cajon.isChecked() else "0")
        _set_config("mensaje_pie_ticket",
                    self._pie_input.toPlainText().strip())
        copias = self._copias_input.text().strip()
        _set_config("copias_ticket_cliente", copias if copias.isdigit() else "1")
        QMessageBox.information(self, "✅ Guardado",
                                "Configuración de impresión guardada.")


# ── Tab: Negocio (solo admin) ─────────────────────────────────────────────────

class NegocioTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # ── Card: Datos del negocio ───────────────────────────────────
        c = _card(lay, "🏪 Datos del Negocio")
        c.addWidget(_lbl(
            "Esta información aparece en las facturas y tickets impresos."))

        fields = [
            ("nombre_negocio",  "Nombre del negocio:",    "La Placita"),
            ("subtitulo",       "Subtítulo:",             "Cafetería & Heladería"),
            ("direccion",       "Dirección:",             "Santa Fe, Santa Cruz — Bolivia"),
            ("telefono",        "Teléfono:",              "+591 77113371"),
            ("email",           "Email:",                 "info@laplacita.com"),
            ("ruc_nit",         "RUC / NIT:",             ""),
        ]

        self._inputs = {}
        for clave, label, placeholder in fields:
            c.addWidget(_lbl(label))
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            inp.setFixedHeight(38)
            inp.setStyleSheet(INPUT_STYLE)
            inp.setText(_get_config(clave, placeholder))
            c.addWidget(inp)
            self._inputs[clave] = inp

        # ── Card: Rutas de exportación ────────────────────────────────
        c2 = _card(lay, "📁 Rutas de Exportación")
        c2.addWidget(_lbl(
            "Carpeta donde se guardan los PDFs de facturas y los reportes Excel."))

        for clave, label, default in [
            ("ruta_facturas_pdf",  "PDFs de Facturas:",      "Desktop/La Placita/Facturas"),
            ("ruta_reportes_pdf",  "Reportes PDF:",          "Desktop/La Placita/Reportes Finanzas PDF"),
            ("ruta_reportes_excel","Reportes Excel:",        "Desktop/La Placita/Reportes Finanzas Excel"),
        ]:
            c2.addWidget(_lbl(label))
            row = QHBoxLayout()
            inp = QLineEdit()
            inp.setFixedHeight(38)
            inp.setStyleSheet(INPUT_STYLE)
            inp.setText(_get_config(clave, default))
            inp.setReadOnly(True)
            row.addWidget(inp)
            browse = QPushButton("📂")
            browse.setFixedSize(38, 38)
            browse.setStyleSheet(BTN_SECONDARY)
            browse.clicked.connect(
                lambda _, i=inp, k=clave: self._browse(i, k))
            row.addWidget(browse)
            c2.addLayout(row)
            self._inputs[clave] = inp

        # Botón guardar
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("💾  Guardar")
        save_btn.setStyleSheet(BTN_PRIMARY)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

        lay.addStretch()
        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _browse(self, inp: QLineEdit, clave: str):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            inp.setText(folder)
            _set_config(clave, folder)

    def _save(self):
        for clave, inp in self._inputs.items():
            _set_config(clave, inp.text().strip())
        QMessageBox.information(self, "✅ Guardado",
                                "Datos del negocio guardados.")


# ── Tab: Seguridad ────────────────────────────────────────────────────────────

class SeguridadTab(QWidget):
    def __init__(self):
        super().__init__()
        self._user = get_current_user()
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # ── Card: Cambiar contraseña propia ───────────────────────────
        c = _card(lay, "🔑 Cambiar Mi Contraseña")

        c.addWidget(_lbl("Contraseña actual:"))
        self._pw_actual = QLineEdit()
        self._pw_actual.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw_actual.setFixedHeight(38)
        self._pw_actual.setStyleSheet(INPUT_STYLE)
        c.addWidget(self._pw_actual)

        c.addWidget(_lbl("Nueva contraseña:"))
        self._pw_nueva = QLineEdit()
        self._pw_nueva.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw_nueva.setFixedHeight(38)
        self._pw_nueva.setStyleSheet(INPUT_STYLE)
        c.addWidget(self._pw_nueva)

        c.addWidget(_lbl("Confirmar nueva contraseña:"))
        self._pw_confirmar = QLineEdit()
        self._pw_confirmar.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw_confirmar.setFixedHeight(38)
        self._pw_confirmar.setStyleSheet(INPUT_STYLE)
        c.addWidget(self._pw_confirmar)

        btn_pw = QPushButton("🔒  Cambiar Contraseña")
        btn_pw.setStyleSheet(BTN_PRIMARY)
        btn_pw.clicked.connect(self._cambiar_password)
        c.addWidget(btn_pw)

        # ── Card: Clave maestra (solo admin) ──────────────────────────
        if self._user and self._user.is_admin():
            c2 = _card(lay, "🛡️ Clave Maestra del Sistema")
            c2.addWidget(_lbl(
                "La clave maestra se usa para anular facturas y desanularlas. "
                "Guardala en un lugar seguro.", hint=True))

            c2.addWidget(_lbl("Clave maestra actual:"))
            self._master_actual = QLineEdit()
            self._master_actual.setEchoMode(QLineEdit.EchoMode.Password)
            self._master_actual.setFixedHeight(38)
            self._master_actual.setStyleSheet(INPUT_STYLE)
            c2.addWidget(self._master_actual)

            c2.addWidget(_lbl("Nueva clave maestra:"))
            self._master_nueva = QLineEdit()
            self._master_nueva.setEchoMode(QLineEdit.EchoMode.Password)
            self._master_nueva.setFixedHeight(38)
            self._master_nueva.setStyleSheet(INPUT_STYLE)
            c2.addWidget(self._master_nueva)

            c2.addWidget(_lbl("Confirmar nueva clave maestra:"))
            self._master_confirmar = QLineEdit()
            self._master_confirmar.setEchoMode(QLineEdit.EchoMode.Password)
            self._master_confirmar.setFixedHeight(38)
            self._master_confirmar.setStyleSheet(INPUT_STYLE)
            c2.addWidget(self._master_confirmar)

            btn_master = QPushButton("🛡️  Cambiar Clave Maestra")
            btn_master.setStyleSheet(BTN_DANGER)
            btn_master.clicked.connect(self._cambiar_master)
            c2.addWidget(btn_master)

        lay.addStretch()
        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _cambiar_password(self):
        from database.connection import db
        actual    = self._pw_actual.text().strip()
        nueva     = self._pw_nueva.text().strip()
        confirmar = self._pw_confirmar.text().strip()

        if not actual or not nueva or not confirmar:
            QMessageBox.warning(self, "Campos vacíos",
                                "Completá todos los campos.")
            return
        if nueva != confirmar:
            QMessageBox.warning(self, "No coinciden",
                                "La nueva contraseña no coincide.")
            return
        if len(nueva) < 6:
            QMessageBox.warning(self, "Contraseña débil",
                                "La contraseña debe tener al menos 6 caracteres.")
            return

        # Verificar contraseña actual
        row = db.fetch_one(
            "SELECT password FROM usuarios WHERE id = ?",
            (self._user.id,))
        if not row or not _verify_password(actual, row['password']):
            QMessageBox.critical(self, "Error",
                                 "La contraseña actual es incorrecta.")
            return

        db.execute_query(
            "UPDATE usuarios SET password = ? WHERE id = ?",
            (_hash_password(nueva), self._user.id))

        self._pw_actual.clear()
        self._pw_nueva.clear()
        self._pw_confirmar.clear()
        QMessageBox.information(self, "✅ Listo",
                                "Contraseña cambiada correctamente.")

    def _cambiar_master(self):
        from ui.reset_password_dialog import get_master_hash, set_master_password
        actual    = self._master_actual.text().strip()
        nueva     = self._master_nueva.text().strip()
        confirmar = self._master_confirmar.text().strip()

        if not actual or not nueva or not confirmar:
            QMessageBox.warning(self, "Campos vacíos",
                                "Completá todos los campos.")
            return
        if nueva != confirmar:
            QMessageBox.warning(self, "No coinciden",
                                "La nueva clave maestra no coincide.")
            return
        if len(nueva) < 4:
            QMessageBox.warning(self, "Muy corta",
                                "La clave maestra debe tener al menos 4 caracteres.")
            return

        stored = get_master_hash()
        if not stored or not _verify_password(actual, stored):
            QMessageBox.critical(self, "Error",
                                 "La clave maestra actual es incorrecta.")
            return

        set_master_password(nueva)
        self._master_actual.clear()
        self._master_nueva.clear()
        self._master_confirmar.clear()
        QMessageBox.information(self, "✅ Listo",
                                "Clave maestra cambiada correctamente.")


# ── Tab: Sistema (solo admin) ─────────────────────────────────────────────────

class SistemaTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # ── Card: Backup ──────────────────────────────────────────────
        c = _card(lay, "💾 Base de Datos")
        c.addWidget(_lbl(
            "El sistema realiza backups automáticos cada 24 horas y mantiene "
            "los últimos 7. También podés hacer uno manual ahora.", hint=True))

        btn_backup = QPushButton("📦  Hacer Backup Ahora")
        btn_backup.setStyleSheet(BTN_PRIMARY)
        btn_backup.clicked.connect(self._backup)
        c.addWidget(btn_backup)

        btn_open_backups = QPushButton("📂  Abrir Carpeta de Backups")
        btn_open_backups.setStyleSheet(BTN_SECONDARY)
        btn_open_backups.clicked.connect(self._open_backups)
        c.addWidget(btn_open_backups)

        # ── Card: Información del sistema ─────────────────────────────
        c2 = _card(lay, "ℹ️ Información del Sistema")
        from pathlib import Path
        db_path = Path.home() / '.restaurant_pos' / 'restaurant.db'
        size_mb = (db_path.stat().st_size / 1024 / 1024
                   if db_path.exists() else 0)

        from database.connection import db as _db
        for label, value in [
            ("Versión:", "1.0.0"),
            ("Base de datos:", str(db_path)),
            ("Tamaño BD:", f"{size_mb:.2f} MB"),
            ("Usuarios registrados:", str(_db.get_table_count('usuarios'))),
            ("Productos:",           str(_db.get_table_count('productos'))),
            ("Ventas totales:",      str(_db.get_table_count('ventas'))),
        ]:
            row = QHBoxLayout()
            k = QLabel(label)
            k.setStyleSheet(
                "font-size: 13px; font-weight: 600; color: #6B7280; "
                "background: transparent; border: none")
            k.setFixedWidth(180)
            v = QLabel(value)
            v.setStyleSheet(
                "font-size: 13px; color: #1F2937; background: transparent;border: none")
            v.setWordWrap(True)
            row.addWidget(k)
            row.addWidget(v)
            row.addStretch()
            c2.addLayout(row)

        lay.addStretch()
        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _backup(self):
        from database.connection import db as _db
        ok, path = _db.backup_database()
        if ok:
            QMessageBox.information(self, "✅ Backup creado",
                                    f"Backup guardado en:\n{path}")
        else:
            QMessageBox.critical(self, "Error",
                                 f"No se pudo crear el backup:\n{path}")

    def _open_backups(self):
        import subprocess
        from pathlib import Path
        backup_dir = Path.home() / '.restaurant_pos' / 'backups'
        backup_dir.mkdir(exist_ok=True)
        subprocess.Popen(f'explorer "{backup_dir}"')


# ── Widget principal ──────────────────────────────────────────────────────────

class SettingsWidget(QWidget):

    def __init__(self):
        super().__init__()
        self._user = get_current_user()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 40)
        root.setSpacing(20)

        # Header
        header = QVBoxLayout()
        header.setSpacing(4)
        title = QLabel("⚙️ Configuración")
        title.setStyleSheet(
            "font-size: 32px; font-weight: 700; color: #1F2937; border: none")
        subtitle = QLabel("Ajustes del sistema y preferencias")
        subtitle.setStyleSheet("font-size: 14px; color: #6B7280; border: none")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        # Tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                background: #F9FAFB;
                padding: 16px;
            }
            QTabBar::tab {
                padding: 10px 22px;
                font-size: 13px;
                font-weight: 600;
                color: #6B7280;
                border: none;
                margin-right: 4px;
                border-radius: 8px 8px 0 0;
            }
            QTabBar::tab:selected {
                color: #FF6B35;
                border-bottom: 2px solid #FF6B35;
                background: white;
            }
            QTabBar::tab:hover:!selected {
                color: #374151;
                background: #F3F4F6;
            }
        """)

        # Impresión — visible para todos
        tabs.addTab(ImpresionTab(), "🖨️  Impresión")

        # Negocio y Sistema — solo admin
        if self._user and self._user.is_admin():
            tabs.addTab(NegocioTab(),   "🏪  Negocio")
            tabs.addTab(SistemaTab(),   "💾  Sistema")

        # Seguridad — todos (cambio de contraseña propia)
        tabs.addTab(SeguridadTab(), "🔑  Seguridad")

        root.addWidget(tabs)