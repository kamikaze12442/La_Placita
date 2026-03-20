"""
Database Connection Manager
Handles SQLite database connections and initialization
OPTIMIZADO: WAL mode, cache, PRAGMAs de rendimiento
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional
import threading 
from datetime import datetime  


class DatabaseManager:
    """Singleton database manager"""
    
    _instance: Optional['DatabaseManager'] = None
    _connection: Optional[sqlite3.Connection] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._connection is None:
            self.db_path = self._get_db_path()
            self.connect()
            self.initialize_database()
    
    def _get_db_path(self) -> Path:
        data_dir = Path.home() / '.restaurant_pos'
        data_dir.mkdir(exist_ok=True)
        return data_dir / 'restaurant.db'
    
    def connect(self) -> sqlite3.Connection:
        try:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._connection.row_factory = sqlite3.Row

            # ─── OPTIMIZACIONES DE RENDIMIENTO ──────────────────────
            pragmas = [
                "PRAGMA foreign_keys = ON",
                "PRAGMA journal_mode = WAL",       # Escrituras sin bloquear lecturas
                "PRAGMA synchronous = NORMAL",     # Balance seguridad/velocidad
                "PRAGMA cache_size = -8000",       # 8 MB de cache en memoria
                "PRAGMA temp_store = MEMORY",      # Tablas temporales en RAM
                "PRAGMA mmap_size = 134217728",    # 128 MB memory-mapped I/O
                "PRAGMA optimize",                 # Optimiza el plan de queries
            ]
            for pragma in pragmas:
                self._connection.execute(pragma)
            # ────────────────────────────────────────────────────────

            self._connection.commit()
            print(f"✔ Conectado a base de datos: {self.db_path}")
            return self._connection
        except sqlite3.Error as e:
            print(f"✗ Error al conectar a la base de datos: {e}")
            raise
    
    def get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self.connect()
        return self._connection
    
    def initialize_database(self):
        try:
            schema_path = Path(__file__).parent / 'schema.sql'
            if not schema_path.exists():
                print(f"✗ Archivo schema.sql no encontrado en: {schema_path}")
                return
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            cursor = self._connection.cursor()
            cursor.executescript(schema_sql)
            self._connection.commit()
            self._run_migrations()
            self._schedule_backup()
            print("✔ Base de datos inicializada correctamente")
        except sqlite3.Error as e:
            print(f"✗ Error al inicializar base de datos: {e}")
            raise
        except Exception as e:
            print(f"✗ Error inesperado: {e}")
            raise
    def _run_migrations(self):
        """Aplica columnas faltantes en tablas existentes (idempotente)."""
        cur = self._connection.cursor()

        def cols(tabla):
            cur.execute(f"PRAGMA table_info({tabla})")
            return {row[1] for row in cur.fetchall()}

        def add_col(tabla, col, definition):
            if col not in cols(tabla):
                cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {definition}")
                print(f"  + migración: '{col}' agregado a {tabla}")

        # ventas
        add_col("ventas", "monto_efectivo", "DECIMAL(10,2) DEFAULT 0")
        add_col("ventas", "monto_qr",       "DECIMAL(10,2) DEFAULT 0")
        add_col("ventas", "tipo_pedido",    "TEXT DEFAULT 'mesa'")

        # productos
        add_col("productos", "disponible", "INTEGER NOT NULL DEFAULT 1")

        # insumos (por si la tabla existía antes sin estas columnas)
        add_col("insumos", "envase_tipo",     "TEXT")
        add_col("insumos", "envase_cantidad", "REAL DEFAULT 1")
        add_col("insumos", "descripcion",     "TEXT")

        # movimientos_insumos (por si existía sin estas columnas)
        add_col("movimientos_insumos", "venta_id",       "INTEGER")
        add_col("movimientos_insumos", "stock_anterior", "REAL NOT NULL DEFAULT 0")
        add_col("movimientos_insumos", "stock_nuevo",    "REAL NOT NULL DEFAULT 0")
        add_col("movimientos_insumos", "usuario_id",     "INTEGER")

        # Crear arqueos_caja si no existe (tabla nueva, la antigua era arqueo_caja)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS arqueos_caja (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id           INTEGER NOT NULL,
                fecha_inicio         TEXT    NOT NULL,
                fecha_cierre         TEXT,
                estado               TEXT    NOT NULL DEFAULT 'abierto'
                                             CHECK(estado IN ('abierto','cerrado')),
                monto_inicial        REAL    DEFAULT 0,
                sistema_efectivo     REAL    DEFAULT 0,
                sistema_qr           REAL    DEFAULT 0,
                sistema_tarjeta      REAL    DEFAULT 0,
                sistema_total        REAL    DEFAULT 0,
                total_transacciones  INTEGER DEFAULT 0,
                conteo_efectivo      REAL    DEFAULT 0,
                conteo_qr            REAL    DEFAULT 0,
                conteo_tarjeta       REAL    DEFAULT 0,
                diferencia_efectivo  REAL    DEFAULT 0,
                diferencia_qr        REAL    DEFAULT 0,
                diferencia_tarjeta   REAL    DEFAULT 0,
                diferencia_total     REAL    DEFAULT 0,
                denominaciones       TEXT    DEFAULT '{}',
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_arqueos_usuario ON arqueos_caja(usuario_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_arqueos_estado  ON arqueos_caja(estado)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_arqueos_fecha   ON arqueos_caja(fecha_inicio)")

        self._connection.commit()
    def execute_query(self, query: str, params: tuple = None):
        """Execute INSERT/UPDATE/DELETE"""
        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self._connection.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"✗ Error ejecutando query: {e}")
            self._connection.rollback()
            raise
    
    def execute_many(self, query: str, params_list: list):
        """Execute batch INSERT/UPDATE — mucho más rápido que execute_query en loop"""
        try:
            cursor = self._connection.cursor()
            cursor.executemany(query, params_list)
            self._connection.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            print(f"✗ Error en execute_many: {e}")
            self._connection.rollback()
            raise

    def fetch_one(self, query: str, params: tuple = None) -> Optional[sqlite3.Row]:
        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"✗ Error en fetch_one: {e}")
            return None
    
    def fetch_all(self, query: str, params: tuple = None) -> list:
        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"✗ Error en fetch_all: {e}")
            return []
    
    def close(self):
        if self._connection:
            # Optimizar antes de cerrar
            try:
                self._connection.execute("PRAGMA optimize")
            except Exception:
                pass
            self._connection.close()
            self._connection = None
            print("✔ Conexión a base de datos cerrada")
    def _schedule_backup(self):
        """Programa backup automático cada 24 horas."""
        
        def _do_backup():
            backup_dir = Path.home() / '.restaurant_pos' / 'backups'
            backup_dir.mkdir(exist_ok=True)

            # Mantener solo los últimos 7 backups
            backups = sorted(backup_dir.glob('*.db'))
            while len(backups) >= 7:
                backups[0].unlink()
                backups.pop(0)

            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"backup_{fecha}.db"

            try:
                # Backup seguro usando la API de SQLite (no shutil)
                # Esto garantiza consistencia aunque haya escrituras en curso
                conn_backup = sqlite3.connect(str(backup_path))
                self._connection.backup(conn_backup)
                conn_backup.close()
                print(f"✔ Backup automático: {backup_path.name}")
            except Exception as e:
                print(f"✗ Error en backup automático: {e}")

        t = threading.Thread(target=_do_backup, daemon=True)
        t.start()
        
    def backup_database(self, backup_path: str = None) -> tuple:
        """Backup manual — devuelve (True, path) o (False, error)."""
        if not backup_path:
            backup_dir = Path.home() / '.cafeteria_LaPlacita' / 'backups'
            backup_dir.mkdir(exist_ok=True)
            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = str(backup_dir / f"backup_manual_{fecha}.db")
        try:
            conn_backup = sqlite3.connect(backup_path)
            self._connection.backup(conn_backup)
            conn_backup.close()
            print(f"✔ Backup creado: {backup_path}")
            return True, backup_path
        except Exception as e:
            print(f"✗ Error al crear backup: {e}")
            return False, str(e)
    
    def get_table_count(self, table_name: str) -> int:
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.fetch_one(query)
        return result['count'] if result else 0


# Global database instance
db = DatabaseManager()


# Convenience functions
def get_connection() -> sqlite3.Connection:
    return db.get_connection()

def execute_query(query: str, params: tuple = None):
    return db.execute_query(query, params)

def fetch_one(query: str, params: tuple = None) -> Optional[sqlite3.Row]:
    return db.fetch_one(query, params)

def fetch_all(query: str, params: tuple = None) -> list:
    return db.fetch_all(query, params)


if __name__ == '__main__':
    print("Testing database connection...")
    db = DatabaseManager()
    print(f"\nUsuarios: {db.get_table_count('usuarios')}")
    print(f"Productos: {db.get_table_count('productos')}")
    print(f"Categorías: {db.get_table_count('categorias')}")
    print("\n✔ Base de datos funcionando correctamente")