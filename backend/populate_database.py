#!/usr/bin/env python3
"""
🎯 Script de Población de Base de Datos - IndieHOY
==================================================

Pobla la base de datos con datos realistas para testing:
- 5 usuarios activos + 2 con problemas
- 4 shows indies
- 2 templates de email (approval/rejection)
- 10 solicitudes de descuentos con estados variados

Uso:
    python populate_database.py
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

# Configuración
DB_PATH = "./data/charro_bot.db"

class DatabasePopulator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Conectar a la base de datos"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"📡 Conectado a: {self.db_path}")
    
    def disconnect(self):
        """Desconectar de la base de datos"""
        if self.conn:
            self.conn.close()
            print("📡 Desconectado de la base de datos")
    
    def clear_data(self):
        """Limpiar datos existentes (excepto esquema)"""
        print("🧹 Limpiando datos existentes...")
        
        tables = ['supervision_queue', 'payment_history', 'email_templates', 'shows', 'users']
        for table in tables:
            try:
                self.cursor.execute(f"DELETE FROM {table}")
                print(f"   ✅ {table} limpiada")
            except Exception as e:
                print(f"   ⚠️ Error limpiando {table}: {e}")
        
        self.conn.commit()
        print("✅ Limpieza completada")
    
    def populate_users(self):
        """Poblar usuarios (5 activos + 2 con problemas)"""
        print("👥 Poblando usuarios...")
        
        users_data = [
            # 5 USUARIOS ACTIVOS
            {
                "name": "María González",
                "email": "maria.gonzalez@gmail.com",
                "dni": 12345678,
                "phone": "+54 11 1234-5678",
                "city": "Buenos Aires",
                "how_did_you_find_us": "instagram",
                "favorite_music_genre": "indie rock",
                "subscription_active": True,
                "monthly_fee_current": True
            },
            {
                "name": "Juan Pérez",
                "email": "juan.perez@hotmail.com",
                "dni": 23456789,
                "phone": "+54 11 2345-6789",
                "city": "Córdoba",
                "how_did_you_find_us": "referral",
                "favorite_music_genre": "folk",
                "subscription_active": True,
                "monthly_fee_current": True
            },
            {
                "name": "Ana Martínez",
                "email": "ana.martinez@yahoo.com",
                "dni": 34567890,
                "phone": "+54 11 3456-7890",
                "city": "Rosario",
                "how_did_you_find_us": "google",
                "favorite_music_genre": "electronic",
                "subscription_active": True,
                "monthly_fee_current": True
            },
            {
                "name": "Carlos López",
                "email": "carlos.lopez@gmail.com",
                "dni": 45678901,
                "phone": "+54 11 4567-8901",
                "city": "Mendoza",
                "how_did_you_find_us": "facebook",
                "favorite_music_genre": "jazz",
                "subscription_active": True,
                "monthly_fee_current": True
            },
            {
                "name": "Sofía Rodríguez",
                "email": "sofia.rodriguez@outlook.com",
                "dni": 56789012,
                "phone": "+54 11 5678-9012",
                "city": "La Plata",
                "how_did_you_find_us": "instagram",
                "favorite_music_genre": "indie pop",
                "subscription_active": True,
                "monthly_fee_current": True
            },
            # 2 USUARIOS CON PROBLEMAS
            {
                "name": "Pedro Morales",
                "email": "pedro.morales@gmail.com",
                "dni": 67890123,
                "phone": "+54 11 6789-0123",
                "city": "Tucumán",
                "how_did_you_find_us": "referral",
                "favorite_music_genre": "rock",
                "subscription_active": False,  # ❌ SUSCRIPCIÓN INACTIVA
                "monthly_fee_current": False
            },
            {
                "name": "Laura Fernández",
                "email": "laura.fernandez@hotmail.com",
                "dni": 78901234,
                "phone": "+54 11 7890-1234",
                "city": "Salta",
                "how_did_you_find_us": "google",
                "favorite_music_genre": "alternative",
                "subscription_active": True,
                "monthly_fee_current": False  # ❌ PAGO ATRASADO
            }
        ]
        
        for user_data in users_data:
            registration_date = datetime.now() - timedelta(days=random.randint(30, 365))
            
            # No especificar ID, dejar que SQLite auto-incremente
            self.cursor.execute("""
                INSERT INTO users (
                    name, email, dni, phone, city, registration_date,
                    how_did_you_find_us, favorite_music_genre, subscription_active,
                    monthly_fee_current, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data["name"], user_data["email"], user_data["dni"],
                user_data["phone"], user_data["city"], registration_date.isoformat(),
                user_data["how_did_you_find_us"], user_data["favorite_music_genre"],
                user_data["subscription_active"], user_data["monthly_fee_current"],
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
        
        self.conn.commit()
        print(f"   ✅ {len(users_data)} usuarios creados")
    
    def populate_shows(self):
        """Poblar shows indies"""
        print("🎵 Poblando shows...")
        
        # URL por defecto para shows sin imagen específica
        default_img = "https://indiehoy.com/wp-content/uploads/2024/05/comunidad-logo-blanco-1.png"
        today = datetime.now()
        
        shows_data = [
            # AGOSTO 2025
            {
                "code": "BANDALOS2025_CBA",
                "title": "Bandalos Chinos",
                "artist": "Bandalos Chinos",
                "venue": "Estadio Atenas",
                "img": "https://indiehoy.com/wp-content/uploads/2025/07/bandalos-chinos-en-cordoba-capital-2025-atenas-450x563.jpg",
                "show_date": datetime(2025, 8, 1, 21, 0),
                "max_discounts": 0,  # Beneficio Agotado
                "ticketing_link": "https://www.ticketek.com.ar/bandalos-chinos-cordoba",
                "other_data": {
                    "discount_percentage": 0,
                    "discount_type": "Beneficio Agotado",
                    "instructions": "Lamentablemente los descuentos para este show se han agotado.",
                    "category": "Indie Rock",
                    "city": "Córdoba"
                }
            },
            {
                "code": "MAITE2025",
                "title": "Maite Fleischmann",
                "artist": "Maite Fleischmann", 
                "venue": "Roseti",
                "img": "https://indiehoy.com/wp-content/uploads/2025/07/maite-450x450.jpg",
                "show_date": datetime(2025, 8, 1, 22, 0),
                "max_discounts": 50,  # Gratis con Comunidad
                "ticketing_link": "https://www.plateanet.com/maite-fleischmann",
                "other_data": {
                    "discount_percentage": 100,
                    "discount_type": "Gratis con Comunidad",
                    "instructions": "¡Entrada completamente gratuita para miembros de IndieHOY Comunidad!",
                    "category": "Indie Folk",
                    "city": "Buenos Aires"
                }
            },
            {
                "code": "BHAVI2025_CBA",
                "title": "Bhavi",
                "artist": "Bhavi",
                "venue": "Estadio Kempes",
                "img": default_img,
                "show_date": datetime(2025, 8, 7, 21, 0),
                "max_discounts": 25,
                "ticketing_link": "https://www.ticketek.com.ar/bhavi-cordoba",
                "other_data": {
                    "discount_percentage": 30,
                    "discount_type": "30% OFF",
                    "instructions": "Aplicá tu código de descuento en el checkout para obtener 30% OFF.",
                    "category": "Trap/Hip Hop",
                    "city": "Córdoba"
                }
            },
            {
                "code": "LAVALENTI2025",
                "title": "La Valenti",
                "artist": "La Valenti",
                "venue": "Konex",
                "img": default_img,
                "show_date": datetime(2025, 8, 8, 22, 0),
                "max_discounts": 30,
                "ticketing_link": "https://www.tuentrada.com/la-valenti",
                "other_data": {
                    "discount_percentage": 20,
                    "discount_type": "20% OFF",
                    "instructions": "Descuento del 20% disponible para miembros de la comunidad.",
                    "category": "Indie Pop",
                    "city": "Buenos Aires"
                }
            },
            {
                "code": "NICOLASJAAR2025",
                "title": "Nicolás Jaar",
                "artist": "Nicolás Jaar",
                "venue": "Deseo",
                "img": default_img,
                "show_date": datetime(2025, 8, 18, 23, 0),
                "max_discounts": 20,
                "ticketing_link": "https://www.plateanet.com/nicolas-jaar",
                "other_data": {
                    "discount_percentage": 20,
                    "discount_type": "20% OFF",
                    "instructions": "Show de música electrónica experimental. 20% OFF para la comunidad.",
                    "category": "Electrónica Experimental",
                    "city": "Buenos Aires"
                }
            },
            
            # SEPTIEMBRE 2025
            {
                "code": "CLUBZ2025",
                "title": "Clubz",
                "artist": "Clubz",
                "venue": "Niceto Club",
                "img": "https://indiehoy.com/wp-content/uploads/2025/07/clubz-indiehoy-450x562.jpg",
                "show_date": datetime(2025, 9, 25, 22, 30),
                "max_discounts": 40,
                "ticketing_link": "https://www.plateanet.com/clubz",
                "other_data": {
                    "discount_percentage": 20,
                    "discount_type": "20% OFF",
                    "instructions": "Descuento del 20% en Niceto Club para este show imperdible.",
                    "category": "Electro Pop",
                    "city": "Buenos Aires"
                }
            },
            {
                "code": "ARBOL2025_TEMP",
                "title": "Árbol",
                "artist": "Árbol",
                "venue": "Auditorio Sur",
                "img": default_img,
                "show_date": datetime(2025, 9, 13, 21, 0),
                "max_discounts": 15,
                "ticketing_link": "https://www.tuentrada.com/arbol",
                "other_data": {
                    "discount_percentage": 50,
                    "discount_type": "50% OFF",
                    "instructions": "¡Descuento especial del 50% para este show de rock nacional!",
                    "category": "Rock Nacional",
                    "city": "Temperley"
                }
            },
            
            # OCTUBRE 2025
            {
                "code": "LICHI2025",
                "title": "Lichi",
                "artist": "Lichi",
                "venue": "Niceto Club",
                "img": "https://indiehoy.com/wp-content/uploads/2025/05/lucy-patane-lichi-rosario-450x563.jpg",
                "show_date": datetime(2025, 10, 5, 21, 30),
                "max_discounts": 35,
                "ticketing_link": "https://www.plateanet.com/lichi",
                "other_data": {
                    "discount_percentage": 30,
                    "discount_type": "30% OFF",
                    "instructions": "Show íntimo en Niceto Club con 30% OFF para la comunidad.",
                    "category": "Indie Folk",
                    "city": "Buenos Aires"
                }
            },
            {
                "code": "SHAILA2025",
                "title": "Shaila",
                "artist": "Shaila",
                "venue": "Obras",
                "img": default_img,
                "show_date": datetime(2025, 10, 11, 20, 0),
                "max_discounts": 25,
                "ticketing_link": "https://www.ticketek.com.ar/shaila",
                "other_data": {
                    "discount_percentage": 20,
                    "discount_type": "20% OFF",
                    "instructions": "Shaila en el Estadio Obras con 20% OFF.",
                    "category": "Punk Rock",
                    "city": "Buenos Aires"
                }
            },
            {
                "code": "RUSOWSKY2025",
                "title": "Rusowsky",
                "artist": "Rusowsky",
                "venue": "C Art Media",
                "img": default_img,
                "show_date": datetime(2025, 10, 24, 22, 0),
                "max_discounts": 30,
                "ticketing_link": "https://www.tuentrada.com/rusowsky",
                "other_data": {
                    "discount_percentage": 20,
                    "discount_type": "20% OFF",
                    "instructions": "Show de indie pop español con 20% OFF.",
                    "category": "Indie Pop",
                    "city": "Buenos Aires"
                }
            },
            
            # NOVIEMBRE 2025
            {
                "code": "FMK2025",
                "title": "FMK",
                "artist": "FMK",
                "venue": "Niceto Club",
                "img": default_img,
                "show_date": datetime(2025, 11, 30, 22, 0),
                "max_discounts": 40,
                "ticketing_link": "https://www.plateanet.com/fmk",
                "other_data": {
                    "discount_percentage": 20,
                    "discount_type": "20% OFF",
                    "instructions": "FMK en Niceto Club con 20% OFF para la comunidad.",
                    "category": "Reggaeton/Trap",
                    "city": "Buenos Aires"
                }
            },
            
            # EVENTOS ESPECIALES CON IMAGEN
            {
                "code": "OPERACIONES2025",
                "title": "Operaciones Culturales",
                "artist": "Las Tussi, El Club Audiovisual y más",
                "venue": "Niceto Club",
                "img": "https://indiehoy.com/wp-content/uploads/2025/07/operacionesculturales-450x562.jpg",
                "show_date": today,
                "max_discounts": 50,
                "ticketing_link": "https://www.plateanet.com/operaciones-culturales",
                "other_data": {
                    "discount_percentage": 20,
                    "discount_type": "20% OFF",
                    "instructions": "Evento cultural múltiple con varios artistas y 20% OFF.",
                    "category": "Evento Cultural",
                    "city": "Buenos Aires"
                }
            },
            {
                "code": "ABRILSOSA2025",
                "title": "Abril Sosa",
                "artist": "Abril Sosa",
                "venue": "Centro Cultural de Quilmes",
                "img": "https://indiehoy.com/wp-content/uploads/2025/06/abril-sosa-quilmes-450x563.jpg",
                "show_date": today,
                "max_discounts": 25,
                "ticketing_link": "https://www.tuentrada.com/abril-sosa",
                "other_data": {
                    "discount_percentage": 25,
                    "discount_type": "25% OFF", 
                    "instructions": "Show íntimo de Abril Sosa en Quilmes con 25% OFF.",
                    "category": "Indie Folk",
                    "city": "Quilmes"
                }
            }
        ]
        
        for show_data in shows_data:
            # No especificar ID, dejar que SQLite auto-incremente
            self.cursor.execute("""
                INSERT INTO shows (
                    code, title, artist, venue, img, show_date, max_discounts,
                    ticketing_link, other_data, active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                show_data["code"], show_data["title"], show_data["artist"],
                show_data["venue"], show_data["img"], show_data["show_date"].isoformat(),
                show_data["max_discounts"], show_data["ticketing_link"],
                json.dumps(show_data["other_data"]), True, datetime.now().isoformat()
            ))
        
        self.conn.commit()
        print(f"   ✅ {len(shows_data)} shows creados")
    
    def populate_email_templates(self):
        """Poblar templates de email"""
        print("📧 Poblando templates de email...")
        
        templates_data = [
            {
                "template_name": "approved",
                "subject": "¡Tu descuento para {show_title} ha sido aprobado! 🎉",
                "body": """¡Hola {user_name}!

¡Excelentes noticias! Tu solicitud de descuento ha sido APROBADA.

🎵 DETALLES DEL EVENTO:
• Evento: {show_title}
• Artista: {show_artist}
• Venue: {show_venue}
• Código de descuento: {discount_code}

📝 INSTRUCCIONES:
{other_data}

⏰ IMPORTANTE: Este código es válido por 7 días desde la fecha de este email.

¡Gracias por ser parte de la comunidad IndieHOY!

Saludos,
El equipo de IndieHOY 🎶"""
            },
            {
                "template_name": "rejected",
                "subject": "Información sobre tu solicitud de descuento - IndieHOY",
                "body": """Hola {user_name},

Gracias por contactarte con IndieHOY.

Lamentablemente, no podemos procesar tu solicitud de descuento para {show_title} en este momento.

🔍 POSIBLES MOTIVOS:
• El evento ya no tiene descuentos disponibles
• Tu suscripción no está activa
• Hay pagos pendientes en tu cuenta
• El evento ya pasó o fue cancelado

💡 SOLUCIONES:
• Verificá el estado de tu suscripción en tu perfil
• Contactanos si tenés dudas sobre tu cuenta
• Revisá nuestros otros eventos disponibles

¡Esperamos poder ayudarte pronto!

Saludos,
El equipo de IndieHOY 🎶"""
            }
        ]
        
        for template_data in templates_data:
            # No especificar ID, dejar que SQLite auto-incremente
            self.cursor.execute("""
                INSERT INTO email_templates (
                    template_name, subject, body, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                template_data["template_name"], template_data["subject"],
                template_data["body"], datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        
        self.conn.commit()
        print(f"   ✅ {len(templates_data)} templates creados")
    
    def populate_discount_requests(self):
        """Poblar solicitudes de descuentos con estados variados"""
        print("🎫 Poblando solicitudes de descuentos...")
        
        # Estados de delivery para variedad
        delivery_statuses = [
            None,  # Sin enviar
            "sent",  # Enviado
            "delivered",  # Entregado
            "bounced",  # Rebotado
            "failed"  # Falló
        ]
        
        # 🔄 Obtener IDs reales de usuarios y shows creados (ahora auto-incrementados)
        self.cursor.execute("SELECT id FROM users ORDER BY id LIMIT 7")
        user_ids = [row[0] for row in self.cursor.fetchall()]
        
        self.cursor.execute("SELECT id FROM shows ORDER BY id LIMIT 4") 
        show_ids = [row[0] for row in self.cursor.fetchall()]
        
        if len(user_ids) < 7 or len(show_ids) < 4:
            print(f"   ⚠️ No hay suficientes usuarios ({len(user_ids)}/7) o shows ({len(show_ids)}/4)")
            return
        
        requests_data = [
            # 5 APROBADOS
            {"user_id": user_ids[0], "show_id": show_ids[0], "status": "approved", "delivery": "delivered"},
            {"user_id": user_ids[1], "show_id": show_ids[1], "status": "approved", "delivery": "sent"},
            {"user_id": user_ids[2], "show_id": show_ids[2], "status": "approved", "delivery": None},
            {"user_id": user_ids[3], "show_id": show_ids[3], "status": "approved", "delivery": "delivered"},
            {"user_id": user_ids[4], "show_id": show_ids[0], "status": "approved", "delivery": "bounced"},
            
            # 1 RECHAZADO
            {"user_id": user_ids[5], "show_id": show_ids[1], "status": "rejected", "delivery": "sent"},
            
            # 4 ENVIADOS con diferentes resultados
            {"user_id": user_ids[0], "show_id": show_ids[2], "status": "sent", "delivery": "delivered"},
            {"user_id": user_ids[1], "show_id": show_ids[3], "status": "sent", "delivery": "failed"},
            {"user_id": user_ids[2], "show_id": show_ids[0], "status": "sent", "delivery": "bounced"},
            {"user_id": user_ids[6], "show_id": show_ids[1], "status": "sent", "delivery": "delivered"}
        ]
        
        for req_data in requests_data:
            request_id = str(uuid.uuid4())
            discount_code = f"INDIE{random.randint(1000, 9999)}"
            
            # Obtener datos del usuario y show por ID (ahora auto-incrementados)
            self.cursor.execute("SELECT name, email FROM users WHERE id = ?", (req_data["user_id"],))
            user_row = self.cursor.fetchone()
            if not user_row:
                print(f"   ⚠️ Usuario ID {req_data['user_id']} no encontrado, saltando...")
                continue
            user_name, user_email = user_row
            
            self.cursor.execute("SELECT title, artist FROM shows WHERE id = ?", (req_data["show_id"],))
            show_row = self.cursor.fetchone()
            if not show_row:
                print(f"   ⚠️ Show ID {req_data['show_id']} no encontrado, saltando...")
                continue
            show_title, show_artist = show_row
            
            # Determinar tipo de decisión y contenido del email
            if req_data["status"] == "approved":
                decision_type = "approved"
                email_subject = f"¡Tu descuento para {show_title} ha sido aprobado! 🎉"
                email_content = f"""¡Hola {user_name}!

¡Excelentes noticias! Tu solicitud de descuento ha sido APROBADA.

🎵 DETALLES DEL EVENTO:
• Evento: {show_title}
• Artista: {show_artist}
• Código de descuento: {discount_code}

📝 Seguí las instrucciones en la plataforma de ticketing.

¡Gracias por ser parte de IndieHOY! 🎶"""
            else:
                decision_type = "rejected"
                email_subject = f"Información sobre tu solicitud - {show_title}"
                email_content = f"""Hola {user_name},

Lamentablemente no podemos procesar tu solicitud para {show_title}.

Contactanos si tenés dudas.

Saludos,
IndieHOY 🎶"""
            
            created_at = datetime.now() - timedelta(days=random.randint(1, 30))
            reviewed_at = created_at + timedelta(hours=random.randint(1, 48)) if req_data["status"] != "pending" else None
            
            # No especificar ID, dejar que SQLite auto-incremente
            self.cursor.execute("""
                INSERT INTO supervision_queue (
                    request_id, user_email, user_name, show_description,
                    decision_type, decision_source, show_id, email_subject,
                    email_content, confidence_score, reasoning, processing_time,
                    status, email_delivery_status, created_at, reviewed_at,
                    reviewed_by, supervisor_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request_id, user_email, user_name, f"{show_title} - {show_artist}",
                decision_type, "prefilter_template", req_data["show_id"],
                email_subject, email_content, 0.95, 
                f"Usuario válido, show disponible, {decision_type}",
                round(random.uniform(0.5, 2.0), 2), req_data["status"],
                req_data["delivery"], created_at.isoformat(),
                reviewed_at.isoformat() if reviewed_at else None,
                "supervisor@indiehoy.com" if reviewed_at else None,
                f"Procesado automáticamente - {decision_type}" if reviewed_at else None
            ))
        
        self.conn.commit()
        print(f"   ✅ {len(requests_data)} solicitudes creadas")
        print(f"      • 5 aprobadas")
        print(f"      • 1 rechazada") 
        print(f"      • 4 enviadas (con diferentes estados de delivery)")
    
    def show_summary(self):
        """Mostrar resumen de los datos poblados"""
        print("\n📊 RESUMEN DE DATOS POBLADOS:")
        print("=" * 50)
        
        # Contar registros por tabla
        tables = [
            ("users", "👥 Usuarios"),
            ("shows", "🎵 Shows"),
            ("email_templates", "📧 Templates"),
            ("supervision_queue", "🎫 Solicitudes")
        ]
        
        for table, label in tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = self.cursor.fetchone()[0]
            print(f"{label}: {count}")
        
        # Detalles de solicitudes por estado
        print("\n🎫 SOLICITUDES POR ESTADO:")
        self.cursor.execute("""
            SELECT status, COUNT(*) 
            FROM supervision_queue 
            GROUP BY status
        """)
        for status, count in self.cursor.fetchall():
            print(f"   • {status}: {count}")
        
        # Detalles de delivery status
        print("\n📧 ESTADOS DE ENTREGA:")
        self.cursor.execute("""
            SELECT email_delivery_status, COUNT(*) 
            FROM supervision_queue 
            GROUP BY email_delivery_status
        """)
        for delivery, count in self.cursor.fetchall():
            delivery_name = delivery or "Sin enviar"
            print(f"   • {delivery_name}: {count}")

def main():
    """Función principal"""
    print("🚀 INICIANDO POBLACIÓN DE BASE DE DATOS")
    print("=" * 60)
    
    populator = DatabasePopulator(DB_PATH)
    
    try:
        # Conectar
        populator.connect()
        
        # Limpiar datos existentes
        populator.clear_data()
        
        # Poblar datos
        populator.populate_users()
        populator.populate_shows() 
        populator.populate_email_templates()
        populator.populate_discount_requests()
        
        # Mostrar resumen
        populator.show_summary()
        
        print("\n🎉 ¡POBLACIÓN COMPLETADA EXITOSAMENTE!")
        print("La base de datos está lista para usar.")
        
    except Exception as e:
        print(f"❌ Error durante la población: {e}")
        return 1
    
    finally:
        populator.disconnect()
    
    return 0

if __name__ == "__main__":
    exit(main()) 