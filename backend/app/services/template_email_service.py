"""
Template Email Service
Replaces LLM with fixed templates and real database data
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from sqlalchemy.orm import Session
from app.models.database import Show, User


class TemplateEmailService:
    """
    🚀 SIMPLE & RELIABLE EMAIL GENERATION
    
    Uses fixed templates with real database data instead of LLM.
    Benefits:
    - ⚡ Super fast (< 100ms)
    - 🎯 100% reliable 
    - 🚫 No hallucinations
    - 📧 Consistent formatting
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def generate_approval_email(self, user: User, show: Show, reasoning: str = "") -> Dict[str, Any]:
        """
        ✅ Generate approval email with real data from database
        """
        discount_code = f"DESC-{show.code}-{uuid.uuid4().hex[:8].upper()}"
        discount_percentage = 15  # Fixed 15% discount
        original_price = show.other_data.get('price', 0) if show.other_data else 0
        discounted_price = int(original_price * 0.85)  # 15% off
        
        subject = f"✅ Descuento Aprobado - {show.title}"
        
        content = f"""Estimado/a {user.name},

¡Excelente noticia! Su solicitud de descuento ha sido APROBADA.

🎫 DETALLES DEL SHOW:
• Show: {show.title}
• Artista: {show.artist}
• Venue: {show.venue}
• Fecha: {show.show_date.strftime('%d/%m/%Y')}

💰 INFORMACIÓN DEL DESCUENTO:
• Precio original: ${original_price:,}
• Descuento: {discount_percentage}%
• Precio final: ${discounted_price:,}
• Código de descuento: {discount_code}

📧 INSTRUCCIONES:
1. Presente este email en la boletería
2. Mencione el código: {discount_code}
3. Válido hasta: {(datetime.now() + timedelta(days=7)).strftime('%d/%m/%Y')}

Disfrute del show!

Saludos cordiales,
Equipo IndieHOY

---
Este descuento es personal e intransferible.
Un descuento por persona por show."""

        return {
            "email_subject": subject,
            "email_content": content,
            "decision_type": "approved",
            "show_id": show.id,
            "confidence_score": 1.0,
            "reasoning": reasoning or f"Show disponible con {show.get_remaining_discounts(self.db)} descuentos restantes",
            "discount_code": discount_code,
            "discount_percentage": discount_percentage,
            "original_price": original_price,
            "discounted_price": discounted_price
        }
    
    def generate_rejection_email(self, user_name: str, user_email: str, reason_code: str, show_info: str = "") -> Dict[str, Any]:
        """
        ❌ Generate rejection email with specific reason
        """
        
        reasons = {
            "user_not_found": {
                "subject": "❌ Usuario no registrado",
                "content": f"""Estimado/a {user_name},

Lamentamos informarle que no pudimos procesar su solicitud de descuento.

❌ MOTIVO DEL RECHAZO:
Su email ({user_email}) no se encuentra registrado en nuestra base de datos de suscriptores.

✅ SOLUCIÓN:
1. Verifique que está usando el email correcto
2. Complete su registro en nuestra plataforma
3. Asegúrese de tener una suscripción activa

Para registrarse o consultas, contáctenos a info@indiehoy.com

Saludos cordiales,
Equipo IndieHOY"""
            },
            "payment_overdue": {
                "subject": "❌ Pagos pendientes",
                "content": f"""Estimado/a {user_name},

Lamentamos informarle que no pudimos procesar su solicitud de descuento.

❌ MOTIVO DEL RECHAZO:
Su cuenta tiene pagos pendientes que deben ser regularizados.

✅ SOLUCIÓN:
1. Regularice sus pagos pendientes
2. Una vez al día con los pagos, podrá solicitar descuentos nuevamente

Para consultas sobre pagos, contáctenos a pagos@indiehoy.com

Saludos cordiales,
Equipo IndieHOY"""
            },
            "subscription_inactive": {
                "subject": "❌ Suscripción inactiva",
                "content": f"""Estimado/a {user_name},

Lamentamos informarle que no pudimos procesar su solicitud de descuento.

❌ MOTIVO DEL RECHAZO:
Su suscripción se encuentra inactiva.

✅ SOLUCIÓN:
1. Active su suscripción
2. Una vez activa, podrá solicitar descuentos

Para reactivar su suscripción, contáctenos a suscripciones@indiehoy.com

Saludos cordiales,
Equipo IndieHOY"""
            },
            "no_discounts_available": {
                "subject": "❌ Sin descuentos disponibles",
                "content": f"""Estimado/a {user_name},

Lamentamos informarle que no hay descuentos disponibles para el show solicitado.

🎭 SHOW SOLICITADO:
{show_info}

❌ MOTIVO DEL RECHAZO:
Los descuentos para este show se han agotado.

✅ RECOMENDACIONES:
• Esté atento a nuestras próximas promociones
• Suscríbase a nuestras notificaciones para enterarse primero

Saludos cordiales,
Equipo IndieHOY"""
            },
            "duplicate_request": {
                "subject": "❌ Solicitud duplicada",
                "content": f"""Estimado/a {user_name},

Ya ha solicitado un descuento para este show recientemente.

🎭 SHOW:
{show_info}

❌ MOTIVO DEL RECHAZO:
Solo se permite una solicitud de descuento por persona por show.

✅ INFORMACIÓN:
Revise su email para la respuesta de su solicitud anterior.

Saludos cordiales,
Equipo IndieHOY"""
            }
        }
        
        template = reasons.get(reason_code, reasons["user_not_found"])
        
        return {
            "email_subject": template["subject"],
            "email_content": template["content"],
            "decision_type": "rejected",
            "show_id": None,
            "confidence_score": 1.0,
            "reasoning": f"Rechazo automático: {reason_code}",
            "rejection_reason": reason_code
        }
    
    def generate_clarification_email(self, user_name: str, user_email: str, available_shows: list, user_query: str) -> Dict[str, Any]:
        """
        ❓ Generate clarification email when multiple shows match
        """
        subject = "❓ Aclaración necesaria - Seleccione su show"
        
        shows_list = ""
        for i, show in enumerate(available_shows, 1):
            price = show.other_data.get('price', 'N/A') if show.other_data else 'N/A'
            remaining = show.get_remaining_discounts(self.db)
            shows_list += f"""
{i}. {show.title} - {show.artist}
   📍 Venue: {show.venue}
   📅 Fecha: {show.show_date.strftime('%d/%m/%Y')}
   💰 Precio: ${price}
   🎫 Descuentos disponibles: {remaining}
"""
        
        content = f"""Estimado/a {user_name},

Recibimos su solicitud de descuento, pero necesitamos una aclaración.

🔍 USTED SOLICITÓ:
"{user_query}"

❓ PROBLEMA:
Encontramos múltiples shows que coinciden con su búsqueda.

🎭 SHOWS DISPONIBLES CON DESCUENTOS:
{shows_list}

✅ PRÓXIMOS PASOS:
1. Responda este email indicando el número del show que desea
2. O visite nuestro formulario web para seleccionar directamente
3. Procesaremos su solicitud inmediatamente

🔗 Formulario web: http://localhost:8000/request

Saludos cordiales,
Equipo IndieHOY

---
Este email es generado automáticamente por nuestro sistema."""

        return {
            "email_subject": subject,
            "email_content": content,
            "decision_type": "needs_clarification",
            "show_id": None,
            "confidence_score": 0.8,
            "reasoning": f"Múltiples shows encontrados para: {user_query}",
            "available_shows": [show.id for show in available_shows]
        } 