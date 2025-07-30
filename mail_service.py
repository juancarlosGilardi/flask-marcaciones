import smtplib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def send_marking_email(user_data, marking_data, ruc):
    """Enviar email simple para marcaciones de Ingreso y Salida"""
    try:
        marking_type = marking_data.get('marcationType')
        
        # Solo enviar para Ingreso y Salida
        if marking_type not in ['Ingreso', 'Salida']:
            return
        
        # Configuración fija de email (como en tu app Flutter anterior)
        email_origen = 'marcacionesneodeter@gmail.com'
        email_password = 'ougfzzjgmayydkhr'
        email_destino = 'jc_gilardi@yahoo.com'
        
        # Datos del email
        now = datetime.now()
        formatted_date = now.strftime("%d/%m/%Y")
        formatted_time = now.strftime("%H:%M:%S")
        
        # Crear mensaje simple
        subject = f'Nueva Marcacion - {user_data["userName"]} ({marking_type})'
        body = f'''Usuario: {user_data["userName"]}
Email: {user_data["userEmail"]}
DNI: {user_data["userDni"]}
Tipo: {marking_type}
Fecha: {formatted_date}
Hora: {formatted_time}'''
        
        # Enviar email usando smtplib básico
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_origen, email_password)
            
            message = f'Subject: {subject}\n\n{body}'
            server.sendmail(email_origen, email_destino, message.encode('utf-8'))
        
        logger.info(f"📧 Email enviado exitosamente para {marking_type} - {user_data['userName']}")
        
    except Exception as e:
        logger.warning(f"⚠️ Error enviando email: {e}")
        # No fallar la marcación por problemas de email