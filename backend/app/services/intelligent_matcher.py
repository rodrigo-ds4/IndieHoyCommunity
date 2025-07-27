"""
Intelligent Show Matcher using LangChain
Handles sophisticated fuzzy matching and email generation for pre-validated requests
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

# LangChain imports
from langchain_ollama import OllamaLLM

from app.services.discount_prefilter import PreFilterResult


@dataclass
class MatchingResult:
    """Result of intelligent show matching"""
    status: str  # "approved", "needs_clarification"
    show_selected: Optional[Dict[str, Any]]
    email_content: str
    reasoning: str
    confidence: float
    llm_used: bool = True


class IntelligentShowMatcher:
    """
    🤖 INTELLIGENT MATCHER: LangChain-powered show matching and email generation
    
    Responsibilities:
    - Sophisticated fuzzy matching between pre-validated candidate shows
    - Intelligent selection when multiple shows match
    - Personalized email generation
    - Context-aware decision making
    
    IMPORTANT: This class assumes all business validations are already done by PreFilter
    """
    
    def __init__(self, db_session=None):
        self._llm = None
        self.db = db_session
    
    @property
    def llm(self):
        """Lazy initialization of LLM to avoid blocking startup"""
        if self._llm is None:
            self._llm = OllamaLLM(
                model="llama3",
                base_url="http://host.docker.internal:11434",
                temperature=0.3,
                timeout=30
            )
        return self._llm
    
    async def process_validated_request(self, prefilter_result: PreFilterResult) -> MatchingResult:
        """
        🎯 Main processing method for pre-validated requests
        
        Args:
            prefilter_result: Clean, validated data from PreFilter (user validation only)
            
        Returns:
            MatchingResult with selected show and generated email OR clarification request
        """
        user_data = prefilter_result.user_data
        original_description = prefilter_result.original_description
        
        # 🧠 LLM ALWAYS handles show matching - this is the core logic
        show_analysis = await self._llm_analyze_show_request(original_description, user_data)
        
        if show_analysis["status"] == "found_single":
            # ✅ Clear match found - approve with email
            selected_show = show_analysis["selected_show"]
            email_content = await self._llm_generate_approval_email(user_data, selected_show)
            
            return MatchingResult(
                status="approved",
                show_selected=selected_show,
                email_content=email_content,
                reasoning=f"Show identificado correctamente: {selected_show['title']}",
                confidence=show_analysis["confidence"],
                llm_used=True
            )
            
        elif show_analysis["status"] == "found_multiple":
            # 🤔 Multiple matches - ask for clarification
            clarification_email = await self._llm_generate_clarification_email(
                user_data, show_analysis["candidate_shows"], original_description
            )
            
            return MatchingResult(
                status="needs_clarification",
                show_selected=None,
                email_content=clarification_email,
                reasoning=f"Múltiples shows encontrados, pidiendo clarificación: {[s['title'] for s in show_analysis['candidate_shows']]}",
                confidence=show_analysis["confidence"],
                llm_used=True
            )
            
        else:  # "not_found"
            # ❓ No matches - ask for clarification
            clarification_email = await self._llm_generate_not_found_email(user_data, original_description)
            
            return MatchingResult(
                status="needs_clarification", 
                show_selected=None,
                email_content=clarification_email,
                reasoning=f"No se encontró show para '{original_description}', pidiendo clarificación",
                confidence=show_analysis["confidence"],
                llm_used=True
            )
    
    async def _llm_select_best_match(self, original_description: str, 
                                   candidate_shows: List[Dict[str, Any]], 
                                   user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to intelligently select the best matching show from candidates
        """
        prompt = self._build_matching_prompt(original_description, candidate_shows, user_data)
        
        try:
            llm_response = await self.llm.ainvoke(prompt)
            parsed_response = self._parse_matching_response(llm_response)
            
            # Find the selected show by ID
            selected_id = parsed_response.get("selected_show_id")
            for show in candidate_shows:
                if show["id"] == selected_id:
                    return show
            
            # Fallback: return first show if parsing fails
            return candidate_shows[0]
            
        except Exception as e:
            # Fallback: return highest similarity show
            return max(candidate_shows, key=lambda s: s["similarity_score"])
    
    def _build_matching_prompt(self, original_description: str, 
                             candidate_shows: List[Dict[str, Any]], 
                             user_data: Dict[str, Any]) -> str:
        """Build prompt for intelligent show matching"""
        
        shows_text = ""
        for i, show in enumerate(candidate_shows, 1):
            shows_text += f"""
{i}. ID: {show['id']}
   Título: {show['title']}
   Artista: {show['artist']}
   Venue: {show['venue']}
   Fecha: {show['show_date']}
   Género: {show.get('genre', 'N/A')}
   Similitud básica: {show['similarity_score']:.0%}
   Descuentos disponibles: {show['remaining_discounts']}"""
        
        return f"""Eres un experto en matching de shows musicales. Tu tarea es seleccionar el show que mejor coincida con la solicitud del usuario.

SOLICITUD DEL USUARIO: "{original_description}"

DATOS DEL USUARIO:
- Nombre: {user_data['name']}
- Género favorito: {user_data['favorite_music_genre']}
- Ciudad: {user_data['city']}

SHOWS CANDIDATOS (todos tienen descuentos disponibles):
{shows_text}

INSTRUCCIONES:
1. Analiza la descripción original del usuario
2. Considera el contexto (venue, fecha, género)
3. Ten en cuenta las preferencias del usuario
4. Selecciona el show que mejor coincida

Responde EXACTAMENTE en este formato JSON:
{{
  "selected_show_id": 123,
  "reasoning": "Explicación detallada de por qué este show es el mejor match",
  "confidence": 0.95
}}"""
    
    async def _llm_analyze_show_request(self, description: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🧠 LLM analyzes show request and finds matches with available discounts
        
        Returns:
        - {"status": "found_single", "selected_show": {...}, "confidence": 0.9}
        - {"status": "found_multiple", "candidate_shows": [...], "confidence": 0.7}  
        - {"status": "not_found", "confidence": 0.3}
        """
        from app.models.database import Show
        from sqlalchemy.orm import Session
        
        # Get all active shows with discounts
        # We need access to the database - get it from somewhere
        # For now, let's assume we can access it (we'll need to pass it in)
        
        # Build LLM prompt for show analysis
        prompt = self._build_show_analysis_prompt(description, user_data)
        
        try:
            llm_response = await self.llm.ainvoke(prompt)
            return self._parse_show_analysis_response(llm_response)
            
        except Exception as e:
            # Fallback: return not found
            return {
                "status": "not_found",
                "confidence": 0.1,
                "error": str(e)
            }
    
    def _build_show_analysis_prompt(self, description: str, user_data: Dict[str, Any]) -> str:
        """Build prompt for LLM to analyze show request"""
        
        # Get actual shows from database
        shows_context = self._get_available_shows_context()
        if not shows_context:
            shows_context = "No hay shows disponibles con descuentos en este momento."
        
        return f"""Eres un experto en identificar shows musicales. Analiza la solicitud del usuario y determina qué show está pidiendo.

SOLICITUD DEL USUARIO: "{description}"

USUARIO:
- Nombre: {user_data['name']}
- Género favorito: {user_data['favorite_music_genre']}
- Ciudad: {user_data['city']}

{shows_context}

Tu tarea:
1. Buscar shows que coincidan con la descripción (usa fuzzy matching inteligente)
2. Solo considerar shows CON descuentos disponibles
3. Decidir si hay 1 match claro, múltiples matches, o ninguno

Responde EXACTAMENTE en este formato JSON:

Para 1 MATCH CLARO:
{{
  "status": "found_single",
  "selected_show": {{"id": 1, "title": "Los Piojos Tributo", "artist": "Los Piojos", "venue": "Luna Park", "show_date": "2025-08-15", "remaining_discounts": 10}},
  "confidence": 0.95,
  "reasoning": "Match exacto encontrado"
}}

Para MÚLTIPLES MATCHES:
{{
  "status": "found_multiple", 
  "candidate_shows": [{{"id": 1, "title": "Show 1", "artist": "Artist 1", "venue": "Venue 1", "show_date": "2025-08-15", "remaining_discounts": 5}}, {{"id": 2, "title": "Show 2", "artist": "Artist 2", "venue": "Venue 2", "show_date": "2025-08-20", "remaining_discounts": 3}}],
  "confidence": 0.7,
  "reasoning": "Múltiples shows coinciden"
}}

Para NINGÚN MATCH:
{{
  "status": "not_found",
  "confidence": 0.3,
  "reasoning": "No se encontró show que coincida"
}}"""
    
    def _parse_show_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM show analysis response"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            return {
                "status": "not_found",
                "confidence": 0.1,
                "reasoning": f"Error parsing response: {str(e)}"
            }
    
    async def _llm_generate_approval_email(self, user_data: Dict[str, Any], 
                                         selected_show: Dict[str, Any]) -> str:
        """Generate personalized approval email using LLM"""
        
        prompt = f"""Genera un email de aprobación de descuento personalizado y profesional.

DATOS DEL USUARIO:
- Nombre: {user_data['name']}
- Género favorito: {user_data['favorite_music_genre']}

SHOW APROBADO:
- Título: {selected_show['title']}
- Artista: {selected_show['artist']}
- Venue: {selected_show['venue']}
- Fecha: {selected_show['show_date']}
- Precio: ${selected_show.get('price', 'N/A')}
- Instrucciones: {selected_show.get('discount_instructions', 'Contacte la boletería con este código de aprobación')}

INSTRUCCIONES:
1. Saluda al usuario por su nombre
2. Confirma que su solicitud fue aprobada
3. Incluye todos los detalles del show
4. Explica cómo usar el descuento
5. Mantén un tono profesional pero amigable
6. Termina con información de contacto

Genera solo el contenido del email (sin asunto):"""
        
        try:
            email_content = await self.llm.ainvoke(prompt)
            return email_content.strip()
        except Exception as e:
            # Fallback email template
            return self._generate_fallback_email(user_data, selected_show)
    
    def _parse_matching_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM matching response"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            return {"selected_show_id": None, "reasoning": "Error al procesar respuesta de IA", "confidence": 0.5}
    
    def _generate_fallback_email(self, user_data: Dict[str, Any], 
                                selected_show: Dict[str, Any]) -> str:
        """Generate fallback email if LLM fails"""
        return f"""Estimado/a {user_data['name']},

¡Excelente noticia! Su solicitud de descuento ha sido aprobada.

DETALLES DEL SHOW:
• Show: {selected_show['title']}
• Artista: {selected_show['artist']}
• Venue: {selected_show['venue']}
• Fecha: {selected_show['show_date']}

INSTRUCCIONES PARA EL DESCUENTO:
{selected_show.get('discount_instructions', 'Contacte la boletería con este código de aprobación')}

Para cualquier consulta, puede contactarnos respondiendo a este email.

Saludos cordiales,
Equipo IndieHOY"""

    async def _llm_generate_clarification_email(self, user_data: Dict[str, Any], 
                                              candidate_shows: List[Dict[str, Any]], 
                                              original_description: str) -> str:
        """Generate email asking for clarification when multiple shows match"""
        
        shows_list = ""
        for i, show in enumerate(candidate_shows, 1):
            shows_list += f"{i}. {show['title']} - {show['artist']} en {show['venue']}\n"
        
        prompt = f"""Genera un email pidiendo clarificación porque encontramos múltiples shows que podrían coincidir.

USUARIO: {user_data['name']}
BÚSQUEDA ORIGINAL: "{original_description}"

SHOWS ENCONTRADOS:
{shows_list}

INSTRUCCIONES:
1. Saluda cordialmente al usuario
2. Explica que encontramos varios shows que podrían coincidir
3. Lista los shows encontrados
4. Pide que responda con el show específico que desea
5. Mantén tono profesional y servicial

Genera solo el contenido del email:"""
        
        try:
            email_content = await self.llm.ainvoke(prompt)
            return email_content.strip()
        except Exception as e:
            # Fallback email
            return f"""Estimado/a {user_data['name']},

Hemos recibido su solicitud de descuento para "{original_description}".

Encontramos varios shows que podrían coincidir con su búsqueda:

{shows_list}

Por favor, responda a este email indicando específicamente cuál de estos shows es el que desea, para poder procesar su solicitud de descuento.

Saludos cordiales,
Equipo IndieHOY"""
    
    async def _llm_generate_not_found_email(self, user_data: Dict[str, Any], 
                                          original_description: str) -> str:
        """Generate email when no shows are found"""
        
        prompt = f"""Genera un email explicando que no encontramos shows que coincidan con la búsqueda.

USUARIO: {user_data['name']}
BÚSQUEDA: "{original_description}"

INSTRUCCIONES:
1. Saluda cordialmente
2. Explica que no encontramos shows que coincidan
3. Sugiere verificar la escritura del artista/show
4. Ofrece ayuda para encontrar el show correcto
5. Mantén tono servicial y positivo

Genera solo el contenido del email:"""
        
        try:
            email_content = await self.llm.ainvoke(prompt)
            return email_content.strip()
        except Exception as e:
            # Fallback email
            return f"""Estimado/a {user_data['name']},

Hemos recibido su solicitud de descuento para "{original_description}".

Lamentablemente, no pudimos encontrar un show que coincida exactamente con su búsqueda.

Por favor:
• Verifique la escritura del nombre del artista o show
• Asegúrese de que el show tenga fecha próxima
• Responda a este email con más detalles del show que busca

Estaremos encantados de ayudarle a encontrar el show correcto.

Saludos cordiales,
Equipo IndieHOY"""

    async def test_llm_connection(self) -> Dict[str, Any]:
        """Test LLM connection"""
        try:
            test_prompt = "Responde solo con 'CONEXIÓN EXITOSA' si puedes leerme."
            response = await self.llm.ainvoke(test_prompt)
            
            return {
                "success": True,
                "message": "Conexión con Ollama exitosa",
                "model_response": response,
                "model_used": "llama3"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Error conectando con Ollama"
            } 

    def _get_available_shows_context(self) -> str:
        """Get real shows from database for LLM context"""
        if not self.db:
            # Fallback if no DB session
            return """
        SHOWS DISPONIBLES CON DESCUENTOS:
        1. Los Piojos Tributo - Luna Park - 10 descuentos disponibles
        2. Tini en Concierto - Movistar Arena - 15 descuentos disponibles  
        3. Wos en Vivo - Microestadio Malvinas - 8 descuentos disponibles
        """
        
        try:
            from app.models.database import Show
            
            # Get active shows
            shows = self.db.query(Show).filter(Show.active == True).all()
            
            shows_list = []
            for i, show in enumerate(shows, 1):
                remaining = show.get_remaining_discounts(self.db)
                if remaining > 0:  # Only shows with available discounts
                    show_date_str = show.show_date.strftime("%Y-%m-%d") if show.show_date else "Fecha TBD"
                    shows_list.append(f"{i}. {show.title} - {show.artist} - {show.venue} - {show_date_str} - {remaining} descuentos disponibles")
            
            if shows_list:
                return "\nSHOWS DISPONIBLES CON DESCUENTOS:\n" + "\n".join(shows_list)
            else:
                return "No hay shows disponibles con descuentos en este momento."
                
        except Exception as e:
            # Fallback in case of error
            return f"Error accediendo a shows: {str(e)}" 