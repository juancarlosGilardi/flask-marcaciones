#!/usr/bin/env python3
"""
HISPE PULSE v2.0 - Sistema de Marcaciones PWA
Aplicación Flask optimizada con validación GPS y funcionalidades PWA
"""

from flask import Flask, request, jsonify, render_template, session, redirect, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import os
import sys
import time

# Importar servicios modulares
from auth import auth_service
from database import db_service
from location_service import location_service
from mail_service import send_marking_email

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hispe_pulse.log'),
        logging.StreamHandler()
    ]
)

# Inicializar Flask
app = Flask(__name__)
CORS(app)

# Configuración de la aplicación
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.permanent_session_lifetime = timedelta(hours=8)

# ============================================================================
# RUTAS DE PÁGINAS WEB
# ============================================================================

@app.route('/')
def home():
    """Página de inicio - redirige según autenticación"""
    return redirect('/dashboard' if auth_service.is_authenticated() else '/login')

@app.route('/login')
def login_page():
    """Página de login"""
    if auth_service.is_authenticated():
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/register')
def register_page():
    """Página de registro"""
    if auth_service.is_authenticated():
        return redirect('/dashboard')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard principal de marcaciones"""
    return render_template('index.html')

# ============================================================================
# RUTAS PWA
# ============================================================================

@app.route('/manifest.json')
def serve_manifest():
    """Servir manifest.json para PWA"""
    return jsonify({
        "name": "HISPE PULSE - Sistema de Marcaciones",
        "short_name": "HISPE PULSE",
        "description": "Sistema inteligente de marcaciones de asistencia para Hispe SAC",
        "start_url": "/dashboard",
        "display": "standalone",
        "orientation": "portrait-primary",
        "theme_color": "#2c3e50",
        "background_color": "#34495e",
        "scope": "/",
        "lang": "es-PE",
        "dir": "ltr",
        "id": "hispe-pulse-pwa",
        
        "icons": [
            {"src": "/static/icons/icon-72.png", "sizes": "72x72", "type": "image/png"},
            {"src": "/static/icons/icon-96.png", "sizes": "96x96", "type": "image/png"},
            {"src": "/static/icons/icon-128.png", "sizes": "128x128", "type": "image/png"},
            {"src": "/static/icons/icon-144.png", "sizes": "144x144", "type": "image/png"},
            {"src": "/static/icons/icon-152.png", "sizes": "152x152", "type": "image/png"},
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/icons/icon-384.png", "sizes": "384x384", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
        ],
        
        "shortcuts": [
            {
                "name": "Marcar Ingreso",
                "url": "/dashboard?action=ingreso",
                "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}]
            },
            {
                "name": "Marcar Salida",
                "url": "/dashboard?action=salida",
                "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}]
            }
        ],
        
        "display_override": ["window-controls-overlay", "standalone", "minimal-ui"],
        "categories": ["business", "productivity"]
    })

@app.route('/sw.js')
def serve_service_worker():
    """Servir service worker con headers correctos"""
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

# ============================================================================
# API DE AUTENTICACIÓN
# ============================================================================

@app.route('/api/register', methods=['POST'])
def api_register():
    """Registrar nuevo usuario"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400
        
        result = auth_service.register_user(
            name=data.get('name', ''),
            email=data.get('email', ''),
            dni=data.get('dni', ''),
            password=data.get('password', ''),
            device_id=request.headers.get('User-Agent', '')[:100]
        )
        
        return jsonify(result), 201
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logging.error(f"❌ Error en registro: {e}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    """Iniciar sesión"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400
        
        result = auth_service.login_user(
            email=data.get('email', ''),
            password=data.get('password', '')
        )
        
        # Configurar sesión permanente si se solicita
        if data.get('rememberMe', False):
            session.permanent = True
        
        logging.info(f"✅ Login desde IP: {request.remote_addr}")
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 401
    except Exception as e:
        logging.error(f"❌ Error en login: {e}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Cerrar sesión"""
    try:
        result = auth_service.logout_user()
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"❌ Error en logout: {e}")
        return jsonify({'success': False, 'error': 'Error cerrando sesión'}), 500

# ============================================================================
# API DE MARCACIONES
# ============================================================================

@app.route('/api/user')
def get_user():
    """Obtener datos del usuario actual"""
    try:
        user_data = auth_service.get_current_user()
        return jsonify(user_data), 200
    except Exception as e:
        logging.error(f"❌ Error obteniendo usuario: {e}")
        return jsonify({'error': 'Error obteniendo datos del usuario'}), 500

@app.route('/api/attendance/today')
def get_today_attendance():
    """Obtener marcaciones del día actual"""
    try:
        user_data = auth_service.get_current_user()
        attendance = db_service.get_today_attendance(user_data['userEmail'])
        
        if attendance is None:
            return jsonify({'error': 'Error consultando marcaciones'}), 500
            
        return jsonify(attendance), 200
        
    except Exception as e:
        logging.error(f"❌ Error en get_today_attendance: {e}")
        return jsonify({'error': 'Error consultando marcaciones'}), 500

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    """Marcar asistencia con validación GPS completa"""
    try:
        # Validar entrada
        if not request.is_json:
            return jsonify({'error': 'Content-Type debe ser application/json'}), 415

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        # Extraer y validar datos básicos
        qr_code = data.get('qrCode', '').strip()
        marcation_type = data.get('marcationType', '').strip()
        user_latitude = data.get('latitude')
        user_longitude = data.get('longitude')
        location_accuracy = data.get('accuracy', 0)
        
        # Validaciones básicas
        if not qr_code or not marcation_type:
            return jsonify({'error': 'QR code y tipo de marcación son requeridos'}), 400
            
        if user_latitude is None or user_longitude is None:
            return jsonify({'error': 'Coordenadas GPS requeridas'}), 400
            
        # Validar tipo de marcación
        valid_types = ['Ingreso', 'Inicio de Refrigerio', 'Salida de Refrigerio', 'Salida']
        if marcation_type not in valid_types:
            return jsonify({'error': f'Tipo de marcación no válido: {marcation_type}'}), 400
        
        # Validar y convertir coordenadas
        try:
            user_latitude = float(user_latitude)
            user_longitude = float(user_longitude)
            location_accuracy = float(location_accuracy) if location_accuracy else 0
        except (ValueError, TypeError):
            return jsonify({'error': 'Coordenadas deben ser números válidos'}), 400
            
        if not (-90 <= user_latitude <= 90 and -180 <= user_longitude <= 180):
            return jsonify({'error': 'Coordenadas fuera de rango válido'}), 400
        
        # ✅ VALIDACIÓN GPS COMPLETA
        logging.info(f"🎯 Validando ubicación para {marcation_type}")
        
        location_report = location_service.generate_location_report(
            user_lat=user_latitude,
            user_lng=user_longitude,
            qr_code=qr_code,
            accuracy=location_accuracy
        )
        
        # Verificar validación
        if not location_report['summary']['overall_valid']:
            primary_issue = location_report['summary']['primary_issue']
            logging.warning(f"❌ Validación GPS falló: {primary_issue}")
            
            return jsonify({
                'error': primary_issue,
                'location_report': {
                    'distance': location_report['validation'].get('distance'),
                    'accuracy': location_accuracy,
                    'qr_valid': location_report['qr_info']['valid'],
                    'user_coordinates': f"{user_latitude:.6f}, {user_longitude:.6f}"
                },
                'code': 'LOCATION_VALIDATION_FAILED'
            }), 400
        
        # ✅ VALIDACIÓN EXITOSA
        distance = location_report['validation'].get('distance', 'N/A')
        logging.info(f"✅ Validación GPS exitosa - Distancia: {distance}m")
            
        # Obtener datos del usuario y procesar marcación
        user_data = auth_service.get_user_for_marking()
        
        result = db_service.mark_attendance(
            user_data=user_data,
            marcation_type=marcation_type,
            qr_code=qr_code,
            latitude=user_latitude,
            longitude=user_longitude,
            accuracy=location_accuracy
        )
        
        # ✅ ENVIAR EMAIL PARA INGRESO Y SALIDA
        try:
            if marcation_type in ['Ingreso', 'Salida']:
                # Extraer RUC del QR code
                ruc = qr_code.split('|')[0] if '|' in qr_code else qr_code
                if '_' in ruc:
                    ruc = ruc.split('_')[0]  # Para QRs formato "HISPE_lat_lng"
                
                logging.info(f"📧 Enviando email para {marcation_type} - RUC: {ruc}")
                
                send_marking_email(
                    user_data={
                        'userName': user_data['name'],
                        'userEmail': user_data['email'],
                        'userDni': user_data['dni']
                    },
                    marking_data={'marcationType': marcation_type},
                    ruc=ruc
                )
                
                logging.info(f"✅ Email enviado exitosamente para {marcation_type}")
                
        except Exception as email_error:
            # No fallar la marcación por problemas de email
            logging.warning(f"⚠️ Error enviando email (marcación exitosa): {email_error}")
        
        # Respuesta exitosa con información de ubicación
        response_data = {
            'success': True,
            'message': result['message'],
            'data': {
                **result['data'],
                'location_info': {
                    'distance_to_qr': distance,
                    'gps_accuracy': f"±{location_accuracy}m",
                    'coordinates': f"{user_latitude:.6f}, {user_longitude:.6f}",
                    'validation_passed': True
                }
            }
        }
        
        logging.info(f"✅ Marcación '{marcation_type}' exitosa para {user_data['name']}")
        return jsonify(response_data), 201

    except ValueError as e:
        logging.warning(f"❌ Error de validación: {e}")
        return jsonify({'error': str(e), 'code': 'BUSINESS_LOGIC_ERROR'}), 400
        
    except Exception as e:
        logging.error(f"❌ Error interno en marcación: {e}")
        return jsonify({
            'error': 'Error interno del servidor',
            'code': 'INTERNAL_SERVER_ERROR'
        }), 500

# ============================================================================
# API DE VALIDACIÓN Y UTILIDADES
# ============================================================================

@app.route('/api/location/validate', methods=['POST'])
def validate_location():
    """Validar ubicación sin realizar marcación"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
            
        qr_code = data.get('qrCode', '').strip()
        user_latitude = data.get('latitude')
        user_longitude = data.get('longitude')
        accuracy = data.get('accuracy', 0)
        
        if not qr_code or user_latitude is None or user_longitude is None:
            return jsonify({'error': 'QR code y coordenadas son requeridos'}), 400
            
        # Validar y convertir coordenadas
        try:
            user_latitude = float(user_latitude)
            user_longitude = float(user_longitude)
            accuracy = float(accuracy) if accuracy else 0
        except (ValueError, TypeError):
            return jsonify({'error': 'Coordenadas inválidas'}), 400
            
        # Generar reporte completo
        location_report = location_service.generate_location_report(
            user_lat=user_latitude,
            user_lng=user_longitude,
            qr_code=qr_code,
            accuracy=accuracy
        )
        
        return jsonify({
            'valid': location_report['summary']['overall_valid'],
            'report': location_report,
            'summary': location_report['summary']['primary_issue']
        }), 200
        
    except Exception as e:
        logging.error(f"❌ Error validando ubicación: {e}")
        return jsonify({'error': 'Error interno validando ubicación'}), 500

@app.route('/api/qr/info', methods=['POST'])
def get_qr_info():
    """Obtener información de un código QR"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'QR code requerido'}), 400
            
        qr_code = data.get('qrCode', '').strip()
        if not qr_code:
            return jsonify({'error': 'QR code vacío'}), 400
            
        # Validar formato del QR
        qr_info = location_service.validate_qr_format(qr_code)
        
        if qr_info['valid'] and qr_info.get('coordinates'):
            # Agregar información de ubicación
            lat, lng = qr_info['coordinates']
            location_info = location_service.get_location_info(lat, lng)
            qr_info['location_info'] = location_info
            qr_info['in_peru'] = location_service.is_within_peru(lat, lng)
        
        return jsonify(qr_info), 200
        
    except Exception as e:
        logging.error(f"❌ Error obteniendo info de QR: {e}")
        return jsonify({'error': 'Error procesando QR code'}), 500

@app.route('/api/config')
def get_system_config():
    """Obtener configuración del sistema"""
    config = {
        'gps_settings': {
            'max_distance_meters': float(os.getenv('MAX_GPS_DISTANCE', '700.0')),
            'max_accuracy_meters': float(os.getenv('MAX_GPS_ACCURACY', '600.0')),
            'timeout_seconds': int(os.getenv('GPS_TIMEOUT', '10'))
        },
        'app_settings': {
            'app_name': 'HISPE PULSE',
            'version': '2.0.0',
            'support_email': os.getenv('SUPPORT_EMAIL', 'soporte@hispe.com'),
            'company_name': 'HISPE'
        },
        'features': {
            'gps_validation': True,
            'offline_mode': True,
            'timezone': 'America/Lima'
        }
    }
    
    return jsonify(config), 200

@app.route('/api/health')
def health_check():
    """Health check del sistema"""
    try:
        # Test de base de datos
        start_time = time.time()
        db_status = db_service.test_connection()
        db_latency = round((time.time() - start_time) * 1000, 2) if db_status else None
        
        # Test de servicios
        test_qr = "HISPE_-12.0464_-77.0428"
        location_service_status = 'available'
        try:
            location_service.validate_qr_format(test_qr)
        except:
            location_service_status = 'error'
        
        # Estado general
        overall_status = 'healthy' if db_status and location_service_status == 'available' else 'degraded'
        
        health_data = {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'database': {
                'status': 'connected' if db_status else 'disconnected',
                'latency_ms': db_latency
            },
            'services': {
                'location_service': location_service_status,
                'auth_service': 'available'
            },
            'user_session': {
                'authenticated': auth_service.is_authenticated(),
                'email': session.get('user_email', 'anonymous')
            },
            'system': {
                'version': '2.0.0',
                'environment': 'production' if not app.debug else 'development',
                'timezone': 'America/Lima'
            }
        }
        
        status_code = 200 if overall_status == 'healthy' else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logging.error(f"❌ Error en health check: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.before_request
def log_request():
    """Log de requests para debugging"""
    if request.endpoint and '/api/' in request.url:
        logging.info(f"🌐 {request.method} {request.url} - IP: {request.remote_addr}")

@app.after_request
def add_headers(response):
    """Headers de seguridad y PWA"""
    
    # Headers de seguridad básicos
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Headers para PWA
    if '/static/' in request.url:
        response.headers['Cache-Control'] = 'public, max-age=31536000'
    else:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    
    # Service Worker
    if request.endpoint == 'serve_service_worker':
        response.headers['Service-Worker-Allowed'] = '/'
        response.headers['Cache-Control'] = 'no-cache'
    
    # Manifest
    if request.path.endswith('manifest.json'):
        response.headers['Content-Type'] = 'application/manifest+json'
    
    return response

# ============================================================================
# MANEJO DE ERRORES
# ============================================================================

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Solicitud incorrecta', 'code': 400}), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'No autorizado', 'code': 401}), 401

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Recurso no encontrado', 'code': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"❌ Error 500: {error}")
    return jsonify({'error': 'Error interno del servidor', 'code': 500}), 500

# ============================================================================
# INICIALIZACIÓN Y EJECUCIÓN
# ============================================================================

def validate_environment():
    """Validar variables de entorno críticas"""
    required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DB']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logging.error(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        print("⚠️ Configure las variables de entorno requeridas antes de iniciar")
        return False
    return True

def initialize_services():
    """Inicializar servicios de la aplicación"""
    try:
        # Inicializar base de datos
        logging.info("🔧 Inicializando base de datos...")
        db_service.init_database()
        
        # Verificar servicios
        if not db_service.test_connection():
            raise Exception("No se pudo conectar a la base de datos")
        
        # Test del servicio de ubicación
        test_qr = "HISPE_-12.0464_-77.0428"
        test_result = location_service.validate_qr_format(test_qr)
        
        if test_result['valid']:
            logging.info("✅ Servicio de ubicación funcionando")
        else:
            logging.warning("⚠️ Problema con servicio de ubicación")
            
        logging.info("✅ Servicios inicializados correctamente")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error inicializando servicios: {e}")
        return False

def print_startup_info():
    """Mostrar información de inicio"""
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    port = int(os.getenv('FLASK_PORT', '5001'))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    print("\n🚀 HISPE PULSE v2.0 - Sistema de Marcaciones PWA")
    print("=" * 60)
    print(f"🌐 Servidor: http://localhost:{port}")
    print(f"🔐 Login: http://localhost:{port}/login")
    print(f"👤 Registro: http://localhost:{port}/register") 
    print(f"📊 Dashboard: http://localhost:{port}/dashboard")
    print(f"🏥 Health: http://localhost:{port}/api/health")
    print(f"📱 Manifest: http://localhost:{port}/manifest.json")
    print(f"🗃️ BD: {os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}")
    print(f"🔧 Debug: {'Activado' if debug_mode else 'Desactivado'}")
    print(f"📍 GPS: ±{os.getenv('MAX_GPS_DISTANCE', '700')}m")
    print("=" * 60)
    print("✅ Sistema listo para recibir conexiones\n")
    
    return debug_mode, host, port

def main():
    """Función principal"""
    try:
        # Validar entorno
        if not validate_environment():
            sys.exit(1)
        
        # Inicializar servicios
        if not initialize_services():
            sys.exit(1)
        
        # Configurar y ejecutar servidor
        debug_mode, host, port = print_startup_info()
        
        app.run(debug=debug_mode, host=host, port=port, threaded=True)
        
    except KeyboardInterrupt:
        logging.info("🛑 Servidor detenido por el usuario")
    except Exception as e:
        logging.error(f"❌ Error fatal del servidor: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()