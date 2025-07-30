"""
auth.py - Servicio de autenticación para HISPE PULSE
Maneja registro, login, validaciones y sesiones
"""

import re
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from database import db_service

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        # Datos MOCK para compatibilidad con tests existentes
        self.MOCK_USER = {
            'userName': 'Juan Carlos Pérez',
            'userEmail': 'juan.perez@hispe.com',
            'userDni': '12345678',
            'deviceId': 'device_mock_001'
        }
    
    def validate_email(self, email):
        """Validar formato de email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_dni(self, dni):
        """Validar DNI peruano (8 dígitos)"""
        return dni.isdigit() and len(dni) == 8
    
    def validate_password(self, password):
        """Validar contraseña (mínimo 6 caracteres)"""
        return len(password) >= 6
    
    def register_user(self, name, email, dni, password, device_id=None):
        """Registrar nuevo usuario"""
        try:
            # Validaciones
            if not name or len(name.strip()) < 2:
                raise ValueError("El nombre debe tener al menos 2 caracteres")
            
            if not self.validate_email(email):
                raise ValueError("Por favor, ingrese un email válido")
            
            if not self.validate_dni(dni):
                raise ValueError("El DNI debe tener exactamente 8 dígitos")
            
            if not self.validate_password(password):
                raise ValueError("La contraseña debe tener al menos 6 caracteres")
            
            # Verificar si ya existe
            if db_service.get_user_by_email(email):
                raise ValueError("Ya existe un usuario con este email")
            
            if db_service.get_user_by_dni(dni):
                raise ValueError("Ya existe un usuario con este DNI")
            
            # Crear usuario
            password_hash = generate_password_hash(password)
            user_id = db_service.create_user(
                name=name.strip(),
                email=email.strip().lower(),
                dni=dni.strip(),
                password_hash=password_hash,
                device_id=device_id
            )
            
            logger.info(f"✅ Usuario registrado: {name} ({email})")
            return {
                'success': True,
                'message': 'Usuario registrado exitosamente',
                'user_id': user_id
            }
            
        except ValueError as e:
            logger.warning(f"❌ Error de validación en registro: {e}")
            raise e
        except Exception as e:
            logger.error(f"❌ Error interno en registro: {e}")
            raise Exception("Error interno del servidor")
    
    def login_user(self, email, password):
        """Iniciar sesión de usuario"""
        try:
            if not email or not password:
                raise ValueError("Email y contraseña son requeridos")
            
            # Buscar usuario
            user = db_service.get_user_by_email(email.strip().lower())
            if not user:
                raise ValueError("Email o contraseña incorrectos")
            
            # Verificar contraseña
            if not check_password_hash(user['password_hash'], password):
                raise ValueError("Email o contraseña incorrectos")
            
            # Crear sesión
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_dni'] = user['dni']
            session['device_id'] = user['device_id']
            session['is_authenticated'] = True
            
            logger.info(f"✅ Login exitoso: {user['name']} ({user['email']})")
            return {
                'success': True,
                'message': 'Inicio de sesión exitoso',
                'user': {
                    'id': user['id'],
                    'name': user['name'],
                    'email': user['email'],
                    'dni': user['dni']
                }
            }
            
        except ValueError as e:
            logger.warning(f"❌ Error de login: {e}")
            raise e
        except Exception as e:
            logger.error(f"❌ Error interno en login: {e}")
            raise Exception("Error interno del servidor")
    
    def logout_user(self):
        """Cerrar sesión de usuario"""
        user_email = session.get('user_email', 'Usuario desconocido')
        session.clear()
        logger.info(f"✅ Logout exitoso: {user_email}")
        return {
            'success': True,
            'message': 'Sesión cerrada exitosamente'
        }
    
    def is_authenticated(self):
        """Verificar si el usuario está autenticado"""
        return session.get('is_authenticated', False)
    
    def get_current_user(self):
        """Obtener datos del usuario actual de la sesión"""
        if self.is_authenticated():
            return {
                'id': session.get('user_id'),
                'userName': session.get('user_name'),
                'userEmail': session.get('user_email'),
                'userDni': session.get('user_dni'),
                'deviceId': session.get('device_id')
            }
        else:
            # Modo MOCK para desarrollo/testing
            return self.MOCK_USER
    
    def get_user_for_marking(self):
        """Obtener datos del usuario para marcaciones"""
        if self.is_authenticated():
            return {
                'name': session.get('user_name'),
                'email': session.get('user_email'),
                'dni': session.get('user_dni'),
                'device_id': session.get('device_id')
            }
        else:
            # Modo MOCK para desarrollo/testing
            return {
                'name': self.MOCK_USER['userName'],
                'email': self.MOCK_USER['userEmail'],
                'dni': self.MOCK_USER['userDni'],
                'device_id': self.MOCK_USER['deviceId']
            }
    
    def require_auth(self, allow_mock=True):
        """Middleware para requerir autenticación"""
        if self.is_authenticated():
            return True
        elif allow_mock:
            # Permite modo MOCK para desarrollo
            logger.info("🔓 Usando modo MOCK para desarrollo")
            return True
        else:
            raise ValueError("Autenticación requerida")

# Instancia global del servicio de autenticación
auth_service = AuthService()