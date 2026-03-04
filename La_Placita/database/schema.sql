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
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_factura VARCHAR(20) UNIQUE NOT NULL,
    usuario_id INTEGER NOT NULL,
    cliente VARCHAR(100),
    subtotal DECIMAL(10, 2) NOT NULL,
    descuento DECIMAL(10, 2) DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    metodo_pago VARCHAR(20) NOT NULL CHECK(metodo_pago IN ('efectivo', 'qr', 'tarjeta')),
    estado VARCHAR(20) DEFAULT 'completada',
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
