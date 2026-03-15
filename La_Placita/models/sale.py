"""
Sale Model — La Placita POS
Al crear una venta, descuenta automáticamente los insumos según las recetas.
Productos sin receta se venden normalmente sin descontar nada.
"""

def _rget(row, key, default=None):
    """Acceso seguro a sqlite3.Row: devuelve default si la columna no existe."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return default

from typing import Optional, List
from datetime import datetime, date
from database.connection import db
import traceback


class SaleDetail:
    def __init__(self, id=None, venta_id=None, producto_id=None, cantidad=1,
                 precio_unitario=0.0, subtotal=0.0, producto_nombre=None):
        self.id               = id
        self.venta_id         = venta_id
        self.producto_id      = producto_id
        self.cantidad         = cantidad
        self.precio_unitario  = precio_unitario
        self.subtotal         = subtotal
        self.producto_nombre  = producto_nombre

    def calculate_subtotal(self):
        self.subtotal = self.cantidad * self.precio_unitario
        return self.subtotal


class Sale:

    def __init__(self, id=None, numero_factura=None, usuario_id=None,
                 cliente="Cliente General", subtotal=0.0, descuento=0.0,
                 total=0.0, metodo_pago="efectivo", estado="completada",
                 fecha_venta=None, items=None,
                 monto_efectivo=0.0, monto_qr=0.0, tipo_pedido="mesa"):
        self.id               = id
        self.numero_factura   = numero_factura
        self.usuario_id       = usuario_id
        self.cliente          = cliente
        self.subtotal         = subtotal
        self.descuento        = descuento
        self.total            = total
        self.metodo_pago      = metodo_pago
        self.estado           = estado
        self.fecha_venta      = fecha_venta or datetime.now().isoformat()
        self.items            = items or []
        self.monto_efectivo   = monto_efectivo
        self.monto_qr         = monto_qr
        self.tipo_pedido      = tipo_pedido

    # ──────────────────────────────────────────────────────────────────────────
    # Número de factura
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def generate_invoice_number() -> str:
        date_part = datetime.now().strftime("%Y%m%d")
        result = db.fetch_one(
            "SELECT numero_factura FROM ventas WHERE numero_factura LIKE ? "
            "ORDER BY numero_factura DESC LIMIT 1",
            (f"FACT-{date_part}-%",)
        )
        new_number = (int(result["numero_factura"].split("-")[-1]) + 1) if result else 1
        return f"FACT-{date_part}-{new_number:04d}"

    # ──────────────────────────────────────────────────────────────────────────
    # Crear venta + descuento automático de insumos
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def create(usuario_id: int, items: List[SaleDetail],
               cliente: str = "Cliente General", metodo_pago: str = "efectivo",
               descuento: float = 0.0, monto_efectivo: float = 0.0,
               monto_qr: float = 0.0, tipo_pedido: str = "mesa") -> Optional[int]:
        """
        Crea la venta, registra detalles y descuenta insumos automáticamente.
        Devuelve (sale_id, alertas_stock). sale_id=None si falla.
        """
        try:
            numero_factura = Sale.generate_invoice_number()
            subtotal = sum(i.subtotal for i in items)
            total    = subtotal - descuento
            ahora    = datetime.now().isoformat()

            sale_id = db.execute_query(
                """INSERT INTO ventas
                   (numero_factura, usuario_id, cliente, subtotal, descuento,
                    total, metodo_pago, estado, fecha_venta,
                    monto_efectivo, monto_qr, tipo_pedido)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (numero_factura, usuario_id, cliente, subtotal, descuento,
                 total, metodo_pago, "completada", ahora,
                 monto_efectivo, monto_qr, tipo_pedido)
            )

            for item in items:
                db.execute_query(
                    """INSERT INTO detalle_ventas
                       (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                       VALUES (?,?,?,?,?)""",
                    (sale_id, item.producto_id, item.cantidad,
                     item.precio_unitario, item.subtotal)
                )

            # ── Descuento automático de insumos ──────────────────────────────
            alertas = Sale._descontar_insumos(items, sale_id, usuario_id)
            if alertas:
                print(f"⚠️  Stock bajo después de venta #{sale_id}: {', '.join(alertas)}")

            print(f"✓ Venta {numero_factura} — Bs {total:.2f}")
            return sale_id, alertas

        except Exception as e:
            print(f"✗ Error creando venta: {e}")
            traceback.print_exc()
            return None, []

    @staticmethod
    def _descontar_insumos(items: List[SaleDetail], venta_id: int,
                            usuario_id: int) -> list:
        """
        Por cada ítem de la venta busca su receta y descuenta los insumos.
        Productos sin receta se ignoran silenciosamente.
        Devuelve lista de nombres de insumos que quedaron con stock <= 0.
        """
        alertas = []
        ahora   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for item in items:
            receta_rows = db.fetch_all(
                """SELECT r.insumo_id, r.cantidad,
                          i.nombre, i.stock_actual, i.unidad
                   FROM recetas r
                   JOIN insumos i ON r.insumo_id = i.id
                   WHERE r.producto_id = ?""",
                (item.producto_id,)
            )
            for ri in receta_rows:
                consumo     = ri["cantidad"] * item.cantidad
                stock_ant   = ri["stock_actual"]
                stock_nuevo = stock_ant - consumo

                # Stock mínimo = 0 (no permitir negativos)
                stock_nuevo = max(stock_nuevo, 0.0)

                # Actualizar stock
                db.execute_query(
                    "UPDATE insumos SET stock_actual = ? WHERE id = ?",
                    (stock_nuevo, ri["insumo_id"])
                )
                # Registrar movimiento
                db.execute_query(
                    """INSERT INTO movimientos_insumos
                       (insumo_id, tipo, cantidad, stock_anterior, stock_nuevo,
                        motivo, venta_id, usuario_id, fecha)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (ri["insumo_id"], "consumo", consumo, stock_ant, stock_nuevo,
                     f"Venta #{venta_id}", venta_id, usuario_id, ahora)
                )
                if stock_ant > 0 and stock_nuevo == 0:
                    alertas.append(f"{ri['nombre']} (agotado)")
                elif stock_nuevo == 0 and stock_ant == 0:
                    pass  # ya estaba en 0, no alertar de nuevo

        return alertas

    # ──────────────────────────────────────────────────────────────────────────
    # Consultas
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_by_id(sale_id: int) -> Optional["Sale"]:
        sale_row = db.fetch_one("SELECT * FROM ventas WHERE id = ?", (sale_id,))
        if not sale_row:
            return None
        details_rows = db.fetch_all(
            """SELECT d.*, p.nombre as producto_nombre
               FROM detalle_ventas d
               JOIN productos p ON d.producto_id = p.id
               WHERE d.venta_id = ?""",
            (sale_id,)
        )
        items = [
            SaleDetail(id=r["id"], venta_id=r["venta_id"],
                       producto_id=r["producto_id"], cantidad=r["cantidad"],
                       precio_unitario=r["precio_unitario"], subtotal=r["subtotal"],
                       producto_nombre=r["producto_nombre"])
            for r in details_rows
        ]
        return Sale(
            id=sale_row["id"], numero_factura=sale_row["numero_factura"],
            usuario_id=sale_row["usuario_id"], cliente=sale_row["cliente"],
            subtotal=sale_row["subtotal"], descuento=sale_row["descuento"],
            total=sale_row["total"], metodo_pago=sale_row["metodo_pago"],
            estado=sale_row["estado"], fecha_venta=sale_row["fecha_venta"],
            monto_efectivo=_rget(sale_row, "monto_efectivo", 0),
            monto_qr=_rget(sale_row, "monto_qr", 0),
            tipo_pedido=_rget(sale_row, "tipo_pedido", "mesa"),
            items=items,
        )

    @staticmethod
    def get_all(limit=100, offset=0,
                fecha_desde=None, fecha_hasta=None) -> List["Sale"]:
        q      = "SELECT * FROM ventas WHERE 1=1"
        params = []
        if fecha_desde:
            q += " AND DATE(fecha_venta) >= ?"; params.append(fecha_desde)
        if fecha_hasta:
            q += " AND DATE(fecha_venta) <= ?"; params.append(fecha_hasta)
        q += " ORDER BY fecha_venta DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = db.fetch_all(q, tuple(params))
        return [
            Sale(id=r["id"], numero_factura=r["numero_factura"],
                 usuario_id=r["usuario_id"], cliente=r["cliente"],
                 subtotal=r["subtotal"], descuento=r["descuento"],
                 total=r["total"], metodo_pago=r["metodo_pago"],
                 estado=r["estado"], fecha_venta=r["fecha_venta"],
                 monto_efectivo=_rget(r, "monto_efectivo", 0),
                 monto_qr=_rget(r, "monto_qr", 0),
                 tipo_pedido=_rget(r, "tipo_pedido", "mesa"))
            for r in rows
        ]

    @staticmethod
    def get_sales_by_date(fecha: date) -> List["Sale"]:
        s = fecha.isoformat()
        return Sale.get_all(fecha_desde=s, fecha_hasta=s)

    @staticmethod
    def get_sales_summary(fecha_desde=None, fecha_hasta=None) -> dict:
        try:
            q = """SELECT COUNT(*) as total_ventas, SUM(total) as total_ingresos,
                          SUM(descuento) as total_descuentos, AVG(total) as promedio_venta
                   FROM ventas WHERE 1=1"""
            params = []
            if fecha_desde:
                q += " AND DATE(fecha_venta) >= ?"; params.append(fecha_desde)
            if fecha_hasta:
                q += " AND DATE(fecha_venta) <= ?"; params.append(fecha_hasta)
            r = db.fetch_one(q, tuple(params) if params else None)
            return {
                "total_ventas":      r["total_ventas"]      or 0,
                "total_ingresos":    r["total_ingresos"]    or 0,
                "total_descuentos":  r["total_descuentos"]  or 0,
                "promedio_venta":    r["promedio_venta"]    or 0,
            }
        except Exception as e:
            print(f"✗ get_sales_summary: {e}")
            return {"total_ventas": 0, "total_ingresos": 0,
                    "total_descuentos": 0, "promedio_venta": 0}

    @staticmethod
    def get_top_products(limit=10, fecha_desde=None, fecha_hasta=None) -> list:
        try:
            q = """SELECT p.nombre, SUM(d.cantidad) as total_vendido,
                          SUM(d.subtotal) as total_ingresos,
                          COUNT(DISTINCT d.venta_id) as num_ventas
                   FROM detalle_ventas d
                   JOIN productos p ON d.producto_id = p.id
                   JOIN ventas v ON d.venta_id = v.id
                   WHERE 1=1"""
            params = []
            if fecha_desde:
                q += " AND DATE(v.fecha_venta) >= ?"; params.append(fecha_desde)
            if fecha_hasta:
                q += " AND DATE(v.fecha_venta) <= ?"; params.append(fecha_hasta)
            q += " GROUP BY p.id, p.nombre ORDER BY total_vendido DESC LIMIT ?"
            params.append(limit)
            rows = db.fetch_all(q, tuple(params))
            return [{"nombre": r["nombre"], "total_vendido": r["total_vendido"],
                     "total_ingresos": r["total_ingresos"], "num_ventas": r["num_ventas"]}
                    for r in rows]
        except Exception as e:
            print(f"✗ get_top_products: {e}")
            return []

    @staticmethod
    def delete(sale_id: int) -> bool:
        try:
            db.execute_query("UPDATE ventas SET estado='anulada' WHERE id=?", (sale_id,))
            return True
        except Exception as e:
            print(f"✗ delete sale: {e}"); return False

    def __repr__(self):
        return f"<Sale {self.numero_factura}: Bs {self.total:.2f}>"