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
    def abrir(monto_inicial: float = 0) -> Optional['ArqueoCaja']:
        """
        Abre un nuevo arqueo para el usuario actual.
        Solo se permite uno abierto por usuario a la vez.
        """
        usuario = get_current_user()
        if not usuario:
            return None

        # Verificar que no tenga ya uno abierto
        existente = ArqueoCaja.get_abierto_por_usuario(usuario.id)
        if existente:
            return existente  # Retorna el existente sin crear uno nuevo

        now = datetime.now().isoformat()
        arqueo_id = db.execute_query(
            """INSERT INTO arqueos_caja (usuario_id, fecha_inicio, estado, monto_inicial)
               VALUES (?, ?, 'abierto', ?)""",
            (usuario.id, now, monto_inicial)
        )
        return ArqueoCaja.get_by_id(arqueo_id)

    @staticmethod
    def calcular_ventas_sistema(usuario_id: int, fecha_inicio: str) -> dict:
        """
        Calcula las ventas del sistema desde la apertura de caja
        hasta ahora, filtradas por el cajero que abrió la caja.
        """
        query = """
            SELECT
                COALESCE(SUM(CASE WHEN metodo_pago='efectivo' THEN total ELSE 0 END), 0) as efectivo,
                COALESCE(SUM(CASE WHEN metodo_pago='qr'       THEN total ELSE 0 END), 0) as qr,
                COALESCE(SUM(CASE WHEN metodo_pago='tarjeta'  THEN total ELSE 0 END), 0) as tarjeta,
                COALESCE(SUM(total), 0) as total,
                COUNT(*) as transacciones
            FROM ventas
            WHERE usuario_id = ?
              AND estado = 'completada'
              AND fecha_venta >= ?
        """
        row = db.fetch_one(query, (usuario_id, fecha_inicio))
        if row:
            return {
                'efectivo':      float(row['efectivo']),
                'qr':            float(row['qr']),
                'tarjeta':       float(row['tarjeta']),
                'total':         float(row['total']),
                'transacciones': int(row['transacciones']),
            }
        return {'efectivo': 0, 'qr': 0, 'tarjeta': 0, 'total': 0, 'transacciones': 0}

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

        dif_ef  = round(conteo_efectivo - ventas['efectivo'], 2)
        dif_qr  = round(conteo_qr       - ventas['qr'],       2)
        dif_tar = round(conteo_tarjeta  - ventas['tarjeta'],  2)
        dif_tot = round(dif_ef + dif_qr + dif_tar,            2)

        now = datetime.now().isoformat()
        db.execute_query(
            """UPDATE arqueos_caja SET
                estado='cerrado', fecha_cierre=?,
                sistema_efectivo=?, sistema_qr=?, sistema_tarjeta=?, sistema_total=?,
                total_transacciones=?,
                conteo_efectivo=?, conteo_qr=?, conteo_tarjeta=?,
                diferencia_efectivo=?, diferencia_qr=?, diferencia_tarjeta=?, diferencia_total=?,
                denominaciones=?
               WHERE id=?""",
            (now,
             ventas['efectivo'], ventas['qr'], ventas['tarjeta'], ventas['total'],
             ventas['transacciones'],
             conteo_efectivo, conteo_qr, conteo_tarjeta,
             dif_ef, dif_qr, dif_tar, dif_tot,
             json.dumps(denominaciones),
             arqueo_id)
        )
        return ArqueoCaja.get_by_id(arqueo_id)
