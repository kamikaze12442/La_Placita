"""
models/inventory.py
Insumos, Recetas y movimientos de inventario.
El descuento automático al vender se hace desde Sale.create()
llamando a descontar_insumos_por_venta().
"""

from datetime import datetime
from typing import Optional, List
from database.connection import db


def _rget(row, key, default=None):
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# Insumo
# ─────────────────────────────────────────────────────────────────────────────

class Insumo:
    def __init__(self, id=None, nombre="", categoria=None, unidad="unidades",
                 stock_actual=0.0, stock_minimo=0.0, costo_unitario=0.0,
                 activo=1, descripcion=None, fecha_creacion=None,
                 envase_tipo=None, envase_cantidad=1.0):
        self.id              = id
        self.nombre          = nombre
        self.categoria       = categoria
        self.unidad          = unidad
        self.stock_actual    = float(stock_actual or 0)
        self.stock_minimo    = float(stock_minimo or 0)
        self.costo_unitario  = float(costo_unitario or 0)
        self.activo          = activo
        self.descripcion     = descripcion
        self.fecha_creacion  = fecha_creacion
        self.envase_tipo     = envase_tipo          # 'caja','bolsa','paquete','balde' o None
        self.envase_cantidad = float(envase_cantidad or 1)  # unidades por envase

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo

    @property
    def tiene_envase(self):
        return bool(self.envase_tipo)

    @property
    def envase_label(self):
        """Ej: '1 caja = 24 huevos'"""
        UNIDADES_A_UNIDADES = {"Paquete", "Caja", "Bolsa"}
        unidad = self.unidad
        unidad_txt = "unidades" if unidad in UNIDADES_A_UNIDADES else unidad
        if not self.tiene_envase:
            return None
        n = int(self.envase_cantidad) if self.envase_cantidad == int(self.envase_cantidad) else self.envase_cantidad
        return f"1 {self.envase_tipo} = {n} {unidad_txt}"

    # ── CRUD ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _from_row(row) -> "Insumo":
        return Insumo(
            id=row["id"], nombre=row["nombre"], categoria=_rget(row, "categoria", None),
            unidad=row["unidad"], stock_actual=row["stock_actual"],
            stock_minimo=row["stock_minimo"], costo_unitario=row["costo_unitario"],
            activo=_rget(row, "activo", 1), descripcion=_rget(row, "descripcion", None),
            fecha_creacion=_rget(row, "fecha_creacion", None),
            envase_tipo=_rget(row, "envase_tipo", None),
            envase_cantidad=_rget(row, "envase_cantidad", 1.0),
        )

    @staticmethod
    def get_all(solo_activos=True) -> List["Insumo"]:
        q = "SELECT * FROM insumos"
        if solo_activos:
            q += " WHERE activo = 1"
        q += " ORDER BY nombre"
        rows = db.fetch_all(q)
        return [Insumo._from_row(r) for r in rows]

    @staticmethod
    def get_by_id(insumo_id: int) -> Optional["Insumo"]:
        row = db.fetch_one("SELECT * FROM insumos WHERE id = ?", (insumo_id,))
        return Insumo._from_row(row) if row else None

    @staticmethod
    def get_stock_bajo() -> List["Insumo"]:
        rows = db.fetch_all(
            "SELECT * FROM insumos WHERE activo=1 AND stock_actual <= stock_minimo "
            "ORDER BY nombre"
        )
        return [Insumo._from_row(r) for r in rows]

    @staticmethod
    def create(nombre, unidad, stock_minimo=0, costo_unitario=0,
               categoria=None, descripcion=None, stock_actual=0,
               envase_tipo=None, envase_cantidad=1.0) -> Optional[int]:
        return db.execute_query(
            """INSERT INTO insumos
               (nombre, categoria, unidad, stock_actual, stock_minimo, costo_unitario,
                descripcion, envase_tipo, envase_cantidad)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (nombre, categoria, unidad, stock_actual, stock_minimo, costo_unitario,
             descripcion, envase_tipo, float(envase_cantidad or 1))
        )

    @staticmethod
    def update(insumo_id, **kwargs) -> bool:
        campos = ["nombre", "categoria", "unidad", "stock_minimo",
                  "costo_unitario", "descripcion", "activo",
                  "envase_tipo", "envase_cantidad"]
        sets, vals = [], []
        for c in campos:
            if c in kwargs:
                sets.append(f"{c} = ?")
                vals.append(kwargs[c])
        if not sets:
            return False
        vals.append(insumo_id)
        db.execute_query(f"UPDATE insumos SET {', '.join(sets)} WHERE id = ?", tuple(vals))
        return True

    @staticmethod
    def delete(insumo_id) -> bool:
        """Desactivar (soft-delete) para preservar historial."""
        db.execute_query("UPDATE insumos SET activo=0 WHERE id=?", (insumo_id,))
        return True

    # ── Movimientos ───────────────────────────────────────────────────────────

    def registrar_movimiento(self, tipo: str, delta: float,
                              motivo: str = None, usuario_id: int = None,
                              venta_id: int = None) -> bool:
        """
        delta positivo = entrada, negativo = salida.
        Stock no puede quedar menor a 0.
        """
        try:
            stock_ant = self.stock_actual
            stock_nvo = max(stock_ant + delta, 0.0)
            db.execute_query(
                "UPDATE insumos SET stock_actual = ? WHERE id = ?",
                (stock_nvo, self.id)
            )
            db.execute_query(
                """INSERT INTO movimientos_insumos
                   (insumo_id, tipo, cantidad, stock_anterior, stock_nuevo,
                    motivo, venta_id, usuario_id, fecha)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (self.id, tipo, delta, stock_ant, stock_nvo,
                 motivo, venta_id, usuario_id,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            self.stock_actual = stock_nvo
            return True
        except Exception as e:
            print(f"✗ Error movimiento insumo {self.id}: {e}")
            return False

    # Alias para compatibilidad con código antiguo
    def registrar_movimiento_insumo(self, tipo, delta, motivo=None):
        return self.registrar_movimiento(tipo, delta, motivo)


# ─────────────────────────────────────────────────────────────────────────────
# Receta
# ─────────────────────────────────────────────────────────────────────────────

class RecetaItem:
    def __init__(self, id=None, producto_id=None, insumo_id=None,
                 cantidad=1.0, insumo_nombre=None, insumo_unidad=None):
        self.id            = id
        self.producto_id   = producto_id
        self.insumo_id     = insumo_id
        self.cantidad      = float(cantidad)
        self.insumo_nombre = insumo_nombre
        self.insumo_unidad = insumo_unidad


class Receta:

    @staticmethod
    def get_por_producto(producto_id: int) -> List[RecetaItem]:
        rows = db.fetch_all(
            """SELECT r.*, i.nombre as insumo_nombre, i.unidad as insumo_unidad
               FROM recetas r
               JOIN insumos i ON r.insumo_id = i.id
               WHERE r.producto_id = ?
               ORDER BY i.nombre""",
            (producto_id,)
        )
        return [
            RecetaItem(
                id=r["id"], producto_id=r["producto_id"],
                insumo_id=r["insumo_id"], cantidad=r["cantidad"],
                insumo_nombre=r["insumo_nombre"], insumo_unidad=r["insumo_unidad"]
            )
            for r in rows
        ]

    @staticmethod
    def set_receta(producto_id: int, items: list) -> bool:
        """
        items = [{"insumo_id": int, "cantidad": float}, ...]
        Reemplaza toda la receta del producto.
        """
        try:
            db.execute_query("DELETE FROM recetas WHERE producto_id = ?", (producto_id,))
            for it in items:
                db.execute_query(
                    "INSERT OR REPLACE INTO recetas (producto_id, insumo_id, cantidad) "
                    "VALUES (?,?,?)",
                    (producto_id, it["insumo_id"], it["cantidad"])
                )
            return True
        except Exception as e:
            print(f"✗ Error guardando receta: {e}")
            return False

    @staticmethod
    def tiene_receta(producto_id: int) -> bool:
        row = db.fetch_one(
            "SELECT COUNT(*) as n FROM recetas WHERE producto_id=?", (producto_id,)
        )
        return (row["n"] if row else 0) > 0

    @staticmethod
    def productos_con_receta() -> set:
        """Devuelve set de producto_ids que tienen receta."""
        rows = db.fetch_all("SELECT DISTINCT producto_id FROM recetas")
        return {r["producto_id"] for r in rows}


# ─────────────────────────────────────────────────────────────────────────────
# Descuento automático al vender
# ─────────────────────────────────────────────────────────────────────────────

def descontar_insumos_por_venta(items_venta: list, venta_id: int,
                                 usuario_id: int) -> list:
    """
    items_venta = [{"producto_id": int, "cantidad": int}, ...]
    Descuenta insumos según recetas. Devuelve lista de alertas
    (insumos que quedaron con stock <= 0).
    """
    alertas = []
    for item in items_venta:
        receta = Receta.get_por_producto(item["producto_id"])
        for ri in receta:
            insumo = Insumo.get_by_id(ri.insumo_id)
            if not insumo:
                continue
            delta = -(ri.cantidad * item["cantidad"])
            insumo.registrar_movimiento(
                tipo="venta", delta=delta,
                motivo=f"Venta #{venta_id}",
                usuario_id=usuario_id, venta_id=venta_id
            )
            if insumo.stock_actual <= 0:
                alertas.append(
                    f"{insumo.nombre} ({insumo.stock_actual:.2f} {insumo.unidad})"
                )
    return alertas


# ─────────────────────────────────────────────────────────────────────────────
# Historial
# ─────────────────────────────────────────────────────────────────────────────

def get_todos_movimientos_insumos(desde=None, hasta=None,
                                   usuario_id=None, limit=500) -> list:
    q = """
        SELECT mi.*, i.nombre as insumo, i.unidad,
               u.nombre as usuario
        FROM movimientos_insumos mi
        JOIN insumos i  ON mi.insumo_id  = i.id
        LEFT JOIN usuarios u ON mi.usuario_id = u.id
        WHERE 1=1
    """
    params = []
    if desde:
        q += " AND mi.fecha >= ?"; params.append(desde)
    if hasta:
        q += " AND mi.fecha <= ?"; params.append(hasta)
    if usuario_id:
        q += " AND mi.usuario_id = ?"; params.append(usuario_id)
    q += f" ORDER BY mi.fecha DESC LIMIT {limit}"
    return [dict(r) for r in db.fetch_all(q, tuple(params) if params else None)]


# ─────────────────────────────────────────────────────────────────────────────
# Compatibilidad con código antiguo
# ─────────────────────────────────────────────────────────────────────────────

def registrar_movimiento(producto_id, tipo, delta, motivo=None, usuario_id=None):
    """Movimiento de stock en tabla productos (código legado)."""
    try:
        row = db.fetch_one("SELECT stock FROM productos WHERE id=?", (producto_id,))
        if not row:
            return False
        stock_ant = row["stock"]
        stock_nvo = stock_ant + delta
        if stock_nvo < 0:
            return False
        db.execute_query("UPDATE productos SET stock=? WHERE id=?",
                         (stock_nvo, producto_id))
        db.execute_query(
            """INSERT INTO movimientos_inventario
               (producto_id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, usuario_id, fecha)
               VALUES (?,?,?,?,?,?,?,?)""",
            (producto_id, tipo, delta, stock_ant, stock_nvo, motivo, usuario_id,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        return True
    except Exception as e:
        print(f"✗ registrar_movimiento: {e}")
        return False


def get_todos_movimientos(limite=500):
    rows = db.fetch_all(
        """SELECT mi.*, p.nombre as producto, u.nombre as usuario
           FROM movimientos_inventario mi
           JOIN productos p ON mi.producto_id = p.id
           LEFT JOIN usuarios u ON mi.usuario_id = u.id
           ORDER BY mi.fecha DESC LIMIT ?""",
        (limite,)
    )
    return [dict(r) for r in rows]


def get_productos_stock_bajo():
    rows = db.fetch_all("SELECT * FROM productos WHERE stock <= 5 ORDER BY nombre")
    return [dict(r) for r in rows]