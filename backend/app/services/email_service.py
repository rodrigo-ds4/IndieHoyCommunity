"""
Email Service
Handles email sending and management
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import settings

"""
Email Template Engine
Generates email templates in Spanish for discount responses
"""

from typing import Dict, Any


class EmailTemplateEngine:
    """
    📧 EMAIL TEMPLATE ENGINE - Generates emails in Spanish
    
    All email content generated in Spanish for consistency
    """
    
    def __init__(self):
        pass
    
    def generate_approval_email(self, user_data: Dict[str, Any], show_data: Dict[str, Any]) -> str:
        """Generate approval email in Spanish"""
        return f"""Estimado/a {user_data['name']},

¡Excelente noticia! Su solicitud de descuento ha sido aprobada.

DETALLES DEL SHOW:
• Título: {show_data['title']}
• Artista: {show_data['artist']}
• Venue: {show_data['venue']}
• Fecha: {show_data['show_date']}
• Precio: ${show_data.get('price', 'N/A')}

INSTRUCCIONES PARA EL DESCUENTO:
{show_data.get('discount_instructions', 'Contacte la boletería con este código de aprobación')}

Para cualquier consulta, puede contactarnos respondiendo a este email.

Saludos cordiales,
Equipo IndieHOY"""
    
    def generate_rejection_email(self, user_name: str, reason: str) -> str:
        """Generate rejection email in Spanish"""
        
        # Map technical reasons to user-friendly Spanish messages
        user_friendly_reasons = {
            "no está registrado": "su email no se encuentra en nuestro sistema de suscriptores",
            "cuotas mensuales pendientes": "tiene pagos pendientes que deben regularizarse",
            "suscripción no está activa": "su suscripción necesita ser activada",
            "no encontramos shows": "no hay shows disponibles que coincidan con su búsqueda",
            "ya tiene una solicitud": "ya solicitó un descuento para este show anteriormente",
            "descuentos agotados": "los descuentos para este show se han agotado",
            "sin descuentos": "este show no tiene descuentos disponibles"
        }
        
        friendly_reason = reason
        for key, friendly in user_friendly_reasons.items():
            if key in reason.lower():
                friendly_reason = friendly
                break
        
        return f"""Estimado/a {user_name},

Hemos recibido su solicitud de descuento, pero lamentablemente no podemos procesarla en este momento porque {friendly_reason}.

Por favor:
• Verifique su información de cuenta
• Asegúrese de que sus pagos estén al día
• Contacte nuestro soporte si necesita asistencia

Puede responder a este email para obtener más información.

Saludos cordiales,
Equipo IndieHOY"""


class EmailService:
    """
    Service for sending emails to users
    Handles both approval and rejection emails
    """
    
    def __init__(self):
        # Email configuration would come from settings
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USERNAME', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.from_email = getattr(settings, 'FROM_EMAIL', 'noreply@charrobot.com')
    
    async def send_discount_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        email_content: str,
        request_id: int,
        is_approval: bool = False,
        discount_percentage: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Send discount decision email to user
        
        Returns:
        {
            "sent": bool,
            "message_id": str,
            "error": str (if failed)
        }
        """
        
        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"Charro Bot <{self.from_email}>"
            msg['To'] = to_email
            
            # Create HTML and text versions
            text_content = self._create_text_version(email_content)
            html_content = self._create_html_version(
                email_content, 
                to_name, 
                is_approval, 
                discount_percentage,
                request_id
            )
            
            # Attach parts
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # For development, just log the email instead of sending
            if settings.ENVIRONMENT == "development":
                return await self._log_email_for_dev(msg, to_email, email_content)
            
            # Send email in production
            return await self._send_smtp_email(msg, to_email)
            
        except Exception as e:
            return {
                "sent": False,
                "error": str(e),
                "timestamp": datetime.now()
            }
    
    async def _send_smtp_email(self, msg: MIMEMultipart, to_email: str) -> Dict[str, Any]:
        """Send email via SMTP"""
        
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            text = msg.as_string()
            server.sendmail(self.from_email, to_email, text)
            server.quit()
            
            return {
                "sent": True,
                "message_id": msg.get('Message-ID', 'unknown'),
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            return {
                "sent": False,
                "error": f"SMTP error: {str(e)}",
                "timestamp": datetime.now()
            }
    
    async def _log_email_for_dev(
        self, 
        msg: MIMEMultipart, 
        to_email: str, 
        content: str
    ) -> Dict[str, Any]:
        """Log email to console for development"""
        
        print("\n" + "="*80)
        print("📧 EMAIL SENT (DEVELOPMENT MODE)")
        print("="*80)
        print(f"To: {to_email}")
        print(f"Subject: {msg['Subject']}")
        print(f"From: {msg['From']}")
        print("\nContent:")
        print("-" * 40)
        print(content)
        print("="*80 + "\n")
        
        return {
            "sent": True,
            "message_id": f"dev_{datetime.now().timestamp()}",
            "timestamp": datetime.now(),
            "note": "Email logged to console (development mode)"
        }
    
    def _create_text_version(self, email_content: str) -> str:
        """Create plain text version of email"""
        return email_content
    
    def _create_html_version(
        self,
        email_content: str,
        to_name: str,
        is_approval: bool,
        discount_percentage: Optional[float],
        request_id: int
    ) -> str:
        """Create HTML version of email with styling"""
        
        # Convert line breaks to HTML
        html_content = email_content.replace('\n', '<br>')
        
        # Choose colors based on approval status
        if is_approval:
            header_color = "#10B981"  # Green
            icon = "✅"
        else:
            header_color = "#EF4444"  # Red  
            icon = "❌"
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Respuesta de Descuento</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f7f7f7; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: {header_color}; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 30px; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #666; }}
                .highlight {{ background-color: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{icon} Respuesta a tu Solicitud</h1>
                </div>
                <div class="content">
                    {html_content}
                    
                    {"<div class='highlight'><strong>💰 Descuento otorgado: " + str(discount_percentage) + "%</strong></div>" if is_approval and discount_percentage else ""}
                </div>
                <div class="footer">
                    <p>ID de solicitud: {request_id}</p>
                    <p>© 2024 Charro Bot - Sistema automatizado de descuentos</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    async def send_test_email(self, to_email: str) -> Dict[str, Any]:
        """Send test email for debugging"""
        
        return await self.send_discount_email(
            to_email=to_email,
            to_name="Usuario de Prueba",
            subject="🤖 Email de Prueba - Charro Bot",
            email_content="Este es un email de prueba del sistema Charro Bot.",
            request_id=0,
            is_approval=True,
            discount_percentage=15.0
        )
    
    def validate_email_format(self, email: str) -> bool:
        """Basic email format validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None 