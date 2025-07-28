"""
Template Email Service
Generates emails using dynamic templates stored in the database.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import logging
from sqlalchemy.orm import Session
from app.models.database import Show, User, EmailTemplate

# Configure logging
logger = logging.getLogger(__name__)

class TemplateEmailService:
    """
        DYNAMIC & RELIABLE EMAIL GENERATION
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def _get_template(self, template_name: str) -> Dict[str, str]:
        """
        Fetches an email template from the database.
        Returns a fallback template if not found to ensure system stability.
        """
        template = self.db.query(EmailTemplate).filter(EmailTemplate.template_name == template_name).first()
        if template:
            return {"subject": template.subject, "body": template.body}

        logger.warning(f"Email template '{template_name}' not found in database. Using fallback.")
        
        # Fallback templates to prevent crashes if DB is not populated
        fallbacks = {
            "approval": {
                "subject": "✅ ¡Tu descuento para {show_title} fue aprobado!",
                "body": "¡Hola {user_name}!\n\nBuenas noticias. Tu solicitud de descuento para el show de {show_title} fue aprobada.\n\nSeguí los siguientes pasos:\n{discount_details}\n\nCódigo de Descuento: {discount_code}\n\nPresentá este email en la boletería para hacerlo válido. ¡Que lo disfrutes!\n\n- El equipo de IndieHOY."
            },
            "rejection_user_not_found": {
                "subject": "❌ Solicitud de descuento - Usuario no encontrado",
                "body": "Hola {user_name},\n\nNo pudimos procesar tu solicitud porque el email {user_email} no está registrado."
            }
        }
        
        default_fallback = {
            "subject": "Actualización sobre tu solicitud de descuento",
            "body": "Hubo una actualización sobre tu solicitud de descuento para {show_description}."
        }

        return fallbacks.get(template_name, default_fallback)

    def _replace_placeholders(self, text: str, context: Dict[str, Any]) -> str:
        """
        Replaces placeholders like {key} or {nested.key} in a string with values from a context dict.
        """
        for key, value in context.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text

    def _build_context(self, user: Optional[User] = None, show: Optional[Show] = None, **kwargs) -> Dict[str, Any]:
        """
        Builds a flattened context dictionary for placeholder replacement.
        """
        context = {}
        
        # Flatten user data
        if user:
            context.update({
                "user_name": user.name,
                "user_email": user.email,
            })
        
        # Flatten show data, including other_data
        if show:
            context.update({
                "show_title": show.title,
                "show_artist": show.artist,
                "show_venue": show.venue,
                "show_date": show.show_date.strftime('%d/%m/%Y'),
                "show_code": show.code
            })
            if show.other_data:
                for k, v in show.other_data.items():
                    context[f"other_data.{k}"] = v
        
        # Add any other dynamic data passed to the function
        context.update(kwargs)
        
        # Add a default value for any missing placeholders to avoid errors
        import collections
        context = collections.defaultdict(lambda: '[DATO NO DISPONIBLE]', context)
        
        return context

    def generate_approval_email(self, user: User, show: Show, reasoning: str = "") -> Dict[str, Any]:
        """
        ✅ Genera el email de aprobación usando una plantilla base de la DB
           y los detalles específicos del descuento desde el campo `other_data` del show.
        """
        template = self._get_template("approval")
        
        # 1. El código de descuento se sigue generando de forma única
        discount_code = f"DESC-{show.code}-{uuid.uuid4().hex[:8].upper()}"

        # 2. Los detalles específicos del descuento se leen del JSON del show
        #    Esto hace que cada show pueda tener su propia lógica (2x1, 30%, etc.)
        discount_details = "[No se especificaron detalles para este descuento. Contactar a soporte.]"
        if show.other_data and 'discount_details' in show.other_data:
            discount_details = show.other_data['discount_details']

        # 3. Se construye el contexto para reemplazar los placeholders
        context = self._build_context(
            user=user,
            show=show,
            discount_code=discount_code,
            discount_details=discount_details, # <-- Se inyectan los detalles específicos
            expiry_date=(datetime.now() + timedelta(days=7)).strftime('%d/%m/%Y')
        )
        
        subject = self._replace_placeholders(template["subject"], context)
        content = self._replace_placeholders(template["body"], context)

        return {
            "email_subject": subject,
            "email_content": content,
            "decision_type": "approved",
            "show_id": show.id,
            "confidence_score": 1.0,
            "reasoning": reasoning or f"Discount details extracted from show data.",
            "discount_code": discount_code,
            "discount_percentage": None, # Ya no lo calculamos aquí
        }

    def generate_rejection_email(self, user_name: str, user_email: str, reason_code: str, show_info: str = "") -> Dict[str, Any]:
        """
        ❌ Generate rejection email using a database template based on the reason code.
        """
        template_name = f"rejection_{reason_code}"
        template = self._get_template(template_name)
        
        context = self._build_context(
            user_name=user_name,
            user_email=user_email,
            show_description=show_info
        )
        
        subject = self._replace_placeholders(template["subject"], context)
        content = self._replace_placeholders(template["body"], context)

        return {
            "email_subject": subject,
            "email_content": content,
            "decision_type": "rejected",
            "show_id": None,
            "confidence_score": 1.0,
            "reasoning": f"Automatic rejection: {reason_code}",
            "rejection_reason": reason_code
        } 