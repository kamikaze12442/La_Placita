-- Restaurant POS Database Schema - OPTIMIZADO
-- SQLite Database

-- Tabla de Usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK(rol IN ('admin', 'cajero')),
    activo BOOLEAN DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP
);

-- Tabla de Categorías de Productos
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    icono VARCHAR(10),
    activo BOOLEAN DEFAULT 1
);

-- Tabla de Productos
-- CAMBIO CLAVE: UNIQUE(nombre, precio, categoria_id) para prevenir duplicados
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10, 2) NOT NULL,
    costo DECIMAL(10, 2) DEFAULT 0,
    categoria_id INTEGER,
    stock INTEGER DEFAULT 0,
    imagen VARCHAR(255),
    activo BOOLEAN DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id),
    UNIQUE (nombre, precio, categoria_id)  -- ← PREVIENE DUPLICADOS
);

-- Tabla de Ventas
-- Tabla de Ventas
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_factura VARCHAR(20) UNIQUE NOT NULL,
    usuario_id INTEGER NOT NULL,
    cliente VARCHAR(100),
    subtotal DECIMAL(10, 2) NOT NULL,
    descuento DECIMAL(10, 2) DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    metodo_pago VARCHAR(20) NOT NULL CHECK(metodo_pago IN ('efectivo','qr','tarjeta','mixto')),
    estado VARCHAR(20) DEFAULT 'completada',
    monto_efectivo DECIMAL(10,2) DEFAULT 0,
    monto_qr DECIMAL(10,2) DEFAULT 0,
    tipo_pedido TEXT DEFAULT 'mesa',
    motivo_anulacion TEXT DEFAULT NULL,
    marcada INTEGER DEFAULT 0,
    motivo_marca TEXT DEFAULT NULL,
    fecha_venta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Tabla de Detalle de Ventas
CREATE TABLE IF NOT EXISTS detalle_ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Tabla de Gastos
CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concepto VARCHAR(100) NOT NULL,
    monto DECIMAL(10, 2) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK(tipo IN ('fijo', 'variable')),
    categoria VARCHAR(50),
    descripcion TEXT,
    fecha_gasto DATE NOT NULL,
    usuario_id INTEGER,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Tabla de Configuración
