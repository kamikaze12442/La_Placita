"""
Product Model
ACTUALIZADO: _COLS_LISTA ahora incluye 'imagen' para mostrarlo en POS y tabla
"""

from typing import Optional, List
from database.connection import db

# imagen incluida para que POS y tabla de productos puedan mostrarla sin get_by_id
_COLS_LISTA = "id, nombre, precio, costo, categoria_id, stock, imagen, activo, COALESCE(disponible,1) as disponible"
_COLS_FULL  = "id, nombre, descripcion, precio, costo, categoria_id, stock, imagen, activo, fecha_creacion, COALESCE(disponible,1) as disponible"


class Product:

    def __init__(self, id: int, nombre: str, precio: float,
                 descripcion: str = None, costo: float = 0,
                 categoria_id: int = None, stock: int = 0,
                 imagen: str = None, activo: bool = True,
                 fecha_creacion: str = None,
                 disponible: int = 1, **kwargs):
        self.id            = id
        self.nombre        = nombre
        self.descripcion   = descripcion
        self.precio        = precio
        self.costo         = costo
        self.categoria_id  = categoria_id
        self.stock         = stock
        self.imagen        = imagen
        self.activo        = activo
        self.fecha_creacion = fecha_creacion
        self.disponible    = int(disponible)  # 1=controla stock, 0=vende sin stock

    # ── READ ──────────────────────────────────────────────────────────

    @staticmethod
    def get_all(activo_only: bool = True,
                limit: int = 200, offset: int = 0) -> List['Product']:
        where = "WHERE activo = 1" if activo_only else ""
        query = f"""
            SELECT {_COLS_LISTA} FROM productos
            {where} ORDER BY nombre LIMIT ? OFFSET ?
        """
        return [Product(**dict(r)) for r in db.fetch_all(query, (limit, offset))]

    @staticmethod
    def count(activo_only: bool = True) -> int:
        where = "WHERE activo = 1" if activo_only else ""
        r = db.fetch_one(f"SELECT COUNT(*) as c FROM productos {where}")
        return r['c'] if r else 0

    @staticmethod
    def get_by_id(product_id: int) -> Optional['Product']:
        query = f"SELECT {_COLS_FULL} FROM productos WHERE id = ?"
        r = db.fetch_one(query, (product_id,))
        return Product(**dict(r)) if r else None

    @staticmethod
    def get_by_category(categoria_id: int,
                        limit: int = 200, offset: int = 0) -> List['Product']:
        query = f"""
            SELECT {_COLS_LISTA} FROM productos
            WHERE categoria_id = ? AND activo = 1
            ORDER BY nombre LIMIT ? OFFSET ?
        """
        return [Product(**dict(r)) for r in db.fetch_all(query, (categoria_id, limit, offset))]

    @staticmethod
    def search(search_term: str, limit: int = 100) -> List['Product']:
        query = f"""
            SELECT {_COLS_LISTA} FROM productos
            WHERE nombre LIKE ? AND activo = 1
            ORDER BY nombre LIMIT ?
        """
        return [Product(**dict(r)) for r in db.fetch_all(query, (f"%{search_term}%", limit))]

    # ── WRITE ─────────────────────────────────────────────────────────

    @staticmethod
    def create(nombre: str, precio: float, descripcion: str = None,
               costo: float = 0, categoria_id: int = None,
               stock: int = 0, imagen: str = None) -> int:
        return db.execute_query(
            """INSERT INTO productos
               (nombre, descripcion, precio, costo, categoria_id, stock, imagen)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (nombre, descripcion, precio, costo, categoria_id, stock, imagen)
        )

    @staticmethod
    def update(product_id: int, **kwargs) -> bool:
        allowed = ['nombre', 'descripcion', 'precio', 'costo',
                   'categoria_id', 'stock', 'imagen', 'activo']
        sets, params = [], []
        for k, v in kwargs.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return False
        params.append(product_id)
        try:
            db.execute_query(f"UPDATE productos SET {', '.join(sets)} WHERE id = ?", tuple(params))
            return True
        except Exception as e:
            print(f"Error updating product: {e}")
            return False

    @staticmethod
    def set_disponible(product_id: int, disponible: bool) -> bool:
        """Admin: activa o desactiva control de stock para un producto."""
        db.execute_query(
            "UPDATE productos SET disponible = ? WHERE id = ?",
            (1 if disponible else 0, product_id)
        )
        return True

    @staticmethod
    def delete(product_id: int, hard: bool = False) -> bool:
        if hard:
            ref = db.fetch_one(
                "SELECT COUNT(*) as c FROM detalle_ventas WHERE producto_id = ?",
                (product_id,)
            )
            if ref and ref['c'] > 0:
                return False
            try:
                db.execute_query("DELETE FROM productos WHERE id = ?", (product_id,))
                return True
            except Exception as e:
                print(f"Error hard-deleting: {e}")
                return False
        return Product.update(product_id, activo=0)

    @staticmethod
    def delete_batch(product_ids: List[int], hard: bool = False) -> int:
        if not product_ids:
            return 0
        ph = ",".join("?" * len(product_ids))
        if hard:
            refs = db.fetch_one(
                f"SELECT COUNT(*) as c FROM detalle_ventas WHERE producto_id IN ({ph})",
                tuple(product_ids)
            )
            if refs and refs['c'] > 0:
                return 0
            db.execute_query(f"DELETE FROM productos WHERE id IN ({ph})", tuple(product_ids))
        else:
            db.execute_query(f"UPDATE productos SET activo=0 WHERE id IN ({ph})", tuple(product_ids))
        return len(product_ids)

    @staticmethod
    def update_stock(product_id: int, quantity: int) -> bool:
        try:
            db.execute_query("UPDATE productos SET stock = stock + ? WHERE id = ?",
                             (quantity, product_id))
            return True
        except Exception as e:
            print(f"Error updating stock: {e}")
            return False

    def get_margen(self) -> float:
        return ((self.precio - self.costo) / self.precio * 100) if self.precio else 0

    def __repr__(self):
        return f"<Product {self.id}: {self.nombre} Bs {self.precio}>"


class Category:

    def __init__(self, id: int, nombre: str, icono: str = None,
                 activo: bool = True, **kwargs):
        self.id     = id
        self.nombre = nombre
        self.icono  = icono
        self.activo = activo

    @staticmethod
    def get_all() -> List['Category']:
        return [Category(**dict(r)) for r in
                db.fetch_all("SELECT id, nombre, icono, activo FROM categorias WHERE activo=1 ORDER BY nombre")]

    @staticmethod
    def get_by_id(cat_id: int) -> Optional['Category']:
        r = db.fetch_one("SELECT id, nombre, icono, activo FROM categorias WHERE id=?", (cat_id,))
        return Category(**dict(r)) if r else None

    def get_products_count(self) -> int:
        r = db.fetch_one(
            "SELECT COUNT(*) as c FROM productos WHERE categoria_id=? AND activo=1", (self.id,)
        )
        return r['c'] if r else 0