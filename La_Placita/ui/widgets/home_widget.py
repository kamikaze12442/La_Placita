"""
Home Widget - Dashboard
KPIs · Top 5 compactos · Gráfico toggle (Ventas por Hora / Días Pico)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy, QPushButton,
    QStackedWidget, QDateEdit, QToolTip, QApplication,
)
from PySide6.QtCore import Qt, QMargins, QDate, QRect, QTimer, QPoint
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QCursor
from PySide6.QtCharts import (
    QChart, QChartView,
    QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    QSplineSeries, QScatterSeries,
)
from datetime import datetime, timedelta, date
from database.connection import db


# ══════════════════════════════════════════════════════════════
#  Localización española
# ══════════════════════════════════════════════════════════════
_DIAS_ES = {
    "Monday": "Lunes",    "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes",
    "Saturday": "Sábado", "Sunday": "Domingo",
}
_MESES_ES = {
    "January": "Enero",   "February": "Febrero", "March": "Marzo",
    "April":   "Abril",   "May":      "Mayo",     "June":  "Junio",
    "July":    "Julio",   "August":   "Agosto",   "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre","December":  "Diciembre",
}
# Número de día SQLite (%w: 0=domingo … 6=sábado) → nombre español
_WDAY_ES = {
    0: "Domingo", 1: "Lunes",    2: "Martes", 3: "Miércoles",
    4: "Jueves",  5: "Viernes",  6: "Sábado",
}

def _fecha_es(d: date) -> str:
    return (
        f"{_DIAS_ES.get(d.strftime('%A'), d.strftime('%A'))} "
        f"{d.strftime('%d/%m/%Y')}"
    )

def _subtitulo_es() -> str:
    n = datetime.now()
    return (
        f"Resumen del día  ·  "
        f"{_DIAS_ES.get(n.strftime('%A'), n.strftime('%A'))} "
        f"{n.strftime('%d')} de "
        f"{_MESES_ES.get(n.strftime('%B'), n.strftime('%B'))}, "
        f"{n.strftime('%Y')}"
    )


# ══════════════════════════════════════════════════════════════
#  Paleta
# ══════════════════════════════════════════════════════════════
C = {
    "bg":           "#F3F4F6",
    "card":         "#FFFFFF",
    "border":       "#E5E7EB",
    "text_primary": "#111827",
    "text_muted":   "#6B7280",
    "text_light":   "#9CA3AF",

    "orange":       "#FF6B35",
    "orange_h":     "#E85D2A",
    "orange_p":     "#CC4F1F",
    "orange_bg":    "#FFF4EF",

    "blue":         "#3B82F6",
    "blue_h":       "#2563EB",
    "blue_p":       "#1D4ED8",
    "blue_bg":      "#EFF6FF",

    "green":        "#10B981",
    "green_h":      "#059669",
    "green_p":      "#047857",
    "green_bg":     "#ECFDF5",

    "amber":        "#F59E0B",
    "amber_h":      "#D97706",
    "amber_p":      "#B45309",
    "amber_bg":     "#FFFBEB",

    "purple":       "#8B5CF6",
    "purple_h":     "#7C3AED",
    "purple_p":     "#6D28D9",
    "purple_bg":    "#F5F3FF",
}

CARD_STYLE = "QFrame { background-color: white; border: none; border-radius: 14px; }"

# ── QCalendarWidget — estilo azul (igual a imagen de referencia) ──────────
CALENDAR_QSS = """
QCalendarWidget {
    background-color: white;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
}
QCalendarWidget #qt_calendar_navigationbar {
    background-color: #3B82F6;
    border-radius: 10px 10px 0 0;
    padding: 4px 6px;
    min-height: 34px;
}
QCalendarWidget QToolButton {
    background-color: transparent;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 8px;
    min-width: 26px;
    min-height: 0;
}
QCalendarWidget QToolButton:hover   { background-color: rgba(255,255,255,0.22); }
QCalendarWidget QToolButton:pressed { background-color: rgba(255,255,255,0.38); }
QCalendarWidget QToolButton#qt_calendar_prevmonth,
QCalendarWidget QToolButton#qt_calendar_nextmonth {
    color: #10B981;
    font-size: 16px;
    font-weight: 700;
}
QCalendarWidget QToolButton::menu-indicator { image: none; }
QCalendarWidget QSpinBox {
    background-color: transparent;
    color: white;
    border: none;
    font-size: 13px;
    font-weight: 700;
    selection-background-color: rgba(255,255,255,0.30);
    selection-color: white;
}
QCalendarWidget QSpinBox::up-button,
QCalendarWidget QSpinBox::down-button { width: 0; height: 0; }
QCalendarWidget QAbstractItemView {
    background-color: white;
    color: #111827;
    selection-background-color: #3B82F6;
    selection-color: white;
    alternate-background-color: white;
    gridline-color: transparent;
    font-size: 13px;
    outline: none;
}
QCalendarWidget QAbstractItemView:enabled  { color: #111827; }
QCalendarWidget QAbstractItemView:disabled { color: #D1D5DB; }
QCalendarWidget QHeaderView {
    background-color: #F9FAFB;
    border: none;
}
QCalendarWidget QHeaderView::section {
    background-color: #F9FAFB;
    color: #6B7280;
    font-size: 11px;
    font-weight: 600;
    border: none;
    padding: 4px 0;
}
"""


# ══════════════════════════════════════════════════════════════
#  _make_date_edit
# ══════════════════════════════════════════════════════════════
def _make_date_edit(default_offset: int = 0, focus_bg: str = "#EFF6FF") -> QDateEdit:
    de = QDateEdit()
    de.setCalendarPopup(True)
    de.setDate(QDate.currentDate().addDays(default_offset))
    de.setDisplayFormat("dd/MM/yyyy")
    de.setFixedHeight(32)
    de.setMinimumWidth(110)
    de.setStyleSheet(f"""
        QDateEdit {{
            background-color: {C['bg']};
            border: none;
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 12px;
            color: {C['text_primary']};
            min-height: 0;
        }}
        QDateEdit:focus {{ background-color: {focus_bg}; }}
        QDateEdit::drop-down {{
            subcontrol-origin:   padding;
            subcontrol-position: right center;
            width: 22px;
            border: none;
        }}
        QDateEdit::down-arrow {{
            image: none;
            border-left:  4px solid transparent;
            border-right: 4px solid transparent;
            border-top:   5px solid {C['text_muted']};
            margin-right: 8px;
        }}
    """)
    cal = de.calendarWidget()
    cal.setStyleSheet(CALENDAR_QSS)
    cal.setVerticalHeaderFormat(cal.VerticalHeaderFormat.NoVerticalHeader)
    return de


# ══════════════════════════════════════════════════════════════
#  _make_btn_icono
# ══════════════════════════════════════════════════════════════
def _make_btn_icono(
    texto:        str,
    color:        str,
    color_hover:  str,
    color_pressed:str,
    ancho:  int = 32,
    alto:   int = 30,
    font_size: int = 12,
    radius: int = 7,
    text_color: str = "white",
) -> tuple:
    contenedor = QWidget()
    contenedor.setFixedSize(ancho, alto)

    btn = QPushButton("", contenedor)
    btn.setFixedSize(ancho, alto)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            border: none; border-radius: {radius}px;
            min-height: 0; padding: 0;
        }}
        QPushButton:hover   {{ background-color: {color_hover}; }}
        QPushButton:pressed {{ background-color: {color_pressed}; }}
    """)

    lbl = QLabel(texto, contenedor)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setFixedSize(ancho, alto)
    lbl.setStyleSheet(
        f"background: transparent; border: none; "
        f"font-size: {font_size}px; font-weight: 600; color: {text_color};"
    )
    lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    return contenedor, btn


# ══════════════════════════════════════════════════════════════
#  Tooltip flotante persistente
#  Resuelve el problema de los 2 segundos usando un QLabel custom.
# ══════════════════════════════════════════════════════════════
class FloatTooltip(QLabel):
    """
    Tooltip personalizado que se posiciona junto al cursor y permanece
    visible durante `duration_ms` milisegundos sin importar el movimiento
    del mouse dentro de la serie.
    """
    _instance = None   # singleton reutilizable

    @classmethod
    def show_at_cursor(cls, html: str, duration_ms: int = 6000):
        if cls._instance is None:
            cls._instance = cls()
        t = cls._instance
        t.setText(html)
        t.adjustSize()
        pos = QCursor.pos() + QPoint(14, 14)
        # Evitar que salga fuera de la pantalla
        screen = QApplication.primaryScreen().availableGeometry()
        if pos.x() + t.width()  > screen.right():
            pos.setX(pos.x() - t.width()  - 28)
        if pos.y() + t.height() > screen.bottom():
            pos.setY(pos.y() - t.height() - 28)
        t.move(pos)
        t.show()
        t._timer.stop()
        t._timer.start(duration_ms)

    @classmethod
    def hide_tip(cls):
        if cls._instance:
            cls._instance._timer.stop()
            cls._instance.hide()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setStyleSheet("""
            QLabel {
                background-color: #1F2937;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
        """)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)


