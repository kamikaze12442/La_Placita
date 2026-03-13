"""
Migración: crea la tabla paquetes_insumos.
Ejecutar UNA sola vez:
    python run_migration_paquetes.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.expanduser("~"), ".restaurant_pos", "restaurant.db")

def run():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paquetes_insumos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre          TEXT NOT NULL,
            proveedor       TEXT,
            nota            TEXT,
            items_json      TEXT DEFAULT '[]',
            ajustes_json    TEXT DEFAULT '[]',
            costo_total     DECIMAL(10,2) DEFAULT 0,
            usuario_id      INTEGER,
            fecha_registro  TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)
    conn.commit()
    print("✓ Tabla paquetes_insumos lista")
    conn.close()

if __name__ == "__main__":
    run()
