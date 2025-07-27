"""
Chat Service
Handles chatbot conversation logic
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.llm_service import LLMService
from app.models.database import User
from app.models.chat import ChatHistory, MessageType


class ChatService:
    """
    Service for chatbot conversation management
    Integrates with LLM service and handles context
    """
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.llm_service = LLMService()
        # In-memory conversation history (for simple implementation)
        # In production, this would be stored in database or Redis
        self.conversation_memory = {}
    
    async def process_message(
        self,
        message: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user message and generate bot response
        
        Returns:
        {
            "content": str,
            "timestamp": datetime,
            "confidence": float,
            "message_type": MessageType,
            "suggested_actions": List[str]
        }
        """
        
        # 1. Classify message type
        message_type = await self.llm_service.classify_message(message)
        
        # 2. Get conversation context
        conversation_context = self._get_conversation_context(user_id)
        
        # 3. Build system prompt based on message type
        system_prompt = self._build_system_prompt(message_type, context)
        
        # 4. Generate response
        llm_response = await self.llm_service.generate_response(
            prompt=message,
            context=conversation_context,
            system_prompt=system_prompt
        )
        
        if llm_response["success"]:
            response_content = llm_response["content"]
            confidence = 0.8
        else:
            response_content = self._get_fallback_response(message_type)
            confidence = 0.3
        
        # 5. Determine suggested actions
        suggested_actions = self._get_suggested_actions(message_type, message)
        
        # 6. Store in conversation memory
        response_data = {
            "content": response_content,
            "timestamp": datetime.now(),
            "confidence": confidence,
            "message_type": message_type,
            "suggested_actions": suggested_actions
        }
        
        self._update_conversation_memory(user_id, message, response_content)
        
        return response_data
    
    def _build_system_prompt(self, message_type: str, context: Optional[Dict] = None) -> str:
        """Build system prompt based on message type"""
        
        base_prompt = """
        Eres Charro Bot, un asistente amigable para un sistema de descuentos en shows y conciertos.
        
        Tu personalidad:
        - Amigable y cercano (usa "vos" argentino)
        - Profesional pero relajado
        - Entusiasta por la música y shows
        - Siempre positivo y servicial
        
        Reglas importantes:
        - Responde en español argentino
        - Sé conciso pero útil
        - Si no sabés algo, admitilo y pedí que contacten a un humano
        - Nunca prometas descuentos, solo explicá el proceso
        """
        
        if message_type == "discount_request":
            return base_prompt + """
            
            El usuario está preguntando sobre descuentos. Explicale:
            1. Cómo funciona el sistema de solicitud
            2. Qué información necesita proporcionar
            3. Que un agente automático evalúa las solicitudes
            4. Los tiempos de respuesta (24-48 horas)
            
            NO prometas que van a obtener el descuento, solo explicá el proceso.
            """
            
        elif message_type == "show_info":
            return base_prompt + """
            
            El usuario pregunta sobre shows. Ayudalo con:
            1. Información general sobre eventos
            2. Cómo ver la programación
            3. Proceso de compra de entradas
            4. Políticas de descuentos
            """
            
        elif message_type == "greeting":
            return base_prompt + """
            
            El usuario te está saludando. Respondé:
            1. Con un saludo amigable
            2. Presentate brevemente
            3. Preguntá en qué podés ayudar
            4. Mencioná las principales cosas que podés hacer
            """
            
        else:  # general_query
            return base_prompt + """
            
            Responde la consulta general del usuario lo mejor que puedas.
            Si está relacionado con shows, descuentos o el sistema, ayudalo.
            Si no podés responder, derivalo amablemente a contacto humano.
            """
    
    def _get_suggested_actions(self, message_type: str, message: str) -> List[str]:
        """Get suggested actions based on message type"""
        
        if message_type == "discount_request":
            return [
                "complete_discount_form",
                "view_available_shows", 
                "check_eligibility",
                "contact_support"
            ]
        elif message_type == "show_info":
            return [
                "view_show_calendar",
                "search_shows",
                "check_ticket_prices"
            ]
        elif message_type == "greeting":
            return [
                "ask_about_discounts",
                "browse_shows",
                "get_help"
            ]
        else:
            return [
                "contact_support",
                "browse_shows"
            ]
    
    def _get_fallback_response(self, message_type: str) -> str:
        """Get fallback response if LLM fails"""
        
        fallbacks = {
            "discount_request": """
            ¡Hola! Para solicitar un descuento, necesitás completar nuestro formulario con:
            - Tu información de contacto
            - El show que te interesa
            - La razón por la cual solicitás el descuento
            
            Un agente automático evaluará tu solicitud en 24-48 horas.
            """,
            
            "show_info": """
            ¡Hola! Te puedo ayudar con información sobre nuestros shows y el sistema de descuentos.
            ¿Hay algo específico que te gustaría saber?
            """,
            
            "greeting": """
            ¡Hola! Soy Charro Bot 🤠
            
            Te puedo ayudar con:
            • Información sobre descuentos
            • Consultas sobre shows
            • Proceso de solicitudes
            
            ¿En qué te puedo ayudar?
            """,
            
            "general_query": """
            Disculpá, no pude procesar tu consulta correctamente.
            ¿Podrías reformularla o contactar a nuestro equipo de soporte?
            """
        }
        
        return fallbacks.get(message_type, fallbacks["general_query"])
    
    def _get_conversation_context(self, user_id: str) -> Dict[str, Any]:
        """Get recent conversation context for user"""
        
        if user_id not in self.conversation_memory:
            return {}
        
        # Return last 5 messages for context
        recent_messages = self.conversation_memory[user_id][-5:]
        
        return {
            "recent_messages": recent_messages,
            "message_count": len(self.conversation_memory[user_id])
        }
    
    def _update_conversation_memory(self, user_id: str, user_message: str, bot_response: str):
        """Update conversation memory"""
        
        if user_id not in self.conversation_memory:
            self.conversation_memory[user_id] = []
        
        self.conversation_memory[user_id].append({
            "user": user_message,
            "bot": bot_response,
            "timestamp": datetime.now()
        })
        
        # Keep only last 20 messages to prevent memory bloat
        if len(self.conversation_memory[user_id]) > 20:
            self.conversation_memory[user_id] = self.conversation_memory[user_id][-20:]
    
    async def get_history(self, user_id: str, limit: int = 50) -> List[ChatHistory]:
        """Get chat history for user"""
        
        # In production, this would query the database
        # For now, return from memory
        
        if user_id not in self.conversation_memory:
            return []
        
        history = []
        messages = self.conversation_memory[user_id][-limit:]
        
        for i, msg in enumerate(messages):
            history.append(ChatHistory(
                id=i,
                user_id=user_id,
                message=msg["user"],
                response=msg["bot"],
                timestamp=msg["timestamp"]
            ))
        
        return history
    
    async def clear_history(self, user_id: str):
        """Clear chat history for user"""
        
        if user_id in self.conversation_memory:
            del self.conversation_memory[user_id]
    
    async def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get conversation statistics"""
        
        if user_id not in self.conversation_memory:
            return {"message_count": 0, "first_interaction": None}
        
        messages = self.conversation_memory[user_id]
        
        return {
            "message_count": len(messages),
            "first_interaction": messages[0]["timestamp"] if messages else None,
            "last_interaction": messages[-1]["timestamp"] if messages else None
        } 