# ══════════════════════════════════════════════════════════════
#  KPI Card — estilo imagen de referencia
#  Icono pequeño arriba izquierda · Valor grande · Label pequeño
# ══════════════════════════════════════════════════════════════
class StatCard(QFrame):
    def __init__(self, icon, value, label, pct_text="", pct_up=True):
        """
        pct_text: string como "↑ 5.2%" o "" para no mostrarlo
        pct_up:   True=verde, False=rojo
        """
        super().__init__()
        # Borde sutil igual al de la imagen de referencia
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1.5px solid #E5E7EB;
                border-radius: 14px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(130)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)

        # Icono — caja gris claro, alineada a la izquierda
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(42, 42)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"background-color: {C['bg']}; color: {C['text_muted']}; "
            f"font-size: 20px; border-radius: 10px; border: none;"
        )
        root.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignLeft)

        # Valor + porcentaje en la misma fila
        val_row = QHBoxLayout()
        val_row.setSpacing(10)
        val_row.setContentsMargins(0, 0, 0, 0)

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(
            f"font-size: 30px; font-weight: 700; "
            f"color: {C['text_primary']}; border: none;"
        )
        val_row.addWidget(val_lbl)

        if pct_text:
            pct_color = C["green"] if pct_up else "#EF4444"
            pct_lbl = QLabel(pct_text)
            pct_lbl.setStyleSheet(
                f"font-size: 12px; font-weight: 600; color: {pct_color}; "
                f"border: none; background: transparent;"
            )
            pct_lbl.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
            )
            val_row.addWidget(pct_lbl)

        val_row.addStretch()
        root.addLayout(val_row)

        # Label descriptivo
        lbl_lbl = QLabel(label)
        lbl_lbl.setStyleSheet(
            f"font-size: 13px; color: {C['text_muted']}; "
            f"font-weight: 500; border: none;"
        )
        root.addWidget(lbl_lbl)


