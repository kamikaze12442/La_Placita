"""
Migración: sistema de insumos + recetas para descuento automático de inventario.
Ejecutar UNA sola vez:
    python run_migration_recetas.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.expanduser("~"), ".restaurant_pos", "restaurant.db")


def _cols(cur, tabla):
    cur.execute(f"PRAGMA table_info({tabla})")
    return {row[1] for row in cur.fetchall()}


def _add_col(cur, tabla, col, definition):
    cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {definition}")
    print(f"  + columna '{col}' agregada a {tabla}")


def _index(cur, name, tabla, col):
    cur.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {tabla}({col})")


def run():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── 1. insumos ─────────────────────────────────────────────────────────
    cur.execute("""
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
        )
    """)
    print("✓ Tabla insumos")

    # ── 2. recetas ─────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recetas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            insumo_id   INTEGER NOT NULL,
            cantidad    REAL    NOT NULL,
            UNIQUE (producto_id, insumo_id),
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
            FOREIGN KEY (insumo_id)   REFERENCES insumos(id)   ON DELETE CASCADE
        )
    """)
    print("✓ Tabla recetas")

    # ── 3. movimientos_insumos: crear o parchear columnas faltantes ─────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_insumos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            insumo_id       INTEGER NOT NULL,
            tipo            TEXT    NOT NULL,
            cantidad        REAL    NOT NULL,
            stock_anterior  REAL    NOT NULL DEFAULT 0,
            stock_nuevo     REAL    NOT NULL DEFAULT 0,
            motivo          TEXT,
            venta_id        INTEGER,
            usuario_id      INTEGER,
            fecha           TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)
    mi = _cols(cur, "movimientos_insumos")
    if "venta_id"       not in mi: _add_col(cur, "movimientos_insumos", "venta_id",       "INTEGER")
    if "stock_anterior" not in mi: _add_col(cur, "movimientos_insumos", "stock_anterior", "REAL NOT NULL DEFAULT 0")
    if "stock_nuevo"    not in mi: _add_col(cur, "movimientos_insumos", "stock_nuevo",    "REAL NOT NULL DEFAULT 0")
    if "usuario_id"     not in mi: _add_col(cur, "movimientos_insumos", "usuario_id",     "INTEGER")
    print("✓ Tabla movimientos_insumos")

    # ── 4. Índices ──────────────────────────────────────────────────────────
    _index(cur, "idx_recetas_producto",  "recetas",             "producto_id")
    _index(cur, "idx_recetas_insumo",    "recetas",             "insumo_id")
    _index(cur, "idx_movinsumos_insumo", "movimientos_insumos", "insumo_id")
    _index(cur, "idx_movinsumos_fecha",  "movimientos_insumos", "fecha")
    _index(cur, "idx_movinsumos_venta",  "movimientos_insumos", "venta_id")
    _index(cur, "idx_insumos_activo",    "insumos",             "activo")
    print("✓ Índices")

    # ── 5. Columna 'disponible' en productos ────────────────────────────────
    if "disponible" not in _cols(cur, "productos"):
        _add_col(cur, "productos", "disponible", "INTEGER NOT NULL DEFAULT 1")
    else:
        print("  · 'disponible' en productos ya existía")

    conn.commit()
    conn.close()
    print("\n✅ Migración completada.")


if __name__ == "__main__":
    run()