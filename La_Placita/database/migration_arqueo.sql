-- ============================================================
-- MIGRACIÓN: Tabla de Arqueo de Caja
-- Ejecutar con: python run_migration_arqueo.py
-- ============================================================

CREATE TABLE IF NOT EXISTS arqueos_caja (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    fecha_inicio TIMESTAMP NOT NULL,
    fecha_cierre TIMESTAMP,
    estado VARCHAR(20) DEFAULT 'abierto' CHECK(estado IN ('abierto', 'cerrado')),

    -- Monto inicial declarado al abrir caja
    monto_inicial DECIMAL(10,2) DEFAULT 0,

    -- Ventas del sistema por método (calculado automáticamente)
    sistema_efectivo DECIMAL(10,2) DEFAULT 0,
    sistema_qr       DECIMAL(10,2) DEFAULT 0,
    sistema_tarjeta  DECIMAL(10,2) DEFAULT 0,
    sistema_total    DECIMAL(10,2) DEFAULT 0,
    total_transacciones INTEGER DEFAULT 0,

    -- Conteo físico ingresado por el cajero al cerrar
    conteo_efectivo  DECIMAL(10,2) DEFAULT 0,
    conteo_qr        DECIMAL(10,2) DEFAULT 0,
    conteo_tarjeta   DECIMAL(10,2) DEFAULT 0,

    -- Diferencia calculada (conteo - sistema)
    diferencia_efectivo DECIMAL(10,2) DEFAULT 0,
    diferencia_qr       DECIMAL(10,2) DEFAULT 0,
    diferencia_tarjeta  DECIMAL(10,2) DEFAULT 0,
    diferencia_total    DECIMAL(10,2) DEFAULT 0,

    -- Denominaciones de billetes/monedas (JSON)
    denominaciones TEXT DEFAULT '{}',

    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_arqueos_usuario ON arqueos_caja(usuario_id);
CREATE INDEX IF NOT EXISTS idx_arqueos_fecha   ON arqueos_caja(fecha_inicio);
CREATE INDEX IF NOT EXISTS idx_arqueos_estado  ON arqueos_caja(estado);
