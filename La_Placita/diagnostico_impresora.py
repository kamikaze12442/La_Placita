"""
Diagnóstico de impresora SAT 15TUS
Ejecutar con: python diagnostico_impresora.py
"""

print("=" * 50)
print("DIAGNÓSTICO IMPRESORA SAT 15TUS")
print("=" * 50)

# ── 1. Verificar pywin32 ──────────────────────────────
print("\n[1] Verificando pywin32...")
try:
    import win32print
    print("    ✅ pywin32 instalado correctamente")
except ImportError:
    print("    ❌ pywin32 NO instalado")
    print("       Ejecutá: pip install pywin32")
    exit()

# ── 2. Listar todas las impresoras ────────────────────
print("\n[2] Impresoras instaladas en Windows:")
try:
    printers = win32print.EnumPrinters(
        win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    )
    if not printers:
        print("    ❌ No se encontró ninguna impresora instalada")
    for i, p in enumerate(printers):
        print(f"    [{i}] Nombre: '{p[2]}'")
        print(f"         Server: {p[0]}, Flags: {p[1]}")
except Exception as e:
    print(f"    ❌ Error: {e}")

# ── 3. Impresora predeterminada ───────────────────────
print("\n[3] Impresora predeterminada:")
try:
    default = win32print.GetDefaultPrinter()
    print(f"    → '{default}'")
except Exception as e:
    print(f"    ❌ Error: {e}")

# ── 4. Intentar abrir la SAT directamente ─────────────
print("\n[4] Intentando abrir SAT 15TUS...")
SAT_NAME = "SATSAT15TUSDBC6"
try:
    h = win32print.OpenPrinter(SAT_NAME)
    print(f"    ✅ Impresora '{SAT_NAME}' abierta correctamente")

    # Ver info de la impresora
    info = win32print.GetPrinter(h, 2)
    print(f"    Estado : {info['Status']}")
    print(f"    Puerto  : {info['pPortName']}")
    print(f"    Driver  : {info['pDriverName']}")
    win32print.ClosePrinter(h)
except Exception as e:
    print(f"    ❌ Error abriendo '{SAT_NAME}': {e}")

# ── 5. Intentar enviar datos RAW de prueba ────────────
print("\n[5] Intentando enviar datos RAW...")
test_data = (
    b'\x1b@'           # Init
    b'\x1ba\x01'       # Centro
    b'PRUEBA SAT 15TUS\n'
    b'Impresion RAW OK\n'
    b'\n\n\n'
    b'\x1dV\x41\x00'   # Corte
)

try:
    # Buscar cualquier impresora SAT disponible
    all_printers = [p[2] for p in win32print.EnumPrinters(
        win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    )]

    target = None
    if SAT_NAME in all_printers:
        target = SAT_NAME
    else:
        for name in all_printers:
            if "SAT" in name.upper():
                target = name
                break

    if not target and all_printers:
        target = all_printers[0]
        print(f"    ⚠ SAT no encontrada, usando: '{target}'")

    if target:
        h = win32print.OpenPrinter(target)
        job = win32print.StartDocPrinter(h, 1, ("Test", None, "RAW"))
        win32print.StartPagePrinter(h)
        win32print.WritePrinter(h, test_data)
        win32print.EndPagePrinter(h)
        win32print.EndDocPrinter(h)
        win32print.ClosePrinter(h)
        print(f"    ✅ Datos enviados a '{target}'")
        print("       Si la impresora está encendida, debería imprimir ahora")
    else:
        print("    ❌ No se encontró ninguna impresora para enviar la prueba")

except Exception as e:
    print(f"    ❌ Error enviando datos: {e}")
    print(f"       Detalle: {type(e).__name__}")

print("\n" + "=" * 50)
print("Compartí este resultado para continuar el diagnóstico")
print("=" * 50)
input("\nPresioná Enter para cerrar...")
