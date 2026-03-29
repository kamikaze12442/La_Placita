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

def _build_recibo(sale, nombre_negocio, nombre, subtitulo, telefono,
                  mensaje_pie, abrir_cajon: bool = False) -> bytes:
    """Construye el recibo completo como bytes ESC/POS."""
    ANCHO = 32
    buf = bytearray()

    def add(b: bytes):
        buf.extend(b)

    def linea(texto=""):
        add(_encode(str(texto)) + b'\n')

    def sep(c="-"):
        add(_encode(c * ANCHO) + b'\n')

    def fila(izq, der, ancho=ANCHO):
        """Fila con texto izquierda y derecha alineados."""
        espacio = ancho - len(izq) - len(der)
        linea(izq + " " * max(1, espacio) + der)

    # ── Inicializar ───────────────────────────────────────────────
    add(INIT)

    # ── Encabezado ────────────────────────────────────────────────
    add(ALIGN_CENTER + BOLD_ON + DOUBLE_ON)
    linea(nombre_negocio)
    add(DOUBLE_OFF)
    linea(nombre)
    add(BOLD_OFF)
    if subtitulo:
        linea(subtitulo)
    if telefono:
        linea(f"Tel: {telefono}")
    add(ALIGN_LEFT)
    sep("=")

    # ── Datos de la venta ─────────────────────────────────────────
    fecha = datetime.fromisoformat(
        sale.fecha_venta).strftime("%d/%m/%Y  %H:%M")
    linea(f"Factura : {sale.numero_factura}")
    linea(f"Fecha   : {fecha}")
    linea(f"Cliente : {sale.cliente or 'Cliente General'}")
    metodos = {
        "efectivo": "Efectivo",
        "qr":       "QR",
        "tarjeta":  "Tarjeta",
        "mixto":    "Mixto",
    }
    linea(f"Pago    : {metodos.get(sale.metodo_pago, sale.metodo_pago.title())}")

    # Desglose pago mixto
    if sale.metodo_pago == "mixto":
        if getattr(sale, 'monto_efectivo', 0):
            fila("  Efectivo:", f"Bs {sale.monto_efectivo:.2f}")
        if getattr(sale, 'monto_qr', 0):
            fila("  QR:",       f"Bs {sale.monto_qr:.2f}")

    sep()

    # ── Cabecera de items ─────────────────────────────────────────
    add(BOLD_ON)
    linea(f"{'Producto':<18}{'Cant':>4}{'Total':>10}")
    add(BOLD_OFF)
    sep()

    # ── Agrupar productos repetidos ───────────────────────────────
    from collections import defaultdict
    agrupado = {}
    orden    = []
    for item in sale.items:
        key = item.producto_nombre
        if key not in agrupado:
            agrupado[key] = {"cantidad": 0, "precio": item.precio_unitario,
                             "subtotal": 0}
            orden.append(key)
        agrupado[key]["cantidad"] += item.cantidad
        agrupado[key]["subtotal"] += item.subtotal

    # ── Items ─────────────────────────────────────────────────────
    for key in orden:
        vals   = agrupado[key]
        nombre_prod = key[:17]
        cant   = str(vals["cantidad"])
        total  = f"Bs {vals['subtotal']:.2f}"
        linea(f"{nombre_prod:<18}{cant:>4}{total:>10}")
        if vals["cantidad"] > 1:
            linea(f"  @ Bs {vals['precio']:.2f} c/u")

    sep("=")

    # ── Totales ───────────────────────────────────────────────────
    add(ALIGN_RIGHT)
    if sale.descuento and sale.descuento > 0:
        fila("Subtotal:", f"Bs {sale.subtotal:.2f}")
        fila("Descuento:", f"- Bs {sale.descuento:.2f}")
        sep()

    add(BOLD_ON + DOUBLE_ON)
    linea(f"TOTAL: Bs {sale.total:.2f}")
    add(DOUBLE_OFF + BOLD_OFF + ALIGN_LEFT)
    sep("=")

    # ── Pie ───────────────────────────────────────────────────────
    add(ALIGN_CENTER)
    for linea_pie in mensaje_pie.split("\n"):
        linea(linea_pie)

    add(FEED_3)
    add(CUT)

    # ── Cajón de dinero ───────────────────────────────────────────
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
                    nombre_negocio: str = "La Placita",
                    nombre:str=("Cafeteria & Heladeria"),
                    subtitulo: str = "Sucursal Santa Fe",
                    telefono: str = "77113371",
                    mensaje_pie: str = "Gracias por su visita!\nVuelva pronto",
                    abrir_cajon: bool = True) -> tuple:
    """
    Imprime el recibo de una venta.
    abrir_cajon=True  → envía señal al drawer después del corte
                        (solo actúa si el método de pago es efectivo o mixto)
    """
    try:
        data = _build_recibo(sale, nombre_negocio,nombre, subtitulo, telefono,
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


def _build_ticket_cocina(sale) -> bytes:
    """Ticket para cocina con ítems, precios, total, cliente y método de pago."""
    ANCHO = 32
    buf = bytearray()

    def add(b): buf.extend(b)
    def linea(t=""): add(_encode(str(t)) + b'\n')
    def sep(c="-"): add(_encode(c * ANCHO) + b'\n')
    def fila(izq, der, ancho=ANCHO):
        espacio = ancho - len(izq) - len(der)
        linea(izq + " " * max(1, espacio) + der)

    add(INIT)
    add(ALIGN_CENTER + BOLD_ON + DOUBLE_ON)
    linea("** COCINA **")
    add(DOUBLE_OFF + BOLD_OFF)

    fecha = datetime.fromisoformat(
        sale.fecha_venta).strftime("%d/%m/%Y  %H:%M")
    linea(f"Factura: {sale.numero_factura}")
    linea(fecha)

    tipo = getattr(sale, 'tipo_pedido', 'mesa')
    tipo_label = "PARA LLEVAR" if tipo == "llevar" else "EN MESA"
    add(BOLD_ON)
    linea(tipo_label)
    add(BOLD_OFF)

    sep("=")
    add(ALIGN_LEFT)
    linea(f"Cliente : {sale.cliente or 'Cliente General'}")
    metodos = {
        "efectivo": "Efectivo",
        "qr":       "QR",
        "tarjeta":  "Tarjeta",
        "mixto":    "Mixto",
    }
    linea(f"Pago    : {metodos.get(sale.metodo_pago, sale.metodo_pago.title())}")
    sep()

    add(BOLD_ON)
    linea(f"{'Producto':<18}{'Cant':>4}{'Total':>10}")
    add(BOLD_OFF)
    sep()

    # Agrupar
    agrupado = {}
    orden = []
    for item in sale.items:
        key = item.producto_nombre
        if key not in agrupado:
            agrupado[key] = {"cantidad": 0, "precio": item.precio_unitario,
                             "subtotal": 0}
            orden.append(key)
        agrupado[key]["cantidad"] += item.cantidad
        agrupado[key]["subtotal"] += item.subtotal

    for key in orden:
        vals = agrupado[key]
        nombre_prod = key[:17]
        cant  = str(vals["cantidad"])
        total = f"Bs {vals['subtotal']:.2f}"
        linea(f"{nombre_prod:<18}{cant:>4}{total:>10}")
        if vals["cantidad"] > 1:
            linea(f"  @ Bs {vals['precio']:.2f} c/u")

    sep("=")
    add(ALIGN_RIGHT + BOLD_ON + DOUBLE_ON)
    linea(f"TOTAL: Bs {sale.total:.2f}")
    add(DOUBLE_OFF + BOLD_OFF + ALIGN_LEFT)
    sep("=")

    add(ALIGN_CENTER)
    linea("Preparar pedido")
    add(FEED_3 + CUT)

    return bytes(buf)


def imprimir_ticket_cocina(sale) -> tuple:
    """
    Imprime ticket simplificado para cocina.
    Solo muestra ítems y cantidades, sin precios ni totales.
    """
    try:
        data = _build_ticket_cocina(sale)
        return _imprimir_bytes(data)
    except Exception as e:
        return False, f"Error generando ticket cocina: {e}"