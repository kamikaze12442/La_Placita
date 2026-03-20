"""
Arqueo de Caja Model
Gestión de apertura y cierre de caja por cajero/admin,
con comparación sistema vs conteo físico.
"""

import json
from typing import Optional, List
from datetime import datetime
from database.connection import db
from models.user import get_current_user


class ArqueoCaja:

    def __init__(self, id: int, usuario_id: int, fecha_inicio: str,
                 estado: str = 'abierto', monto_inicial: float = 0,
                 fecha_cierre: str = None,
                 sistema_efectivo: float = 0, sistema_qr: float = 0,
                 sistema_tarjeta: float = 0, sistema_total: float = 0,
                 total_transacciones: int = 0,
                 conteo_efectivo: float = 0, conteo_qr: float = 0,
                 conteo_tarjeta: float = 0,
                 diferencia_efectivo: float = 0, diferencia_qr: float = 0,
                 diferencia_tarjeta: float = 0, diferencia_total: float = 0,
                 denominaciones: str = '{}', **kwargs):
        self.id                  = id
        self.usuario_id          = usuario_id
        self.fecha_inicio        = fecha_inicio
        self.fecha_cierre        = fecha_cierre
        self.estado              = estado
        self.monto_inicial       = monto_inicial
        self.sistema_efectivo    = sistema_efectivo
        self.sistema_qr          = sistema_qr
        self.sistema_tarjeta     = sistema_tarjeta
        self.sistema_total       = sistema_total
        self.total_transacciones = total_transacciones
        self.conteo_efectivo     = conteo_efectivo
        self.conteo_qr           = conteo_qr
        self.conteo_tarjeta      = conteo_tarjeta
        self.diferencia_efectivo = diferencia_efectivo
        self.diferencia_qr       = diferencia_qr
        self.diferencia_tarjeta  = diferencia_tarjeta
        self.diferencia_total    = diferencia_total
        self.denominaciones      = json.loads(denominaciones) if isinstance(denominaciones, str) else denominaciones

    # ── READ ──────────────────────────────────────────────────────────

    @staticmethod
    def get_abierto_por_usuario(usuario_id: int) -> Optional['ArqueoCaja']:
        """Retorna el arqueo abierto del usuario, si existe."""
        row = db.fetch_one(
            "SELECT * FROM arqueos_caja WHERE usuario_id=? AND estado='abierto' ORDER BY fecha_inicio DESC LIMIT 1",
            (usuario_id,)
        )
        return ArqueoCaja(**dict(row)) if row else None

    @staticmethod
    def get_all(limit: int = 100) -> List['ArqueoCaja']:
        rows = db.fetch_all(
            "SELECT * FROM arqueos_caja ORDER BY fecha_inicio DESC LIMIT ?", (limit,)
        )
        return [ArqueoCaja(**dict(r)) for r in rows]

    @staticmethod
    def get_by_usuario(usuario_id: int, limit: int = 50) -> List['ArqueoCaja']:
        rows = db.fetch_all(
            "SELECT * FROM arqueos_caja WHERE usuario_id=? ORDER BY fecha_inicio DESC LIMIT ?",
            (usuario_id, limit)
        )
        return [ArqueoCaja(**dict(r)) for r in rows]

    @staticmethod
    def get_by_id(arqueo_id: int) -> Optional['ArqueoCaja']:
        row = db.fetch_one("SELECT * FROM arqueos_caja WHERE id=?", (arqueo_id,))
        return ArqueoCaja(**dict(row)) if row else None

    # ── WRITE ─────────────────────────────────────────────────────────

    @staticmethod
    def abrir(monto_inicial: float = 0, usuario_id: int = None) -> Optional['ArqueoCaja']:
        """
        Abre un nuevo arqueo para el usuario.
        usuario_id: pasar explícitamente para evitar problemas con
                    la variable global en el ejecutable compilado.
        Solo se permite un arqueo abierto por usuario a la vez.
        """
        # Preferir usuario_id explícito; fallback a get_current_user()
        uid = usuario_id
        if not uid:
            usuario = get_current_user()
            if not usuario:
                print("✗ ArqueoCaja.abrir: no hay usuario autenticado")
                return None
            uid = usuario.id
 
        # Verificar que no tenga ya uno abierto
        existente = ArqueoCaja.get_abierto_por_usuario(uid)
        if existente:
            return existente  # Retorna el existente sin crear uno nuevo
 
        now = datetime.now().isoformat()
        try:
            arqueo_id = db.execute_query(
                """INSERT INTO arqueos_caja (usuario_id, fecha_inicio, estado, monto_inicial)
                   VALUES (?, ?, 'abierto', ?)""",
                (uid, now, monto_inicial)
            )
            print(f"✓ Caja abierta: arqueo_id={arqueo_id}, usuario_id={uid}")
            return ArqueoCaja.get_by_id(arqueo_id)
        except Exception as e:
            print(f"✗ Error abriendo caja: {e}")
            return None

    @staticmethod
    def calcular_ventas_sistema(usuario_id: int, fecha_inicio: str) -> dict:
        """
        Calcula las ventas del sistema desde la apertura de caja.
        Las ventas mixtas se distribuyen en efectivo/QR usando
        monto_efectivo y monto_qr guardados en cada venta.
        """
        query = """
            SELECT
                -- Efectivo puro + porción efectivo de ventas mixtas
                COALESCE(SUM(
                    CASE WHEN metodo_pago = 'efectivo' THEN total
                         WHEN metodo_pago = 'mixto'   THEN COALESCE(monto_efectivo, 0)
                         ELSE 0 END
                ), 0) AS efectivo,

                -- QR puro + porción QR de ventas mixtas
                COALESCE(SUM(
                    CASE WHEN metodo_pago = 'qr'    THEN total
                         WHEN metodo_pago = 'mixto' THEN COALESCE(monto_qr, 0)
                         ELSE 0 END
                ), 0) AS qr,

                COALESCE(SUM(total), 0) AS total,
                COUNT(*)                AS transacciones
            FROM ventas
            WHERE usuario_id = ?
              AND estado     = 'completada'
              AND fecha_venta >= ?
        """
        row = db.fetch_one(query, (usuario_id, fecha_inicio))
        if row:
            return {
                'efectivo':      float(row['efectivo']),
                'qr':            float(row['qr']),
                'total':         float(row['total']),
                'transacciones': int(row['transacciones']),
            }
        return {'efectivo': 0, 'qr': 0, 'total': 0, 'transacciones': 0}

    @staticmethod
    def cerrar(arqueo_id: int, conteo_efectivo: float, conteo_qr: float,
               conteo_tarjeta: float, denominaciones: dict) -> Optional['ArqueoCaja']:
        """
        Cierra el arqueo, guarda el conteo físico y calcula las diferencias.
        """
        arqueo = ArqueoCaja.get_by_id(arqueo_id)
        if not arqueo or arqueo.estado == 'cerrado':
            return None

        # Recalcular ventas del sistema al momento del cierre
        ventas = ArqueoCaja.calcular_ventas_sistema(arqueo.usuario_id, arqueo.fecha_inicio)
        

        dif_ef  = round(conteo_efectivo - (ventas['efectivo'] + arqueo.monto_inicial), 2)
        dif_qr  = round(conteo_qr       - ventas['qr'],       2)
        dif_tot = round(dif_ef + dif_qr,                      2)

        now = datetime.now().isoformat()
        db.execute_query(
            """UPDATE arqueos_caja SET
                estado='cerrado', fecha_cierre=?,
                sistema_efectivo=?, sistema_qr=?, sistema_tarjeta=0, sistema_total=?,
                total_transacciones=?,
                conteo_efectivo=?, conteo_qr=?, conteo_tarjeta=0,
                diferencia_efectivo=?, diferencia_qr=?, diferencia_tarjeta=0, diferencia_total=?,
                denominaciones=?
               WHERE id=?""",
            (now,
             ventas['efectivo'], ventas['qr'], ventas['total'],
             ventas['transacciones'],
             conteo_efectivo, conteo_qr,
             dif_ef, dif_qr, dif_tot,
             json.dumps(denominaciones),
             arqueo_id)
        )
        return ArqueoCaja.get_by_id(arqueo_id)