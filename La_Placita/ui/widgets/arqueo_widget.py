"""
Arqueo de Caja Widget
Apertura, cierre y historial de arqueos por cajero/admin.
Incluye conteo de denominaciones, comparación sistema vs físico y diferencias.
"""

import json
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox, QFrame, QDoubleSpinBox,
    QHeaderView, QScrollArea, QGridLayout, QSpinBox, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from models.arqueo import ArqueoCaja
from models.user import get_current_user, User
from database.connection import db


# ── Denominaciones bolivianas ──────────────────────────────────────────────────
BILLETES  = [200, 100, 50, 20, 10]
MONEDAS   = [5, 2, 1, 0.50, 0.20, 0.10]


def _color_diferencia(valor: float) -> str:
    if valor > 0:  return "#10B981"   # verde  — sobrante
    if valor < 0:  return "#EF4444"   # rojo   — faltante
    return "#6B7280"                  # gris   — exacto


def _texto_diferencia(valor: float) -> str:
    if valor > 0:  return f"▲ Bs {valor:+.2f}  (sobrante)"
    if valor < 0:  return f"▼ Bs {valor:+.2f}  (faltante)"
    return "✓ Exacto"


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Abrir Caja
# ──────────────────────────────────────────────────────────────────────────────

class AbrirCajaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🟢 Abrir Caja")
        self.setMinimumWidth(380)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        info = QLabel(
            "Al abrir la caja quedará registrado tu usuario y la hora de inicio.\n"
            "Todas las ventas que realices desde este momento quedarán\n"
            "asociadas a este arqueo."
        )
        info.setStyleSheet("color: #6B7280; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.monto_inicial = QDoubleSpinBox()
        self.monto_inicial.setRange(0, 999999)
        self.monto_inicial.setDecimals(2)
        self.monto_inicial.setPrefix("Bs ")
        self.monto_inicial.setValue(0)
        form.addRow("Fondo inicial en caja:", self.monto_inicial)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("🟢 Abrir Caja")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_monto(self) -> float:
        return self.monto_inicial.value()


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Cerrar Caja (conteo físico + denominaciones)
# ──────────────────────────────────────────────────────────────────────────────

class CerrarCajaDialog(QDialog):
    def __init__(self, arqueo: ArqueoCaja, parent=None):
        super().__init__(parent)
        self.arqueo = arqueo
        self.setWindowTitle("🔴 Cerrar Caja — Conteo Físico")
        self.setMinimumWidth(520)
        self._denom_spins: dict = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # ── Resumen del sistema ────────────────────────────────────────
        ventas = ArqueoCaja.calcular_ventas_sistema(
            self.arqueo.usuario_id, self.arqueo.fecha_inicio
        )

        sistema_frame = QFrame()
        sistema_frame.setStyleSheet("""
            QFrame { background:#F0FDF4; border:1px solid #86EFAC;
                     border-radius:8px; padding:10px; }
        """)
        sf_layout = QGridLayout(sistema_frame)
        sf_layout.addWidget(QLabel("<b>📊 Ventas registradas en sistema</b>"), 0, 0, 1, 2)

        datos = [
            ("💵 Efectivo",  ventas['efectivo']),
            ("💱 QR",        ventas['qr']),
            ("💳 Tarjeta",   ventas['tarjeta']),
            ("🧾 Total",     ventas['total']),
        ]
        for i, (lbl, val) in enumerate(datos, 1):
            sf_layout.addWidget(QLabel(lbl), i, 0)
            v = QLabel(f"Bs {val:.2f}")
            v.setStyleSheet("font-weight:600;")
            sf_layout.addWidget(v, i, 1)

        trans_lbl = QLabel(f"Transacciones: {ventas['transacciones']}")
        trans_lbl.setStyleSheet("color:#6B7280; font-size:11px;")
        sf_layout.addWidget(trans_lbl, len(datos)+1, 0, 1, 2)
        layout.addWidget(sistema_frame)

        # ── Scroll con conteo ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setSpacing(12)

        # Denominaciones bolivianas
        denom_frame = QFrame()
        denom_frame.setStyleSheet("""
            QFrame { background:#F9FAFB; border:1px solid #E5E7EB;
                     border-radius:8px; padding:10px; }
        """)
        df = QGridLayout(denom_frame)
        df.addWidget(QLabel("<b>🪙 Conteo de billetes y monedas (Bs)</b>"), 0, 0, 1, 4)

        col = 0
        row_idx = 1
        for denom in BILLETES + MONEDAS:
            lbl = QLabel(f"Bs {denom:.2f}" if denom < 1 else f"Bs {int(denom)}")
            spin = QSpinBox()
            spin.setRange(0, 9999)
            spin.setFixedWidth(80)
            spin.valueChanged.connect(self._update_totals)
            self._denom_spins[denom] = spin
            df.addWidget(lbl,  row_idx, col * 2)
            df.addWidget(spin, row_idx, col * 2 + 1)
            col += 1
            if col >= 2:
                col = 0
                row_idx += 1

        c_layout.addWidget(denom_frame)

        # Totales conteo físico
        totales_frame = QFrame()
        totales_frame.setStyleSheet("""
            QFrame { background:#F9FAFB; border:1px solid #E5E7EB;
                     border-radius:8px; padding:10px; }
        """)
        tf = QFormLayout(totales_frame)
        tf.addRow(QLabel("<b>💰 Conteo físico (total por método)</b>"))

        self.conteo_efectivo_lbl = QLabel("Bs 0.00")
        self.conteo_efectivo_lbl.setStyleSheet("font-weight:600; font-size:14px;")
        tf.addRow("💵 Efectivo (billetes+monedas):", self.conteo_efectivo_lbl)

        self.conteo_qr_spin = QDoubleSpinBox()
        self.conteo_qr_spin.setRange(0, 999999)
        self.conteo_qr_spin.setDecimals(2)
        self.conteo_qr_spin.setPrefix("Bs ")
        tf.addRow("💱 QR (ingresa monto):", self.conteo_qr_spin)

        self.conteo_tarjeta_spin = QDoubleSpinBox()
        self.conteo_tarjeta_spin.setRange(0, 999999)
        self.conteo_tarjeta_spin.setDecimals(2)
        self.conteo_tarjeta_spin.setPrefix("Bs ")
        tf.addRow("💳 Tarjeta (ingresa monto):", self.conteo_tarjeta_spin)

        c_layout.addWidget(totales_frame)

        # Diferencias en tiempo real
        self.dif_frame = QFrame()
        self.dif_frame.setStyleSheet("""
            QFrame { background:#FFF7ED; border:1px solid #FCD34D;
                     border-radius:8px; padding:10px; }
        """)
        df2 = QFormLayout(self.dif_frame)
        df2.addRow(QLabel("<b>📊 Diferencia (conteo − sistema)</b>"))
        self.dif_ef_lbl  = QLabel("—")
        self.dif_qr_lbl  = QLabel("—")
        self.dif_tar_lbl = QLabel("—")
        self.dif_tot_lbl = QLabel("—")
        df2.addRow("💵 Efectivo:", self.dif_ef_lbl)
        df2.addRow("💱 QR:",       self.dif_qr_lbl)
        df2.addRow("💳 Tarjeta:",  self.dif_tar_lbl)
        df2.addRow("🔢 Total:",    self.dif_tot_lbl)
        c_layout.addWidget(self.dif_frame)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Conectar spins de QR/Tarjeta
        self.conteo_qr_spin.valueChanged.connect(self._update_totals)
        self.conteo_tarjeta_spin.valueChanged.connect(self._update_totals)
        self._ventas = ventas
        self._update_totals()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("🔴 Cerrar Caja")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_totals(self):
        # Sumar denominaciones → efectivo físico
        ef = sum(denom * spin.value() for denom, spin in self._denom_spins.items())
        self.conteo_efectivo_lbl.setText(f"Bs {ef:.2f}")

        qr  = self.conteo_qr_spin.value()
        tar = self.conteo_tarjeta_spin.value()

        dif_ef  = round(ef  - self._ventas['efectivo'], 2)
        dif_qr  = round(qr  - self._ventas['qr'],       2)
        dif_tar = round(tar - self._ventas['tarjeta'],  2)
        dif_tot = round(dif_ef + dif_qr + dif_tar,      2)

        for lbl, val in [(self.dif_ef_lbl, dif_ef), (self.dif_qr_lbl, dif_qr),
                         (self.dif_tar_lbl, dif_tar), (self.dif_tot_lbl, dif_tot)]:
            lbl.setText(_texto_diferencia(val))
            lbl.setStyleSheet(f"font-weight:600; color:{_color_diferencia(val)};")

    def get_data(self):
        ef  = sum(denom * spin.value() for denom, spin in self._denom_spins.items())
        qr  = self.conteo_qr_spin.value()
        tar = self.conteo_tarjeta_spin.value()
        denom_dict = {str(k): v.value() for k, v in self._denom_spins.items() if v.value() > 0}
        return ef, qr, tar, denom_dict


# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: Caja Actual
# ──────────────────────────────────────────────────────────────────────────────

class CajaActualTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(16)
        self._layout.setContentsMargins(20, 20, 20, 20)

    def refresh(self):
        # Limpiar layout
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        usuario = get_current_user()
        arqueo  = ArqueoCaja.get_abierto_por_usuario(usuario.id)

        if arqueo:
            self._render_caja_abierta(arqueo)
        else:
            self._render_caja_cerrada()

    def _render_caja_cerrada(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { background:#F9FAFB; border:2px dashed #D1D5DB;
                     border-radius:16px; padding:40px; }
        """)
        fl = QVBoxLayout(frame)
        fl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🔒")
        icon.setStyleSheet("font-size:48px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(icon)

        msg = QLabel("No hay caja abierta")
        msg.setStyleSheet("font-size:20px; font-weight:700; color:#1F2937;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(msg)

        sub = QLabel("Abre la caja para comenzar a registrar ventas en este turno.")
        sub.setStyleSheet("color:#6B7280; font-size:13px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(sub)

        abrir_btn = QPushButton("🟢  Abrir Caja")
        abrir_btn.setStyleSheet("""
            QPushButton { background:#10B981; color:white; font-size:15px;
                          font-weight:700; padding:14px 40px; border-radius:10px; }
            QPushButton:hover { background:#059669; }
        """)
        abrir_btn.setFixedWidth(220)
        abrir_btn.clicked.connect(self._abrir_caja)
        fl.addWidget(abrir_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._layout.addWidget(frame)
        self._layout.addStretch()

    def _render_caja_abierta(self, arqueo: ArqueoCaja):
        ventas = ArqueoCaja.calcular_ventas_sistema(arqueo.usuario_id, arqueo.fecha_inicio)

        # Header
        header = QHBoxLayout()
        status = QLabel("🟢  Caja Abierta")
        status.setStyleSheet("font-size:22px; font-weight:700; color:#10B981;")
        header.addWidget(status)
        header.addStretch()

        cerrar_btn = QPushButton("🔴  Cerrar Caja")
        cerrar_btn.setStyleSheet("""
            QPushButton { background:#EF4444; color:white; font-weight:700;
                          padding:10px 28px; border-radius:8px; }
            QPushButton:hover { background:#DC2626; }
        """)
        cerrar_btn.clicked.connect(lambda: self._cerrar_caja(arqueo))
        header.addWidget(cerrar_btn)
        self._layout.addLayout(header)

        # Info apertura
        inicio = arqueo.fecha_inicio[:16].replace('T', ' ')
        info = QLabel(f"Apertura: {inicio}  ·  Fondo inicial: Bs {arqueo.monto_inicial:.2f}")
        info.setStyleSheet("color:#6B7280; font-size:12px;")
        self._layout.addWidget(info)

        # Tarjetas de ventas
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        for icono, lbl, val, color in [
            ("💵", "Efectivo",      ventas['efectivo'],      "#10B981"),
            ("💱", "QR",            ventas['qr'],            "#3B82F6"),
            ("💳", "Tarjeta",       ventas['tarjeta'],       "#8B5CF6"),
            ("🧾", "Total ventas",  ventas['total'],         "#FF6B35"),
            ("🔢", "Transacciones", ventas['transacciones'], "#F59E0B"),
        ]:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{ background:white; border:1px solid #E5E7EB;
                          border-radius:12px; padding:16px; }}
            """)
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(icono + "  " + lbl))
            v_lbl = QLabel(f"Bs {val:.2f}" if isinstance(val, float) else str(val))
            v_lbl.setStyleSheet(f"font-size:20px; font-weight:700; color:{color};")
            cl.addWidget(v_lbl)
            cards_row.addWidget(card)

        self._layout.addLayout(cards_row)
        self._layout.addStretch()

    def _abrir_caja(self):
        dialog = AbrirCajaDialog(self)
        if dialog.exec():
            monto = dialog.get_monto()
            ArqueoCaja.abrir(monto)
            self.refresh()

    def _cerrar_caja(self, arqueo: ArqueoCaja):
        dialog = CerrarCajaDialog(arqueo, self)
        if dialog.exec():
            ef, qr, tar, denoms = dialog.get_data()
            resultado = ArqueoCaja.cerrar(arqueo.id, ef, qr, tar, denoms)
            if resultado:
                dif = resultado.diferencia_total
                color = _color_diferencia(dif)
                msg = (
                    f"✅ Caja cerrada correctamente.\n\n"
                    f"Diferencia total: {_texto_diferencia(dif)}"
                )
                QMessageBox.information(self, "Caja Cerrada", msg)
                self.refresh()


# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: Historial de Arqueos
# ──────────────────────────────────────────────────────────────────────────────

class HistorialArqueosTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        top = QHBoxLayout()

        usuario = get_current_user()
        self.filtro_combo = QComboBox()
        self.filtro_combo.addItem("Mis arqueos", usuario.id)
        if usuario.is_admin():
            self.filtro_combo.addItem("Todos los cajeros", None)
            users = User.get_all()
            for u in users:
                self.filtro_combo.addItem(f"  {u.nombre}", u.id)
        self.filtro_combo.currentIndexChanged.connect(self.load_data)
        top.addWidget(QLabel("Ver:"))
        top.addWidget(self.filtro_combo)
        top.addStretch()

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_data)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "#", "Cajero", "Apertura", "Cierre", "Estado",
            "Sis. Efec.", "Sis. QR", "Sis. Tar.", "Total Sis.",
            "Diferencia", "Trans."
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def load_data(self):
        filtro_id = self.filtro_combo.currentData()
        usuario   = get_current_user()

        if filtro_id is None:
            arqueos = ArqueoCaja.get_all()
        else:
            arqueos = ArqueoCaja.get_by_usuario(filtro_id)

        # Mapa usuario id → nombre
        user_map = {u.id: u.nombre for u in User.get_all()}

        self.table.setRowCount(len(arqueos))
        for row, a in enumerate(arqueos):
            self.table.setItem(row, 0,  QTableWidgetItem(str(a.id)))
            self.table.setItem(row, 1,  QTableWidgetItem(user_map.get(a.usuario_id, '—')))
            self.table.setItem(row, 2,  QTableWidgetItem(a.fecha_inicio[:16].replace('T',' ')))
            cierre = a.fecha_cierre[:16].replace('T',' ') if a.fecha_cierre else '—'
            self.table.setItem(row, 3,  QTableWidgetItem(cierre))

            estado_item = QTableWidgetItem("🟢 Abierto" if a.estado == 'abierto' else "🔴 Cerrado")
            estado_item.setForeground(QColor("#10B981" if a.estado == 'abierto' else "#EF4444"))
            self.table.setItem(row, 4,  estado_item)

            self.table.setItem(row, 5,  QTableWidgetItem(f"Bs {a.sistema_efectivo:.2f}"))
            self.table.setItem(row, 6,  QTableWidgetItem(f"Bs {a.sistema_qr:.2f}"))
            self.table.setItem(row, 7,  QTableWidgetItem(f"Bs {a.sistema_tarjeta:.2f}"))
            self.table.setItem(row, 8,  QTableWidgetItem(f"Bs {a.sistema_total:.2f}"))

            dif = a.diferencia_total
            dif_item = QTableWidgetItem(_texto_diferencia(dif))
            dif_item.setForeground(QColor(_color_diferencia(dif)))
            self.table.setItem(row, 9,  dif_item)
            self.table.setItem(row, 10, QTableWidgetItem(str(a.total_transacciones)))


# ──────────────────────────────────────────────────────────────────────────────
# WIDGET PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

class ArqueoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title = QLabel("🏦 Arqueo de Caja")
        title.setStyleSheet("font-size:28px; font-weight:700; color:#1F2937;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        sub = QLabel("Gestión de apertura, cierre e historial de caja por cajero.")
        sub.setStyleSheet("color:#6B7280; font-size:13px;")
        layout.addWidget(sub)

        tabs = QTabWidget()
        self.caja_tab = CajaActualTab()
        tabs.addTab(self.caja_tab,        "🟢 Caja Actual")
        tabs.addTab(HistorialArqueosTab(), "📋 Historial de Arqueos")
        layout.addWidget(tabs)