# ══════════════════════════════════════════════════════════════
#  Top-5 compact card
# ══════════════════════════════════════════════════════════════
class TopCompactCard(QFrame):
    _RANK_STYLES = [
        ("#FF6B35", "#FFF4EF"), ("#3B82F6", "#EFF6FF"),
        ("#10B981", "#ECFDF5"), ("#F59E0B", "#FFFBEB"),
        ("#8B5CF6", "#F5F3FF"),
    ]
    _RANK_DOT = ["#FFD700", "#C0C0C0", "#CD7F32", "#D1D5DB", "#D1D5DB"]

    def __init__(self, title, items):
        super().__init__()
        self.setStyleSheet(CARD_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(6)

        hdr = QLabel(title)
        hdr.setStyleSheet(
            f"font-size: 13px; font-weight: 700; "
            f"color: {C['text_primary']}; border: none;"
        )
        root.addWidget(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['border']}; border: none;")
        root.addWidget(sep)

        if not items:
            e = QLabel("Sin datos disponibles")
            e.setStyleSheet(f"color: {C['text_light']}; font-size: 12px; border: none;")
            e.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(e)
        else:
            for i, item in enumerate(items[:5]):
                color, bg = self._RANK_STYLES[i]
                rw = QWidget()
                rw.setStyleSheet(f"QWidget {{ background: {bg}; border-radius: 8px; }}")
                rl = QHBoxLayout(rw)
                rl.setContentsMargins(8, 5, 8, 5)
                rl.setSpacing(8)

                dot = QLabel(str(i + 1))
                dot.setFixedSize(20, 20)
                dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
                dot.setStyleSheet(
                    f"background-color: {self._RANK_DOT[i]}; color: white; "
                    f"font-size: 10px; font-weight: 700; border-radius: 10px;"
                )
                rl.addWidget(dot)

                name = QLabel(item['nombre'])
                name.setStyleSheet(
                    f"font-size: 12px; font-weight: 600; color: {C['text_primary']}; "
                    f"background: transparent; border: none;"
                )
                name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                rl.addWidget(name)

                qty = QLabel(f"{item['cantidad_vendida']} uds")
                qty.setStyleSheet(
                    f"font-size: 11px; font-weight: 700; color: {color}; "
                    f"background: transparent; border: none;"
                )
                rl.addWidget(qty)
                root.addWidget(rw)


# ══════════════════════════════════════════════════════════════
#  Días Pico Promedio card
# ══════════════════════════════════════════════════════════════
class PeakDaysCard(QFrame):
    """Top 3 días de la semana con mayor venta promedio en el rango."""

    _MEDAL = ["#FFD700", "#C0C0C0", "#CD7F32"]

    def __init__(self, peak_days: list):
        """
        peak_days: list of dicts {dia_nombre, promedio, apariciones}
                   ordenados desc por promedio, máx 3 items.
        """
        super().__init__()
        self.setStyleSheet(CARD_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(6)

        hdr = QLabel("Días Pico Promedio")
        hdr.setStyleSheet(
            f"font-size: 13px; font-weight: 700; "
            f"color: {C['text_primary']}; border: none;"
        )
        root.addWidget(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['border']}; border: none;")
        root.addWidget(sep)

        if not peak_days:
            e = QLabel("Sin datos suficientes en el rango")
            e.setStyleSheet(f"color: {C['text_light']}; font-size: 12px; border: none;")
            e.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(e)
        else:
            for i, row in enumerate(peak_days[:3]):
                rw = QWidget()
                rw.setStyleSheet(
                    f"QWidget {{ background: {C['purple_bg']}; border-radius: 8px; }}"
                )
                rl = QHBoxLayout(rw)
                rl.setContentsMargins(8, 6, 8, 6)
                rl.setSpacing(8)

                dot = QLabel(str(i + 1))
                dot.setFixedSize(20, 20)
                dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
                dot.setStyleSheet(
                    f"background-color: {self._MEDAL[i]}; color: white; "
                    f"font-size: 10px; font-weight: 700; border-radius: 10px;"
                )
                rl.addWidget(dot)

                name = QLabel(row['dia_nombre'])
                name.setStyleSheet(
                    f"font-size: 12px; font-weight: 600; color: {C['text_primary']}; "
                    f"background: transparent; border: none;"
                )
                name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                rl.addWidget(name)

                venta_lbl = QLabel(f"Bs {row['promedio']:.0f}")
                venta_lbl.setStyleSheet(
                    f"font-size: 11px; font-weight: 700; color: {C['purple']}; "
                    f"background: transparent; border: none;"
                )
                rl.addWidget(venta_lbl)

                ap_lbl = QLabel(f"({row['apariciones']} sem.)")
                ap_lbl.setStyleSheet(
                    f"font-size: 10px; color: {C['text_light']}; "
                    f"background: transparent; border: none;"
                )
                rl.addWidget(ap_lbl)

                root.addWidget(rw)


# ══════════════════════════════════════════════════════════════
#  Summary strip
# ══════════════════════════════════════════════════════════════
class SummaryStrip(QFrame):
    def __init__(self, items: list, accent: str, bg: str):
        super().__init__()
        # Height auto — 50px for ≤4 cols, 50px still fine for 7 because labels shrink
        self.setFixedHeight(50)
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border: none; border-radius: 10px; }}"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(0)

        # Adaptive spacing: tighter when many columns
        n     = len(items)
        gap   = 14 if n > 4 else 20
        f_lbl = 9  if n > 4 else 10
        f_val = 12 if n > 4 else 13

        for i, (lbl_txt, val_txt) in enumerate(items):
            if i > 0:
                div = QFrame()
                div.setFixedSize(1, 26)
                div.setStyleSheet(f"background: {accent}50; border: none;")
                row.addWidget(div)
                row.addSpacing(gap)

            col = QVBoxLayout()
            col.setSpacing(1)
            col.setContentsMargins(0, 0, 0, 0)

            l = QLabel(lbl_txt)
            l.setStyleSheet(
                f"font-size: {f_lbl}px; color: {accent}; font-weight: 600; "
                f"background: transparent; border: none;"
            )
            col.addWidget(l)

            v = QLabel(val_txt)
            v.setStyleSheet(
                f"font-size: {f_val}px; font-weight: 700; "
                f"color: {C['text_primary']}; background: transparent; border: none;"
            )
            col.addWidget(v)

            row.addLayout(col)
            row.addSpacing(gap)

        row.addStretch()


