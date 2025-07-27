"""
Test suite for LLM discount decision system
20 comprehensive test cases including edge cases, confusing names, and complex scenarios
"""
import pytest
from app.services.langchain_agent_service import LangChainAgentService


class TestLLMDiscountDecisions:
    """Comprehensive test suite for LLM decision making"""

    # ✅ CASOS DE APROBACIÓN VÁLIDOS
    
    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_01_valid_user_exact_match(self, agent_service, complex_test_users, complex_test_shows):
        """Test 1: Usuario válido con match exacto de show"""
        request_data = {
            "request_id": 1,
            "user_name": "Sebastian Valido",
            "user_email": "sebastian.valido@test.com",
            "show_description": "Los Piojos Tributo en Luna Park"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["decision"] == "approved"
        assert result["show_id"] is not None
        assert result["confidence"] > 0.7
        assert "Piojos" in result["reasoning"] or "válido" in result["reasoning"]

    @pytest.mark.llm 
    @pytest.mark.asyncio
    async def test_02_valid_user_fuzzy_match(self, agent_service, complex_test_users, complex_test_shows):
        """Test 2: Usuario válido con fuzzy matching (Wos -> Wos en Vivo)"""
        request_data = {
            "request_id": 2,
            "user_name": "Maria Perfecta",
            "user_email": "maria.perfecta@test.com", 
            "show_description": "Wos Microestadio"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["decision"] == "approved"
        assert result["show_id"] is not None
        assert "Wos" in result["reasoning"] or "Microestadio" in result["reasoning"]

    @pytest.mark.llm
    @pytest.mark.asyncio  
    async def test_03_valid_user_different_genre(self, agent_service, complex_test_users, complex_test_shows):
        """Test 3: Usuario válido con género diferente pero show disponible"""
        request_data = {
            "request_id": 3,
            "user_name": "Carlos Completo",
            "user_email": "carlos.completo@test.com",
            "show_description": "Tini en Concierto"  # Usuario prefiere cumbia, pero es pop
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        # Puede aprobar o rechazar según criterio del LLM sobre género
        assert result["confidence"] > 0.5

    # ❌ CASOS DE RECHAZO - CUOTAS ATRASADAS

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_04_user_fees_behind(self, agent_service, complex_test_users, complex_test_shows):
        """Test 4: Usuario con cuotas atrasadas"""
        request_data = {
            "request_id": 4,
            "user_name": "Juan Atrasado",
            "user_email": "juan.atrasado@test.com",
            "show_description": "Los Piojos Tributo"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["decision"] == "rejected"
        assert "cuota" in result["reasoning"].lower() or "pago" in result["reasoning"].lower()

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_05_user_fees_behind_good_show(self, agent_service, complex_test_users, complex_test_shows):
        """Test 5: Usuario moroso pero con show perfecto (debería rechazar igual)"""
        request_data = {
            "request_id": 5,
            "user_name": "Ana Deudora",
            "user_email": "ana.deudora@test.com",
            "show_description": "Folklore Argentino"  # Coincide con su género favorito
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["decision"] == "rejected"
        assert "cuota" in result["reasoning"].lower() or "pago" in result["reasoning"].lower()

    # ❌ CASOS DE RECHAZO - SUSCRIPCIÓN INACTIVA

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_06_inactive_subscription(self, agent_service, complex_test_users, complex_test_shows):
        """Test 6: Usuario con suscripción inactiva"""
        request_data = {
            "request_id": 6,
            "user_name": "Pedro Inactivo", 
            "user_email": "pedro.inactivo@test.com",
            "show_description": "Los Piojos Tributo"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["decision"] == "rejected"
        assert "suscripción" in result["reasoning"].lower() or "activ" in result["reasoning"].lower()

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_07_double_problem_user(self, agent_service, complex_test_users, complex_test_shows):
        """Test 7: Usuario con suscripción inactiva Y cuotas atrasadas"""
        request_data = {
            "request_id": 7,
            "user_name": "Ricardo Doble",
            "user_email": "ricardo.doble@test.com",
            "show_description": "Tango Milonga"  # Coincide con su género
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["decision"] == "rejected"
        # Debería mencionar al menos uno de los problemas
        reasoning_lower = result["reasoning"].lower()
        assert "suscripción" in reasoning_lower or "cuota" in reasoning_lower or "pago" in reasoning_lower

    # ❌ CASOS DE RECHAZO - SIN DESCUENTOS DISPONIBLES

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_08_sold_out_show(self, agent_service, complex_test_users, complex_test_shows):
        """Test 8: Show sin descuentos disponibles (sold out)"""
        request_data = {
            "request_id": 8,
            "user_name": "Sebastian Valido",
            "user_email": "sebastian.valido@test.com",
            "show_description": "Abel Pintos Sold Out"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True  
        assert result["decision"] == "rejected"
        reasoning_lower = result["reasoning"].lower()
        assert "descuento" in reasoning_lower or "disponible" in reasoning_lower or "cupo" in reasoning_lower

    @pytest.mark.llm 
    @pytest.mark.asyncio
    async def test_09_full_capacity_show(self, agent_service, complex_test_users, complex_test_shows):
        """Test 9: Otro show sin descuentos (Charly García)"""
        request_data = {
            "request_id": 9,
            "user_name": "Maria Perfecta",
            "user_email": "maria.perfecta@test.com",
            "show_description": "Charly García Completo"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["decision"] == "rejected"
        reasoning_lower = result["reasoning"].lower()
        assert "descuento" in reasoning_lower or "disponible" in reasoning_lower

    # 🤔 CASOS COMPLEJOS - NOMBRES CONFUSOS

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_10_confusing_name_angeles(self, agent_service, complex_test_users, complex_test_shows):
        """Test 10: Nombre confuso - Los Angeles de Charlie"""
        request_data = {
            "request_id": 10,
            "user_name": "Sebastian Valido",
            "user_email": "sebastian.valido@test.com",
            "show_description": "Los Angeles Charlie Club"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        # El LLM debería poder manejar la ambigüedad
        if result["decision"] == "approved":
            assert result["show_id"] is not None
        assert result["confidence"] > 0.5

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_11_confusing_name_beriso(self, agent_service, complex_test_users, complex_test_shows):
        """Test 11: Súper confuso - La Beriso en La Beriso"""
        request_data = {
            "request_id": 11,
            "user_name": "Carlos Completo", 
            "user_email": "carlos.completo@test.com",
            "show_description": "La Beriso"  # ¿Banda, venue, o ciudad?
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        # Debería manejar la ambigüedad de alguna manera
        assert result["confidence"] > 0.3

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_12_minimal_info_show(self, agent_service, complex_test_users, complex_test_shows):
        """Test 12: Show con nombre mínimo - "Show de Juan" """
        request_data = {
            "request_id": 12,
            "user_name": "Maria Perfecta",
            "user_email": "maria.perfecta@test.com",
            "show_description": "Juan"  # Muy ambiguo
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        # Puede aprobar si encuentra el match o rechazar por ambigüedad
        assert result["confidence"] > 0.3

    # 🎭 CASOS FUZZY MATCHING CHALLENGE

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_13_fuzzy_piojos_variation(self, agent_service, complex_test_users, complex_test_shows):
        """Test 13: Fuzzy matching - "Los Piosos" vs "Los Piojos" """
        request_data = {
            "request_id": 13,
            "user_name": "Sebastian Valido",
            "user_email": "sebastian.valido@test.com",
            "show_description": "Los Piosos Club Atlético"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        if result["decision"] == "approved":
            assert result["show_id"] is not None
            assert result["confidence"] > 0.6  # Debería tener confianza razonable

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_14_fuzzy_gender_variation(self, agent_service, complex_test_users, complex_test_shows):
        """Test 14: Fuzzy matching - "Las Piojas" (cambio de género)"""
        request_data = {
            "request_id": 14,
            "user_name": "Maria Perfecta",
            "user_email": "maria.perfecta@test.com",
            "show_description": "Las Piojas Rosario"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        if result["decision"] == "approved":
            assert "Piojas" in result["reasoning"] or "Rosario" in result["reasoning"]

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_15_fuzzy_false_positive(self, agent_service, complex_test_users, complex_test_shows):
        """Test 15: Fuzzy que puede ser falso positivo - "Los Piojos Falsos" """
        request_data = {
            "request_id": 15,
            "user_name": "Carlos Completo",
            "user_email": "carlos.completo@test.com", 
            "show_description": "Los Piojos Falsos Córdoba"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        # Debería distinguir entre "Los Piojos" y "Los Piojos Falsos"
        if result["decision"] == "approved":
            assert "Falsos" in result["reasoning"]

    # 🎪 CASOS EXTREMOS

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_16_extreme_short_name(self, agent_service, complex_test_users, complex_test_shows):
        """Test 16: Show con nombre extremadamente corto - "A" """
        request_data = {
            "request_id": 16,
            "user_name": "Sebastian Valido",
            "user_email": "sebastian.valido@test.com",
            "show_description": "A en Lugar A"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        if result["decision"] == "approved":
            assert result["show_id"] is not None

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_17_extreme_long_name(self, agent_service, complex_test_users, complex_test_shows):
        """Test 17: Show con nombre extremadamente largo"""
        request_data = {
            "request_id": 17,
            "user_name": "Maria Perfecta",
            "user_email": "maria.perfecta@test.com",
            "show_description": "Artista Con Nombre Muy Muy Muy Largo"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        if result["decision"] == "approved":
            assert "Largo" in result["reasoning"]

    # 🎵 CASOS GÉNEROS DIVERSOS

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_18_classical_music(self, agent_service, complex_test_users, complex_test_shows):
        """Test 18: Música clásica - diferente a géneros populares"""
        request_data = {
            "request_id": 18,
            "user_name": "Sebastian Valido",  # Le gusta rock
            "user_email": "sebastian.valido@test.com",
            "show_description": "Orquesta Sinfónica Teatro San Martín"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        # Puede aprobar por disponibilidad o rechazar por género
        assert result["confidence"] > 0.5

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_19_electronic_music(self, agent_service, complex_test_users, complex_test_shows):
        """Test 19: Música electrónica en club nocturno"""
        request_data = {
            "request_id": 19,
            "user_name": "Maria Perfecta",  # Le gusta pop
            "user_email": "maria.perfecta@test.com",
            "show_description": "DJ Electrónico Niceto"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["confidence"] > 0.5

    # ❌ CASOS EDGE FINALES

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_20_inactive_show(self, agent_service, complex_test_users, complex_test_shows):
        """Test 20: Show cancelado/inactivo"""
        request_data = {
            "request_id": 20,
            "user_name": "Sebastian Valido",
            "user_email": "sebastian.valido@test.com", 
            "show_description": "Show Cancelado Venue Cerrado"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["decision"] == "rejected"
        reasoning_lower = result["reasoning"].lower()
        assert "cancelado" in reasoning_lower or "inactivo" in reasoning_lower or "disponible" in reasoning_lower


class TestLLMEdgeCases:
    """Additional edge cases and error handling"""
    
    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_nonexistent_user(self, agent_service, complex_test_users, complex_test_shows):
        """Test: Usuario que no existe en BD"""
        request_data = {
            "request_id": 21,
            "user_name": "Usuario Fantasma",
            "user_email": "fantasma@noexiste.com",
            "show_description": "Los Piojos Tributo"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["decision"] == "rejected"
        assert "usuario" in result["reasoning"].lower() or "registrado" in result["reasoning"].lower()

    @pytest.mark.llm
    @pytest.mark.asyncio
    async def test_completely_nonexistent_show(self, agent_service, complex_test_users, complex_test_shows):
        """Test: Show completamente inventado"""
        request_data = {
            "request_id": 22,
            "user_name": "Sebastian Valido",
            "user_email": "sebastian.valido@test.com",
            "show_description": "Banda Completamente Inventada en Venue Inexistente de Ciudad Falsa"
        }
        
        result = await agent_service.process_discount_request(request_data)
        
        assert result["success"] == True
        assert result["decision"] == "rejected"
        assert "encontr" in result["reasoning"].lower() or "exist" in result["reasoning"].lower() 