CREATE TABLE IF NOT EXISTS configuracion (
    clave VARCHAR(50) PRIMARY KEY,
    valor TEXT NOT NULL,
    descripcion TEXT,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Datos iniciales
-- ============================================================

INSERT OR IGNORE INTO usuarios (id, nombre, email, password, rol) 
VALUES (1, 'Administrador', 'admin@restaurant.com', 'admin123', 'admin');

INSERT OR IGNORE INTO usuarios (id, nombre, email, password, rol) 
VALUES (2, 'Juan Pérez', 'cajero@restaurant.com', 'cajero123', 'cajero');

INSERT OR IGNORE INTO categorias (nombre, icono) VALUES 
('Comidas', '🍽️'),
('Bebidas', '🥤'),
('Extras', '🍟'),
('Combos', '🎁'),
('Postres', '🍰');



INSERT OR IGNORE INTO configuracion (clave, valor, descripcion) VALUES 
('nombre_negocio', 'Restaurant POS', 'Nombre del negocio'),
('moneda', 'Bs', 'Símbolo de moneda'),
('iva', '0', 'Porcentaje de IVA'),
('direccion', 'Calle Principal #123', 'Dirección del negocio'),
('telefono', '+591 12345678', 'Teléfono de contacto'),
('email', 'info@restaurant.com', 'Email de contacto');

-- ============================================================
-- Índices optimizados
-- Cubren los patrones de consulta más frecuentes:
--   • Lista de productos activos ordenada por nombre
--   • Filtro por categoría + activo
--   • Búsqueda por nombre
--   • Joins en ventas y detalle_ventas
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_productos_activo_nombre  ON productos(activo, nombre);
CREATE INDEX IF NOT EXISTS idx_productos_activo_cat     ON productos(activo, categoria_id);
CREATE INDEX IF NOT EXISTS idx_productos_nombre         ON productos(nombre);

CREATE INDEX IF NOT EXISTS idx_ventas_fecha     ON ventas(fecha_venta);
CREATE INDEX IF NOT EXISTS idx_ventas_usuario   ON ventas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_ventas_estado    ON ventas(estado);

CREATE INDEX IF NOT EXISTS idx_detalle_venta    ON detalle_ventas(venta_id);
CREATE INDEX IF NOT EXISTS idx_detalle_producto ON detalle_ventas(producto_id);

CREATE INDEX IF NOT EXISTS idx_gastos_fecha     ON gastos(fecha_gasto);
-- ============================================================
-- Tablas de inventario
-- ============================================================

CREATE TABLE IF NOT EXISTS insumos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT    NOT NULL UNIQUE,
    unidad          TEXT    NOT NULL,
    stock_actual    REAL    NOT NULL DEFAULT 0,
    stock_minimo    REAL    NOT NULL DEFAULT 0,
    costo_unitario  REAL    NOT NULL DEFAULT 0,
    categoria       TEXT,
    descripcion     TEXT,
    activo          INTEGER NOT NULL DEFAULT 1,
    envase_tipo     TEXT,
    envase_cantidad REAL    DEFAULT 1,
    fecha_creacion  TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS recetas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    insumo_id   INTEGER NOT NULL,
    cantidad    REAL    NOT NULL,
    UNIQUE (producto_id, insumo_id),
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    FOREIGN KEY (insumo_id)   REFERENCES insumos(id)   ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS movimientos_insumos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    insumo_id       INTEGER NOT NULL,
    tipo            TEXT    NOT NULL CHECK(tipo IN ('entrada','consumo','ajuste','merma')),
    cantidad        REAL    NOT NULL,
    stock_anterior  REAL    NOT NULL DEFAULT 0,
    stock_nuevo     REAL    NOT NULL DEFAULT 0,
    motivo          TEXT,
    venta_id        INTEGER,
    usuario_id      INTEGER,
    fecha           TEXT    DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (insumo_id)   REFERENCES insumos(id),
    FOREIGN KEY (usuario_id)  REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS paquetes_insumos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    proveedor       TEXT,
    nota            TEXT,
    items_json      TEXT DEFAULT '[]',
    ajustes_json    TEXT DEFAULT '[]',
    costo_total     DECIMAL(10,2) DEFAULT 0,
    usuario_id      INTEGER,
    fecha_registro  TEXT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- ============================================================
-- Arqueo de caja
-- ============================================================

CREATE TABLE IF NOT EXISTS arqueo_caja (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id      INTEGER NOT NULL,
    fecha_inicio    TEXT    NOT NULL,
    fecha_cierre    TEXT,
    monto_inicial   REAL    NOT NULL DEFAULT 0,
    monto_final     REAL,
    estado          TEXT    NOT NULL DEFAULT 'abierto'
                            CHECK(estado IN ('abierto','cerrado')),
    observaciones   TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Alias con el nombre que usa el modelo ArqueoCaja
CREATE TABLE IF NOT EXISTS arqueos_caja (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id           INTEGER NOT NULL,
    fecha_inicio         TEXT    NOT NULL,
    fecha_cierre         TEXT,
    estado               TEXT    NOT NULL DEFAULT 'abierto'
                                 CHECK(estado IN ('abierto','cerrado')),
    monto_inicial        REAL    DEFAULT 0,
    sistema_efectivo     REAL    DEFAULT 0,
    sistema_qr           REAL    DEFAULT 0,
    sistema_tarjeta      REAL    DEFAULT 0,
    sistema_total        REAL    DEFAULT 0,
    total_transacciones  INTEGER DEFAULT 0,
    conteo_efectivo      REAL    DEFAULT 0,
    conteo_qr            REAL    DEFAULT 0,
    conteo_tarjeta       REAL    DEFAULT 0,
    diferencia_efectivo  REAL    DEFAULT 0,
    diferencia_qr        REAL    DEFAULT 0,
    diferencia_tarjeta   REAL    DEFAULT 0,
    diferencia_total     REAL    DEFAULT 0,
    denominaciones       TEXT    DEFAULT '{}',
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_arqueos_usuario ON arqueos_caja(usuario_id);
CREATE INDEX IF NOT EXISTS idx_arqueos_estado  ON arqueos_caja(estado);
CREATE INDEX IF NOT EXISTS idx_arqueos_fecha   ON arqueos_caja(fecha_inicio);

-- ============================================================
-- Índices de inventario
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_recetas_producto  ON recetas(producto_id);
CREATE INDEX IF NOT EXISTS idx_recetas_insumo    ON recetas(insumo_id);
CREATE INDEX IF NOT EXISTS idx_movinsumos_insumo ON movimientos_insumos(insumo_id);
CREATE INDEX IF NOT EXISTS idx_movinsumos_fecha  ON movimientos_insumos(fecha);
CREATE INDEX IF NOT EXISTS idx_movinsumos_venta  ON movimientos_insumos(venta_id);
CREATE INDEX IF NOT EXISTS idx_insumos_activo    ON insumos(activo);