"""
Migración: agrega campos de envase a la tabla insumos.
Ejecutar UNA sola vez:
    python run_migration_envase.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.expanduser("~"), ".restaurant_pos", "restaurant.db")

def run():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute("PRAGMA table_info(insumos)")
    cols = {row[1] for row in cur.fetchall()}

    added = []
    if "envase_tipo" not in cols:
        cur.execute("ALTER TABLE insumos ADD COLUMN envase_tipo TEXT")
        added.append("envase_tipo")
    if "envase_cantidad" not in cols:
        cur.execute("ALTER TABLE insumos ADD COLUMN envase_cantidad REAL DEFAULT 1")
        added.append("envase_cantidad")

    conn.commit(); conn.close()

    if added:
        for c in added: print(f"  + columna '{c}' agregada")
    else:
        print("  · columnas ya existían")
    print("✅ Migración envase completada.")

if __name__ == "__main__":
    run()
