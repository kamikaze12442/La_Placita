"""
Inventory Model
Gestión de stock de productos e insumos con historial completo de movimientos.
"""

from typing import Optional, List
from datetime import datetime
from database.connection import db
from models.user import get_current_user


# ──────────────────────────────────────────────────────────────────────────────
# MOVIMIENTOS DE PRODUCTOS (stock de lo que se vende)
# ──────────────────────────────────────────────────────────────────────────────

def registrar_movimiento(producto_id: int, tipo: str, cantidad: int,
                          motivo: str = None) -> bool:
    """
    Registra un movimiento de stock de un producto y actualiza su stock.
    tipo: 'entrada' | 'venta' | 'ajuste' | 'merma'
    cantidad: positivo para entradas, negativo para salidas.
    """
    usuario = get_current_user()
    if not usuario:
        return False

    result = db.fetch_one("SELECT stock FROM productos WHERE id = ?", (producto_id,))
    if not result:
        return False

    stock_anterior = result['stock']
    stock_nuevo    = stock_anterior + cantidad

    if stock_nuevo < 0:
        return False  # No permitir stock negativo

    try:
        db.execute_query(
            "UPDATE productos SET stock = ? WHERE id = ?",
            (stock_nuevo, producto_id)
        )
        db.execute_query(
            """INSERT INTO movimientos_inventario
               (producto_id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, usuario_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (producto_id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, usuario.id)
        )
        return True
    except Exception as e:
        print(f"Error registrando movimiento: {e}")
        return False


def descontar_stock_venta(producto_id: int, cantidad: int) -> bool:
    """Llamado automáticamente al completar una venta."""
    return registrar_movimiento(producto_id, 'venta', -cantidad, 'Venta registrada')


def get_movimientos_producto(producto_id: int, limit: int = 50) -> list:
    """Historial de movimientos de un producto específico."""
    query = """
        SELECT m.id, m.tipo, m.cantidad, m.stock_anterior, m.stock_nuevo,
               m.motivo, m.fecha, u.nombre as usuario
        FROM movimientos_inventario m
        JOIN usuarios u ON m.usuario_id = u.id
        WHERE m.producto_id = ?
        ORDER BY m.fecha DESC
        LIMIT ?
    """
    return [dict(r) for r in db.fetch_all(query, (producto_id, limit))]


def get_todos_movimientos(limit: int = 200) -> list:
    """Historial completo de movimientos de todos los productos."""
    query = """
        SELECT m.id, p.nombre as producto, m.tipo, m.cantidad,
               m.stock_anterior, m.stock_nuevo, m.motivo, m.fecha,
               u.nombre as usuario
        FROM movimientos_inventario m
        JOIN productos p ON m.producto_id = p.id
        JOIN usuarios u ON m.usuario_id = u.id
        ORDER BY m.fecha DESC
        LIMIT ?
    """
    return [dict(r) for r in db.fetch_all(query, (limit,))]


def get_productos_stock_bajo() -> list:
    """Productos cuyo stock está por debajo o igual al mínimo configurado (stock_minimo=5)."""
    query = """
        SELECT p.id, p.nombre, p.stock, c.nombre as categoria
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.activo = 1 AND p.stock <= 5
        ORDER BY p.stock ASC
    """
    return [dict(r) for r in db.fetch_all(query)]


# ──────────────────────────────────────────────────────────────────────────────
# INSUMOS (materias primas)
# ──────────────────────────────────────────────────────────────────────────────

class Insumo:
    def __init__(self, id: int, nombre: str, unidad: str,
                 stock_actual: float = 0, stock_minimo: float = 0,
                 costo_unitario: float = 0, descripcion: str = None,
                 categoria: str = None, activo: bool = True,
                 fecha_creacion: str = None, **kwargs):
        self.id            = id
        self.nombre        = nombre
        self.unidad        = unidad
        self.stock_actual  = stock_actual
        self.stock_minimo  = stock_minimo
        self.costo_unitario = costo_unitario
        self.descripcion   = descripcion
        self.categoria     = categoria
        self.activo        = activo
        self.fecha_creacion = fecha_creacion

    @property
    def stock_bajo(self) -> bool:
        return self.stock_actual <= self.stock_minimo

    # ── READ ──────────────────────────────────────────────────────────

    @staticmethod
    def get_all(activo_only: bool = True) -> List['Insumo']:
        where = "WHERE activo = 1" if activo_only else ""
        rows = db.fetch_all(f"SELECT * FROM insumos {where} ORDER BY nombre")
        return [Insumo(**dict(r)) for r in rows]

    @staticmethod
    def get_by_id(insumo_id: int) -> Optional['Insumo']:
        row = db.fetch_one("SELECT * FROM insumos WHERE id = ?", (insumo_id,))
        return Insumo(**dict(row)) if row else None

    @staticmethod
    def get_stock_bajo() -> List['Insumo']:
        rows = db.fetch_all(
            "SELECT * FROM insumos WHERE activo=1 AND stock_actual <= stock_minimo ORDER BY nombre"
        )
        return [Insumo(**dict(r)) for r in rows]

    # ── WRITE ─────────────────────────────────────────────────────────

    @staticmethod
    def create(nombre: str, unidad: str, stock_minimo: float = 0,
               costo_unitario: float = 0, descripcion: str = None,
               categoria: str = None) -> int:
        return db.execute_query(
            """INSERT INTO insumos (nombre, unidad, stock_minimo, costo_unitario,
               descripcion, categoria) VALUES (?, ?, ?, ?, ?, ?)""",
            (nombre, unidad, stock_minimo, costo_unitario, descripcion, categoria)
        )

    @staticmethod
    def update(insumo_id: int, **kwargs) -> bool:
        allowed = ['nombre', 'unidad', 'stock_minimo', 'costo_unitario',
                   'descripcion', 'categoria', 'activo']
        sets, params = [], []
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return False
        params.append(insumo_id)
        db.execute_query(f"UPDATE insumos SET {', '.join(sets)} WHERE id = ?", tuple(params))
        return True

    def registrar_movimiento_insumo(self, tipo: str, cantidad: float,
                                     motivo: str = None) -> bool:
        """
        Registra un movimiento de insumo.
        tipo: 'entrada' | 'consumo' | 'ajuste' | 'merma'
        cantidad: positivo para entradas, negativo para salidas.
        """
        usuario = get_current_user()
        if not usuario:
            return False

        stock_anterior = self.stock_actual
        stock_nuevo    = round(stock_anterior + cantidad, 3)

        if stock_nuevo < 0:
            return False

        try:
            db.execute_query(
                "UPDATE insumos SET stock_actual = ? WHERE id = ?",
                (stock_nuevo, self.id)
            )
            db.execute_query(
                """INSERT INTO movimientos_insumos
                   (insumo_id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, usuario_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (self.id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, usuario.id)
            )
            self.stock_actual = stock_nuevo
            return True
        except Exception as e:
            print(f"Error en movimiento de insumo: {e}")
            return False

    def get_movimientos(self, limit: int = 50) -> list:
        query = """
            SELECT m.id, m.tipo, m.cantidad, m.stock_anterior, m.stock_nuevo,
                   m.motivo, m.fecha, u.nombre as usuario
            FROM movimientos_insumos m
            JOIN usuarios u ON m.usuario_id = u.id
            WHERE m.insumo_id = ?
            ORDER BY m.fecha DESC LIMIT ?
        """
        return [dict(r) for r in db.fetch_all(query, (self.id, limit))]


def get_todos_movimientos_insumos(limit: int = 200) -> list:
    query = """
        SELECT m.id, i.nombre as insumo, i.unidad, m.tipo, m.cantidad,
               m.stock_anterior, m.stock_nuevo, m.motivo, m.fecha,
               u.nombre as usuario
        FROM movimientos_insumos m
        JOIN insumos i ON m.insumo_id = i.id
        JOIN usuarios u ON m.usuario_id = u.id
        ORDER BY m.fecha DESC LIMIT ?
    """
    return [dict(r) for r in db.fetch_all(query, (limit,))]
