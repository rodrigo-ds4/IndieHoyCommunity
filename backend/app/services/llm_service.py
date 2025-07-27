"""
LLM Service
Handles communication with Ollama LLM
Abstraction layer between FastAPI and Ollama
"""

import httpx
import asyncio
from typing import Dict, Any, Optional
from app.core.config import settings


class LLMService:
    """
    Service for Ollama LLM communication
    Similar to your chat.py but as a service class
    """
    
    def __init__(self):
        self.ollama_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response from Ollama LLM
        Enhanced version of your ask_llama3 function
        """
        
        # Build messages for chat
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        if context:
            context_str = f"Context: {context}\n\nUser message: {prompt}"
            messages.append({"role": "user", "content": context_str})
        else:
            messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 500
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "content": data["message"]["content"].strip(),
                        "model": data["model"],
                        "success": True,
                        "error": None
                    }
                else:
                    return {
                        "content": None,
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except asyncio.TimeoutError:
            return {
                "content": None,
                "success": False,
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "content": None,
                "success": False,
                "error": str(e)
            }
    
    async def classify_message(self, message: str) -> str:
        """
        Classify user message type using LLM
        """
        system_prompt = """You are a message classifier for a show discount system.
        Classify the message into one of these categories:
        - discount_request: User asking for discounts
        - show_info: User asking about shows
        - greeting: Greetings or general conversation
        - general_query: Other questions
        
        Respond with only the category name."""
        
        result = await self.generate_response(message, system_prompt=system_prompt)
        if result["success"]:
            return result["content"].lower().strip()
        return "general_query"
    
    async def check_health(self) -> bool:
        """Check if Ollama is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                return response.status_code == 200
        except:
            return False 