# ══════════════════════════════════════════════════════════════
#  Chart card — toggle Por Hora / Días Pico
# ══════════════════════════════════════════════════════════════
class ChartCard(QFrame):
    VIEW_HOURS = 0
    VIEW_PEAK  = 1

    def __init__(self, db_ref):
        super().__init__()
        self.db = db_ref
        self.setStyleSheet(CARD_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._current_view  = self.VIEW_HOURS
        self._selected_date = date.today()
        self._quick_active  = "hoy"
        self._daily_list:   list = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ── Toggle pill ───────────────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setSpacing(0)

        pill = QFrame()
        pill.setStyleSheet(
            f"QFrame {{ background: {C['bg']}; border: none; border-radius: 10px; }}"
        )
        pill.setFixedHeight(36)
        pill_l = QHBoxLayout(pill)
        pill_l.setContentsMargins(4, 4, 4, 4)
        pill_l.setSpacing(2)

        self._c_hours, self._btn_hours = _make_btn_icono(
            "Por Hora", C["orange"], C["orange_h"], C["orange_p"],
            ancho=110, alto=28, font_size=12, radius=7,
        )
        self._c_peak, self._btn_peak = _make_btn_icono(
            "Días Pico", C["bg"], C["purple_bg"], C["purple"],
            ancho=110, alto=28, font_size=12, radius=7,
            text_color=C["text_muted"],
        )
        self._lbl_hours = self._c_hours.findChild(QLabel)
        self._lbl_peak  = self._c_peak.findChild(QLabel)

        self._btn_hours.clicked.connect(lambda: self._switch_view(self.VIEW_HOURS))
        self._btn_peak.clicked.connect(lambda:  self._switch_view(self.VIEW_PEAK))
        pill_l.addWidget(self._c_hours)
        pill_l.addWidget(self._c_peak)

        top_bar.addWidget(pill)
        top_bar.addStretch()

        self._peak_badge = QLabel()
        self._peak_badge.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {C['orange']}; "
            f"background: {C['orange_bg']}; border: none; "
            f"border-radius: 8px; padding: 4px 12px;"
        )
        self._peak_badge.hide()
        top_bar.addWidget(self._peak_badge)
        root.addLayout(top_bar)

        # ── Controls stack ────────────────────────────────────
        self._controls_stack = QStackedWidget()
        self._controls_stack.setFixedHeight(36)
        self._controls_stack.addWidget(self._build_hour_controls())
        self._controls_stack.addWidget(self._build_peak_controls())
        root.addWidget(self._controls_stack)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['border']}; border: none;")
        root.addWidget(sep)

        # Área de contenido del gráfico (gráfico + card dias pico prom)
        self._content_row = QHBoxLayout()
        self._content_row.setSpacing(14)
        root.addLayout(self._content_row)

        self._strip_container = QVBoxLayout()
        root.addLayout(self._strip_container)

        self._refresh_toggle_styles()
        self._reload_chart()

    # ─── Controls ─────────────────────────────────────────────

    def _build_hour_controls(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._c_hoy,   self._btn_hoy,   self._lbl_hoy   = self._quick_btn("Hoy",          True,  60)
        self._c_ayer,  self._btn_ayer,  self._lbl_ayer  = self._quick_btn("Ayer",         False, 60)
        self._c_fecha, self._btn_fecha, self._lbl_fecha = self._quick_btn("Elegir fecha", False, 90)

        self._btn_hoy.clicked.connect(lambda:   self._set_quick("hoy"))
        self._btn_ayer.clicked.connect(lambda:  self._set_quick("ayer"))
        self._btn_fecha.clicked.connect(lambda: self._set_quick("custom"))

        self._date_picker = _make_date_edit(0, C["orange_bg"])
        self._date_picker.hide()
        self._date_picker.dateChanged.connect(self._on_custom_date_changed)

        for w_ in (self._c_hoy, self._c_ayer, self._c_fecha):
            row.addWidget(w_)
        row.addWidget(self._date_picker)
        row.addStretch()
        return w

    def _build_peak_controls(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        def sep_lbl(t):
            l = QLabel(t)
            l.setStyleSheet(
                f"font-size: 12px; color: {C['text_muted']}; font-weight: 600; border: none;"
            )
            return l

        self._range_start = _make_date_edit(-29, C["purple_bg"])
        self._range_end   = _make_date_edit(0,   C["purple_bg"])

        c_apply, self._btn_apply = _make_btn_icono(
            "Aplicar", C["purple"], C["purple_h"], C["purple_p"],
            ancho=80, alto=30, font_size=12, radius=7,
        )
        self._btn_apply.clicked.connect(self._reload_chart)

        row.addWidget(sep_lbl("Desde:"))
        row.addWidget(self._range_start)
        row.addWidget(sep_lbl("Hasta:"))
        row.addWidget(self._range_end)
        row.addWidget(c_apply)
        row.addStretch()
        return w

    def _quick_btn(self, texto, active, ancho) -> tuple:
        color = C["orange"] if active else C["bg"]
        tc    = "white" if active else C["text_muted"]
        c, btn = _make_btn_icono(
            texto, color,
            C["orange_h"] if active else C["orange_bg"],
            C["orange_p"], ancho=ancho, alto=30, font_size=12, radius=7,
            text_color=tc,
        )
        lbl = c.findChild(QLabel)
        return c, btn, lbl

    # ─── State ────────────────────────────────────────────────

    def _switch_view(self, view: int):
        self._current_view = view
        self._controls_stack.setCurrentIndex(view)
        self._refresh_toggle_styles()
        self._reload_chart()

    def _set_quick(self, mode: str):
        self._quick_active = mode
        if mode == "hoy":
            self._selected_date = date.today()
            self._date_picker.hide()
        elif mode == "ayer":
            self._selected_date = date.today() - timedelta(days=1)
            self._date_picker.hide()
        else:
            self._date_picker.show()
            qd = self._date_picker.date()
            self._selected_date = date(qd.year(), qd.month(), qd.day())
        self._refresh_quick_styles()
        self._reload_chart()

    def _on_custom_date_changed(self, qdate: QDate):
        if self._quick_active == "custom":
            self._selected_date = date(qdate.year(), qdate.month(), qdate.day())
            self._reload_chart()

    def _refresh_toggle_styles(self):
        is_h = self._current_view == self.VIEW_HOURS
        for btn, lbl_w, active, ac, ah, ap in (
            (self._btn_hours, self._lbl_hours, is_h,
             C["orange"], C["orange_h"], C["orange_p"]),
            (self._btn_peak,  self._lbl_peak,  not is_h,
             C["purple"], C["purple_h"], C["purple_p"]),
        ):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ac if active else C['bg']};
                    border: none; border-radius: 7px; min-height: 0; padding: 0;
                }}
                QPushButton:hover   {{ background-color: {ah if active else C['bg']}; }}
                QPushButton:pressed {{ background-color: {ap}; }}
            """)
            if lbl_w:
                lbl_w.setStyleSheet(
                    f"background: transparent; border: none; font-size: 12px; "
                    f"font-weight: {'700' if active else '600'}; "
                    f"color: {'white' if active else C['text_muted']};"
                )

    def _refresh_quick_styles(self):
        for mode, btn, lbl_w in (
            ("hoy",    self._btn_hoy,   self._lbl_hoy),
            ("ayer",   self._btn_ayer,  self._lbl_ayer),
            ("custom", self._btn_fecha, self._lbl_fecha),
        ):
            active = self._quick_active == mode
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C['orange'] if active else C['bg']};
                    border: none; border-radius: 7px; min-height: 0; padding: 0;
                }}
                QPushButton:hover   {{ background-color: {C['orange_h'] if active else C['orange_bg']}; }}
                QPushButton:pressed {{ background-color: {C['orange_p']}; }}
            """)
            if lbl_w:
                lbl_w.setStyleSheet(
                    f"background: transparent; border: none; font-size: 12px; "
                    f"font-weight: {'700' if active else '600'}; "
                    f"color: {'white' if active else C['text_muted']};"
                )

    # ─── Reload ───────────────────────────────────────────────

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _reload_chart(self):
        self._clear_layout(self._content_row)
        self._clear_layout(self._strip_container)
        if self._current_view == self.VIEW_HOURS:
            self._render_hourly()
        else:
            self._render_peak()

    # ─── Hourly ───────────────────────────────────────────────

    def _render_hourly(self):
        target    = str(self._selected_date)
        bs, ords  = self._fetch_hourly(target)
        active    = [h for h, v in bs.items() if v > 0]
        total_bs  = sum(bs.values())
        total_ord = sum(ords.values())
        peak_h    = max(bs, key=bs.get) if active else -1

        if peak_h >= 0 and bs[peak_h] > 0:
            self._peak_badge.setText(
                f"Hora pico  {peak_h:02d}:00  —  Bs {bs[peak_h]:.0f}"
            )
            self._peak_badge.show()
        else:
            self._peak_badge.hide()

        # El gráfico ocupa todo el ancho en modo horario
        chart_w = QWidget()
        chart_l = QVBoxLayout(chart_w)
        chart_l.setContentsMargins(0, 0, 0, 0)
        chart_l.addWidget(self._build_hourly_chart(bs, ords, active))
        self._content_row.addWidget(chart_w)

        label_date = (
            "Hoy"  if self._selected_date == date.today()
            else "Ayer" if self._selected_date == date.today() - timedelta(days=1)
            else self._selected_date.strftime("%d/%m/%Y")
        )
        avg = total_bs / max(len(active), 1)
        self._strip_container.addWidget(SummaryStrip([
            (f"Total ({label_date})", f"Bs {total_bs:.2f}"),
            ("Órdenes",               str(total_ord)),
            ("Hora pico",             f"{peak_h:02d}:00 hs" if peak_h >= 0 else "—"),
            ("Promedio / hora",       f"Bs {avg:.2f}"),
        ], C["orange"], C["orange_bg"]))

    # ─── Peak ─────────────────────────────────────────────────

    def _render_peak(self):
        self._peak_badge.hide()

        qs = self._range_start.date()
        qe = self._range_end.date()
        start = date(qs.year(), qs.month(), qs.day())
        end   = date(qe.year(), qe.month(), qe.day())
        if start > end:
            start, end = end, start

        daily = self._fetch_daily_range(str(start), str(end))
        delta = (end - start).days + 1
        self._daily_list = [
            (start + timedelta(days=i),
             daily.get(start + timedelta(days=i), {'total': 0.0, 'orders': 0}))
            for i in range(delta)
        ]

        # Gráfico ocupa todo el ancho
        chart_container = QWidget()
        cl = QVBoxLayout(chart_container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(self._build_peak_chart(self._daily_list))
        self._content_row.addWidget(chart_container)

        total_bs    = sum(v['total']  for _, v in self._daily_list)
        total_ord   = sum(v['orders'] for _, v in self._daily_list)
        active_days = len([v for _, v in self._daily_list if v['total'] > 0])
        peak_day    = (
            max(self._daily_list, key=lambda x: x[1]['total'])[0]
            if self._daily_list else None
        )
        avg_day = total_bs / max(active_days, 1)

        # Días pico promedio — una sola columna con los nombres separados por coma
        peak_avg   = self._fetch_peak_days_avg(str(start), str(end))
        dias_names = ", ".join(r['dia_nombre'] for r in peak_avg) if peak_avg else "—"

        strip_items = [
            ("Total período",   f"Bs {total_bs:.2f}"),
            ("Órdenes totales", str(total_ord)),
            ("Día pico",        _fecha_es(peak_day) if peak_day else "—"),
            ("Promedio / día",  f"Bs {avg_day:.2f}"),
            ("Días con más clientes", dias_names),
        ]

        self._strip_container.addWidget(
            SummaryStrip(strip_items, C["purple"], C["purple_bg"])
        )

    # ─── Chart builders ───────────────────────────────────────

    def _build_hourly_chart(self, bs, ords, active) -> QChartView:
        lo = max(0,  min(active) - 1) if active else 7
        hi = min(23, max(active) + 1) if active else 21
        display = list(range(lo, hi + 1))
        labels  = [f"{h:02d}:00" for h in display]

        bset = QBarSet("Ventas (Bs)")
        bset.setColor(QColor(C["orange"]))
        bset.setBorderColor(QColor(C["orange"]))
        for h in display:
            bset.append(bs.get(h, 0.0))

        bar_s = QBarSeries()
        bar_s.append(bset)
        bar_s.setBarWidth(0.52)

        spl = self._spline(C["blue"])
        sct = self._scatter(C["blue"])
        spl.setName("Órdenes")
        for idx, h in enumerate(display):
            v = float(ords.get(h, 0))
            spl.append(idx, v)
            sct.append(idx, v)

        chart = self._base_chart()
        for s in (bar_s, spl, sct):
            chart.addSeries(s)
        self._legend(chart, sct)

        ax_x  = self._cat_axis(labels)
        ax_y1 = self._bs_axis(max((bs.get(h, 0) for h in display), default=0),   "Monto (Bs)")
        ax_y2 = self._ord_axis(max((ords.get(h, 0) for h in display), default=0), "Órdenes")

        chart.addAxis(ax_x,  Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(ax_y1, Qt.AlignmentFlag.AlignLeft)
        chart.addAxis(ax_y2, Qt.AlignmentFlag.AlignRight)

        bar_s.attachAxis(ax_x); bar_s.attachAxis(ax_y1)
        spl.attachAxis(ax_x);   spl.attachAxis(ax_y2)
        sct.attachAxis(ax_x);   sct.attachAxis(ax_y2)

        return self._view(chart, len(display))

    def _build_peak_chart(self, daily_list) -> QChartView:
        labels = [d.strftime("%d/%m") for d, _ in daily_list]
        totals = [v['total']  for _, v in daily_list]
        orders = [v['orders'] for _, v in daily_list]
        n = len(daily_list)

        bset = QBarSet("Ventas (Bs)")
        bset.setColor(QColor(C["purple"]))
        bset.setBorderColor(QColor(C["purple"]))
        for v in totals:
            bset.append(v)

        bar_s = QBarSeries()
        bar_s.append(bset)
        bar_s.setBarWidth(min(0.7, max(0.3, 12 / max(n, 1))))

        spl = self._spline(C["blue"])
        sct = self._scatter(C["blue"])
        spl.setName("Órdenes")
        for idx, v in enumerate(orders):
            spl.append(idx, float(v))
            sct.append(idx, float(v))

        # Tooltip persistente con FloatTooltip
        def on_hover(status: bool, idx: int, _bset):
            if status and 0 <= idx < len(daily_list):
                d, data = daily_list[idx]
                FloatTooltip.show_at_cursor(
                    f"<b>{_fecha_es(d)}</b><br>"
                    f"Ventas:&nbsp;&nbsp;&nbsp;Bs {data['total']:.2f}<br>"
                    f"Órdenes:&nbsp;{data['orders']}",
                    duration_ms=6000,
                )
            else:
                FloatTooltip.hide_tip()

        bar_s.hovered.connect(on_hover)

        chart = self._base_chart()
        for s in (bar_s, spl, sct):
            chart.addSeries(s)
        self._legend(chart, sct)

        font_x = QFont("Segoe UI", 9 if n <= 20 else 7)
        ax_x  = self._cat_axis(labels, font=font_x, angle=-45 if n > 14 else 0)
        ax_y1 = self._bs_axis(max(totals, default=0),  "Monto (Bs)")
        ax_y2 = self._ord_axis(max(orders, default=0), "Órdenes")

        chart.addAxis(ax_x,  Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(ax_y1, Qt.AlignmentFlag.AlignLeft)
        chart.addAxis(ax_y2, Qt.AlignmentFlag.AlignRight)

        bar_s.attachAxis(ax_x); bar_s.attachAxis(ax_y1)
        spl.attachAxis(ax_x);   spl.attachAxis(ax_y2)
        sct.attachAxis(ax_x);   sct.attachAxis(ax_y2)

        return self._view(chart, n)

    # ─── Chart helpers ────────────────────────────────────────

    def _base_chart(self):
        c = QChart()
        c.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        c.setAnimationDuration(500)
        c.setBackgroundVisible(False)
        c.setMargins(QMargins(4, 4, 4, 4))
        return c

    def _legend(self, chart, scatter):
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignTop)
        chart.legend().setFont(QFont("Segoe UI", 10))
        for m in chart.legend().markers(scatter):
            m.setVisible(False)

    def _spline(self, color):
        s = QSplineSeries()
        pen = QPen(QColor(color))
        pen.setWidth(2)
        s.setPen(pen)
        return s

    def _scatter(self, color):
        sc = QScatterSeries()
        sc.setMarkerSize(9)
        sc.setColor(QColor(color))
        sc.setBorderColor(QColor("#FFFFFF"))
        return sc

    def _cat_axis(self, labels, font=None, angle=0):
        ax = QBarCategoryAxis()
        ax.append(labels)
        ax.setLabelsFont(font or QFont("Segoe UI", 9))
        ax.setLabelsAngle(angle)
        ax.setGridLineVisible(False)
        return ax

    def _bs_axis(self, max_val, title):
        ax = QValueAxis()
        ax.setMin(0)
        ax.setMax(max(max_val * 1.25, 10))
        ax.setLabelFormat("Bs %.0f")
        ax.setLabelsFont(QFont("Segoe UI", 9))
        ax.setTitleText(title)
        ax.setTitleFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        ax.setTickCount(6)
        ax.setGridLineColor(QColor("#ECECEC"))
        return ax

    def _ord_axis(self, max_val, title):
        ax = QValueAxis()
        ax.setMin(0)
        ax.setMax(max(int(max_val * 1.5), 5))
        ax.setLabelFormat("%d")
        ax.setLabelsFont(QFont("Segoe UI", 9))
        ax.setTitleText(title)
        ax.setTitleFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        ax.setTickCount(6)
        ax.setGridLineVisible(False)
        return ax

    def _view(self, chart, n_slots):
        v = QChartView(chart)
        v.setRenderHint(QPainter.RenderHint.Antialiasing)
        v.setMinimumHeight(max(300, n_slots * 16))
        v.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return v

    # ─── DB helpers ───────────────────────────────────────────

    def _fetch_hourly(self, day):
        rows = self.db.fetch_all(
            """SELECT CAST(strftime('%H', fecha_venta) AS INTEGER) AS hora,
                      COALESCE(SUM(total), 0) AS total, COUNT(*) AS cnt
               FROM ventas
               WHERE DATE(fecha_venta)=? AND estado='completada'
               GROUP BY hora ORDER BY hora""",
            (day,),
        )
        bs = {h: 0.0 for h in range(24)}
        od = {h: 0   for h in range(24)}
        for r in rows:
            h = int(r['hora'])
            bs[h] = float(r['total'])
            od[h] = int(r['cnt'])
        return bs, od

    def _fetch_daily_range(self, start, end):
        rows = self.db.fetch_all(
            """SELECT DATE(fecha_venta) AS dia,
                      COALESCE(SUM(total), 0) AS total, COUNT(*) AS cnt
               FROM ventas
               WHERE DATE(fecha_venta) BETWEEN ? AND ?
                 AND estado='completada'
               GROUP BY dia ORDER BY dia""",
            (start, end),
        )
        result = {}
        for r in rows:
            d = datetime.strptime(r['dia'], "%Y-%m-%d").date()
            result[d] = {'total': float(r['total']), 'orders': int(r['cnt'])}
        return result

    def _fetch_peak_days_avg(self, start: str, end: str) -> list:
        """
        Agrupa ventas por día de la semana en el rango dado.
        Devuelve top 3 desc por promedio diario:
          [{'dia_nombre': str, 'promedio': float, 'apariciones': int}, ...]
        """
        rows = self.db.fetch_all(
            """SELECT
                   CAST(strftime('%w', fecha_venta) AS INTEGER) AS wday,
                   COUNT(DISTINCT DATE(fecha_venta))            AS apariciones,
                   COALESCE(SUM(total), 0)                      AS total_acum
               FROM ventas
               WHERE DATE(fecha_venta) BETWEEN ? AND ?
                 AND estado='completada'
               GROUP BY wday
               ORDER BY (total_acum * 1.0 / COUNT(DISTINCT DATE(fecha_venta))) DESC
               LIMIT 3""",
            (start, end),
        )
        result = []
        for r in rows:
            wday  = int(r['wday'])
            apars = int(r['apariciones'])
            total = float(r['total_acum'])
            result.append({
                'dia_nombre':  _WDAY_ES.get(wday, str(wday)),
                'promedio':    total / apars if apars else 0.0,
                'apariciones': apars,
            })
        return result


# ══════════════════════════════════════════════════════════════
#  HomeWidget
# ══════════════════════════════════════════════════════════════
class HomeWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {C['bg']};")
        self.init_ui()

    def init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        main = QVBoxLayout(content)
        main.setContentsMargins(32, 24, 32, 28)
        main.setSpacing(18)

        # Header
        title = QLabel("Dashboard")
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {C['text_primary']}; border: none;"
        )
        main.addWidget(title)

        subtitle = QLabel(_subtitulo_es())
        subtitle.setStyleSheet(
            f"font-size: 13px; color: {C['text_muted']}; border: none; margin-top: -4px;"
        )
        main.addWidget(subtitle)

        stats = self._get_kpi_stats()

        # ── KPI row (estilo imagen referencia) ────────────────
        kpi = QHBoxLayout()
        kpi.setSpacing(14)

        pct_text = ""
        pct_up   = True
        ayer_total = stats.get('ventas_ayer', 0.0)
        hoy_total  = stats['ventas_hoy']
        if ayer_total > 0:
            diff = ((hoy_total - ayer_total) / ayer_total) * 100
            arrow = "↑" if diff >= 0 else "↓"
            pct_text = f"{arrow} {abs(diff):.1f}%"
            pct_up   = diff >= 0
        elif hoy_total > 0:
            pct_text = "↑ nuevo"
            pct_up   = True

        kpi.addWidget(StatCard("💰", f"Bs {hoy_total:.2f}",          "Ventas de Hoy",       pct_text, pct_up))
        kpi.addWidget(StatCard("🎫", str(stats['ordenes']),            "Órdenes Completadas"))
        kpi.addWidget(StatCard("🍽️", stats['plato_dia'] or "—",       "Plato del Día"))
        kpi.addWidget(StatCard("📊", f"Bs {stats['ticket_prom']:.2f}", "Ticket Promedio"))
        main.addLayout(kpi)

        # ── Top-5 row ─────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(14)
        top.addWidget(TopCompactCard("Top 5 Platos",  stats['top_platos']))
        top.addWidget(TopCompactCard("Top 5 Bebidas", stats['top_bebidas']))
        top.addWidget(TopCompactCard("Top 5 Extras",  stats['top_extras']))
        main.addLayout(top)

        main.addWidget(ChartCard(db))

        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    # ─── Data ─────────────────────────────────────────────────

    def _get_kpi_stats(self) -> dict:
        today     = str(datetime.now().date())
        yesterday = str(datetime.now().date() - timedelta(days=1))

        row = db.fetch_one(
            """SELECT COALESCE(SUM(total),0) AS total, COUNT(*) AS cnt
               FROM ventas
               WHERE DATE(fecha_venta)=? AND estado='completada'""",
            (today,),
        )
        ventas_hoy  = float(row['total']) if row else 0.0
        ordenes     = int(row['cnt'])     if row else 0
        ticket_prom = ventas_hoy / ordenes if ordenes else 0.0

        row_ay = db.fetch_one(
            """SELECT COALESCE(SUM(total),0) AS total
               FROM ventas
               WHERE DATE(fecha_venta)=? AND estado='completada'""",
            (yesterday,),
        )
        ventas_ayer = float(row_ay['total']) if row_ay else 0.0

        r = db.fetch_one(
            """SELECT p.nombre
               FROM detalle_ventas dv
               JOIN productos  p ON dv.producto_id=p.id
               JOIN ventas     v ON dv.venta_id=v.id
               JOIN categorias c ON p.categoria_id=c.id
               WHERE DATE(v.fecha_venta)=? AND c.nombre='Comidas'
               GROUP BY p.nombre
               ORDER BY SUM(dv.cantidad) DESC LIMIT 1""",
            (today,),
        )
        return {
            'ventas_hoy':   ventas_hoy,
            'ventas_ayer':  ventas_ayer,
            'ordenes':      ordenes,
            'ticket_prom':  ticket_prom,
            'plato_dia':    r['nombre'] if r else None,
            'top_platos':   self._top_category('Comidas'),
            'top_bebidas':  self._top_category('Bebidas'),
            'top_extras':   self._top_category('Extras'),
        }

    def _top_category(self, category: str, limit: int = 5) -> list:
        rows = db.fetch_all(
            """SELECT p.nombre, SUM(dv.cantidad) AS cantidad_vendida,
                      SUM(dv.subtotal) AS ingresos
               FROM detalle_ventas dv
               JOIN productos  p ON dv.producto_id=p.id
               JOIN categorias c ON p.categoria_id=c.id
               JOIN ventas     v ON dv.venta_id=v.id
               WHERE c.nombre=? AND v.estado='completada'
               GROUP BY p.id, p.nombre
               ORDER BY cantidad_vendida DESC LIMIT ?""",
            (category, limit),
        )
        return [dict(r) for r in rows]