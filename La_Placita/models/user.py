"""
User Model
Handles user authentication and management
SEGURIDAD: Contraseñas hasheadas con bcrypt
"""

from datetime import datetime
from typing import Optional, List
import bcrypt
from database.connection import db


def _hash_password(plain: str) -> str:
    """Hashea una contraseña en texto plano con bcrypt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


class User:
    """User model"""

    def __init__(self, id: int, nombre: str, email: str, rol: str,
                 activo: bool = True, fecha_creacion: str = None,
                 ultimo_acceso: str = None, password: str = None, **kwargs):
        self.id = id
        self.nombre = nombre
        self.email = email
        self.rol = rol
        self.activo = activo
        self.fecha_creacion = fecha_creacion
        self.ultimo_acceso = ultimo_acceso
        # La contraseña nunca se almacena en el objeto

    # ------------------------------------------------------------------
    # AUTH
    # ------------------------------------------------------------------

    @staticmethod
    def authenticate(email: str, password: str) -> Optional['User']:
        """
        Autentica al usuario buscando por email y verificando el hash bcrypt.
        Ya NO compara texto plano contra texto plano.
        """
        query = """
            SELECT id, nombre, email, password, rol, activo,
                   fecha_creacion, ultimo_acceso
            FROM usuarios
            WHERE email = ? AND activo = 1
        """
        result = db.fetch_one(query, (email,))

        if not result:
            return None

        # Verificar contraseña contra el hash almacenado
        if not _verify_password(password, result['password']):
            return None

        # Actualizar último acceso
        db.execute_query(
            "UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?",
            (datetime.now().isoformat(), result['id'])
        )

        return User(
            id=result['id'],
            nombre=result['nombre'],
            email=result['email'],
            rol=result['rol'],
            activo=bool(result['activo']),
            fecha_creacion=result['fecha_creacion'],
            ultimo_acceso=result['ultimo_acceso']
        )

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    @staticmethod
    def get_by_id(user_id: int) -> Optional['User']:
        """Obtener usuario por ID"""
        query = """
            SELECT id, nombre, email, rol, activo, fecha_creacion, ultimo_acceso
            FROM usuarios WHERE id = ?
        """
        result = db.fetch_one(query, (user_id,))
        if result:
            return User(
                id=result['id'],
                nombre=result['nombre'],
                email=result['email'],
                rol=result['rol'],
                activo=bool(result['activo']),
                fecha_creacion=result['fecha_creacion'],
                ultimo_acceso=result['ultimo_acceso']
            )
        return None

    @staticmethod
    def get_all() -> List['User']:
        """Obtener todos los usuarios (sin exponer el hash)"""
        query = """
            SELECT id, nombre, email, rol, activo, fecha_creacion, ultimo_acceso
            FROM usuarios ORDER BY nombre
        """
        results = db.fetch_all(query)
        return [
            User(
                id=row['id'],
                nombre=row['nombre'],
                email=row['email'],
                rol=row['rol'],
                activo=bool(row['activo']),
                fecha_creacion=row['fecha_creacion'],
                ultimo_acceso=row['ultimo_acceso']
            )
            for row in results
        ]

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    @staticmethod
    def create(nombre: str, email: str, password: str, rol: str) -> int:
        """
        Crear nuevo usuario.
        La contraseña se hashea con bcrypt ANTES de guardar en BD.
        """
        hashed = _hash_password(password)
        query = """
            INSERT INTO usuarios (nombre, email, password, rol)
            VALUES (?, ?, ?, ?)
        """
        return db.execute_query(query, (nombre, email, hashed, rol))

    @staticmethod
    def update(user_id: int, nombre: str = None, email: str = None,
               password: str = None, rol: str = None, activo: bool = None) -> bool:
        """
        Actualizar campos de usuario.
        Si se proporciona una nueva contraseña, se hashea con bcrypt antes de guardar.
        """
        updates = []
        params = []

        if nombre is not None:
            updates.append("nombre = ?")
            params.append(nombre)
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if password is not None:
            # SIEMPRE hashear antes de persistir
            updates.append("password = ?")
            params.append(_hash_password(password))
        if rol is not None:
            updates.append("rol = ?")
            params.append(rol)
        if activo is not None:
            updates.append("activo = ?")
            params.append(1 if activo else 0)

        if not updates:
            return False

        params.append(user_id)
        query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = ?"

        try:
            db.execute_query(query, tuple(params))
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    @staticmethod
    def delete(user_id: int) -> bool:
        """Eliminar usuario (soft delete)"""
        try:
            db.execute_query(
                "UPDATE usuarios SET activo = 0 WHERE id = ?",
                (user_id,)
            )
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def is_admin(self) -> bool:
        return self.rol == 'admin'

    def is_cajero(self) -> bool:
        return self.rol == 'cajero'

    def __repr__(self):
        return f"<User {self.id}: {self.nombre} ({self.rol})>"


# ---------------------------------------------------------------------------
# Sesión global
# ---------------------------------------------------------------------------

current_user: Optional[User] = None


def login(email: str, password: str) -> Optional[User]:
    """Iniciar sesión"""
    global current_user
    user = User.authenticate(email, password)
    if user:
        current_user = user
    return user


def logout():
    """Cerrar sesión"""
    global current_user
    current_user = None


def get_current_user() -> Optional[User]:
    """Obtener usuario actualmente autenticado"""
    return current_user


if __name__ == '__main__':
    print("Testing User model con bcrypt...")
    user = User.authenticate('admin@restaurant.com', 'admin123')
    if user:
        print(f"✓ Login exitoso: {user.nombre} ({user.rol})")
    else:
        print("✗ Login fallido — recuerda ejecutar migrate_passwords.py primero")