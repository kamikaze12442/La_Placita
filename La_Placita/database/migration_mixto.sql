-- ============================================================
-- MIGRACIÓN: Agregar método de pago 'mixto'
-- SQLite no soporta ALTER COLUMN, se recrea la tabla.
-- Ejecutar con: python run_migration_mixto.py
-- ============================================================

-- Paso 1: Renombrar tabla original
ALTER TABLE ventas RENAME TO ventas_old;

-- Paso 2: Crear tabla nueva con constraint actualizado
CREATE TABLE ventas (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_factura   VARCHAR(20) UNIQUE NOT NULL,
    usuario_id       INTEGER NOT NULL,
    cliente          VARCHAR(100),
    subtotal         DECIMAL(10,2) NOT NULL,
    descuento        DECIMAL(10,2) DEFAULT 0,
    total            DECIMAL(10,2) NOT NULL,
    metodo_pago      VARCHAR(20) NOT NULL
                     CHECK(metodo_pago IN ('efectivo','qr','tarjeta','mixto')),
    estado           VARCHAR(20) DEFAULT 'completada',
    fecha_venta      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Paso 3: Copiar datos
INSERT INTO ventas
SELECT id, numero_factura, usuario_id, cliente,
       subtotal, descuento, total, metodo_pago,
       estado, fecha_venta
FROM ventas_old;

-- Paso 4: Eliminar tabla vieja
DROP TABLE ventas_old;

-- Paso 5: Recrear índices
CREATE INDEX IF NOT EXISTS idx_ventas_fecha    ON ventas(fecha_venta);
CREATE INDEX IF NOT EXISTS idx_ventas_usuario  ON ventas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_ventas_estado   ON ventas(estado);
