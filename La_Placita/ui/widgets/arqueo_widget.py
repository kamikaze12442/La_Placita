"""
Arqueo de Caja Widget — Rediseño moderno y compacto
"""

import json
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox, QFrame, QDoubleSpinBox,
    QHeaderView, QScrollArea, QGridLayout, QSpinBox, QComboBox, QDateEdit
)
from PySide6.QtCore import Qt, QTimer, QDate
from PySide6.QtGui import QColor, QFont
from models.arqueo import ArqueoCaja
from models.user import get_current_user, User
from database.connection import db


BILLETES = [200, 100, 50, 20, 10]
MONEDAS  = [5, 2, 1, 0.50, 0.20, 0.10]

def _color_dif(v):
    return "#10B981" if v > 0 else "#EF4444" if v < 0 else "#6B7280"

def _texto_dif(v):
    if v > 0: return f"▲ +Bs {v:.2f} sobrante"
    if v < 0: return f"▼ Bs {v:.2f} faltante"
    return "✓ Exacto"

# ── Estilos reutilizables ─────────────────────────────────────────────────────
BTN_PRIMARY = """
    QPushButton { background:#10B981; color:white; font-size:13px; font-weight:600;
                  padding:8px 20px; border-radius:8px; border:none; }
    QPushButton:hover { background:#059669; }
"""
BTN_DANGER = """
    QPushButton { background:#EF4444; color:white; font-size:13px; font-weight:600;
                  padding:8px 20px; border-radius:8px; border:none; }
    QPushButton:hover { background:#DC2626; }
"""
BTN_SECONDARY = """
    QPushButton { background:#F3F4F6; color:#374151; font-size:13px; font-weight:600;
                  padding:8px 20px; border-radius:8px; border:1px solid #E5E7EB; }
    QPushButton:hover { background:#E5E7EB; }
"""
CARD_STYLE = """
    QFrame { background:white; border:1px solid #E5E7EB;
             border-radius:12px; }
"""
SPIN_STYLE = """
    QDoubleSpinBox, QSpinBox {
        background:white; border:1px solid #E2E8F0;
        border-radius:6px; padding:5px 8px; font-size:13px;
    }
    QDoubleSpinBox:focus, QSpinBox:focus { border-color:#FF6B35; }
"""


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Abrir Caja
# ──────────────────────────────────────────────────────────────────────────────

class AbrirCajaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Abrir Caja")
        self.setFixedWidth(400)
        self.setStyleSheet("background:white;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        title = QLabel("🟢  Apertura de Caja")
        title.setStyleSheet("font-size:17px; font-weight:700; color:#1F2937;")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#E5E7EB;")
        layout.addWidget(sep)

        # Info
        info = QLabel("Se registrará tu usuario y la hora de inicio.\nTodas las ventas de este turno quedarán asociadas a este arqueo.")
        info.setStyleSheet("color:#6B7280; font-size:12px; line-height:1.5;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Fondo inicial
        fondo_frame = QFrame()
        fondo_frame.setStyleSheet("QFrame{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;}")
        fondo_lay = QVBoxLayout(fondo_frame)
        fondo_lay.setContentsMargins(14, 12, 14, 12)

        fondo_lbl = QLabel("Fondo inicial en caja")
        fondo_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#6B7280;")
        fondo_lay.addWidget(fondo_lbl)

        self.monto_inicial = QDoubleSpinBox()
        self.monto_inicial.setRange(0, 999999)
        self.monto_inicial.setDecimals(2)
        self.monto_inicial.setPrefix("Bs ")
        self.monto_inicial.setValue(0)
        self.monto_inicial.setStyleSheet(SPIN_STYLE)
        self.monto_inicial.setFixedHeight(38)
        fondo_lay.addWidget(self.monto_inicial)
        layout.addWidget(fondo_frame)

        # Botones
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet(BTN_SECONDARY)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("🟢  Abrir Caja")
        ok_btn.setStyleSheet(BTN_PRIMARY)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def get_monto(self):
        return self.monto_inicial.value()


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo: Cerrar Caja — Calculadora de efectivo + panel lateral
# ──────────────────────────────────────────────────────────────────────────────

class CerrarCajaDialog(QDialog):
    def __init__(self, arqueo: ArqueoCaja, parent=None):
        super().__init__(parent)
        self.arqueo  = arqueo
        self._ventas = ArqueoCaja.calcular_ventas_sistema(arqueo.usuario_id, arqueo.fecha_inicio)
        self._conteo = {d: 0 for d in BILLETES + MONEDAS}

        self.setWindowTitle("Cierre de Caja")
        self.setMinimumSize(1020, 660)
        self.resize(1060, 700)
        self.setStyleSheet("QDialog { background:#F8FAFC; } QLabel { background:transparent; }")
        self._init_ui()
        self._update_totals()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Barra superior oscura ─────────────────────────────────────
        top_bar = QFrame()
        top_bar.setFixedHeight(54)
        top_bar.setStyleSheet("QFrame { background:#1E293B; border:none; }")
        tb = QHBoxLayout(top_bar)
        tb.setContentsMargins(24, 0, 24, 0)
        tb.setSpacing(10)

        title = QLabel("🔴  Cierre de Caja")
        title.setStyleSheet("font-size:15px; font-weight:700; color:white;")
        tb.addWidget(title)

        inicio = self.arqueo.fecha_inicio[:16].replace('T', ' ')
        sub = QLabel(f"·  Turno iniciado el {inicio}")
        sub.setStyleSheet("font-size:12px; color:#64748B;")
        tb.addWidget(sub)
        tb.addStretch()
        root.addWidget(top_bar)

        # ── Cuerpo ────────────────────────────────────────────────────
        body = QHBoxLayout()
        body.setContentsMargins(20, 16, 20, 12)
        body.setSpacing(14)

        # ═══════════════════════════════════════════════
        # IZQUIERDA: calculadora
        # ═══════════════════════════════════════════════
        left = QVBoxLayout()
        left.setSpacing(10)

        # — Display efectivo contado —
        display = QFrame()
        display.setStyleSheet("""
            QFrame { background:white; border:1px solid #E2E8F0; border-radius:12px; }
        """)
        disp_lay = QHBoxLayout(display)
        disp_lay.setContentsMargins(18, 14, 14, 14)
        disp_lay.setSpacing(0)

        disp_text = QVBoxLayout()
        disp_text.setSpacing(3)
        disp_cap = QLabel("EFECTIVO CONTADO")
        disp_cap.setStyleSheet(
            "font-size:10px; font-weight:700; color:#94A3B8; letter-spacing:1px;")
        disp_text.addWidget(disp_cap)
        self._ef_display = QLabel("Bs 0.00")
        self._ef_display.setStyleSheet(
            "font-size:30px; font-weight:800; color:#1E293B;")
        disp_text.addWidget(self._ef_display)
        self._ef_detalle = QLabel("Sin conteo aún")
        self._ef_detalle.setStyleSheet("font-size:11px; color:#94A3B8;")
        self._ef_detalle.setWordWrap(True)
        disp_text.addWidget(self._ef_detalle)
        disp_lay.addLayout(disp_text)
        disp_lay.addStretch()

        reset_btn = QPushButton("✕  Limpiar")
        reset_btn.setFixedHeight(32)
        reset_btn.setStyleSheet("""
            QPushButton { background:#FEF2F2; color:#EF4444; border:1px solid #FECACA;
                          border-radius:7px; font-size:12px; font-weight:600; padding:0 14px; }
            QPushButton:hover { background:#FEE2E2; }
        """)
        reset_btn.clicked.connect(self._reset_conteo)
        disp_lay.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignTop)
        left.addWidget(display)

        # — Botones denominaciones —
        denom_card = QFrame()
        denom_card.setStyleSheet("""
            QFrame { background:white; border:1px solid #E2E8F0; border-radius:12px; }
        """)
        dc_lay = QVBoxLayout(denom_card)
        dc_lay.setContentsMargins(16, 14, 16, 14)
        dc_lay.setSpacing(10)

        bill_cap = QLabel("BILLETES")
        bill_cap.setStyleSheet(
            "font-size:10px; font-weight:700; color:#94A3B8; letter-spacing:1px;")
        dc_lay.addWidget(bill_cap)

        bill_row = QHBoxLayout()
        bill_row.setSpacing(8)
        for d in BILLETES:
            bill_row.addWidget(self._denom_btn(d, "#F0FDF4", "#16A34A", "#DCFCE7"))
        dc_lay.addLayout(bill_row)

        mon_cap = QLabel("MONEDAS")
        mon_cap.setStyleSheet(
            "font-size:10px; font-weight:700; color:#94A3B8; letter-spacing:1px;")
        dc_lay.addWidget(mon_cap)

        mon_row = QHBoxLayout()
        mon_row.setSpacing(8)
        for d in MONEDAS:
            mon_row.addWidget(self._denom_btn(d, "#EFF6FF", "#2563EB", "#DBEAFE"))
        dc_lay.addLayout(mon_row)

        left.addWidget(denom_card)

        # — QR manual —
        qr_card = QFrame()
        qr_card.setStyleSheet("""
            QFrame { background:white; border:1px solid #E2E8F0; border-radius:12px; }
        """)
        qr_lay = QHBoxLayout(qr_card)
        qr_lay.setContentsMargins(18, 12, 18, 12)

        qr_info = QVBoxLayout()
        qr_info.setSpacing(2)
        qr_title = QLabel("📱  QR — monto recibido en el turno")
        qr_title.setStyleSheet("font-size:13px; font-weight:600; color:#1E293B;")
        qr_sub = QLabel("Ingresa el total cobrado por QR")
        qr_sub.setStyleSheet("font-size:11px; color:#94A3B8;")
        qr_info.addWidget(qr_title)
        qr_info.addWidget(qr_sub)
        qr_lay.addLayout(qr_info)
        qr_lay.addStretch()

        self._qr_spin = QDoubleSpinBox()
        self._qr_spin.setRange(0, 999999)
        self._qr_spin.setDecimals(2)
        self._qr_spin.setPrefix("Bs ")
        self._qr_spin.setFixedWidth(150)
        self._qr_spin.setFixedHeight(38)
        self._qr_spin.setStyleSheet("""
            QDoubleSpinBox { background:#F8FAFC; border:1.5px solid #E2E8F0;
                             border-radius:8px; padding:4px 8px;
                             font-size:15px; font-weight:700; color:#1E293B; }
            QDoubleSpinBox:focus { border-color:#3B82F6; background:white; }
        """)
        self._qr_spin.valueChanged.connect(self._update_totals)
        qr_lay.addWidget(self._qr_spin)
        left.addWidget(qr_card)

        body.addLayout(left, stretch=3)

        # ═══════════════════════════════════════════════
        # DERECHA: sistema + diferencias
        # ═══════════════════════════════════════════════
        right = QVBoxLayout()
        right.setSpacing(10)

        # — Panel sistema —
        sys_card = QFrame()
        sys_card.setStyleSheet("""
            QFrame { background:#1E293B; border-radius:12px; border:none; }
        """)
        sys_lay = QVBoxLayout(sys_card)
        sys_lay.setContentsMargins(18, 16, 18, 16)
        sys_lay.setSpacing(0)

        sys_cap = QLabel("SISTEMA REGISTRÓ")
        sys_cap.setStyleSheet(
            "font-size:10px; font-weight:700; color:#475569; letter-spacing:1px;")
        sys_lay.addWidget(sys_cap)

        sys_lay.addSpacing(10)
        monto_ini = getattr(self.arqueo, 'monto_inicial', 0) or 0

        v = self._ventas
        filas = [
            ("💵", "Efectivo",    (self._ventas['efectivo'] + monto_ini),  "#4ADE80"),
            ("📱", "QR",           v['qr'],        "#60A5FA"),
            ("🧾", "Total ventas", (self._ventas['total'] + monto_ini),     "#FB923C"),
        ]
        for emoji, lbl_txt, val, color in filas:
            row = QHBoxLayout()
            row.setContentsMargins(0, 5, 0, 5)
            k = QLabel(f"{emoji}  {lbl_txt}")
            k.setStyleSheet("font-size:13px; color:#94A3B8;")
            row.addWidget(k)
            row.addStretch()
            vl = QLabel(f"Bs {val:.2f}")
            vl.setStyleSheet(f"font-size:13px; font-weight:700; color:{color};")
            row.addWidget(vl)
            sys_lay.addLayout(row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#334155; margin-top:6px; margin-bottom:6px;")
        sys_lay.addWidget(sep)

        tr_row = QHBoxLayout()
        tr_k = QLabel("🔢  Transacciones")
        tr_k.setStyleSheet("font-size:13px; color:#94A3B8;")
        tr_row.addWidget(tr_k)
        tr_row.addStretch()
        tr_v = QLabel(str(v['transacciones']))
        tr_v.setStyleSheet("font-size:15px; font-weight:800; color:#F59E0B;")
        tr_row.addWidget(tr_v)
        sys_lay.addLayout(tr_row)

        right.addWidget(sys_card)

        # — Panel diferencias en tiempo real —
        dif_card = QFrame()
        dif_card.setStyleSheet("""
            QFrame { background:white; border:1px solid #E2E8F0; border-radius:12px; }
        """)
        dif_lay = QVBoxLayout(dif_card)
        dif_lay.setContentsMargins(18, 14, 18, 14)
        dif_lay.setSpacing(0)

        dif_cap = QLabel("DIFERENCIAS  (conteo − sistema)")
        dif_cap.setStyleSheet(
            "font-size:10px; font-weight:700; color:#94A3B8; letter-spacing:1px;")
        dif_lay.addWidget(dif_cap)
        dif_lay.addSpacing(10)

        self._dif_labels = {}
        for key, emoji, label in [("ef", "💵", "Efectivo"),
                                   ("qr", "📱", "QR"),
                                   ("tot","🧾", "Total")]:
            row = QHBoxLayout()
            row.setContentsMargins(0, 5, 0, 5)
            k = QLabel(f"{emoji}  {label}")
            k.setStyleSheet("font-size:13px; color:#64748B;")
            row.addWidget(k)
            row.addStretch()
            vl = QLabel("—")
            vl.setStyleSheet("font-size:13px; font-weight:700; color:#94A3B8;")
            row.addWidget(vl)
            self._dif_labels[key] = vl
            dif_lay.addLayout(row)

        right.addWidget(dif_card)
        right.addStretch()

        body.addLayout(right, stretch=2)
        root.addLayout(body)

        # ── Pie de página ─────────────────────────────────────────────
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet(
            "QFrame { background:white; border-top:1px solid #E2E8F0; border-radius:0; }")
        ft = QHBoxLayout(footer)
        ft.setContentsMargins(24, 0, 24, 0)
        ft.setSpacing(10)
        ft.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet("""
            QPushButton { background:#F1F5F9; color:#475569; border:1px solid #E2E8F0;
                          border-radius:8px; font-size:13px; font-weight:600; padding:0 20px; }
            QPushButton:hover { background:#E2E8F0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        ft.addWidget(cancel_btn)

        ok_btn = QPushButton("🔴  Confirmar Cierre")
        ok_btn.setFixedHeight(36)
        ok_btn.setStyleSheet("""
            QPushButton { background:#EF4444; color:white; border:none;
                          border-radius:8px; font-size:13px; font-weight:600; padding:0 24px; }
            QPushButton:hover { background:#DC2626; }
        """)
        ok_btn.clicked.connect(self.accept)
        ft.addWidget(ok_btn)

        root.addWidget(footer)

    # ── Helpers ───────────────────────────────────────────────────────

    def _denom_btn(self, denom: float, bg: str, color: str, border: str) -> QPushButton:
        from functools import partial
        text = f"Bs {int(denom)}" if denom >= 1 else f"Bs {denom:.2f}"
        btn  = QPushButton(text)
        btn.setFixedHeight(54)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{bg}; color:{color};
                border:1.5px solid {border};
                border-radius:10px; font-size:15px; font-weight:700;
            }}
            QPushButton:hover  {{ background:{color}22; border-color:{color}; }}
            QPushButton:pressed {{ background:{color}38; }}
        """)
        btn.clicked.connect(partial(self._add, denom))
        return btn

    def _add(self, denom: float, *args):
        self._conteo[denom] += 1
        self._update_totals()

    def _reset_conteo(self):
        for d in self._conteo:
            self._conteo[d] = 0
        self._qr_spin.setValue(0)
        self._update_totals()

    def _update_totals(self):
        ef = sum(d * c for d, c in self._conteo.items())
        qr = self._qr_spin.value()

        # Display
        self._ef_display.setText(f"Bs {ef:.2f}")
        partes = []
        for d in BILLETES + MONEDAS:
            c = self._conteo[d]
            if c:
                txt = f"Bs {int(d)}" if d >= 1 else f"Bs {d:.2f}"
                partes.append(f"{c}×{txt}")
        self._ef_detalle.setText("  +  ".join(partes) if partes else "Sin conteo aún")
        monto_ini = getattr(self.arqueo, 'monto_inicial', 0) or 0

        # Diferencias
        vals = {
            "ef":  round(ef  - (self._ventas['efectivo'] + monto_ini), 2),
            "qr":  round(qr  - self._ventas['qr'],       2),
            "tot": round((ef + qr) - (self._ventas['total'] + monto_ini), 2),
        }
        for key, val in vals.items():
            lbl = self._dif_labels[key]
            lbl.setText(_texto_dif(val))
            lbl.setStyleSheet(
                f"font-size:13px; font-weight:700; color:{_color_dif(val)};")

    def get_data(self):
        ef     = sum(d * c for d, c in self._conteo.items())
        qr     = self._qr_spin.value()
        denoms = {str(k): v for k, v in self._conteo.items() if v > 0}
        return ef, qr, 0.0, denoms


# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: Caja Actual  — sin duplicación, sin mixto
# ──────────────────────────────────────────────────────────────────────────────


def _get_usuario_actual():
    """
    Obtiene el usuario actual con múltiples fallbacks.
    Robusto frente al problema de variable global en ejecutables PyInstaller.
    """
    # Intento 1: variable global normal
    from models.user import get_current_user
    u = get_current_user()
    if u:
        return u

    # Intento 2: reimportar el módulo para forzar la variable global
    import importlib, sys
    try:
        if "models.user" in sys.modules:
            mod = sys.modules["models.user"]
            u = getattr(mod, "current_user", None)
            if u:
                return u
    except Exception:
        pass

    return None

class CajaActualTab(QWidget):
    def __init__(self):
        super().__init__()
        self._arqueo_actual = None
        # Guardar usuario en init, cuando la sesion esta garantizada
        from models.user import get_current_user
        u = get_current_user()
        self._usuario_id = u.id if u else None
        self._usuario_nombre = u.nombre if u else "Usuario"
        if not self._usuario_id:
            # Fallback: buscar en QApplication
            try:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app and hasattr(app, "_current_user") and app._current_user:
                    self._usuario_id = app._current_user.id
                    self._usuario_nombre = app._current_user.nombre
            except Exception:
                pass

        # Layout fijo — nunca se destruye
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # ── Página: caja cerrada ──────────────────────────────────────
        self._page_cerrada = QFrame()
        self._page_cerrada.setStyleSheet("QFrame{background:transparent;border:none;}")
        pc = QVBoxLayout(self._page_cerrada)
        pc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pc.setSpacing(14)

        card_cerrada = QFrame()
        card_cerrada.setStyleSheet("""
            QFrame { background:white; border:1px solid #E5E7EB; border-radius:16px; }
        """)
        card_cerrada.setFixedWidth(420)
        cc = QVBoxLayout(card_cerrada)
        cc.setContentsMargins(36, 32, 36, 32)
        cc.setSpacing(12)
        cc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lk = QLabel("🔒")
        lk.setStyleSheet("font-size:40px;")
        lk.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cc.addWidget(lk)

        lk2 = QLabel("Caja cerrada")
        lk2.setStyleSheet("font-size:18px; font-weight:700; color:#1F2937;")
        lk2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cc.addWidget(lk2)

        lk3 = QLabel("No hay turno activo. Abre la caja\npara comenzar a registrar ventas.")
        lk3.setStyleSheet("font-size:13px; color:#6B7280; line-height:1.5;")
        lk3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cc.addWidget(lk3)

        self._btn_abrir = QPushButton("🟢  Abrir Caja")
        self._btn_abrir.setFixedHeight(42)
        self._btn_abrir.setStyleSheet("""
            QPushButton { background:#10B981; color:white; font-size:14px;
                          font-weight:600; border-radius:8px; border:none; }
            QPushButton:hover { background:#059669; }
        """)
        self._btn_abrir.clicked.connect(self._abrir_caja)
        cc.addWidget(self._btn_abrir)
        pc.addWidget(card_cerrada, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._page_cerrada)

        # ── Página: caja abierta ──────────────────────────────────────
        self._page_abierta = QFrame()
        self._page_abierta.setStyleSheet("QFrame{background:transparent;border:none;}")
        pa = QVBoxLayout(self._page_abierta)
        pa.setContentsMargins(0, 0, 0, 0)
        pa.setSpacing(12)

        # Barra de estado
        self._status_bar = QFrame()
        self._status_bar.setStyleSheet("""
            QFrame { background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; }
        """)
        sb = QHBoxLayout(self._status_bar)
        sb.setContentsMargins(16, 10, 16, 10)
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("font-size:13px; color:#065F46;")
        sb.addWidget(self._status_lbl)
        sb.addStretch()
        self._btn_cerrar = QPushButton("🔴  Cerrar Caja")
        self._btn_cerrar.setFixedHeight(36)
        self._btn_cerrar.setStyleSheet("""
            QPushButton { background:#EF4444; color:white; font-size:13px; font-weight:600;
                          border-radius:8px; border:none; padding:0 18px; }
            QPushButton:hover { background:#DC2626; }
        """)
        self._btn_cerrar.clicked.connect(self._cerrar_caja)
        sb.addWidget(self._btn_cerrar)
        pa.addWidget(self._status_bar)

        # Tarjetas — 4 fijas (sin mixto)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self._cards = {}
        for key, emoji, label, color, bg, border in [
            ("efectivo",      "💵", "Efectivo",      "#10B981", "#F0FDF4", "#BBF7D0"),
            ("qr",            "📱", "QR",             "#3B82F6", "#EFF6FF", "#BFDBFE"),
            ("total",         "🧾", "Total ventas",   "#FF6B35", "#FFF7ED", "#FED7AA"),
            ("transacciones", "🔢", "Transacciones",  "#F59E0B", "#FFFBEB", "#FDE68A"),
        ]:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{ background:{bg}; border:1px solid {border};
                          border-radius:12px; }}
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 14, 18, 14)
            cl.setSpacing(4)

            top = QHBoxLayout()
            e = QLabel(emoji)
            e.setStyleSheet("font-size:20px;")
            top.addWidget(e)
            top.addStretch()
            cl.addLayout(top)

            val_lbl = QLabel("—")
            val_lbl.setStyleSheet(
                f"font-size:20px; font-weight:800; color:{color};")
            cl.addWidget(val_lbl)

            k = QLabel(label)
            k.setStyleSheet("font-size:12px; color:#6B7280; font-weight:500;")
            cl.addWidget(k)

            self._cards[key] = val_lbl
            cards_row.addWidget(card)

        pa.addLayout(cards_row)
        pa.addStretch()
        root.addWidget(self._page_abierta)

        # Timer auto-refresh
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(30000)
        self.refresh()

    # ── Refresh — solo actualiza valores, no recrea widgets ───────────
    def refresh(self):
        uid = self._usuario_id
        if not uid:
            # Ultimo intento de recuperar el usuario
            from models.user import get_current_user
            u = get_current_user()
            if u:
                self._usuario_id = u.id
                uid = u.id
            else:
                try:
                    from PySide6.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app and hasattr(app, "_current_user") and app._current_user:
                        self._usuario_id = app._current_user.id
                        uid = self._usuario_id
                except Exception:
                    pass
        if not uid:
            self._page_cerrada.setVisible(True)
            self._page_abierta.setVisible(False)
            return
        arqueo  = ArqueoCaja.get_abierto_por_usuario(uid)
        self._arqueo_actual = arqueo

        if arqueo:
            ventas = ArqueoCaja.calcular_ventas_sistema(
                arqueo.usuario_id, arqueo.fecha_inicio)
            inicio = arqueo.fecha_inicio[:16].replace("T", " ")
            self._status_lbl.setText(
                f"<b>Caja abierta</b>  ·  Turno desde {inicio}"
                f"  ·  Fondo inicial: <b>Bs {arqueo.monto_inicial:.2f}</b>")
            self._cards["efectivo"].setText(f"Bs {ventas['efectivo']:.2f}")
            self._cards["qr"].setText(f"Bs {ventas['qr']:.2f}")
            self._cards["total"].setText(f"Bs {ventas['total']:.2f}")
            self._cards["transacciones"].setText(str(ventas["transacciones"]))
            self._page_cerrada.setVisible(False)
            self._page_abierta.setVisible(True)
        else:
            self._page_cerrada.setVisible(True)
            self._page_abierta.setVisible(False)

    def _abrir_caja(self):
        dialog = AbrirCajaDialog(self)
        if not dialog.exec():
            return
        uid = self._usuario_id
        if not uid:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error de sesion",
                "No se pudo identificar al usuario.\n"
                "Cierra la aplicacion y vuelve a abrir.")
            return
        # Intentar abrir — si ya hay una abierta, devuelve la existente
        ArqueoCaja.abrir(monto_inicial=dialog.get_monto(), usuario_id=uid)
        # Siempre refrescar, haya o no error
        self.refresh()

    def _cerrar_caja(self):
        if not self._arqueo_actual:
            return
        dialog = CerrarCajaDialog(self._arqueo_actual, self)
        if dialog.exec():
            ef, qr, tar, denoms = dialog.get_data()
            resultado = ArqueoCaja.cerrar(
                self._arqueo_actual.id, ef, qr, tar, denoms)
            if resultado:
                dif = resultado.diferencia_total
                QMessageBox.information(
                    self, "Caja Cerrada",
                    f"✅ Caja cerrada correctamente.\n\n"
                    f"Diferencia total: {_texto_dif(dif)}")
                self.refresh()


# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: Historial — tabla compacta 7 cols + panel de detalle lateral
# ──────────────────────────────────────────────────────────────────────────────

class HistorialArqueosTab(QWidget):
    def __init__(self):
        super().__init__()
        self._arqueos     = []
        self._user_map    = {}
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(0, 8, 0, 0)

        # ── Filtros ───────────────────────────────────────────────────
        fframe = QFrame()
        fframe.setStyleSheet(
            "QFrame{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;}")
        ff = QHBoxLayout(fframe)
        ff.setContentsMargins(12, 8, 12, 8)
        ff.setSpacing(10)

        usuario = get_current_user()
        self.cajero_combo = QComboBox()
        self.cajero_combo.setMinimumWidth(140)
        self.cajero_combo.addItem("Mis arqueos", usuario.id)
        if usuario.is_admin():
            self.cajero_combo.addItem("Todos", None)
            for u in User.get_all():
                self.cajero_combo.addItem(u.nombre, u.id)
        ff.addWidget(QLabel("Cajero:"))
        ff.addWidget(self.cajero_combo)

        self.estado_combo = QComboBox()
        self.estado_combo.addItem("Todos",       None)
        self.estado_combo.addItem("🟢 Abiertos", "abierto")
        self.estado_combo.addItem("🔴 Cerrados", "cerrado")
        ff.addWidget(QLabel("Estado:"))
        ff.addWidget(self.estado_combo)

        self.fecha_desde = QDateEdit()
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_desde.setDisplayFormat("dd/MM/yyyy")
        ff.addWidget(QLabel("Desde:"))
        ff.addWidget(self.fecha_desde)

        self.fecha_hasta = QDateEdit()
        self.fecha_hasta.setCalendarPopup(True)
        self.fecha_hasta.setDate(QDate.currentDate().addDays(1))
        self.fecha_hasta.setDisplayFormat("dd/MM/yyyy")
        ff.addWidget(QLabel("Hasta:"))
        ff.addWidget(self.fecha_hasta)

        buscar_btn = QPushButton("🔍 Buscar")
        buscar_btn.setStyleSheet("""
            QPushButton{background:#3B82F6;color:white;padding:7px 16px;
                        border-radius:7px;font-weight:600;border:none;}
            QPushButton:hover{background:#2563EB;}
        """)
        buscar_btn.clicked.connect(self.load_data)
        ff.addWidget(buscar_btn)

        limpiar_btn = QPushButton("✖")
        limpiar_btn.setStyleSheet(BTN_SECONDARY)
        limpiar_btn.setFixedWidth(36)
        limpiar_btn.clicked.connect(self._limpiar)
        ff.addWidget(limpiar_btn)
        ff.addStretch()
        root.addWidget(fframe)

        self.resumen_lbl = QLabel("")
        self.resumen_lbl.setStyleSheet(
            "color:#6B7280; font-size:12px; padding-left:4px;")
        root.addWidget(self.resumen_lbl)

        # ── Cuerpo: tabla + panel detalle ─────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(12)

        # Tabla compacta 7 columnas
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Cajero", "Apertura", "Cierre", "Estado",
            "Total sistema", "Diferencia", "Trans."
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection)
        self.table.setStyleSheet("""
            QTableWidget { border:1px solid #E5E7EB; border-radius:10px;
                           background:white; font-size:12px;
                           gridline-color:#F3F4F6; outline:none; }
            QHeaderView::section { background:#F9FAFB; color:#6B7280;
                font-weight:600; padding:8px; border:none;
                border-bottom:1px solid #E5E7EB; }
            QTableWidget::item { padding:7px 6px; }
            QTableWidget::item:alternate { background:#F9FAFB; }
            QTableWidget::item:selected { background:#EFF6FF; color:#1E293B; }
        """)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        body.addWidget(self.table, stretch=3)

        # Panel de detalle lateral
        self._detail_panel = QFrame()
        self._detail_panel.setFixedWidth(260)
        self._detail_panel.setStyleSheet("""
            QFrame { background:white; border:1px solid #E5E7EB;
                     border-radius:12px; }
        """)
        self._detail_panel.setVisible(False)
        dp = QVBoxLayout(self._detail_panel)
        dp.setContentsMargins(18, 16, 18, 16)
        dp.setSpacing(0)

        det_cap = QLabel("DETALLE DEL ARQUEO")
        det_cap.setStyleSheet(
            "font-size:10px; font-weight:700; color:#94A3B8; letter-spacing:1px;")
        dp.addWidget(det_cap)
        dp.addSpacing(12)

        self._det_rows = {}
        filas_det = [
            ("cajero",        "👤", "Cajero"),
            ("estado",        "📌", "Estado"),
            ("apertura",      "🕐", "Apertura"),
            ("cierre",        "🕐", "Cierre"),
            ("fondo",         "💼", "Fondo inicial"),
            ("sep1",          None,  None),
            ("efectivo",      "💵", "Efectivo"),
            ("qr",            "📱", "QR"),
            ("total",         "🧾", "Total sistema"),
            ("sep2",          None,  None),
            ("dif",           "📊", "Diferencia"),
            ("trans",         "🔢", "Transacciones"),
        ]
        for key, emoji, label in filas_det:
            if key.startswith("sep"):
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("color:#F1F5F9; margin:8px 0;")
                dp.addWidget(sep)
                continue
            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            rlay  = QHBoxLayout(row_w)
            rlay.setContentsMargins(0, 5, 0, 5)
            rlay.setSpacing(6)
            k = QLabel(f"{emoji}  {label}")
            k.setStyleSheet("font-size:12px; color:#64748B;")
            rlay.addWidget(k)
            rlay.addStretch()
            v = QLabel("—")
            v.setStyleSheet("font-size:12px; font-weight:700; color:#1E293B;")
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            rlay.addWidget(v)
            self._det_rows[key] = v
            dp.addWidget(row_w)

        dp.addStretch()
        body.addWidget(self._detail_panel, stretch=0)
        root.addLayout(body)

    # ── Eventos ───────────────────────────────────────────────────────
    def _limpiar(self):
        self.cajero_combo.setCurrentIndex(0)
        self.estado_combo.setCurrentIndex(0)
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_hasta.setDate(QDate.currentDate().addDays(1))
        self._detail_panel.setVisible(False)
        self.load_data()

    def _on_row_selected(self):
        rows = self.table.selectedItems()
        if not rows:
            self._detail_panel.setVisible(False)
            return
        row = self.table.currentRow()
        if row < 0 or row >= len(self._arqueos):
            return
        a = self._arqueos[row]
        nombre = self._user_map.get(a.usuario_id, "—")
        es_ab  = a.estado == "abierto"
        dif    = a.diferencia_total

        self._det_rows["cajero"].setText(nombre)
        self._det_rows["estado"].setText(
            "🟢 Abierto" if es_ab else "🔴 Cerrado")
        self._det_rows["estado"].setStyleSheet(
            f"font-size:12px; font-weight:700; "
            f"color:{'#10B981' if es_ab else '#EF4444'};")
        self._det_rows["apertura"].setText(
            a.fecha_inicio[:16].replace("T", " "))
        self._det_rows["cierre"].setText(
            a.fecha_cierre[:16].replace("T", " ") if a.fecha_cierre else "—")
        self._det_rows["fondo"].setText(f"Bs {a.monto_inicial:.2f}")
        self._det_rows["efectivo"].setText(f"Bs {a.sistema_efectivo:.2f}")
        self._det_rows["qr"].setText(f"Bs {a.sistema_qr:.2f}")
        self._det_rows["total"].setText(f"Bs {a.sistema_total:.2f}")
        self._det_rows["dif"].setText(_texto_dif(dif))
        self._det_rows["dif"].setStyleSheet(
            f"font-size:12px; font-weight:700; color:{_color_dif(dif)};")
        self._det_rows["trans"].setText(str(a.total_transacciones))
        self._detail_panel.setVisible(True)

    # ── Carga de datos ────────────────────────────────────────────────
    def load_data(self):
        cajero_id = self.cajero_combo.currentData()
        estado    = self.estado_combo.currentData()
        desde     = self.fecha_desde.date().toString("yyyy-MM-dd")
        hasta     = self.fecha_hasta.date().toString("yyyy-MM-dd") + " 23:59:59"

        q      = "SELECT * FROM arqueos_caja WHERE 1=1"
        params = []
        if cajero_id is not None:
            q += " AND usuario_id = ?"
            params.append(cajero_id)
        if estado:
            q += " AND estado = ?"
            params.append(estado)
        q += " AND fecha_inicio >= ? AND fecha_inicio <= ?"
        params += [desde, hasta]
        q += " ORDER BY fecha_inicio DESC LIMIT 200"

        rows = db.fetch_all(q, tuple(params))
        self._arqueos  = []
        for r in rows:
            try:
                self._arqueos.append(ArqueoCaja(**dict(r)))
            except Exception:
                pass

        self._user_map = {u.id: u.nombre for u in User.get_all()}
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._arqueos))
        self._detail_panel.setVisible(False)

        total_sis = 0.0
        total_dif = 0.0

        for row, a in enumerate(self._arqueos):
            nombre = self._user_map.get(a.usuario_id, "—")
            self.table.setItem(row, 0, QTableWidgetItem(nombre))
            self.table.setItem(row, 1, QTableWidgetItem(
                a.fecha_inicio[:16].replace("T", " ")))
            cierre = a.fecha_cierre[:16].replace("T", " ") if a.fecha_cierre else "—"
            self.table.setItem(row, 2, QTableWidgetItem(cierre))

            es_ab    = a.estado == "abierto"
            est_item = QTableWidgetItem("🟢 Abierto" if es_ab else "🔴 Cerrado")
            est_item.setForeground(QColor("#10B981" if es_ab else "#EF4444"))
            self.table.setItem(row, 3, est_item)

            self.table.setItem(row, 4, QTableWidgetItem(
                f"Bs {a.sistema_total:.2f}"))

            dif      = a.diferencia_total
            dif_item = QTableWidgetItem(_texto_dif(dif))
            dif_item.setForeground(QColor(_color_dif(dif)))
            self.table.setItem(row, 5, dif_item)
            self.table.setItem(row, 6, QTableWidgetItem(
                str(a.total_transacciones)))

            total_sis += a.sistema_total
            total_dif += dif

        self.table.setSortingEnabled(True)
        self.resumen_lbl.setText(
            f"📋 {len(self._arqueos)} arqueo(s)  ·  "
            f"Total: Bs {total_sis:.2f}  ·  "
            f"Diferencia acumulada: {_texto_dif(round(total_dif, 2))}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# WIDGET PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

class ArqueoWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title  = QLabel("🏦 Arqueo de Caja")
        title.setStyleSheet("font-size:24px; font-weight:700; color:#1F2937;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        sub = QLabel("Gestión de apertura, cierre e historial de caja por cajero.")
        sub.setStyleSheet("color:#6B7280; font-size:13px; margin-top:-8px;")
        layout.addWidget(sub)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border:1px solid #E5E7EB; border-radius:10px;
                               background:white; }
            QTabBar::tab { padding:8px 20px; font-size:13px; font-weight:600;
                           color:#6B7280; border:none; margin-right:4px; }
            QTabBar::tab:selected { color:#FF6B35; border-bottom:2px solid #FF6B35; }
            QTabBar::tab:hover:!selected { color:#374151; }
        """)
        self.caja_tab = CajaActualTab()
        tabs.addTab(self.caja_tab,        "🟢  Caja Actual")
        tabs.addTab(HistorialArqueosTab(), "📋  Historial")
        layout.addWidget(tabs)