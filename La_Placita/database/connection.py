"""
Database Connection Manager
Handles SQLite database connections and initialization
OPTIMIZADO: WAL mode, cache, PRAGMAs de rendimiento
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional


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
            print("✔ Base de datos inicializada correctamente")
        except sqlite3.Error as e:
            print(f"✗ Error al inicializar base de datos: {e}")
            raise
        except Exception as e:
            print(f"✗ Error inesperado: {e}")
            raise
    
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
    
    def backup_database(self, backup_path: str):
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"✔ Backup creado: {backup_path}")
            return True
        except Exception as e:
            print(f"✗ Error al crear backup: {e}")
            return False
    
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
