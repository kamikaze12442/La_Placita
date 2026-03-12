"""
run_migration_arqueo.py
=======================
Ejecutar UNA SOLA VEZ:  python run_migration_arqueo.py
"""
from pathlib import Path
from database.connection import db

sql_path = Path(__file__).parent / "database" / "migration_arqueo.sql"

with open(sql_path, "r", encoding="utf-8") as f:
    sql = f.read()

conn = db.get_connection()
conn.executescript(sql)
conn.commit()
print("✅ Migración de arqueo de caja aplicada correctamente.")
