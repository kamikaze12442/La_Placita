"""
Product Model
Handles product management
OPTIMIZADO: queries lean, paginación, sin SELECT *, batch delete
"""

from typing import Optional, List
from database.connection import db


# Columnas mínimas para mostrar en listas (evita cargar descripcion, imagen, etc.)
_COLS_LISTA = "id, nombre, precio, costo, categoria_id, stock, activo"
# Columnas completas solo cuando se edita un producto específico
_COLS_FULL  = "id, nombre, descripcion, precio, costo, categoria_id, stock, imagen, activo, fecha_creacion"


class Product:
    """Product model"""
    
    def __init__(self, id: int, nombre: str, precio: float,
                 descripcion: str = None, costo: float = 0,
                 categoria_id: int = None, stock: int = 0,
                 imagen: str = None, activo: bool = True,
                 fecha_creacion: str = None, **kwargs):
        self.id = id
        self.nombre = nombre
        self.descripcion = descripcion
        self.precio = precio
        self.costo = costo
        self.categoria_id = categoria_id
        self.stock = stock
        self.imagen = imagen
        self.activo = activo
        self.fecha_creacion = fecha_creacion

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    @staticmethod
    def get_all(activo_only: bool = True,
                limit: int = 100,
                offset: int = 0) -> List['Product']:
        """
        Obtener productos con paginación.
        
        Antes cargaba los 2000+ productos de golpe con SELECT *.
        Ahora:
          - Solo columnas necesarias para la lista
          - Paginación con LIMIT/OFFSET
        
        Uso en la UI:
            page = 0
            products = Product.get_all(limit=100, offset=page * 100)
        """
        where = "WHERE activo = 1" if activo_only else ""
        query = f"""
            SELECT {_COLS_LISTA}
            FROM productos
            {where}
            ORDER BY nombre
            LIMIT ? OFFSET ?
        """
        results = db.fetch_all(query, (limit, offset))
        return [Product(**dict(row)) for row in results]

    @staticmethod
    def count(activo_only: bool = True) -> int:
        """Total de productos (para calcular páginas en la UI)"""
        where = "WHERE activo = 1" if activo_only else ""
        result = db.fetch_one(f"SELECT COUNT(*) as c FROM productos {where}")
        return result['c'] if result else 0

    @staticmethod
    def get_by_id(product_id: int) -> Optional['Product']:
        """Obtener producto completo por ID (para editar)"""
        query = f"SELECT {_COLS_FULL} FROM productos WHERE id = ?"
        result = db.fetch_one(query, (product_id,))
        return Product(**dict(result)) if result else None

    @staticmethod
    def get_by_category(categoria_id: int,
                        limit: int = 100,
                        offset: int = 0) -> List['Product']:
        """Productos por categoría con paginación"""
        query = f"""
            SELECT {_COLS_LISTA}
            FROM productos
            WHERE categoria_id = ? AND activo = 1
            ORDER BY nombre
            LIMIT ? OFFSET ?
        """
        results = db.fetch_all(query, (categoria_id, limit, offset))
        return [Product(**dict(row)) for row in results]

    @staticmethod
    def search(search_term: str, limit: int = 100) -> List['Product']:
        """
        Buscar productos por nombre.
        Solo busca en 'nombre' (no en descripcion) para usar el índice idx_productos_nombre.
        Si también necesitas buscar en descripcion, agrega un índice aparte.
        """
        query = f"""
            SELECT {_COLS_LISTA}
            FROM productos
            WHERE nombre LIKE ? AND activo = 1
            ORDER BY nombre
            LIMIT ?
        """
        results = db.fetch_all(query, (f"%{search_term}%", limit))
        return [Product(**dict(row)) for row in results]

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    @staticmethod
    def create(nombre: str, precio: float, descripcion: str = None,
               costo: float = 0, categoria_id: int = None,
               stock: int = 0, imagen: str = None) -> int:
        """Crear producto. Retorna el nuevo ID."""
        query = """
            INSERT INTO productos
            (nombre, descripcion, precio, costo, categoria_id, stock, imagen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        return db.execute_query(
            query,
            (nombre, descripcion, precio, costo, categoria_id, stock, imagen)
        )

    @staticmethod
    def update(product_id: int, **kwargs) -> bool:
        """Actualizar campos específicos de un producto."""
        allowed_fields = ['nombre', 'descripcion', 'precio', 'costo',
                          'categoria_id', 'stock', 'imagen', 'activo']

        updates = []
        params = []

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                updates.append(f"{field} = ?")
                params.append(value)

        if not updates:
            return False

        params.append(product_id)
        query = f"UPDATE productos SET {', '.join(updates)} WHERE id = ?"

        try:
            db.execute_query(query, tuple(params))
            return True
        except Exception as e:
            print(f"Error updating product: {e}")
            return False

    @staticmethod
    def delete(product_id: int, hard: bool = False) -> bool:
        """
        Eliminar producto.
        
        hard=False (defecto): soft delete → marca activo=0, conserva historial de ventas.
        hard=True: borra físicamente (solo si no tiene ventas asociadas).
        
        El soft delete es mucho más seguro porque detalle_ventas referencia productos.id.
        """
        if hard:
            # Verificar que no tenga ventas antes de borrar físicamente
            ref = db.fetch_one(
                "SELECT COUNT(*) as c FROM detalle_ventas WHERE producto_id = ?",
                (product_id,)
            )
            if ref and ref['c'] > 0:
                print(f"No se puede eliminar: producto {product_id} tiene {ref['c']} ventas registradas.")
                return False
            try:
                db.execute_query("DELETE FROM productos WHERE id = ?", (product_id,))
                return True
            except Exception as e:
                print(f"Error hard-deleting product: {e}")
                return False
        else:
            return Product.update(product_id, activo=0)

    @staticmethod
    def delete_batch(product_ids: List[int], hard: bool = False) -> int:
        """
        Eliminar múltiples productos de una sola vez.
        Mucho más rápido que llamar delete() en un bucle.
        Retorna la cantidad de productos eliminados.
        """
        if not product_ids:
            return 0

        placeholders = ",".join("?" * len(product_ids))

        if hard:
            # Verificar referencias en ventas
            refs = db.fetch_one(
                f"SELECT COUNT(*) as c FROM detalle_ventas WHERE producto_id IN ({placeholders})",
                tuple(product_ids)
            )
            if refs and refs['c'] > 0:
                print(f"Algunos productos tienen ventas registradas. Usa soft delete.")
                return 0
            try:
                db.execute_query(
                    f"DELETE FROM productos WHERE id IN ({placeholders})",
                    tuple(product_ids)
                )
            except Exception as e:
                print(f"Error en batch hard-delete: {e}")
                return 0
        else:
            try:
                db.execute_query(
                    f"UPDATE productos SET activo = 0 WHERE id IN ({placeholders})",
                    tuple(product_ids)
                )
            except Exception as e:
                print(f"Error en batch soft-delete: {e}")
                return 0

        return len(product_ids)

    @staticmethod
    def update_stock(product_id: int, quantity: int) -> bool:
        """Actualizar stock (suma o resta según signo de quantity)."""
        query = "UPDATE productos SET stock = stock + ? WHERE id = ?"
        try:
            db.execute_query(query, (quantity, product_id))
            return True
        except Exception as e:
            print(f"Error updating stock: {e}")
            return False

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def get_margen(self) -> float:
        if self.precio == 0:
            return 0
        return ((self.precio - self.costo) / self.precio) * 100

    def __repr__(self):
        return f"<Product {self.id}: {self.nombre} - Bs {self.precio}>"


class Category:
    """Category model"""

    def __init__(self, id: int, nombre: str, icono: str = None,
                 activo: bool = True, **kwargs):
        self.id = id
        self.nombre = nombre
        self.icono = icono
        self.activo = activo

    @staticmethod
    def get_all() -> List['Category']:
        query = "SELECT id, nombre, icono, activo FROM categorias WHERE activo = 1 ORDER BY nombre"
        results = db.fetch_all(query)
        return [Category(**dict(row)) for row in results]

    @staticmethod
    def get_by_id(category_id: int) -> Optional['Category']:
        query = "SELECT id, nombre, icono, activo FROM categorias WHERE id = ?"
        result = db.fetch_one(query, (category_id,))
        return Category(**dict(result)) if result else None

    def get_products_count(self) -> int:
        result = db.fetch_one(
            "SELECT COUNT(*) as count FROM productos WHERE categoria_id = ? AND activo = 1",
            (self.id,)
        )
        return result['count'] if result else 0


if __name__ == '__main__':
    print("Testing Product model...")
    total = Product.count()
    print(f"✔ Total productos: {total}")

    # Primera página
    products = Product.get_all(limit=20, offset=0)
    print(f"✔ Página 1 (primeros 20):")
    for p in products[:5]:
        print(f"  - {p.nombre}: Bs {p.precio}")

    categories = Category.get_all()
    print(f"\n✔ Categorías: {len(categories)}")
    for cat in categories:
        print(f"  - {cat.icono} {cat.nombre}: {cat.get_products_count()} productos")
