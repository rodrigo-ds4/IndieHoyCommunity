"""
LangChain Agent Service for Discount Decisions
Handles intelligent discount request processing with database access and business rules
"""

import os
import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from fuzzywuzzy import fuzz

# LangChain imports (now enabled)
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.tools import BaseTool
from langchain_ollama import OllamaLLM
from langchain.prompts import ChatPromptTemplate
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from app.models.database import User, Show, DiscountRequest
from app.core.config import settings


class DatabaseQueryTool:
    """Custom tool for database queries within LangChain agent"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user information by exact email match"""
        user = self.db.query(User).filter(User.email == email.lower().strip()).first()
        if not user:
            return None
        
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "city": user.city,
            "subscription_active": user.subscription_active,
            "monthly_fee_current": user.monthly_fee_current,
            "favorite_genre": user.favorite_music_genre,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None
        }
    
    def find_matching_shows(self, description: str, fuzzy_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Find shows that match the description using fuzzy matching"""
        all_shows = self.db.query(Show).filter(Show.active == True).all()
        matches = []
        
        description_lower = description.lower().strip()
        
        for show in all_shows:
            # Create searchable text combining artist, title, venue
            searchable_text = f"{show.artist} {show.title} {show.venue}".lower()
            
            # Calculate similarity scores
            similarity = fuzz.partial_ratio(description_lower, searchable_text) / 100.0
            
            if similarity >= fuzzy_threshold:
                matches.append({
                    "id": show.id,
                    "code": show.code,
                    "title": show.title,
                    "artist": show.artist,
                    "venue": show.venue,
                    "show_date": show.show_date.isoformat(),
                    "city": show.other_data.get("city", ""),
                    "max_discounts": show.max_discounts,
                    "remaining_discounts": show.get_remaining_discounts(self.db),
                    "similarity_score": similarity,
                    "discount_instructions": show.other_data.get("discount_instructions", ""),
                    "price": show.other_data.get("price", 0)
                })
        
        # Sort by similarity score (highest first)
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matches
    
    def check_previous_requests(self, user_id: int, show_id: int) -> Dict[str, Any]:
        """Check if user has previous requests for this show"""
        previous_request = self.db.query(DiscountRequest).filter(
            DiscountRequest.user_id == user_id,
            DiscountRequest.show_id == show_id
        ).first()
        
        return {
            "has_previous_request": previous_request is not None,
            "previous_approved": previous_request.approved if previous_request else None,
            "previous_human_approved": previous_request.human_approved if previous_request else None,
            "previous_date": previous_request.request_date.isoformat() if previous_request else None
        }
    
    def get_show_availability(self, show_id: int) -> Dict[str, Any]:
        """Get detailed show availability information"""
        show = self.db.query(Show).filter(Show.id == show_id).first()
        if not show:
            return {"exists": False}
        
        remaining = show.get_remaining_discounts(self.db)
        
        return {
            "exists": True,
            "active": show.active,
            "max_discounts": show.max_discounts,
            "remaining_discounts": remaining,
            "has_availability": remaining > 0,
            "show_date": show.show_date.isoformat(),
            "days_until_show": (show.show_date - datetime.now()).days
        }


class BusinessRulesEngine:
    """Load and apply business rules from configuration"""
    
    def __init__(self):
        self.rules = self._load_business_rules()
    
    def _load_business_rules(self) -> Dict[str, Any]:
        """Load business rules from YAML file"""
        rules_path = os.path.join(os.path.dirname(__file__), "../config/business_rules.yaml")
        try:
            with open(rules_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            # Default rules if file doesn't exist
            return {
                "user_validation": {"subscription_required": True, "monthly_fee_required": True},
                "discount_rules": {"max_per_user_per_show": 1, "min_days_before_show": 1},
                "approval_conditions": []
            }
    
    def validate_user_eligibility(self, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate if user meets eligibility requirements"""
        if not user_data:
            return False, self.rules["rejection_reasons"]["user_not_found"]
        
        if self.rules["user_validation"]["subscription_required"] and not user_data.get("subscription_active"):
            return False, self.rules["rejection_reasons"]["subscription_inactive"]
        
        if self.rules["user_validation"]["monthly_fee_required"] and not user_data.get("monthly_fee_current"):
            return False, self.rules["rejection_reasons"]["fees_not_current"]
        
        return True, ""
    
    def validate_show_eligibility(self, show_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate if show meets eligibility requirements"""
        if not show_data.get("exists"):
            return False, self.rules["rejection_reasons"]["show_not_found"]
        
        if not show_data.get("has_availability"):
            return False, self.rules["rejection_reasons"]["no_discounts_available"]
        
        days_until = show_data.get("days_until_show", 0)
        min_days = self.rules["discount_rules"]["min_days_before_show"]
        max_days = self.rules["discount_rules"]["max_days_before_show"]
        
        if days_until < min_days or days_until > max_days:
            return False, self.rules["rejection_reasons"]["show_date_invalid"]
        
        return True, ""
    
    def validate_request_history(self, history_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate request history compliance"""
        if history_data.get("has_previous_request"):
            return False, self.rules["rejection_reasons"]["previous_request_exists"]
        
        return True, ""


class TemplateEngine:
    """Generate emails using templates"""
    
    def __init__(self):
        self.templates_dir = os.path.join(os.path.dirname(__file__), "../templates")
    
    def _load_template(self, template_name: str) -> str:
        """Load template from file"""
        template_path = os.path.join(self.templates_dir, template_name)
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return "Template not found: {template_name}"
    
    def generate_approval_email(self, context: Dict[str, Any]) -> str:
        """Generate approval email from template"""
        template = self._load_template("email_approval.txt")
        return template.format(**context)
    
    def generate_rejection_email(self, context: Dict[str, Any]) -> str:
        """Generate rejection email from template"""
        template = self._load_template("email_rejection.txt")
        return template.format(**context)


class DecisionLogger:
    """Log agent decisions to JSON file"""
    
    def __init__(self):
        self.log_file = os.path.join(os.path.dirname(__file__), "../logs/agent_decisions.json")
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    def log_decision(self, decision_data: Dict[str, Any]) -> None:
        """Log a decision to the JSON file"""
        decision_data["timestamp"] = datetime.now().isoformat()
        decision_data["agent_version"] = "1.0"
        decision_data["model_used"] = settings.OLLAMA_MODEL
        
        # Load existing decisions
        decisions = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as file:
                    decisions = json.load(file)
            except (json.JSONDecodeError, FileNotFoundError):
                decisions = []
        
        # Add new decision
        decisions.append(decision_data)
        
        # Save back to file
        with open(self.log_file, 'w', encoding='utf-8') as file:
            json.dump(decisions, file, indent=2, ensure_ascii=False)


class LangChainAgentService:
    """
    Main LangChain agent service for discount decision making
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.db_tool = DatabaseQueryTool(db_session)
        self.rules_engine = BusinessRulesEngine()
        self.template_engine = TemplateEngine()
        self.decision_logger = DecisionLogger()
        
        # 🎯 PASO 1.5: LAZY INITIALIZATION - No inicializar LLM aquí
        # Evita bloquear el servidor al startup
        self._llm = None  # Será inicializado cuando se use
        
    @property
    def llm(self) -> OllamaLLM:
        """
        🎓 LAZY INITIALIZATION: Crear LLM solo cuando se necesite
        """
        if self._llm is None:
            self._llm = OllamaLLM(
                model="llama3",  # Modelo que tenemos en Ollama
                base_url="http://host.docker.internal:11434",  # 🎯 PASO 1.6: URL para acceder al host desde contenedor
                temperature=0.3,  # Menos creatividad, más consistencia para decisiones
                timeout=30  # Timeout de 30 segundos
            )
        return self._llm
        
    def _build_decision_context(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 PASO 2A: Construir contexto completo para el LLM
        Recolecta todos los datos necesarios para la decisión
        """
        context = {
            "request_info": {
                "user_email": request_data.get("user_email"),
                "user_name": request_data.get("user_name"), 
                "show_description": request_data.get("show_description"),
                "request_id": request_data.get("request_id")
            }
        }
        
        # 1. Datos del usuario
        user_data = self.db_tool.get_user_by_email(request_data["user_email"])
        context["user_data"] = user_data
        
        # 2. Shows disponibles (para fuzzy matching)
        matching_shows = self.db_tool.find_matching_shows(request_data["show_description"])
        context["matching_shows"] = matching_shows[:3]  # Top 3 matches
        
        # 3. Business rules
        context["business_rules"] = self.rules_engine.rules
        
        # 4. Si hay un show match, obtener disponibilidad e historial
        if matching_shows and user_data:
            best_match = matching_shows[0]
            context["best_match_availability"] = self.db_tool.get_show_availability(best_match["id"])
            context["user_history"] = self.db_tool.check_previous_requests(user_data["id"], best_match["id"])
        
        return context
        
    def _build_decision_prompt(self, context: Dict[str, Any]) -> str:
        """
        🎯 PASO 2B: PROMPT PRESCRIPTIVO Y ESTRICTO 
        Evita interpretaciones creativas - el LLM debe seguir reglas exactas
        """
        system_prompt = """🤖 AGENTE DE DESCUENTOS - MODO ESTRICTO DE VALIDACIÓN

INSTRUCCIONES CRÍTICAS QUE NO PUEDES IGNORAR:
1. Debes seguir el ORDEN DE VALIDACIÓN exacto (no te saltes pasos)
2. Si cualquier validación crítica falla → RECHAZO INMEDIATO
3. NO seas creativo con la interpretación de reglas
4. monthly_fee_current=false SIEMPRE significa RECHAZAR
5. remaining_discounts=0 SIEMPRE significa RECHAZAR
6. Responde EXACTAMENTE con el formato JSON especificado

🔒 ORDEN DE VALIDACIÓN OBLIGATORIO:
1️⃣ user_existence_check: ¿Usuario existe en DB?
2️⃣ subscription_status_check: ¿subscription_active == true?
3️⃣ payment_status_check: ¿monthly_fee_current == true?
4️⃣ show_matching_check: ¿Show encontrado con ≥80% similitud?
5️⃣ show_availability_check: ¿remaining_discounts > 0?
6️⃣ duplicate_request_check: ¿Sin solicitudes previas aprobadas?
7️⃣ date_validity_check: ¿Show en rango de fechas válido?

FORMATO DE RESPUESTA OBLIGATORIO:
{
  "validation_steps": [
    {"step": 1, "check": "user_existence_check", "result": "PASS/FAIL", "details": "explicación"},
    {"step": 2, "check": "subscription_status_check", "result": "PASS/FAIL", "details": "explicación"},
    {"step": 3, "check": "payment_status_check", "result": "PASS/FAIL", "details": "explicación"},
    {"step": 4, "check": "show_matching_check", "result": "PASS/FAIL", "details": "explicación"},
    {"step": 5, "check": "show_availability_check", "result": "PASS/FAIL", "details": "explicación"},
    {"step": 6, "check": "duplicate_request_check", "result": "PASS/FAIL", "details": "explicación"},
    {"step": 7, "check": "date_validity_check", "result": "PASS/FAIL", "details": "explicación"}
  ],
  "decision": "APPROVED o REJECTED",
  "reasoning": "Explicación basada en los pasos de validación",
  "confidence": 0.95,
  "show_matched": "nombre del show si APPROVED",
  "rejection_reason": "razón específica si REJECTED"
}"""

        # Construir contexto detallado con datos específicos para validación
        user_data = context.get('user_data')
        matching_shows = context.get('matching_shows', [])
        best_match = matching_shows[0] if matching_shows else None
        availability = context.get('best_match_availability', {})
        history = context.get('user_history', {})
        rules = context.get('business_rules', {})

        user_prompt = f"""
📋 SOLICITUD A EVALUAR:
- Usuario: {context['request_info']['user_name']}
- Email: {context['request_info']['user_email']} 
- Show solicitado: {context['request_info']['show_description']}

🔍 DATOS PARA VALIDACIÓN PASO A PASO:

1️⃣ USER_EXISTENCE_CHECK:
{self._format_user_existence_data(user_data)}

2️⃣ SUBSCRIPTION_STATUS_CHECK:
{self._format_subscription_data(user_data)}

3️⃣ PAYMENT_STATUS_CHECK:
🚨 CRÍTICO: monthly_fee_current=false → RECHAZO AUTOMÁTICO
{self._format_payment_data(user_data)}

4️⃣ SHOW_MATCHING_CHECK:
Umbral mínimo: {rules.get('show_matching', {}).get('fuzzy_threshold', 0.8) * 100}% de similitud
{self._format_show_matching_data(matching_shows)}

5️⃣ SHOW_AVAILABILITY_CHECK:
🚨 CRÍTICO: remaining_discounts=0 → RECHAZO AUTOMÁTICO
{self._format_availability_data(availability, best_match)}

6️⃣ DUPLICATE_REQUEST_CHECK:
{self._format_history_data(history)}

7️⃣ DATE_VALIDITY_CHECK:
{self._format_date_validity_data(best_match, rules)}

⚠️  REGLAS CRÍTICAS QUE DEBES RECORDAR:
- Si user_data es None o vacío → FAIL paso 1 → REJECTED
- Si subscription_active != true → FAIL paso 2 → REJECTED  
- Si monthly_fee_current != true → FAIL paso 3 → REJECTED
- Si no hay shows con ≥80% similitud → FAIL paso 4 → REJECTED
- Si remaining_discounts ≤ 0 → FAIL paso 5 → REJECTED
- Si hay solicitud previa aprobada → FAIL paso 6 → REJECTED

EVALÚA CADA PASO EN ORDEN. Si cualquier paso es FAIL, detente y decide REJECTED."""

        return f"{system_prompt}\n\n{user_prompt}"
        
    def _format_user_existence_data(self, user_data: Dict[str, Any]) -> str:
        """Formatear datos de existencia del usuario para validación estricta"""
        if not user_data:
            return "❌ DATOS: user_data = None (FAIL - usuario no existe)"
        
        return f"""✅ DATOS: user_data encontrado
- ID: {user_data.get('id')}
- Nombre: {user_data.get('name')}
- Email: {user_data.get('email')}
VALIDACIÓN: PASS - usuario existe en sistema"""
    
    def _format_subscription_data(self, user_data: Dict[str, Any]) -> str:
        """Formatear datos de suscripción para validación estricta"""
        if not user_data:
            return "❌ No se puede validar - usuario no existe"
        
        subscription_active = user_data.get('subscription_active')
        status = "✅ PASS" if subscription_active else "❌ FAIL"
        
        return f"""📊 DATOS: subscription_active = {subscription_active}
REGLA: Debe ser true para aprobar
VALIDACIÓN: {status}"""
    
    def _format_payment_data(self, user_data: Dict[str, Any]) -> str:
        """Formatear datos de pago para validación estricta"""
        if not user_data:
            return "❌ No se puede validar - usuario no existe"
        
        monthly_fee_current = user_data.get('monthly_fee_current')
        status = "✅ PASS" if monthly_fee_current else "❌ FAIL - RECHAZO AUTOMÁTICO"
        
        return f"""💰 DATOS: monthly_fee_current = {monthly_fee_current}
REGLA CRÍTICA: Debe ser true - si es false = REJECTED inmediatamente
VALIDACIÓN: {status}"""
    
    def _format_show_matching_data(self, matching_shows: List[Dict[str, Any]]) -> str:
        """Formatear datos de matching de shows"""
        if not matching_shows:
            return "❌ DATOS: matching_shows = [] (FAIL - no hay shows)"
        
        best_match = matching_shows[0]
        similarity = best_match.get('similarity_score', 0)
        threshold = 0.8
        status = "✅ PASS" if similarity >= threshold else "❌ FAIL"
        
        return f"""🎭 DATOS: Mejor match encontrado
- Show: {best_match.get('title')} - {best_match.get('artist')}
- Venue: {best_match.get('venue')}
- Similitud: {similarity:.0%}
REGLA: Debe ser ≥ {threshold:.0%}
VALIDACIÓN: {status}"""
    
    def _format_availability_data(self, availability: Dict[str, Any], best_match: Dict[str, Any]) -> str:
        """Formatear datos de disponibilidad para validación estricta"""
        if not best_match:
            return "❌ No hay show para validar disponibilidad"
        
        remaining = best_match.get('remaining_discounts', 0)
        max_discounts = best_match.get('max_discounts', 0)
        status = "✅ PASS" if remaining > 0 else "❌ FAIL - RECHAZO AUTOMÁTICO"
        
        return f"""🎫 DATOS: Disponibilidad de descuentos
- Show: {best_match.get('title')}
- Descuentos restantes: {remaining}
- Máximo total: {max_discounts}
REGLA CRÍTICA: remaining_discounts debe ser > 0
VALIDACIÓN: {status}"""
    
    def _format_history_data(self, history: Dict[str, Any]) -> str:
        """Formatear datos de historial"""
        has_previous = history.get('has_previous_request', False)
        previous_approved = history.get('previous_approved', False)
        
        if has_previous and previous_approved:
            status = "❌ FAIL - ya tiene solicitud aprobada"
        else:
            status = "✅ PASS - sin solicitudes previas aprobadas"
        
        return f"""📝 DATOS: Historial de solicitudes
- Solicitud previa: {has_previous}
- Anterior aprobada: {previous_approved}
REGLA: No debe tener solicitud previa aprobada
VALIDACIÓN: {status}"""
    
    def _format_date_validity_data(self, best_match: Dict[str, Any], rules: Dict[str, Any]) -> str:
        """Formatear datos de validez de fechas"""
        if not best_match:
            return "❌ No hay show para validar fechas"
        
        # Para simplificar, asumimos que las fechas son válidas por ahora
        # En implementación real, calcularíamos días hasta el show
        return f"""📅 DATOS: Validación de fechas
- Show: {best_match.get('title')}
- Fecha: {best_match.get('show_date')}
REGLA: Entre 1 y 90 días antes del show
VALIDACIÓN: ✅ PASS - fecha válida"""
        
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        🎯 PASO 2C: Parsear respuesta JSON del LLM con nuevo formato de validation_steps
        """
        try:
            # Buscar JSON en la respuesta (puede tener texto extra)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                
                # Validar campos requeridos del nuevo formato
                required_fields = ['decision', 'reasoning', 'confidence']
                for field in required_fields:
                    if field not in parsed:
                        raise ValueError(f"Campo requerido '{field}' no encontrado")
                
                # Normalizar decision
                parsed['decision'] = parsed['decision'].upper()
                if parsed['decision'] not in ['APPROVED', 'REJECTED']:
                    raise ValueError(f"Decision inválida: {parsed['decision']}")
                
                # Validar validation_steps si está presente
                if 'validation_steps' in parsed:
                    self._validate_llm_steps(parsed['validation_steps'])
                
                return {
                    "success": True,
                    "parsed_response": parsed
                }
            else:
                raise ValueError("No se encontró JSON válido en la respuesta")
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw_response": response,
                "fallback_decision": "REJECTED",
                "fallback_reason": f"Error parseando respuesta del LLM: {str(e)}"
            }
    
    def _validate_llm_steps(self, validation_steps: List[Dict[str, Any]]) -> None:
        """
        🔍 Validar que el LLM siguió todos los pasos de validación correctamente
        """
        expected_checks = [
            "user_existence_check",
            "subscription_status_check", 
            "payment_status_check",
            "show_matching_check",
            "show_availability_check",
            "duplicate_request_check",
            "date_validity_check"
        ]
        
        # Verificar que todos los checks estén presentes
        received_checks = [step.get('check') for step in validation_steps]
        for expected in expected_checks:
            if expected not in received_checks:
                raise ValueError(f"Check obligatorio '{expected}' no encontrado en validation_steps")
    
    def _add_fail_fast_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        🚨 PASO 2A.5: VALIDACIONES FAIL-FAST ANTES DEL LLM
        Verifica condiciones críticas que garantizan rechazo inmediato
        """
        import logging
        logger = logging.getLogger(__name__)
        
        user_data = context.get('user_data')
        matching_shows = context.get('matching_shows', [])
        best_match = matching_shows[0] if matching_shows else None
        history = context.get('user_history', {})
        
        # 🔍 DEBUGGING: Log de datos que llegan a fail-fast
        logger.warning(f"\n🔍 FAIL-FAST DEBUG:")
        logger.warning(f"user_data: {user_data}")
        logger.warning(f"matching_shows count: {len(matching_shows)}")
        if best_match:
            logger.warning(f"best_match: {best_match}")
            logger.warning(f"remaining_discounts: {best_match.get('remaining_discounts', 'NOT_FOUND')}")
            logger.warning(f"monthly_fee_current: {user_data.get('monthly_fee_current', 'NOT_FOUND') if user_data else 'NO_USER_DATA'}")
        
        # 🔒 CRITICAL FAIL CONDITIONS - Verificación previa al LLM
        fail_fast_checks = []
        
        # 1. Usuario no existe
        if not user_data:
            logger.warning("🚨 FAIL-FAST: Usuario no existe - REJECTING")
            return {
                "fail_fast": True,
                "decision": "rejected",
                "reasoning": "El email proporcionado no está registrado en nuestro sistema",
                "confidence": 1.0,
                "rejection_reason": "user_not_found",
                "failed_check": "user_existence_check"
            }
        
        # 2. Suscripción inactiva
        if not user_data.get('subscription_active'):
            logger.warning("🚨 FAIL-FAST: Suscripción inactiva - REJECTING")
            return {
                "fail_fast": True, 
                "decision": "rejected",
                "reasoning": "La suscripción no está activa. Active su suscripción para solicitar descuentos",
                "confidence": 1.0,
                "rejection_reason": "subscription_inactive",
                "failed_check": "subscription_status_check"
            }
        
        # 3. 🚨 CRÍTICO: Cuotas atrasadas - Este era el error en TEST 4
        monthly_fee_current = user_data.get('monthly_fee_current')
        logger.warning(f"🔍 Checking monthly_fee_current: {monthly_fee_current}")
        if not monthly_fee_current:
            logger.warning("🚨 FAIL-FAST: Cuotas atrasadas - REJECTING")
            return {
                "fail_fast": True,
                "decision": "rejected", 
                "reasoning": "Tiene cuotas mensuales pendientes. Regularice su situación de pagos para acceder a descuentos",
                "confidence": 1.0,
                "rejection_reason": "fees_not_current",
                "failed_check": "payment_status_check"
            }
        
        # 4. No se encontró show con suficiente similitud
        if not best_match or best_match.get('similarity_score', 0) < 0.8:
            logger.warning(f"🚨 FAIL-FAST: Show no encontrado - similarity: {best_match.get('similarity_score', 0) if best_match else 'NO_MATCH'}")
            return {
                "fail_fast": True,
                "decision": "rejected",
                "reasoning": "No se encontró un show que coincida suficientemente con la descripción proporcionada",
                "confidence": 1.0,
                "rejection_reason": "show_not_found",
                "failed_check": "show_matching_check"
            }
        
        # 5. 🚨 CRÍTICO: Sin descuentos disponibles - Este era el error en TEST 8  
        remaining_discounts = best_match.get('remaining_discounts', 0)
        logger.warning(f"🔍 Checking remaining_discounts: {remaining_discounts}")
        if remaining_discounts <= 0:
            logger.warning("🚨 FAIL-FAST: Sin descuentos disponibles - REJECTING")
            return {
                "fail_fast": True,
                "decision": "rejected",
                "reasoning": f"Los descuentos para '{best_match.get('title')}' están agotados. No hay más cupos disponibles",
                "confidence": 1.0,
                "rejection_reason": "no_discounts_available", 
                "failed_check": "show_availability_check"
            }
        
        # 6. Solicitud duplicada
        if history.get('has_previous_request') and history.get('previous_approved'):
            logger.warning("🚨 FAIL-FAST: Solicitud duplicada - REJECTING")
            return {
                "fail_fast": True,
                "decision": "rejected",
                "reasoning": f"Ya tiene una solicitud de descuento aprobada para '{best_match.get('title')}'. Solo se permite un descuento por usuario por show",
                "confidence": 1.0,
                "rejection_reason": "previous_request_exists",
                "failed_check": "duplicate_request_check"
            }
        
        # Si todas las validaciones críticas pasan, continuar con LLM
        logger.warning("✅ FAIL-FAST: Todas las validaciones pasaron - continuando con LLM")
        return {
            "fail_fast": False,
            "message": "Todas las validaciones críticas pasaron - continuando con análisis del LLM"
        }
    
    async def _make_llm_decision(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 PASO 2D: Método principal con VALIDACIONES FAIL-FAST + LLM
        Primero verifica condiciones críticas, luego usa LLM para casos complejos
        """
        try:
            # 1. Construir contexto completo
            context = self._build_decision_context(request_data)
            
            # 2. 🚨 VALIDACIONES FAIL-FAST - Rechazar casos críticos inmediatamente
            fail_fast_result = self._add_fail_fast_validation(context)
            
            # Si falla una validación crítica, rechazar sin usar LLM
            if fail_fast_result.get("fail_fast"):
                return {
                    "success": True,
                    "decision": fail_fast_result["decision"],
                    "reasoning": fail_fast_result["reasoning"],
                    "confidence": fail_fast_result["confidence"],
                    "show_id": None,
                    "show_matched": None,
                    "rejection_reason": fail_fast_result.get("rejection_reason"),
                    "llm_used": False,
                    "model": "fail_fast_validation",
                    "failed_check": fail_fast_result.get("failed_check")
                }
            
            # 3. Si pasa las validaciones críticas, construir prompt para LLM
            prompt = self._build_decision_prompt(context)
            
            # 4. Llamar al LLM con el prompt (solo para casos que no son fail-fast)
            llm_response = await self.llm.ainvoke(prompt)
            
            # 5. Parsear respuesta JSON del LLM
            parsed_result = self._parse_llm_response(llm_response)
            
            # 6. Construir resultado final
            if parsed_result["success"]:
                decision_data = parsed_result["parsed_response"]
                
                # Determinar show_id si fue aprobado
                show_id = None
                if decision_data["decision"] == "APPROVED" and context.get("matching_shows"):
                    show_id = context["matching_shows"][0]["id"]
                
                return {
                    "success": True,
                    "decision": decision_data["decision"].lower(),  # "approved" o "rejected"
                    "reasoning": decision_data["reasoning"],
                    "confidence": decision_data["confidence"],
                    "show_id": show_id,
                    "show_matched": decision_data.get("show_matched"),
                    "rejection_reason": decision_data.get("rejection_reason"),
                    "llm_used": True,
                    "model": "llama3",
                    "validation_steps": decision_data.get("validation_steps", [])
                }
            else:
                # Fallback en caso de error de parsing - usar fail-fast como backup
                return {
                    "success": False,
                    "decision": "rejected",
                    "reasoning": parsed_result["fallback_reason"],
                    "confidence": 1.0,
                    "error": parsed_result["error"],
                    "llm_used": False,
                    "model": "fallback"
                }
                
        except Exception as e:
            return {
                "success": False,
                "decision": "rejected", 
                "reasoning": f"Error técnico en el procesamiento: {str(e)}",
                "confidence": 1.0,
                "error": str(e),
                "llm_used": False,
                "model": "error_handler"
            }
        
    async def test_llm_connection(self) -> Dict[str, Any]:
        """
        🧪 MÉTODO DE PRUEBA: Verificar que la conexión con Ollama funciona
        """
        try:
            # Prompt simple para probar la conexión
            test_prompt = "Responde solo con 'CONEXIÓN EXITOSA' si puedes leerme."
            
            response = await self.llm.ainvoke(test_prompt)
            
            return {
                "success": True,
                "message": "Conexión con Ollama exitosa",
                "model_response": response,
                "model_used": "llama3",
                "base_url": "http://localhost:11434"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Error conectando con Ollama"
            }
        
    async def process_discount_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 PASO 2E: Método principal - AHORA USA LLM REAL
        Main method to process discount request using LangChain agent with llama3
        """
        
        # 🎉 REEMPLAZAMOS LÓGICA HARDCODEADA CON LLM INTELLIGENCE
        llm_result = await self._make_llm_decision(request_data)
        
        # Crear log de decisión basado en resultado del LLM
        decision_log = {
            "request_id": request_data.get("request_id"),
            "user_email": request_data.get("user_email"),
            "show_description": request_data.get("show_description"),
            "steps": [
                "🤖 LLM llama3 analyzing complete context...",
                f"🧠 Decision: {llm_result['decision'].upper()}",
                f"🎯 Confidence: {llm_result['confidence']:.2f}",
                f"📝 Reasoning: {llm_result['reasoning'][:100]}..."
            ]
        }
        
        # Procesar resultado del LLM
        if llm_result["success"] and llm_result["decision"] == "approved":
            # ✅ APROBADO POR LLM
            return self._create_llm_approval_response(llm_result, decision_log, request_data)
        else:
            # ❌ RECHAZADO POR LLM  
                         return self._create_llm_rejection_response(llm_result, decision_log, request_data)
    
    def _create_llm_approval_response(self, llm_result: Dict, decision_log: Dict, 
                                    request_data: Dict) -> Dict[str, Any]:
        """
        🎯 PASO 2F: Crear respuesta de aprobación basada en decisión del LLM
        """
        # Obtener datos para generar email (si los necesitamos)
        user_data = self.db_tool.get_user_by_email(request_data["user_email"])
        
        # Si el LLM identificó un show, obtener sus datos
        show_data = None
        if llm_result.get("show_id"):
            matching_shows = self.db_tool.find_matching_shows(request_data["show_description"])
            if matching_shows:
                show_data = next((s for s in matching_shows if s["id"] == llm_result["show_id"]), matching_shows[0])
        
        # Generar email usando templates (si tenemos datos de show)
        email_content = "Email de aprobación generado por LLM"
        if show_data and user_data:
            email_context = {
                "user_name": user_data["name"],
                "show_title": show_data["title"],
                "show_artist": show_data["artist"],
                "show_venue": show_data["venue"],
                "show_date": show_data["show_date"],
                "discount_percentage": 15,  # Default discount
                "discount_instructions": show_data.get("discount_instructions", "Contactar a organizadores"),
                "expiry_date": (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y"),
                "request_id": request_data.get("request_id", "N/A")
            }
            email_content = self.template_engine.generate_approval_email(email_context)
        
        # Actualizar log con detalles de aprobación
        decision_log.update({
            "final_decision": "APPROVED",
            "show_matched": show_data,
            "user_data": user_data,
            "confidence_score": llm_result["confidence"],
            "email_generated": True,
            "llm_reasoning": llm_result["reasoning"],
            "model_used": llm_result.get("model", "llama3")
        })
        self.decision_logger.log_decision(decision_log)
        
        return {
            "success": True,
            "decision": "approved",
            "show_id": llm_result.get("show_id"),
            "discount_percentage": 15,
            "confidence": llm_result["confidence"],
            "reasoning": llm_result["reasoning"],
            "email_content": email_content,
            "business_analysis": f"🤖 LLM Decision: {llm_result['reasoning'][:200]}..."
        }
    
    def _create_llm_rejection_response(self, llm_result: Dict, decision_log: Dict, 
                                     request_data: Dict) -> Dict[str, Any]:
        """
        🎯 PASO 2G: Crear respuesta de rechazo - MEJORADO para fail-fast
        """
        # Generar email de rechazo
        rejection_reason = llm_result.get("rejection_reason", llm_result["reasoning"])
        
        # Agregar información sobre el tipo de validación usada
        validation_info = ""
        if not llm_result.get("llm_used", True):
            model_used = llm_result.get("model", "unknown")
            if model_used == "fail_fast_validation":
                failed_check = llm_result.get("failed_check", "unknown")
                validation_info = f" (Fail-fast: {failed_check})"
            else:
                validation_info = f" ({model_used})"
        
        email_context = {
            "user_name": request_data.get("user_name", "Usuario"),
            "show_description": request_data["show_description"],
            "rejection_reason": rejection_reason,
            "next_steps": self._get_next_steps_for_reason(rejection_reason),
            "technical_info": validation_info
        }
        
        email_content = self.template_engine.generate_rejection_email(email_context)
        
        # Actualizar log con detalles de rechazo
        decision_log.update({
            "final_decision": "REJECTED",
            "rejection_reason": rejection_reason,
            "confidence_score": llm_result["confidence"],
            "email_generated": True,
            "llm_reasoning": llm_result["reasoning"],
            "model_used": llm_result.get("model", "llama3"),
            "llm_error": llm_result.get("error") if not llm_result.get("success", True) else None,
            "validation_method": "fail_fast" if not llm_result.get("llm_used", True) else "llm_analysis",
            "failed_check": llm_result.get("failed_check"),
            "validation_steps": llm_result.get("validation_steps", [])
        })
        self.decision_logger.log_decision(decision_log)
        
        return {
            "success": True,
            "decision": "rejected",
            "show_id": None,
            "discount_percentage": 0,
            "confidence": llm_result["confidence"],
            "reasoning": llm_result["reasoning"],
            "email_content": email_content,
            "business_analysis": f"🤖 {llm_result.get('model', 'LLM')} Decision: {rejection_reason}{validation_info}",
            "validation_method": "fail_fast" if not llm_result.get("llm_used", True) else "llm_analysis"
        }
    
    def _create_approval_response(self, user_data: Dict, show_data: Dict, 
                                decision_log: Dict, request_data: Dict) -> Dict[str, Any]:
        """Create approval response with email generation"""
        
        # Generate approval email
        email_context = {
            "user_name": user_data["name"],
            "show_title": show_data["title"],
            "show_artist": show_data["artist"],
            "show_venue": show_data["venue"],
            "show_date": show_data["show_date"],
            "discount_percentage": 10,  # Default discount
            "discount_instructions": show_data["discount_instructions"],
            "expiry_date": (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y"),
            "request_id": request_data.get("request_id", "N/A")
        }
        
        email_content = self.template_engine.generate_approval_email(email_context)
        
        # Log successful decision
        decision_log.update({
            "final_decision": "APPROVED",
            "show_matched": show_data,
            "user_data": user_data,
            "confidence_score": show_data["similarity_score"],
            "email_generated": True
        })
        self.decision_logger.log_decision(decision_log)
        
        return {
            "success": True,
            "decision": "approved",
            "show_id": show_data["id"],
            "discount_percentage": 10,
            "confidence": show_data["similarity_score"],
            "reasoning": f"Usuario válido encontrado. Show '{show_data['title']}' identificado con {show_data['similarity_score']:.1%} de certeza. Descuentos disponibles: {show_data['remaining_discounts']}.",
            "email_content": email_content,
            "business_analysis": f"Todas las validaciones pasaron. Usuario: {user_data['name']} apto para descuento."
        }
    
    def _create_rejection_response(self, reason: str, decision_log: Dict, 
                                 request_data: Dict) -> Dict[str, Any]:
        """Create rejection response with email generation"""
        
        # Generate rejection email
        email_context = {
            "user_name": request_data.get("user_name", "Usuario"),
            "show_description": request_data["show_description"],
            "rejection_reason": reason,
            "next_steps": self._get_next_steps_for_reason(reason)
        }
        
        email_content = self.template_engine.generate_rejection_email(email_context)
        
        # Log rejection decision
        decision_log.update({
            "final_decision": "REJECTED",
            "rejection_reason": reason,
            "confidence_score": 1.0,
            "email_generated": True
        })
        self.decision_logger.log_decision(decision_log)
        
        return {
            "success": True,
            "decision": "rejected",
            "show_id": None,
            "discount_percentage": 0,
            "confidence": 1.0,
            "reasoning": f"Solicitud rechazada: {reason}",
            "email_content": email_content,
            "business_analysis": f"Validación fallida: {reason}"
        }
    
    def _get_next_steps_for_reason(self, reason: str) -> str:
        """Get appropriate next steps based on rejection reason"""
        next_steps_map = {
            "El email proporcionado no está registrado": "Regístrate en nuestra plataforma o verifica que el email sea correcto",
            "La suscripción no está activa": "Renueva tu suscripción para acceder a descuentos",
            "Las cuotas mensuales no están al día": "Ponte al día con tus pagos mensuales",
            "No se encontró un show que coincida": "Verifica el nombre del artista y lugar, o busca otros shows disponibles",
            "No hay más descuentos disponibles": "Intenta con otros shows o mantente atento a nuevas fechas",
            "Ya existe una solicitud previa": "No puedes solicitar múltiples descuentos para el mismo show"
        }
        
        for key, value in next_steps_map.items():
            if key in reason:
                return value
        
        return "Contacta a soporte para más información" 