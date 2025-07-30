"""
database.py - Servicio de base de datos para HISPE PULSE
Maneja todas las operaciones de base de datos de forma centralizada
"""

import os
import logging
import pymysql
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.host = os.getenv('MYSQL_HOST')
        self.port = int(os.getenv('MYSQL_PORT', 3306))
        self.user = os.getenv('MYSQL_USER')
        self.password = os.getenv('MYSQL_PASSWORD')
        self.database = os.getenv('MYSQL_DB')
        
    def get_connection(self):
        """Obtener conexión a MySQL"""
        try:
            return pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
        except Exception as e:
            logger.error(f"❌ Error conectando a la base de datos: {e}")
            return None

    def init_database(self):
        """Inicializar tablas necesarias"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("No se pudo conectar a la base de datos")
                
            with conn.cursor() as cursor:
                # Crear tabla de usuarios
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL UNIQUE,
                        dni VARCHAR(20) NOT NULL UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        device_id VARCHAR(255),
                        is_active TINYINT(1) DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # Crear tabla de marcaciones (compatible con la existente)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS marcaHispe (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        fullname VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        dni VARCHAR(20) NOT NULL,
                        dispositivoid VARCHAR(255),
                        geolocacion VARCHAR(255),
                        latitud_marcacion DECIMAL(10, 8),
                        longitud_marcacion DECIMAL(11, 8),
                        geoemp VARCHAR(255),
                        ruc VARCHAR(255),
                        area VARCHAR(255),
                        fechamarcacion VARCHAR(20) NOT NULL,
                        horaentrada TIME,
                        horaRefrigerioInicio TIME,
                        horaRefrigerioFin TIME,
                        horasalida TIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_email_fecha (email, fechamarcacion),
                        INDEX idx_fecha (fechamarcacion)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
            conn.commit()
            logger.info("✅ Tablas inicializadas correctamente")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Error inicializando base de datos: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def create_user(self, name, email, dni, password_hash, device_id=None):
        """Crear nuevo usuario"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("Error de conexión a la base de datos")
                
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (name, email, dni, password_hash, device_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, email, dni, password_hash, device_id))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"✅ Usuario creado: {name} ({email})")
                return user_id
                
        except pymysql.err.IntegrityError as e:
            if conn:
                conn.rollback()
            if "email" in str(e):
                raise ValueError("Ya existe un usuario con este email")
            elif "dni" in str(e):
                raise ValueError("Ya existe un usuario con este DNI")
            else:
                raise ValueError("Error de datos duplicados")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Error creando usuario: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_user_by_email(self, email):
        """Obtener usuario por email"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return None
                
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE email = %s AND is_active = 1
                """, (email,))
                
                return cursor.fetchone()
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo usuario por email: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_user_by_dni(self, dni):
        """Obtener usuario por DNI"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return None
                
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE dni = %s AND is_active = 1
                """, (dni,))
                
                return cursor.fetchone()
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo usuario por DNI: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_today_attendance(self, email):
        """Obtener marcaciones del día actual"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return None
                
            with conn.cursor() as cursor:
                today_date = datetime.now().strftime('%d/%m/%Y')
                
                cursor.execute("""
                    SELECT horaentrada, horaRefrigerioInicio, horaRefrigerioFin, horasalida
                    FROM marcaHispe 
                    WHERE email = %s AND fechamarcacion = %s
                    ORDER BY id DESC LIMIT 1
                """, (email, today_date))
                
                return cursor.fetchone() or {}
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo marcaciones del día: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def mark_attendance(self, user_data, marcation_type, qr_code, latitude, longitude, accuracy=0):
        """Registrar marcación de asistencia"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("Error de conexión a la base de datos")
                
            with conn.cursor() as cursor:
                now = datetime.now()
                formatted_date = now.strftime('%d/%m/%Y')
                formatted_time = now.strftime('%H:%M:%S')
                location_string = f"{latitude}, {longitude}"
                
                # Obtener registro existente del día
                cursor.execute("""
                    SELECT id, horaentrada, horaRefrigerioInicio, horaRefrigerioFin, horasalida
                    FROM marcaHispe 
                    WHERE email = %s AND fechamarcacion = %s
                    ORDER BY id DESC LIMIT 1
                """, (user_data['email'], formatted_date))
                
                existing_record = cursor.fetchone()
                
                # Lógica según tipo de marcación
                if marcation_type == 'Ingreso':
                    if existing_record and existing_record['horaentrada']:
                        raise ValueError(f'Ya marcó ingreso hoy a las {existing_record["horaentrada"]}')
                    
                    # Insertar nuevo registro
                    cursor.execute("""
                        INSERT INTO marcaHispe (
                            fullname, email, dni, dispositivoid, geolocacion, 
                            latitud_marcacion, longitud_marcacion, fechamarcacion, horaentrada
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_data['name'], user_data['email'], user_data['dni'],
                        user_data.get('device_id'), location_string, 
                        latitude, longitude, formatted_date, formatted_time
                    ))
                    
                else:
                    # Para otras marcaciones, necesita registro previo
                    if not existing_record or not existing_record['horaentrada']:
                        raise ValueError('Debe marcar su Ingreso antes de realizar otra marcación')
                    
                    record_id = existing_record['id']
                    
                    if marcation_type == 'Inicio de Refrigerio':
                        if existing_record['horaRefrigerioInicio']:
                            raise ValueError(f'Ya marcó inicio de refrigerio hoy a las {existing_record["horaRefrigerioInicio"]}')
                        
                        cursor.execute("""
                            UPDATE marcaHispe 
                            SET horaRefrigerioInicio = %s, latitud_marcacion = %s, 
                                longitud_marcacion = %s, geolocacion = %s 
                            WHERE id = %s
                        """, (formatted_time, latitude, longitude, location_string, record_id))
                        
                    elif marcation_type == 'Salida de Refrigerio':
                        if not existing_record['horaRefrigerioInicio']:
                            raise ValueError('Debe marcar inicio de refrigerio primero')
                        if existing_record['horaRefrigerioFin']:
                            raise ValueError(f'Ya marcó salida de refrigerio hoy a las {existing_record["horaRefrigerioFin"]}')
                        
                        cursor.execute("""
                            UPDATE marcaHispe 
                            SET horaRefrigerioFin = %s, latitud_marcacion = %s, 
                                longitud_marcacion = %s, geolocacion = %s 
                            WHERE id = %s
                        """, (formatted_time, latitude, longitude, location_string, record_id))
                        
                    elif marcation_type == 'Salida':
                        if existing_record['horaRefrigerioInicio'] and not existing_record['horaRefrigerioFin']:
                            raise ValueError('Debe terminar su refrigerio antes de marcar la salida')
                        if existing_record['horasalida']:
                            raise ValueError(f'Ya marcó su salida hoy a las {existing_record["horasalida"]}')
                        
                        cursor.execute("""
                            UPDATE marcaHispe 
                            SET horasalida = %s, latitud_marcacion = %s, 
                                longitud_marcacion = %s, geolocacion = %s 
                            WHERE id = %s
                        """, (formatted_time, latitude, longitude, location_string, record_id))
                
                conn.commit()
                
                logger.info(f"✅ Marcación '{marcation_type}' registrada para {user_data['name']}")
                return {
                    'success': True,
                    'message': f'✅ {marcation_type} registrado exitosamente a las {formatted_time}',
                    'data': {
                        'marcationType': marcation_type,
                        'time': formatted_time,
                        'date': formatted_date,
                        'location': location_string
                    }
                }
                
        except ValueError as e:
            # Errores de validación de negocio
            if conn:
                conn.rollback()
            raise e
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Error registrando marcación: {e}")
            raise Exception("Error interno al procesar la marcación")
        finally:
            if conn:
                conn.close()

    def test_connection(self):
        """Probar conexión a la base de datos"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return False
                
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error probando conexión: {e}")
            return False
        finally:
            if conn:
                conn.close()

# Instancia global del servicio
db_service = DatabaseService()