"""
Real SMTP Email Service
Handles actual email sending via SMTP for production use
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

class SMTPEmailService:
    """
    🔥 Servicio real de envío de emails via SMTP
    
    Características:
    - Envío real de emails via SMTP
    - Soporte para Gmail, Outlook, etc.
    - Logging detallado
    - Manejo de errores robusto
    - Modo de prueba (logs sin enviar)
    """
    
    def __init__(self, db_session=None):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.email_enabled = settings.EMAIL_ENABLED
        self.db_session = db_session  # Para actualizar estados en DB
        
        logger.info(f"📧 SMTP Service initialized - Host: {self.smtp_host}:{self.smtp_port}")
        logger.info(f"📧 Email enabled: {self.email_enabled}")
        
        if not self.smtp_user or not self.smtp_password:
            logger.warning("⚠️ SMTP credentials not configured")
    
    def _update_delivery_status(self, supervision_queue_id: int, status: str):
        """Actualizar estado de entrega en la base de datos"""
        if not self.db_session or not supervision_queue_id:
            return
            
        try:
            from app.models.database import SupervisionQueue
            
            item = self.db_session.query(SupervisionQueue).filter(
                SupervisionQueue.id == supervision_queue_id
            ).first()
            
            if item:
                item.email_delivery_status = status
                self.db_session.commit()
                logger.info(f"📊 Updated delivery status for item {supervision_queue_id}: {status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update delivery status: {str(e)}")
            if self.db_session:
                self.db_session.rollback()
    
    def send_email(
        self, 
        to_email: str, 
        subject: str, 
        content: str, 
        user_name: str = None,
        metadata: Dict[str, Any] = None,
        supervision_queue_id: int = None
    ) -> Dict[str, Any]:
        """
        📨 Enviar email real via SMTP con mejores prácticas anti-spam
        
        Args:
            to_email: Email del destinatario
            subject: Asunto del email
            content: Contenido del email (texto plano)
            user_name: Nombre del usuario (opcional)
            metadata: Datos adicionales para logging
            supervision_queue_id: ID del item en supervision_queue para actualizar estado
            
        Returns:
            dict: Resultado del envío con status y detalles
        """
        try:
            # Preparar datos del email
            timestamp = datetime.now().isoformat()
            
            result = {
                "success": False,
                "timestamp": timestamp,
                "to_email": to_email,
                "subject": subject,
                "method": "smtp",
                "enabled": self.email_enabled
            }
            
            # Validar configuración
            if not self.smtp_user or not self.smtp_password:
                error_msg = "SMTP credentials not configured"
                logger.warning(f"⚠️ {error_msg}")
                result.update({
                    "error": error_msg,
                    "message": "Email sending requires SMTP_USER and SMTP_PASSWORD",
                    "mode": "error"
                })
                # Actualizar estado como failed
                if supervision_queue_id:
                    self._update_delivery_status(supervision_queue_id, "failed")
                return result
            
            # Crear mensaje con mejores prácticas anti-spam
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Message-ID'] = f"<{timestamp.replace(':', '').replace('-', '')}@{self.from_email.split('@')[1]}>"
            msg['Date'] = formataddr(('', timestamp))
            
            # Crear versión texto plano (importante para deliverability)
            text_content = self._create_text_version(content)
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            
            # Crear versión HTML profesional
            html_content = self._create_professional_html(content, user_name or "Usuario")
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            # Agregar ambas versiones (mejora deliverability)
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Log del intento de envío
            logger.info(f"📧 Attempting to send email to {to_email}")
            logger.info(f"📧 Subject: {subject}")
            
            if not self.email_enabled:
                # Modo de prueba - solo logging
                logger.info("📧 EMAIL DISABLED - Would send:")
                logger.info(f"   To: {to_email}")
                logger.info(f"   Subject: {subject}")
                logger.info(f"   Content preview: {content[:100]}...")
                logger.info(f"   HTML version created: {len(html_content)} chars")
                
                result.update({
                    "success": True,
                    "message": "Email logged (sending disabled)",
                    "mode": "test"
                })
                # En modo test, marcar como "sent" para testing
                if supervision_queue_id:
                    self._update_delivery_status(supervision_queue_id, "sent")
                return result
            
            # Envío real via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Habilitar TLS
                server.login(self.smtp_user, self.smtp_password)
                
                # Enviar mensaje
                text = msg.as_string()
                server.sendmail(self.from_email, to_email, text)
                
                logger.info(f"✅ Email sent successfully to {to_email}")
                
                result.update({
                    "success": True,
                    "message": "Email sent successfully",
                    "mode": "production",
                    "smtp_host": self.smtp_host
                })
                
                # Actualizar estado como sent (en producción sería "delivered" con webhook)
                if supervision_queue_id:
                    self._update_delivery_status(supervision_queue_id, "sent")
                
                return result
                
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP Authentication failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            result.update({
                "success": False,
                "error": "authentication_failed",
                "message": error_msg,
                "mode": "error"
            })
            if supervision_queue_id:
                self._update_delivery_status(supervision_queue_id, "failed")
            return result
            
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipient refused: {str(e)}"
            logger.error(f"❌ {error_msg}")
            result.update({
                "success": False,
                "error": "recipient_refused",
                "message": error_msg,
                "mode": "error"
            })
            if supervision_queue_id:
                self._update_delivery_status(supervision_queue_id, "bounced")
            return result
            
        except Exception as e:
            error_msg = f"Email sending failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            result.update({
                "success": False,
                "error": "general_error", 
                "message": error_msg,
                "mode": "error"
            })
            if supervision_queue_id:
                self._update_delivery_status(supervision_queue_id, "failed")
            return result
    
    def _create_text_version(self, content: str) -> str:
        """Crear versión texto plano limpia"""
        # Remover HTML si existe
        import re
        text = re.sub(r'<[^>]+>', '', content)
        # Limpiar espacios extra
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _create_professional_html(self, content: str, user_name: str) -> str:
        """Crear versión HTML profesional anti-spam"""
        
        # Convertir saltos de línea a HTML
        html_content = content.replace('\n', '<br>')
        
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>IndieHOY - Sistema de Descuentos</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">🎵 IndieHOY</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Sistema de Descuentos</p>
            </div>
            
            <!-- Content -->
            <div style="background: white; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
                <h2 style="color: #2c3e50; margin-bottom: 20px;">¡Hola {user_name}!</h2>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; border-left: 4px solid #667eea;">
                    {html_content}
                </div>
                
                <div style="margin: 30px 0; text-align: center;">
                    <p style="color: #7f8c8d; font-size: 14px;">Este email fue enviado automáticamente por el sistema de IndieHOY</p>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #34495e; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px;">
                <p style="margin: 0; font-size: 14px;">© 2024 IndieHOY - Plataforma de eventos independientes</p>
                <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.8;">
                    Si no solicitaste este descuento, puedes ignorar este email.
                </p>
            </div>
            
        </body>
        </html>
        """
    
    def send_discount_email(
        self, 
        supervision_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        📧 Enviar email de descuento (aprobado o rechazado)
        
        Args:
            supervision_item: Item de la cola de supervisión
            
        Returns:
            dict: Resultado del envío
        """
        try:
            return self.send_email(
                to_email=supervision_item['user_email'],
                subject=supervision_item['email_subject'],
                content=supervision_item['email_content'],
                user_name=supervision_item['user_name'],
                metadata={
                    'item_id': supervision_item['id'],
                    'show_description': supervision_item['show_description'],
                    'decision_type': supervision_item['decision_type'],
                    'status': supervision_item['status']
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error sending discount email: {str(e)}")
            return {
                "success": False,
                "error": "processing_error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        🧪 Probar conexión SMTP
        
        Returns:
            dict: Resultado de la prueba de conexión
        """
        try:
            logger.info("🧪 Testing SMTP connection...")
            
            if not self.smtp_user or not self.smtp_password:
                return {
                    "success": False,
                    "error": "Credentials not configured",
                    "message": "SMTP_USER and SMTP_PASSWORD are required"
                }
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                
                logger.info("✅ SMTP connection successful")
                return {
                    "success": True,
                    "message": "SMTP connection successful",
                    "host": self.smtp_host,
                    "port": self.smtp_port,
                    "user": self.smtp_user
                }
                
        except Exception as e:
            error_msg = f"SMTP connection failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": "connection_failed",
                "message": error_msg
            } 