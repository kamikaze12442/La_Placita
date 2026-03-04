"""
User Model
Handles user authentication and management
"""

from datetime import datetime
from typing import Optional, List
from database.connection import db


class User:
    """User model"""
    
    def __init__(self, id: int, nombre: str, email: str, rol: str, 
                 activo: bool = True, fecha_creacion: str = None, 
                 ultimo_acceso: str = None, password: str = None, **kwargs):
        """
        Initialize User
        
        Args:
            id: User ID
            nombre: User name
            email: User email
            rol: User role (admin/cajero)
            activo: Active status (optional)
            fecha_creacion: Creation date (optional)
            ultimo_acceso: Last access date (optional)
            password: Password (optional, from DB, not stored in object)
            **kwargs: Additional fields from database (ignored)
        """
        self.id = id
        self.nombre = nombre
        self.email = email
        self.rol = rol
        self.activo = activo
        self.fecha_creacion = fecha_creacion
        self.ultimo_acceso = ultimo_acceso
        # Note: password is not stored in the object for security
    
    @staticmethod
    def authenticate(email: str, password: str) -> Optional['User']:
        """Authenticate user with email and password"""
        query = """
            SELECT * FROM usuarios 
            WHERE email = ? AND password = ? AND activo = 1
        """
        result = db.fetch_one(query, (email, password))
        
        if result:
            # Update last access
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
        return None
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional['User']:
        """Get user by ID"""
        query = "SELECT * FROM usuarios WHERE id = ?"
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
        """Get all users"""
        query = "SELECT * FROM usuarios ORDER BY nombre"
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
    
    @staticmethod
    def create(nombre: str, email: str, password: str, rol: str) -> int:
        """Create new user"""
        query = """
            INSERT INTO usuarios (nombre, email, password, rol) 
            VALUES (?, ?, ?, ?)
        """
        return db.execute_query(query, (nombre, email, password, rol))
    
    @staticmethod
    def update(user_id: int, nombre: str = None, email: str = None, 
               password: str = None, rol: str = None, activo: bool = None) -> bool:
        """Update user"""
        updates = []
        params = []
        
        if nombre is not None:
            updates.append("nombre = ?")
            params.append(nombre)
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if password is not None:
            updates.append("password = ?")
            params.append(password)
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
        """Delete user (soft delete)"""
        try:
            db.execute_query(
                "UPDATE usuarios SET activo = 0 WHERE id = ?",
                (user_id,)
            )
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.rol == 'admin'
    
    def is_cajero(self) -> bool:
        """Check if user is cashier"""
        return self.rol == 'cajero'
    
    def __repr__(self):
        return f"<User {self.id}: {self.nombre} ({self.rol})>"


# Global current user
current_user: Optional[User] = None


def login(email: str, password: str) -> Optional[User]:
    """Login user"""
    global current_user
    user = User.authenticate(email, password)
    if user:
        current_user = user
    return user


def logout():
    """Logout current user"""
    global current_user
    current_user = None


def get_current_user() -> Optional[User]:
    """Get current logged in user"""
    return current_user


if __name__ == '__main__':
    # Test user model
    print("Testing User model...")
    
    # Test authentication
    user = User.authenticate('admin@restaurant.com', 'admin123')
    if user:
        print(f"✓ Login successful: {user.nombre} ({user.rol})")
    else:
        print("✗ Login failed")
    
    # Test get all users
    users = User.get_all()
    print(f"\n✓ Total users: {len(users)}")
    for u in users:
        print(f"  - {u.nombre} ({u.email}) - {u.rol}")
