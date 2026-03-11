"""
Módulo de Impresión Térmica
Impresora SAT 15TUS 58mm USB

Usa win32print directamente — sin python-escpos, sin pyusb, sin libusb.
Solo necesita:  pip install pywin32

Envía comandos ESC/POS como bytes crudos al spooler de Windows.
"""

from datetime import datetime

SAT_PRINTER_NAME = "POS58 Printer"

# ── Comandos ESC/POS básicos ──────────────────────────────────────────────────
ESC  = b'\x1b'
GS   = b'\x1d'

INIT          = ESC + b'@'           # Inicializar impresora
ALIGN_LEFT    = ESC + b'a\x00'
ALIGN_CENTER  = ESC + b'a\x01'
ALIGN_RIGHT   = ESC + b'a\x02'
BOLD_ON       = ESC + b'E\x01'
BOLD_OFF      = ESC + b'E\x00'
DOUBLE_ON     = GS  + b'!\x11'      # doble alto + doble ancho
DOUBLE_OFF    = GS  + b'!\x00'
FEED_3        = b'\n\n\n'
CUT           = GS  + b'V\x41\x00'  # corte parcial
DRAWER_PIN2   = ESC + b'p\x00\x19\xfa'  # abrir cajón — pin 2 (más común)
DRAWER_PIN5   = ESC + b'p\x01\x19\xfa'  # abrir cajón — pin 5 (alternativo)


def _encode(texto: str) -> bytes:
    """Convierte texto a bytes cp437 (compatible con impresoras térmicas)."""
    return texto.encode("cp437", errors="replace")


def _build_recibo(sale, nombre_negocio, subtitulo, telefono, mensaje_pie,
                  abrir_cajon: bool = False) -> bytes:
    """Construye el recibo completo como bytes ESC/POS."""
    ANCHO = 32
    buf = bytearray()

    def add(b: bytes):
        buf.extend(b)

    def linea(texto=""):
        add(_encode(str(texto)) + b'\n')

    def sep(c="-"):
        add(_encode(c * ANCHO) + b'\n')

    # ── Inicializar ───────────────────────────────────────────────────
    add(INIT)

    # ── Encabezado ────────────────────────────────────────────────────
    add(ALIGN_CENTER + BOLD_ON + DOUBLE_ON)
    linea(nombre_negocio)
    add(DOUBLE_OFF + BOLD_OFF)
    linea(subtitulo)
    if telefono:
        linea(telefono)
    add(ALIGN_LEFT)
    sep("=")

    # ── Datos de la venta ─────────────────────────────────────────────
    fecha = datetime.fromisoformat(sale.fecha_venta).strftime("%d/%m/%Y  %H:%M")
    linea(f"Factura : {sale.numero_factura}")
    linea(f"Fecha   : {fecha}")
    linea(f"Cliente : {sale.cliente or 'Cliente General'}")
    metodos = {"efectivo": "Efectivo", "qr": "QR", "tarjeta": "Tarjeta"}
    linea(f"Pago    : {metodos.get(sale.metodo_pago, sale.metodo_pago.title())}")
    sep()

    # ── Cabecera de items ─────────────────────────────────────────────
    add(BOLD_ON)
    linea(f"{'Producto':<18}{'Cant':>4}{'Total':>10}")
    add(BOLD_OFF)
    sep()

    # ── Items ─────────────────────────────────────────────────────────
    for item in sale.items:
        nombre = item.producto_nombre[:17]
        cant   = str(item.cantidad)
        total  = f"Bs {item.subtotal:.2f}"
        linea(f"{nombre:<18}{cant:>4}{total:>10}")
        if item.cantidad > 1:
            linea(f"  @ Bs {item.precio_unitario:.2f} c/u")

    sep("=")

    # ── Totales ───────────────────────────────────────────────────────
    if sale.descuento and sale.descuento > 0:
        add(ALIGN_RIGHT)
        linea(f"Subtotal:  Bs {sale.subtotal:.2f}")
        linea(f"Descuento: Bs {sale.descuento:.2f}")

    add(ALIGN_RIGHT + BOLD_ON + DOUBLE_ON)
    linea(f"TOTAL: Bs {sale.total:.2f}")
    add(DOUBLE_OFF + BOLD_OFF + ALIGN_LEFT)
    sep("=")

    # ── Pie ───────────────────────────────────────────────────────────
    add(ALIGN_CENTER)
    for linea_pie in mensaje_pie.split("\n"):
        linea(linea_pie)

    add(FEED_3)
    add(CUT)

    # ── Cajón de dinero ───────────────────────────────────────────────
    # Solo se abre si el pago fue en efectivo o mixto (no en QR/tarjeta)
    metodo = getattr(sale, 'metodo_pago', '') or ''
    if abrir_cajon and metodo.lower() in ('efectivo', 'mixto'):
        add(DRAWER_PIN2)

    return bytes(buf)


