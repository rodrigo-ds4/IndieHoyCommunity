"""
Sample Data for Testing
Creates realistic users, shows, and sample requests for development
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random

from app.models.database import User, Show, DiscountRequest
from app.core.database import SessionLocal


def create_sample_data():
    """Create sample data for testing the LangChain agent system"""
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(User).count() > 0:
            print("📊 Sample data already exists, skipping creation")
            return
        
        print("📊 Creating sample data...")
        
        # Create 20 realistic users
        users_data = [
            ("Juan Pérez", "juan.perez@gmail.com", 12345678, "011-1234-5678", "Buenos Aires", "instagram", "rock"),
            ("María García", "maria.garcia@hotmail.com", 87654321, "0341-876-5432", "Rosario", "referral", "pop"),
            ("Carlos López", "carlos.lopez@yahoo.com", 11223344, "0351-112-2334", "Córdoba", "google", "jazz"),
            ("Ana Martínez", "ana.martinez@outlook.com", 44332211, "011-4433-2211", "Buenos Aires", "facebook", "folklore"),
            ("Luis Rodríguez", "luis.rodriguez@gmail.com", 55667788, "0341-556-6778", "Rosario", "instagram", "rock"),
            ("Laura Fernández", "laura.fernandez@gmail.com", 88776655, "011-8877-6655", "Buenos Aires", "google", "pop"),
            ("Diego Morales", "diego.morales@hotmail.com", 99887766, "0351-998-8776", "Córdoba", "referral", "tango"),
            ("Sofía Ruiz", "sofia.ruiz@outlook.com", 66778899, "011-6677-8899", "Buenos Aires", "facebook", "indie"),
            ("Martín Silva", "martin.silva@yahoo.com", 33445566, "0341-334-4556", "Rosario", "instagram", "metal"),
            ("Valentina Torres", "valentina.torres@gmail.com", 77889900, "0351-778-8990", "Córdoba", "google", "electronic"),
            ("Andrés Gómez", "andres.gomez@hotmail.com", 22334455, "011-2233-4455", "Buenos Aires", "referral", "cumbia"),
            ("Camila Díaz", "camila.diaz@gmail.com", 55443322, "0341-554-4332", "Rosario", "facebook", "reggaeton"),
            ("Federico Castro", "federico.castro@outlook.com", 11998877, "0351-119-9887", "Córdoba", "instagram", "blues"),
            ("Agustina Vargas", "agustina.vargas@yahoo.com", 44556677, "011-4455-6677", "Buenos Aires", "google", "folk"),
            ("Nicolás Herrera", "nicolas.herrera@gmail.com", 77665544, "0341-776-6554", "Rosario", "referral", "punk"),
            ("Florencia Mendoza", "florencia.mendoza@hotmail.com", 88990011, "0351-889-9001", "Córdoba", "facebook", "alternative"),
            ("Matías Romero", "matias.romero@gmail.com", 33221100, "011-3322-1100", "Buenos Aires", "instagram", "hip-hop"),
            ("Lucía Giménez", "lucia.gimenez@outlook.com", 66554433, "0341-665-5443", "Rosario", "google", "classical"),
            ("Sebastián Peña", "sebastian.pena@yahoo.com", 99001122, "0351-990-0112", "Córdoba", "referral", "reggae"),
            ("Isabella Ramos", "isabella.ramos@gmail.com", 22113344, "011-2211-3344", "Buenos Aires", "facebook", "salsa")
        ]
        
        users = []
        for i, (name, email, dni, phone, city, source, genre) in enumerate(users_data):
            user = User(
                name=name,
                email=email,
                dni=dni,
                phone=phone,
                city=city,
                how_did_you_find_us=source,
                favorite_music_genre=genre,
                subscription_active=random.choice([True, True, True, False]),  # 75% active
                monthly_fee_current=(i >= 10)  # First 10 users NOT current, rest ARE current
            )
            users.append(user)
            db.add(user)
        
        # Create 50 shows with real venues
        shows_data = [
            # BUENOS AIRES VENUES
            ("ROCK001", "Los Piojos Tribute", "Luna Park", "Buenos Aires", "rock", 8000, "Presentar este código en boletería: INDIEHOY15"),
            ("POP002", "Tini en concierto", "Movistar Arena", "Buenos Aires", "pop", 12000, "Escribir a descuentos@movistar-arena.com con código INDIE20"),
            ("JAZZ003", "Escalandrum Live", "Café Tortoni", "Buenos Aires", "jazz", 3500, "Mostrar código en entrada: JAZZTORTONI"),
            ("FOLK004", "Mercedes Sosa Tribute", "Teatro San Martín", "Buenos Aires", "folklore", 4500, "Reservar por mail a reservas@teatrosanmartin.com mencionando INDIEHOY"),
            ("ROCK005", "Divididos", "Estadio Obras", "Buenos Aires", "rock", 6500, "Código de descuento en Ticketek: OBRAS10"),
            ("ELEC006", "Hernán Cattáneo", "Niceto Club", "Buenos Aires", "electronic", 2800, "Presentar en puerta con código: NICETO15"),
            ("INDIE007", "Bandalos Chinos", "La Trastienda", "Buenos Aires", "indie", 3200, "Mail a info@latrastienda.com con INDIE25"),
            ("TANGO008", "Orquesta Típica", "Café Tortoni", "Buenos Aires", "tango", 4000, "Reservas: tortoni@reservas.com - Código: TANGO20"),
            ("METAL009", "Almafuerte Tribute", "Groove", "Buenos Aires", "metal", 2500, "Código en boletería: GROOVE15"),
            ("CUM010", "La Delio Valdez", "Club Atlético Fernández Fierro", "Buenos Aires", "cumbia", 2000, "Escribir a info@cafef.com.ar con CUMBIA10"),
            ("ALT011", "Babasónicos", "Complejo Art Media", "Buenos Aires", "alternative", 5500, "Ticketek con código: ARTMEDIA20"),
            ("HIP012", "Wos en vivo", "Microestadio Malvinas", "Buenos Aires", "hip-hop", 7000, "Mail a info@malvinas.com con código WOS15"),
            ("BLUES013", "Memphis la Blusera", "Notorious", "Buenos Aires", "blues", 3800, "Presentar código: NOTORIOUS10"),
            ("PUNK014", "2 Minutos", "El Teatro Flores", "Buenos Aires", "punk", 2200, "Código en entrada: TEATROFLORES"),
            ("CLAS015", "Orquesta Sinfónica Nacional", "Teatro Colón", "Buenos Aires", "classical", 8500, "Reservas: colon@tickets.com - SINFONICA25"),
            ("REGG016", "Gondwana", "La Usina del Arte", "Buenos Aires", "reggae", 4200, "Mail a usina@reservas.com con REGGAE20"),
            ("SALSA017", "Oscar D'León", "Café Central", "Buenos Aires", "salsa", 3600, "Código de descuento: CENTRAL15"),
            
            # CÓRDOBA VENUES  
            ("ROCK018", "La Renga", "Estadio Kempes", "Córdoba", "rock", 5500, "Ticketek Córdoba - Código: KEMPES20"),
            ("POP019", "Abel Pintos", "Quality Espacio", "Córdoba", "pop", 6800, "Mail a info@quality.com.ar con ABEL15"),
            ("JAZZ020", "Peteco Carabajal", "Teatro del Libertador", "Córdoba", "jazz", 3200, "Reservas: libertador@teatros.cba.gov.ar - PETECO10"),
            
            # 🚨 SHOWS SOLD OUT PARA TESTING (max_discounts = 0)
            ("SOLD001", "Abel Pintos Sold Out", "Teatro Colón", "Buenos Aires", "pop", 15000, "Contactar Teatro Colón con código SOLD001"),
            ("SOLD002", "Charly García Completo", "Luna Park", "Buenos Aires", "rock", 12000, "Show completo - sin descuentos disponibles"),
            
            ("FOLK021", "Los Nocheros", "Teatro Real", "Córdoba", "folklore", 4800, "Código en boletería: REAL25"),
            ("INDIE022", "Conociendo Rusia", "Sala Siranush", "Córdoba", "indie", 2800, "Presentar código: SIRANUSH20"),
            ("ELEC023", "John Talabot", "Club Atlético Belgrano", "Córdoba", "electronic", 3500, "Mail a eventos@belgrano.com con TALABOT15"),
            ("TANGO024", "Quinteto Urbano", "Centro Cultural España", "Córdoba", "tango", 2500, "Código de descuento: ESPAÑA10"),
            ("METAL025", "Rata Blanca", "Complejo Forja", "Córdoba", "metal", 4200, "Ticketek con código: FORJA20"),
            ("CUM026", "Los Palmeras", "Predio Ferial Córdoba", "Córdoba", "cumbia", 3800, "Entrada con código: PALMERAS15"),
            ("ALT027", "Eruca Sativa", "Microestadio Atenas", "Córdoba", "alternative", 3200, "Mail a info@atenas.com con ERUCA25"),
            ("HIP028", "Trueno", "Arena Córdoba", "Córdoba", "hip-hop", 5800, "Código Ticketek: ARENA15"),
            ("BLUES029", "La Mississippi", "Jazz & Pop", "Córdoba", "blues", 2200, "Presentar en entrada: JAZZ10"),
            ("PUNK030", "Mal Momento", "Club Social y Deportivo Liceo", "Córdoba", "punk", 1800, "Código: LICEO20"),
            
            # ROSARIO VENUES
            ("ROCK031", "Las Pelotas", "Estadio Gigante de Arroyito", "Rosario", "rock", 6200, "Ticketek Rosario - Código: GIGANTE25"),
            ("POP032", "Soledad Pastorutti", "Metropolitan", "Rosario", "pop", 5500, "Mail a info@metropolitan.com.ar con SOLE15"),
            ("JAZZ033", "Sumo Tribute", "El Cairo", "Rosario", "jazz", 2800, "Código en puerta: CAIRO20"),
            ("FOLK034", "Chaqueño Palavecino", "Teatro El Círculo", "Rosario", "folklore", 4200, "Reservas: circulo@teatro.com - CHAQUENO10"),
            ("INDIE035", "1915", "Plataforma Lavardén", "Rosario", "indie", 2400, "Presentar código: LAVARDEN15"),
            ("ELEC036", "Djs Pareja", "Fabrik", "Rosario", "electronic", 3000, "Mail a info@fabrikrosario.com con PAREJA25"),
            ("TANGO037", "Carlos Gardel Tribute", "Teatro Municipal", "Rosario", "tango", 3800, "Código de descuento: MUNICIPAL20"),
            ("METAL038", "V8", "Metropolitano Rosario", "Rosario", "metal", 3600, "Ticketek con código: METRO15"),
            ("CUM039", "Damas Gratis", "Club Atlético Newell's", "Rosario", "cumbia", 2600, "Código en entrada: NEWELLS10"),
            ("ALT040", "El Mató a un Policía Motorizado", "Sala Lavardén", "Rosario", "alternative", 3200, "Mail a reservas@lavarden.com con MATO25"),
            ("HIP041", "Duki", "Estadio Cubierto Newell's", "Rosario", "hip-hop", 7200, "Código Ticketek: DUKI20"),
            ("BLUES042", "Pappo Tribute", "Roxy Live", "Rosario", "blues", 2400, "Presentar código: ROXY15"),
            ("PUNK043", "Attaque 77", "Club Social Fisherton", "Rosario", "punk", 2800, "Código en boletería: FISHERTON10"),
            ("CLAS044", "Orquesta Sinfónica de Rosario", "Teatro El Círculo", "Rosario", "classical", 4800, "Reservas con código: SINFONICA30"),
            ("REGG045", "Mimi Maura", "Casa Brava", "Rosario", "reggae", 2200, "Mail a casabrava@eventos.com con MIMI20"),
            ("SALSA046", "Willie Colón", "Quality Hotel", "Rosario", "salsa", 5200, "Código de descuento: QUALITY25"),
            ("ROCK047", "Catupecu Machu", "Metropolitano", "Rosario", "rock", 4800, "Ticketek con CATUPECU15"),
            ("INDIE048", "Él Mató", "Centro Cultural Parque España", "Rosario", "indie", 2600, "Presentar código: PARQUEESPAÑA20"),
            ("ELEC049", "Miss Kittin", "Club 69", "Rosario", "electronic", 3400, "Mail a info@club69.com.ar con KITTIN10"),
            ("FOLK050", "Los Tekis", "Anfiteatro Municipal", "Rosario", "folklore", 3800, "Código municipal: TEKIS25")
        ]
        
        shows = []
        for code, title, venue, city, genre, price, discount_info in shows_data:
            show_date = datetime.now() + timedelta(days=random.randint(1, 90))
            
            # 🚨 SHOWS SOLD OUT - max_discounts = 0
            if "SOLD" in code:
                max_discounts = 0
            else:
                max_discounts = random.randint(5, 25)
            
            show = Show(
                code=code,
                title=title,
                artist=title.split()[0] if " " in title else title,
                venue=venue,
                show_date=show_date,
                max_discounts=max_discounts,
                ticketing_link=f"https://ticketek.com.ar/{code.lower()}",
                other_data={
                    "genre": genre,
                    "price": price,
                    "city": city,
                    "discount_instructions": discount_info,
                    "venue_capacity": random.randint(200, 15000)
                },
                active=random.choice([True, True, True, False])  # 75% active
            )
            shows.append(show)
            db.add(show)

        db.commit()
        print("✅ Sample data created successfully!")
        
        # Print statistics
        print(f"\n📊 STATISTICS:")
        print(f"👤 Users created: {len(users)}")
        print(f"🎭 Shows created: {len(shows)}")
        
        active_users = sum(1 for u in users if u.subscription_active)
        current_users = sum(1 for u in users if u.monthly_fee_current)
        print(f"✅ Active subscriptions: {active_users}/{len(users)}")
        print(f"💳 Current with fees: {current_users}/{len(users)}")
        
        ba_shows = sum(1 for s in shows if s.other_data["city"] == "Buenos Aires")
        cba_shows = sum(1 for s in shows if s.other_data["city"] == "Córdoba") 
        ros_shows = sum(1 for s in shows if s.other_data["city"] == "Rosario")
        print(f"🏙️ Shows by city: BA:{ba_shows}, CBA:{cba_shows}, ROS:{ros_shows}")
        
        print(f"\n🎵 GENRES AVAILABLE:")
        genres = {}
        for s in shows:
            genre = s.other_data["genre"]
            genres[genre] = genres.get(genre, 0) + 1
        for genre, count in sorted(genres.items()):
            print(f"  - {genre}: {count} shows")
        
        print(f"\n📧 SAMPLE USERS (for testing):")
        for i, user in enumerate(users[:5]):
            status = "✅" if user.subscription_active and user.monthly_fee_current else "❌"
            print(f"  {status} {user.email} - {user.name} ({user.city}, {user.favorite_music_genre})")
        print(f"  ... and {len(users)-5} more users")

    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def clear_sample_data():
    """Clear all sample data"""
    db = SessionLocal()
    try:
        print("🗑️ Clearing sample data...")
        db.query(DiscountRequest).delete()
        db.query(Show).delete()
        db.query(User).delete()
        db.commit()
        print("✅ Sample data cleared successfully!")
    except Exception as e:
        print(f"❌ Error clearing sample data: {e}")
        db.rollback()
    finally:
        db.close() 