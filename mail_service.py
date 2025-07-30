import smtplib
import logging
from email.mime.text import MimeText as EmailMimeText
from email.mime.multipart import MimeMultipart as EmailMimeMultipart
from datetime import datetime
from database import db_service

logger = logging.getLogger(__name__)

def get_email_config_by_ruc(ruc):
    """Obtener configuración de email por RUC de la empresa"""
    conn = db_service.get_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT email_origen, email_password, email_destino, empresa
                FROM empresa 
                WHERE ruc = %s
            """, (ruc,))
            return cur.fetchone()
    except Exception as e:
        logger.error(f"Error obteniendo config de email: {e}")
        return None
    finally:
        conn.close()

def send_marking_email(user_data, marking_data, ruc):
    """
    Enviar email de marcación solo para Ingreso y Salida
    """
    marking_type = marking_data.get('marcationType')
    
    # Solo enviar para Ingreso y Salida
    if marking_type not in ['Ingreso', 'Salida']:
        logger.info(f"No se envía email para tipo: {marking_type}")
        return
    
    try:
        # Obtener configuración de email
        email_config = get_email_config_by_ruc(ruc)
        if not email_config:
            logger.warning(f"No se encontró configuración de email para RUC: {ruc}")
            return
        
        email_origen = email_config['email_origen']
        email_password = email_config['email_password']
        email_destino = email_config['email_destino']
        empresa_nombre = email_config['empresa']
        
        if not all([email_origen, email_password, email_destino]):
            logger.warning(f"Configuración de email incompleta para RUC: {ruc}")
            return
        
        # Datos del email
        now = datetime.now()
        formatted_date = now.strftime("%d/%m/%Y")
        formatted_time = now.strftime("%H:%M:%S")
        operation_id = f"MRC-{now.strftime('%Y%m%d%H%M%S')}"
        
        # Crear mensaje
        message = EmailMimeMultipart("alternative")
        message["Subject"] = f"Marcación - {user_data['userName']} ({marking_type})"
        message["From"] = f"Sistema de Marcaciones <{email_origen}>"
        message["To"] = email_destino
        
        # HTML del email
        html_content = build_email_html(
            userName=user_data['userName'],
            userEmail=user_data['userEmail'],
            userDni=user_data['userDni'],
            marcationType=marking_type,
            formattedDate=formatted_date,
            formattedTime=formatted_time,
            empresaNombre=empresa_nombre,
            operationId=operation_id
        )
        
        html_part = EmailMimeText(html_content, "html")
        message.attach(html_part)
        
        # Enviar email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email_origen, email_password)
            server.send_message(message)
        
        logger.info(f"📧 Email enviado exitosamente para {marking_type} - {user_data['userName']}")
        
    except Exception as e:
        logger.error(f"Error enviando email: {e}")

def build_email_html(userName, userEmail, userDni, marcationType, formattedDate, formattedTime, empresaNombre, operationId):
    """Construir HTML del email"""
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ 
                background: linear-gradient(135deg, #2196F3, #1976D2); 
                color: white; padding: 20px; text-align: center; 
                border-radius: 8px 8px 0 0; 
            }}
            .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
            .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .table th, .table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .table th {{ background-color: #f2f2f2; font-weight: bold; }}
            .footer {{ margin-top: 20px; font-size: 12px; color: #666; text-align: center; }}
            .operation-id {{ font-family: monospace; background: #E3F2FD; padding: 2px 6px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🕒 Marcación Registrada</h2>
                <p>{empresaNombre}</p>
                <small>ID: <span class="operation-id">{operationId}</span></small>
            </div>
            <div class="content">
                <table class="table">
                    <tr><td><strong>👤 Usuario:</strong></td><td>{userName}</td></tr>
                    <tr><td><strong>📧 Email:</strong></td><td>{userEmail}</td></tr>
                    <tr><td><strong>🆔 DNI:</strong></td><td>{userDni}</td></tr>
                    <tr><td><strong>📋 Tipo:</strong></td><td><strong>{marcationType}</strong></td></tr>
                    <tr><td><strong>📅 Fecha:</strong></td><td>{formattedDate}</td></tr>
                    <tr><td><strong>⏰ Hora:</strong></td><td><strong>{formattedTime}</strong></td></tr>
                </table>
                
                <div class="footer">
                    <p>📱 Enviado automáticamente por Sistema de Marcaciones</p>
                    <p>⏰ {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
                    <p>🔄 Sistema PWA Flask v2.0</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''