def _build_prueba() -> bytes:
    """Construye una página de prueba como bytes ESC/POS."""
    ANCHO = 32
    buf = bytearray()

    def add(b): buf.extend(b)
    def linea(t=""): add(_encode(str(t)) + b'\n')
    def sep(c="-"): add(_encode(c * ANCHO) + b'\n')

    add(INIT)
    add(ALIGN_CENTER + BOLD_ON + DOUBLE_ON)
    linea("La Placita")
    add(DOUBLE_OFF + BOLD_OFF)
    linea("Prueba de impresion")
    sep()
    linea(datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
    sep()
    add(BOLD_ON)
    linea("Impresora SAT 15TUS OK!")
    add(BOLD_OFF)
    linea("58mm - ESC/POS")
    add(FEED_3 + CUT)

    return bytes(buf)


def _imprimir_bytes(data: bytes) -> tuple:
    """
    Envía bytes RAW directamente al spooler de Windows.
    Este método funciona con cualquier impresora que tenga driver instalado.
    """
    try:
        import win32print  # type: ignore

        # Buscar impresora: primero por nombre exacto, luego SAT, luego default
        printer_name = None

        printers = [p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )]

        if SAT_PRINTER_NAME in printers:
            printer_name = SAT_PRINTER_NAME
        else:
            for name in printers:
                if "SAT" in name.upper() or "POS" in name.upper() or "58" in name:
                    printer_name = name
                    break

        if not printer_name:
            printer_name = win32print.GetDefaultPrinter()

        print(f"✓ Enviando a impresora: {printer_name}")

        # Abrir impresora y enviar trabajo RAW
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            job = win32print.StartDocPrinter(
                hprinter, 1,
                ("Recibo La Placita", None, "RAW")
            )
            try:
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, data)
                win32print.EndPagePrinter(hprinter)
            finally:
                win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)

        return True, "Impreso correctamente ✅"

    except ImportError:
        return False, "pywin32 no instalado.\nEjecutá: pip install pywin32"
    except Exception as e:
        return False, f"Error al imprimir: {e}"


# ── API pública ───────────────────────────────────────────────────────────────

def imprimir_recibo(sale,
                    nombre_negocio: str = "Cafeteria La Placita",
                    subtitulo: str = "Sucursal Santa Fe",
                    telefono: str = "",
                    mensaje_pie: str = "Gracias por su visita!\nVuelva pronto",
                    abrir_cajon: bool = True) -> tuple:
    """
    Imprime el recibo de una venta.
    abrir_cajon=True  → envía señal al drawer después del corte
                        (solo actúa si el método de pago es efectivo o mixto)
    """
    try:
        data = _build_recibo(sale, nombre_negocio, subtitulo, telefono,
                             mensaje_pie, abrir_cajon)
        return _imprimir_bytes(data)
    except Exception as e:
        return False, f"Error generando recibo: {e}"


def imprimir_prueba() -> tuple:
    """Imprime una página de prueba."""
    try:
        data = _build_prueba()
        return _imprimir_bytes(data)
    except Exception as e:
        return False, f"Error generando prueba: {e}"