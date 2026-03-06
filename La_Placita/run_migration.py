"""
run_migration.py
================
Ejecuta la migración de inventario sobre la BD existente.
Correr UNA SOLA VEZ:  python run_migration.py
"""
from pathlib import Path
from database.connection import db

sql_path = Path(__file__).parent / "database" / "migration_inventario.sql"

with open(sql_path, "r", encoding="utf-8") as f:
    sql = f.read()

conn = db.get_connection()
conn.executescript(sql)
conn.commit()
print("✅ Migración de inventario aplicada correctamente.")
