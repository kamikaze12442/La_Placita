"""
Migración: agrega tipo_pedido a la tabla ventas.
Ejecutar UNA sola vez:
    python run_migration_tipo_pedido.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.expanduser("~"), ".restaurant_pos", "restaurant.db")

def run():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("PRAGMA table_info(ventas)")
    cols = {row[1] for row in cur.fetchall()}
    if "tipo_pedido" not in cols:
        cur.execute("ALTER TABLE ventas ADD COLUMN tipo_pedido TEXT DEFAULT 'mesa'")
        conn.commit()
        print("✓ Columna tipo_pedido agregada")
    else:
        print("✓ Ya existe, nada que hacer")
    conn.close()

if __name__ == "__main__":
    run()
