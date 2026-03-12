"""
Migración: agrega monto_efectivo y monto_qr a la tabla ventas.
Ejecutar UNA sola vez desde la carpeta raíz del proyecto:
    python run_migration_mixto2.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.expanduser("~"), ".restaurant_pos", "restaurant.db")

def run():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Verificar si las columnas ya existen
    cur.execute("PRAGMA table_info(ventas)")
    cols = {row[1] for row in cur.fetchall()}

    added = []
    if "monto_efectivo" not in cols:
        cur.execute("ALTER TABLE ventas ADD COLUMN monto_efectivo DECIMAL(10,2) DEFAULT 0")
        added.append("monto_efectivo")

    if "monto_qr" not in cols:
        cur.execute("ALTER TABLE ventas ADD COLUMN monto_qr DECIMAL(10,2) DEFAULT 0")
        added.append("monto_qr")

    if added:
        # Para ventas existentes: si metodo_pago='efectivo' → monto_efectivo=total
        cur.execute("""
            UPDATE ventas SET monto_efectivo = total
            WHERE metodo_pago = 'efectivo' AND monto_efectivo = 0
        """)
        # Si metodo_pago='qr' → monto_qr=total
        cur.execute("""
            UPDATE ventas SET monto_qr = total
            WHERE metodo_pago = 'qr' AND monto_qr = 0
        """)
        conn.commit()
        print(f"✓ Columnas agregadas: {', '.join(added)}")
        print("✓ Datos históricos migrados correctamente")
    else:
        print("✓ Las columnas ya existen, nada que hacer")

    conn.close()

if __name__ == "__main__":
    run()
