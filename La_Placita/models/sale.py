"""
Sale Model
Handles sales and sale details management
"""

from typing import Optional, List, Tuple
from datetime import datetime, date
from database.connection import db
import traceback

class SaleDetail:
    """Sale detail model (items in a sale)"""
    
    def __init__(self, id: int = None, venta_id: int = None, 
                 producto_id: int = None, cantidad: int = 1,
                 precio_unitario: float = 0, subtotal: float = 0,
                 producto_nombre: str = None):
        self.id = id
        self.venta_id = venta_id
        self.producto_id = producto_id
        self.cantidad = cantidad
        self.precio_unitario = precio_unitario
        self.subtotal = subtotal
        self.producto_nombre = producto_nombre
    
    def calculate_subtotal(self):
        """Calculate subtotal"""
        self.subtotal = self.cantidad * self.precio_unitario
        return self.subtotal


class Sale:
    """Sale model"""
    
    def __init__(self, id: int = None, numero_factura: str = None,
                 usuario_id: int = None, cliente: str = "Cliente General",
                 subtotal: float = 0, descuento: float = 0, total: float = 0,
                 metodo_pago: str = "efectivo", estado: str = "completada",
                 fecha_venta: str = None, items: List[SaleDetail] = None,
                 monto_efectivo: float = 0, monto_qr: float = 0,
                 tipo_pedido: str = "mesa", **kwargs):
        self.id = id
        self.numero_factura = numero_factura
        self.usuario_id = usuario_id
        self.cliente = cliente
        self.subtotal = subtotal
        self.descuento = descuento
        self.total = total
        self.metodo_pago = metodo_pago
        self.estado = estado
        self.fecha_venta = fecha_venta or datetime.now().isoformat()
        self.items = items or []
        self.monto_efectivo = monto_efectivo
        self.monto_qr       = monto_qr
        self.tipo_pedido    = tipo_pedido
    
    @staticmethod
    def generate_invoice_number() -> str:
        """Generate unique invoice number"""
        # Format: FACT-YYYYMMDD-NNNN
        today = datetime.now()
        date_part = today.strftime("%Y%m%d")
        
        # Get last invoice of the day
        query = """
            SELECT numero_factura FROM ventas 
            WHERE numero_factura LIKE ? 
            ORDER BY numero_factura DESC LIMIT 1
        """
        pattern = f"FACT-{date_part}-%"
        result = db.fetch_one(query, (pattern,))
        
        if result:
            # Extract number and increment
            last_number = int(result['numero_factura'].split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"FACT-{date_part}-{new_number:04d}"
    
    @staticmethod
    def create(usuario_id: int, items: List[SaleDetail],
               cliente: str = "Cliente General", metodo_pago: str = "efectivo",
               descuento: float = 0,
               monto_efectivo: float = 0, monto_qr: float = 0,
               tipo_pedido: str = "mesa") -> Optional[int]:
        """Create new sale with items"""
        try:
            # Generate invoice number
            numero_factura = Sale.generate_invoice_number()

            # Calculate totals
            subtotal = sum(item.subtotal for item in items)
            total = subtotal - descuento

            # Para ventas no-mixtas, deducir los montos automáticamente
            if metodo_pago == "efectivo":
                monto_efectivo = total
                monto_qr       = 0.0
            elif metodo_pago == "qr":
                monto_efectivo = 0.0
                monto_qr       = total
            # mixto: usa los valores recibidos tal cual

            # Insert sale
            sale_query = """
                INSERT INTO ventas
                (numero_factura, usuario_id, cliente, subtotal, descuento,
                 total, metodo_pago, estado, fecha_venta, monto_efectivo, monto_qr,
                 tipo_pedido)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            sale_id = db.execute_query(
                sale_query,
                (numero_factura, usuario_id, cliente, subtotal, descuento,
                 total, metodo_pago, "completada", datetime.now().isoformat(),
                 monto_efectivo, monto_qr, tipo_pedido)
            )
            
            # Insert sale details
            detail_query = """
                INSERT INTO detalle_ventas 
                (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """
            
            for item in items:
                db.execute_query(
                    detail_query,
                    (sale_id, item.producto_id, item.cantidad, 
                     item.precio_unitario, item.subtotal)
                )
                
                # Update product stock
                db.execute_query(
                    "UPDATE productos SET stock = stock - ? WHERE id = ?",
                    (item.cantidad, item.producto_id)
                )
            
            print(f"✓ Sale created: {numero_factura} - Total: Bs {total:.2f}")
            return sale_id
        
        except Exception as e:
            print(f"✗ Error creating sale: {e}")
            traceback.print_exc()   # ← agrega esta línea
            return None
    
    @staticmethod
    def get_by_id(sale_id: int) -> Optional['Sale']:
        """Get sale by ID with details"""
        try:
            # Get sale
            sale_query = "SELECT * FROM ventas WHERE id = ?"
            sale_row = db.fetch_one(sale_query, (sale_id,))
            
            if not sale_row:
                return None
            
            # Get details
            details_query = """
                SELECT d.*, p.nombre as producto_nombre
                FROM detalle_ventas d
                JOIN productos p ON d.producto_id = p.id
                WHERE d.venta_id = ?
            """
            details_rows = db.fetch_all(details_query, (sale_id,))
            
            items = [
                SaleDetail(
                    id=row['id'],
                    venta_id=row['venta_id'],
                    producto_id=row['producto_id'],
                    cantidad=row['cantidad'],
                    precio_unitario=row['precio_unitario'],
                    subtotal=row['subtotal'],
                    producto_nombre=row['producto_nombre']
                )
                for row in details_rows
            ]
            
            return Sale(
                id=sale_row['id'],
                numero_factura=sale_row['numero_factura'],
                usuario_id=sale_row['usuario_id'],
                cliente=sale_row['cliente'],
                subtotal=sale_row['subtotal'],
                descuento=sale_row['descuento'],
                total=sale_row['total'],
                metodo_pago=sale_row['metodo_pago'],
                estado=sale_row['estado'],
                fecha_venta=sale_row['fecha_venta'],
                items=items,
                monto_efectivo=float(sale_row['monto_efectivo'] or 0),
                monto_qr=float(sale_row['monto_qr'] or 0),
                tipo_pedido=sale_row['tipo_pedido'] or 'mesa',
            )
            
        except Exception as e:
            print(f"✗ Error getting sale: {e}")
            return None
    
    @staticmethod
    def get_all(limit: int = 100, offset: int = 0, 
                fecha_desde: str = None, fecha_hasta: str = None) -> List['Sale']:
        """Get all sales with optional date filter"""
        try:
            query = "SELECT * FROM ventas WHERE 1=1"
            params = []
            
            if fecha_desde:
                query += " AND DATE(fecha_venta) >= ?"
                params.append(fecha_desde)
            
            if fecha_hasta:
                query += " AND DATE(fecha_venta) <= ?"
                params.append(fecha_hasta)
            
            query += " ORDER BY fecha_venta DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            rows = db.fetch_all(query, tuple(params))
            
            return [
                Sale(
                    id=row['id'],
                    numero_factura=row['numero_factura'],
                    usuario_id=row['usuario_id'],
                    cliente=row['cliente'],
                    subtotal=row['subtotal'],
                    descuento=row['descuento'],
                    total=row['total'],
                    metodo_pago=row['metodo_pago'],
                    estado=row['estado'],
                    fecha_venta=row['fecha_venta']
                )
                for row in rows
            ]
            
        except Exception as e:
            print(f"✗ Error getting sales: {e}")
            return []
    
    @staticmethod
    def get_sales_by_date(fecha: date) -> List['Sale']:
        """Get all sales for a specific date"""
        fecha_str = fecha.isoformat()
        return Sale.get_all(fecha_desde=fecha_str, fecha_hasta=fecha_str)
    
    @staticmethod
    def get_sales_summary(fecha_desde: str = None, fecha_hasta: str = None) -> dict:
        """Get sales summary with totals"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_ventas,
                    SUM(total) as total_ingresos,
                    SUM(descuento) as total_descuentos,
                    AVG(total) as promedio_venta
                FROM ventas
                WHERE 1=1
            """
            params = []
            
            if fecha_desde:
                query += " AND DATE(fecha_venta) >= ?"
                params.append(fecha_desde)
            
            if fecha_hasta:
                query += " AND DATE(fecha_venta) <= ?"
                params.append(fecha_hasta)
            
            result = db.fetch_one(query, tuple(params) if params else None)
            
            return {
                'total_ventas': result['total_ventas'] or 0,
                'total_ingresos': result['total_ingresos'] or 0,
                'total_descuentos': result['total_descuentos'] or 0,
                'promedio_venta': result['promedio_venta'] or 0
            }
            
        except Exception as e:
            print(f"✗ Error getting summary: {e}")
            return {
                'total_ventas': 0,
                'total_ingresos': 0,
                'total_descuentos': 0,
                'promedio_venta': 0
            }
    
    @staticmethod
    def get_top_products(limit: int = 10, fecha_desde: str = None, 
                        fecha_hasta: str = None) -> List[dict]:
        """Get top selling products"""
        try:
            query = """
                SELECT 
                    p.nombre,
                    SUM(d.cantidad) as total_vendido,
                    SUM(d.subtotal) as total_ingresos,
                    COUNT(DISTINCT d.venta_id) as num_ventas
                FROM detalle_ventas d
                JOIN productos p ON d.producto_id = p.id
                JOIN ventas v ON d.venta_id = v.id
                WHERE 1=1
            """
            params = []
            
            if fecha_desde:
                query += " AND DATE(v.fecha_venta) >= ?"
                params.append(fecha_desde)
            
            if fecha_hasta:
                query += " AND DATE(v.fecha_venta) <= ?"
                params.append(fecha_hasta)
            
            query += """
                GROUP BY p.id, p.nombre
                ORDER BY total_vendido DESC
                LIMIT ?
            """
            params.append(limit)
            
            results = db.fetch_all(query, tuple(params))
            
            return [
                {
                    'nombre': row['nombre'],
                    'total_vendido': row['total_vendido'],
                    'total_ingresos': row['total_ingresos'],
                    'num_ventas': row['num_ventas']
                }
                for row in results
            ]
            
        except Exception as e:
            print(f"✗ Error getting top products: {e}")
            return []
    
    @staticmethod
    def delete(sale_id: int) -> bool:
        """Delete sale (soft delete by changing status)"""
        try:
            db.execute_query(
                "UPDATE ventas SET estado = 'anulada' WHERE id = ?",
                (sale_id,)
            )
            return True
        except Exception as e:
            print(f"✗ Error deleting sale: {e}")
            return False
    
    def __repr__(self):
        return f"<Sale {self.numero_factura}: Bs {self.total:.2f}>"


if __name__ == '__main__':
    # Test sale model
    from models.product import Product
    
    print("Testing Sale model...")
    
    # Test invoice generation
    invoice_num = Sale.generate_invoice_number()
    print(f"✓ Generated invoice: {invoice_num}")
    
    # Get sales summary
    summary = Sale.get_sales_summary()
    print(f"\n✓ Sales Summary:")
    print(f"  Total ventas: {summary['total_ventas']}")
    print(f"  Total ingresos: Bs {summary['total_ingresos']:.2f}")
    
    # Get top products
    top = Sale.get_top_products(limit=5)
    print(f"\n✓ Top 5 Products:")
    for i, product in enumerate(top, 1):
        print(f"  {i}. {product['nombre']}: {product['total_vendido']} unidades")