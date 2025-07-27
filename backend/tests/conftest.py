"""
Pytest fixtures for LLM discount system testing
"""
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base, User, Show
# from app.services.langchain_agent_service import LangChainAgentService  # OLD - using new architecture
from app.core.database import get_db
from datetime import datetime, timedelta
import random


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    yield db
    
    db.close()


@pytest.fixture(scope="function")
def agent_service(test_db):
    """Create new DiscountDecisionService with test database"""
    from app.services.discount_decision_service import DiscountDecisionService
    return DiscountDecisionService(test_db)


@pytest.fixture(scope="function")
def complex_test_users(test_db):
    """Create complex test users with various edge cases"""
    users_data = [
        # ✅ VÁLIDOS - Cuotas al día
        ("Sebastian Valido", "sebastian.valido@test.com", 12345678, True, True, "Buenos Aires", "rock"),
        ("Maria Perfecta", "maria.perfecta@test.com", 87654321, True, True, "Córdoba", "pop"),
        ("Carlos Completo", "carlos.completo@test.com", 11223344, True, True, "Rosario", "cumbia"),
        
        # ❌ CUOTAS ATRASADAS
        ("Juan Atrasado", "juan.atrasado@test.com", 99887766, True, False, "Buenos Aires", "rock"),
        ("Ana Deudora", "ana.deudora@test.com", 55443322, True, False, "Mendoza", "folk"),
        ("Luis Moroso", "luis.moroso@test.com", 33221100, True, False, "Córdoba", "jazz"),
        
        # ❌ SUSCRIPCIÓN INACTIVA  
        ("Pedro Inactivo", "pedro.inactivo@test.com", 77889900, False, True, "Buenos Aires", "rock"),
        ("Sofia Suspendida", "sofia.suspendida@test.com", 66554433, False, True, "Rosario", "pop"),
        
        # ❌ AMBOS PROBLEMAS
        ("Ricardo Doble", "ricardo.doble@test.com", 44332211, False, False, "La Plata", "tango"),
        ("Elena Problema", "elena.problema@test.com", 22114455, False, False, "Mar del Plata", "rock"),
        
        # ✅ CASOS EDGE VÁLIDOS
        ("Nombre Con Espacios Raros", "espacios@test.com", 12121212, True, True, "Buenos Aires", "indie"),
        ("José María Fernández-López", "jose.maria@test.com", 34343434, True, True, "Córdoba", "folk"),
    ]
    
    users = []
    for name, email, dni, subscription, fees, city, genre in users_data:
        user = User(
            name=name,
            email=email,
            dni=dni,
            phone=f"011-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
            city=city,
            subscription_active=subscription,
            monthly_fee_current=fees,
            how_did_you_find_us="test",
            favorite_music_genre=genre,
            registration_date=datetime.now()
        )
        users.append(user)
        test_db.add(user)
    
    test_db.commit()
    return users


@pytest.fixture(scope="function") 
def complex_test_shows(test_db):
    """Create complex test shows with confusing names and edge cases"""
    shows_data = [
        # ✅ SHOWS CON DESCUENTOS DISPONIBLES
        ("ROCK001", "Los Piojos Tributo", "Los Piojos", "Luna Park", 10, "Buenos Aires", "rock", 8000),
        ("POP002", "Tini en Concierto", "Tini", "Movistar Arena", 15, "Buenos Aires", "pop", 12000),
        ("WOS003", "Wos en Vivo", "Wos", "Microestadio Malvinas", 8, "Buenos Aires", "rap", 7000),
        
        # ❌ SIN DESCUENTOS (0 remaining)
        ("SOLD001", "Abel Pintos Sold Out", "Abel Pintos", "Teatro Colón", 0, "Buenos Aires", "folk", 15000),
        ("FULL002", "Charly García Completo", "Charly García", "Estadio Único", 0, "La Plata", "rock", 20000),
        
        # 🤔 NOMBRES CONFUSOS/AMBIGUOS
        ("CONF001", "Los Angeles de Charlie", "Los Angeles", "Charlie Club", 5, "Buenos Aires", "rock", 3000),
        ("CONF002", "La Beriso en La Beriso", "La Beriso", "Estadio La Beriso", 3, "La Beriso", "rock", 5000),
        ("CONF003", "Show de Juan", "Juan", "Casa de Juan", 2, "Buenos Aires", "indie", 1500),
        ("CONF004", "Banda Sinónimo", "Los Sinónimos", "Teatro Sinónimo", 4, "Córdoba", "rock", 4000),
        
        # 🎭 NOMBRES SIMILARES (fuzzy matching challenge)
        ("SIM001", "Los Piosos", "Los Piosos", "Club Atlético", 6, "Buenos Aires", "rock", 3500),
        ("SIM002", "Las Piojas", "Las Piojas", "Centro Cultural", 7, "Rosario", "rock", 2800),
        ("SIM003", "Los Piojos Falsos", "Los Piojos Falsos", "Bar El Refugio", 3, "Córdoba", "rock", 2000),
        
        # 🎪 SHOWS EXTREMOS
        ("EXT001", "A", "A", "Lugar A", 1, "Buenos Aires", "experimental", 500),
        ("EXT002", "Artista Con Nombre Muy Muy Muy Largo Que Casi No Entra", "Artista Largo", "Venue Largo", 2, "Buenos Aires", "indie", 1000),
        
        # 🎵 GÉNEROS DIVERSOS  
        ("DIV001", "Orquesta Sinfónica", "Filarmónica", "Teatro San Martín", 12, "Buenos Aires", "clasica", 8000),
        ("DIV002", "DJ Electrónico", "DJ Electronic", "Niceto Club", 20, "Buenos Aires", "electronica", 3000),
        ("DIV003", "Tango Milonga", "Los Tangueros", "Salón Canning", 8, "Buenos Aires", "tango", 2500),
        ("DIV004", "Folklore Argentino", "Los Folkloristas", "Peña Nacional", 6, "Buenos Aires", "folklore", 3500),
        
        # ❌ SHOWS INACTIVOS
        ("INAC001", "Show Cancelado", "Artista Cancelado", "Venue Cerrado", 10, "Buenos Aires", "rock", 5000),
        ("INAC002", "Evento Suspendido", "Banda Suspendida", "Local Clausurado", 5, "Córdoba", "pop", 4000),
    ]
    
    shows = []
    for code, title, artist, venue, max_discounts, city, genre, price in shows_data:
        show_date = datetime.now() + timedelta(days=random.randint(7, 60))
        
        show = Show(
            code=code,
            title=title,
            artist=artist,
            venue=venue,
            show_date=show_date,
            max_discounts=max_discounts,
            ticketing_link=f"https://tickets.com/{code.lower()}",
            active=(not code.startswith("INAC")),  # Inactivos empiezan con INAC
            other_data={
                "genre": genre,
                "price": price,
                "city": city,
                "discount_instructions": f"Contactar {venue} con código {code}",
                "venue_capacity": random.randint(200, 15000)
            }
        )
        shows.append(show)
        test_db.add(show)
    
    test_db.commit()
    return shows


@pytest.fixture(scope="function")
def test_request_data():
    """Base test request data"""
    return {
        "request_id": 999,
        "user_name": "Test User",
        "user_email": "test@example.com", 
        "show_description": "Test Show"
    } 