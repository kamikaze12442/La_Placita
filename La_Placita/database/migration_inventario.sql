-- ============================================================
-- MIGRACIÓN: Tablas de Inventario
-- Ejecutar UNA SOLA VEZ con: python run_migration.py
-- ============================================================

-- Tabla de Insumos (materias primas)
CREATE TABLE IF NOT EXISTS insumos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    unidad VARCHAR(20) NOT NULL,         -- kg, litros, unidades, etc.
    stock_actual DECIMAL(10,3) DEFAULT 0,
    stock_minimo DECIMAL(10,3) DEFAULT 0, -- umbral de alerta
    costo_unitario DECIMAL(10,2) DEFAULT 0,
    categoria VARCHAR(50),
    activo BOOLEAN DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Movimientos de Inventario (productos terminados)
CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK(tipo IN ('entrada','venta','ajuste','merma')),
    cantidad INTEGER NOT NULL,
    stock_anterior INTEGER NOT NULL,
    stock_nuevo INTEGER NOT NULL,
    motivo TEXT,
    usuario_id INTEGER NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Tabla de Movimientos de Insumos
CREATE TABLE IF NOT EXISTS movimientos_insumos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insumo_id INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK(tipo IN ('entrada','consumo','ajuste','merma')),
    cantidad DECIMAL(10,3) NOT NULL,
    stock_anterior DECIMAL(10,3) NOT NULL,
    stock_nuevo DECIMAL(10,3) NOT NULL,
    motivo TEXT,
    usuario_id INTEGER NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (insumo_id) REFERENCES insumos(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_mov_inv_producto ON movimientos_inventario(producto_id);
CREATE INDEX IF NOT EXISTS idx_mov_inv_fecha    ON movimientos_inventario(fecha);
CREATE INDEX IF NOT EXISTS idx_mov_ins_insumo   ON movimientos_insumos(insumo_id);
CREATE INDEX IF NOT EXISTS idx_mov_ins_fecha    ON movimientos_insumos(fecha);
CREATE INDEX IF NOT EXISTS idx_insumos_activo   ON insumos(activo);
