"""
Sección de Impresora para la pestaña de Configuración
Permite probar la impresora y configurar datos del negocio
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QFormLayout, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal


# ── Worker para imprimir en hilo separado (no bloquea la UI) ─────────────────

class PrintWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, mode="test", sale=None):
        super().__init__()
        self.mode = mode
        self.sale = sale

    def run(self):
        try:
            from utils.printer import imprimir_recibo, imprimir_prueba
            if self.mode == "test":
                ok, msg = imprimir_prueba()
            else:
                ok, msg = imprimir_recibo(self.sale)
            self.finished.emit(ok, msg)
        except Exception as e:
            self.finished.emit(False, str(e))


# ── Widget de configuración de impresora ─────────────────────────────────────

class PrinterSettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # ── Encabezado ────────────────────────────────────────────────
        title = QLabel("🖨️ Configuración de Impresora")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1F2937;")
        layout.addWidget(title)

        sub = QLabel("Impresora térmica 58mm conectada por USB")
        sub.setStyleSheet("color: #6B7280; font-size: 13px;")
        layout.addWidget(sub)

        # ── Estado de conexión ────────────────────────────────────────
        status_frame = QFrame()
        status_frame.setStyleSheet(
            "QFrame{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;padding:14px;}"
        )
        status_layout = QHBoxLayout(status_frame)

        self._status_lbl = QLabel("⚪  Estado desconocido — haz una prueba de impresión")
        self._status_lbl.setStyleSheet("color: #6B7280; font-size: 13px;")
        status_layout.addWidget(self._status_lbl)
        status_layout.addStretch()

        test_btn = QPushButton("🖨️  Imprimir página de prueba")
        test_btn.setStyleSheet("""
            QPushButton{background:#3B82F6;color:white;padding:10px 20px;
                        border-radius:8px;font-weight:600;}
            QPushButton:hover{background:#2563EB;}
            QPushButton:disabled{background:#D1D5DB;color:#9CA3AF;}
        """)
        test_btn.clicked.connect(self._print_test)
        self._test_btn = test_btn
        status_layout.addWidget(test_btn)

        layout.addWidget(status_frame)

        # ── Datos del negocio para el recibo ──────────────────────────
        biz_group = QGroupBox("Datos que aparecen en el recibo")
        biz_group.setStyleSheet("""
            QGroupBox{
                font-weight: 600; color: #374151; font-size: 13px;
                border: 1px solid #E5E7EB; border-radius: 10px;
                margin-top: 10px; padding-top: 10px;
            }
            QGroupBox::title{subcontrol-origin: margin; left: 14px; padding: 0 6px;}
        """)
        biz_layout = QFormLayout(biz_group)
        biz_layout.setSpacing(12)

        self._nombre_input = QLineEdit("Cafetería La Placita")
        self._subtitulo_input = QLineEdit("Sucursal Santa Fe")
        self._pie_input = QLineEdit("¡Gracias por su visita!")
        self._telefono_input = QLineEdit("")
        self._telefono_input.setPlaceholderText("Ej: +591 7XXXXXXX")

        biz_layout.addRow("Nombre del negocio:", self._nombre_input)
        biz_layout.addRow("Subtítulo / Sucursal:", self._subtitulo_input)
        biz_layout.addRow("Teléfono (opcional):", self._telefono_input)
        biz_layout.addRow("Mensaje de despedida:", self._pie_input)

        layout.addWidget(biz_group)

        # ── Info impresora detectada ───────────────────────────────────
        detected_frame = QFrame()
        detected_frame.setStyleSheet(
            "QFrame{background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;padding:10px;}"
        )
        dl = QVBoxLayout(detected_frame)
        dl.addWidget(QLabel("🖨️  <b>Impresora configurada:</b>"))
        name_lbl = QLabel("SATSAT15TUSDBC6  (SAT 15TUS USB 58mm)")
        name_lbl.setStyleSheet("color:#065F46; font-size:13px; font-weight:600;")
        dl.addWidget(name_lbl)
        layout.addWidget(detected_frame)

        # ── Botón guardar ─────────────────────────────────────────────
        save_btn = QPushButton("💾  Guardar configuración")
        save_btn.setStyleSheet("""
            QPushButton{background:#10B981;color:white;padding:12px 28px;
                        border-radius:8px;font-weight:700;font-size:14px;}
            QPushButton:hover{background:#059669;}
        """)
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # ── Info de ayuda ─────────────────────────────────────────────
        help_frame = QFrame()
        help_frame.setStyleSheet(
            "QFrame{background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:12px;}"
        )
        hl = QVBoxLayout(help_frame)
        hl.setSpacing(4)

        QLabel_title = QLabel("ℹ️  Requisitos de la impresora")
        QLabel_title.setStyleSheet("font-weight: 700; color: #1E40AF;")
        hl.addWidget(QLabel_title)

        for linea in [
            "• Impresora 58mm con protocolo ESC/POS (Xprinter, Epson, Star, genéricas)",
            "• Conectada por USB a la computadora",
            "• Drivers instalados (Windows los instala automáticamente en la mayoría de casos)",
            "• Librería instalada: pip install python-escpos",
        ]:
            lbl = QLabel(linea)
            lbl.setStyleSheet("color: #1E40AF; font-size: 12px;")
            hl.addWidget(lbl)

        layout.addWidget(help_frame)
        layout.addStretch()

    def _print_test(self):
        self._test_btn.setEnabled(False)
        self._test_btn.setText("⏳  Imprimiendo...")
        self._status_lbl.setText("⏳  Enviando a impresora...")

        self._worker = PrintWorker(mode="test")
        self._worker.finished.connect(self._on_test_done)
        self._worker.start()

    def _on_test_done(self, ok: bool, msg: str):
        self._test_btn.setEnabled(True)
        self._test_btn.setText("🖨️  Imprimir página de prueba")

        if ok:
            self._status_lbl.setText("🟢  Impresora conectada y funcionando")
            self._status_lbl.setStyleSheet("color: #10B981; font-size: 13px; font-weight: 600;")
        else:
            self._status_lbl.setText("🔴  No se pudo conectar a la impresora")
            self._status_lbl.setStyleSheet("color: #EF4444; font-size: 13px; font-weight: 600;")
            QMessageBox.warning(self, "Error de impresión", msg)

    def _save_config(self):
        # Guardar en un archivo simple de configuración
        from pathlib import Path
        import json

        config = {
            "nombre_negocio": self._nombre_input.text().strip(),
            "subtitulo":      self._subtitulo_input.text().strip(),
            "telefono":       self._telefono_input.text().strip(),
            "mensaje_pie":    self._pie_input.text().strip(),
        }

        config_path = Path(__file__).parent.parent.parent / "config_impresora.json"
        try:
            config_path.write_text(
                json.dumps(config, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            QMessageBox.information(self, "Guardado",
                "✅ Configuración de impresora guardada correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")

    def get_config(self) -> dict:
        """Retorna la configuración actual para usar al imprimir."""
        from pathlib import Path
        import json

        config_path = Path(__file__).parent.parent.parent / "config_impresora.json"
        if config_path.exists():
            try:
                return json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "nombre_negocio": "Cafetería La Placita",
            "subtitulo":      "Sucursal Santa Fe",
            "telefono":       "",
            "mensaje_pie":    "¡Gracias por su visita!",
        }