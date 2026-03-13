"""
Migración: sistema de insumos + recetas para descuento automático de inventario.
Ejecutar UNA sola vez:
    python run_migration_recetas.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.expanduser("~"), ".restaurant_pos", "restaurant.db")

SQL = """
CREATE TABLE IF NOT EXISTS insumos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT    NOT NULL UNIQUE,
    unidad          TEXT    NOT NULL,
    stock_actual    REAL    NOT NULL DEFAULT 0,
    stock_minimo    REAL    NOT NULL DEFAULT 0,
    costo_unitario  REAL    NOT NULL DEFAULT 0,
    categoria       TEXT,
    activo          INTEGER NOT NULL DEFAULT 1,
    fecha_creacion  TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS recetas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    insumo_id   INTEGER NOT NULL,
    cantidad    REAL    NOT NULL,
    UNIQUE (producto_id, insumo_id),
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    FOREIGN KEY (insumo_id)   REFERENCES insumos(id)   ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS movimientos_insumos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    insumo_id       INTEGER NOT NULL,
    tipo            TEXT    NOT NULL CHECK(tipo IN ('entrada','consumo','ajuste','merma')),
    cantidad        REAL    NOT NULL,
    stock_anterior  REAL    NOT NULL,
    stock_nuevo     REAL    NOT NULL,
    motivo          TEXT,
    venta_id        INTEGER,
    usuario_id      INTEGER,
    fecha           TEXT    DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (insumo_id)  REFERENCES insumos(id),
    FOREIGN KEY (venta_id)   REFERENCES ventas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_recetas_producto   ON recetas(producto_id);
CREATE INDEX IF NOT EXISTS idx_recetas_insumo     ON recetas(insumo_id);
CREATE INDEX IF NOT EXISTS idx_movinsumos_insumo  ON movimientos_insumos(insumo_id);
CREATE INDEX IF NOT EXISTS idx_movinsumos_fecha   ON movimientos_insumos(fecha);
CREATE INDEX IF NOT EXISTS idx_movinsumos_venta   ON movimientos_insumos(venta_id);
CREATE INDEX IF NOT EXISTS idx_insumos_activo     ON insumos(activo);
"""

def run():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.executescript(SQL)

    # Columna 'disponible' en productos (para bloquear agotados)
    cur.execute("PRAGMA table_info(productos)")
    cols = [row[1] for row in cur.fetchall()]
    if "disponible" not in cols:
        cur.execute("ALTER TABLE productos ADD COLUMN disponible INTEGER NOT NULL DEFAULT 1")
        print("✓ Columna 'disponible' agregada a productos")
    else:
        print("✓ Columna 'disponible' ya existía")

    conn.commit()
    conn.close()

    print("✓ Tabla insumos")
    print("✓ Tabla recetas")
    print("✓ Tabla movimientos_insumos")
    print("✓ Índices")
    print("\n✅ Migración completada.")

if __name__ == "__main__":
    run()
