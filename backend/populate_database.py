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
DB_PATH = "/app/data/charro_bot.db"

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
        
        for i, user_data in enumerate(users_data, 1):
            registration_date = datetime.now() - timedelta(days=random.randint(30, 365))
            
            self.cursor.execute("""
                INSERT INTO users (
                    id, name, email, dni, phone, city, registration_date,
                    how_did_you_find_us, favorite_music_genre, subscription_active,
                    monthly_fee_current, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                i, user_data["name"], user_data["email"], user_data["dni"],
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
        
        shows_data = [
            {
                "code": "TINI2024",
                "title": "Tini - Cupido Tour",
                "artist": "Tini Stoessel",
                "venue": "Movistar Arena",
                "show_date": datetime(2024, 9, 15, 21, 0),
                "max_discounts": 20,
                "ticketing_link": "https://www.ticketek.com.ar/tini-cupido-tour",
                "other_data": {
                    "discount_percentage": 15,
                    "instructions": "Seguí los siguientes pasos:\n1. Ingresá a Ticketek con tu cuenta\n2. Seleccioná las entradas para Tini - Cupido Tour\n3. En el checkout, ingresá el código de descuento\n4. Completá la compra\n\n¡Disfrutá del show!",
                    "category": "Pop Nacional",
                    "age_restriction": "ATP"
                }
            },
            {
                "code": "BANDALOS2024",
                "title": "Bandalos Chinos en vivo",
                "artist": "Bandalos Chinos",
                "venue": "Niceto Club",
                "show_date": datetime(2024, 8, 22, 22, 30),
                "max_discounts": 15,
                "ticketing_link": "https://www.plateanet.com/bandalos-chinos",
                "other_data": {
                    "discount_percentage": 20,
                    "instructions": "Seguí los siguientes pasos:\n1. Comprá tu entrada en Plateanet\n2. Usá el código antes del pago\n3. Llegá temprano, el venue es íntimo\n4. Llevá efectivo para bebidas\n\n¡Nos vemos en el show!",
                    "category": "Indie Rock",
                    "age_restriction": "+16"
                }
            },
            {
                "code": "MIRANDA2024",
                "title": "Miranda! - Fuerte Tour",
                "artist": "Miranda!",
                "venue": "Teatro Flores",
                "show_date": datetime(2024, 10, 5, 20, 0),
                "max_discounts": 12,
                "ticketing_link": "https://www.tuentrada.com/miranda-fuerte-tour",
                "other_data": {
                    "discount_percentage": 25,
                    "instructions": "Seguí los siguientes pasos:\n1. Entrá a TuEntrada.com\n2. Buscá 'Miranda! - Fuerte Tour'\n3. Aplicá tu código de descuento\n4. Elegí tu ubicación preferida\n5. Finalizá la compra\n\n¡Te esperamos para cantar todos los hits!",
                    "category": "Electropop",
                    "age_restriction": "ATP"
                }
            },
            {
                "code": "CONOCIENDO2024",
                "title": "Conociendo Rusia - Cabildo Tour",
                "artist": "Conociendo Rusia",
                "venue": "Uniclub",
                "show_date": datetime(2024, 11, 12, 21, 30),
                "max_discounts": 8,
                "ticketing_link": "https://www.tickethoy.com/conociendo-rusia",
                "other_data": {
                    "discount_percentage": 30,
                    "instructions": "Seguí los siguientes pasos:\n1. Ingresá a TicketHoy\n2. Seleccioná Conociendo Rusia - Cabildo Tour\n3. Elegí tu entrada (campo o platea)\n4. Aplicá el código en 'Promociones'\n5. Completá el pago\n\n¡Preparate para una noche increíble!",
                    "category": "Indie Nacional",
                    "age_restriction": "+18"
                }
            }
        ]
        
        for i, show_data in enumerate(shows_data, 1):
            self.cursor.execute("""
                INSERT INTO shows (
                    id, code, title, artist, venue, show_date, max_discounts,
                    ticketing_link, other_data, active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                i, show_data["code"], show_data["title"], show_data["artist"],
                show_data["venue"], show_data["show_date"].isoformat(),
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
        
        for i, template_data in enumerate(templates_data, 1):
            self.cursor.execute("""
                INSERT INTO email_templates (
                    id, template_name, subject, body, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                i, template_data["template_name"], template_data["subject"],
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
        
        requests_data = [
            # 5 APROBADOS
            {"user_id": 1, "show_id": 1, "status": "approved", "delivery": "delivered"},
            {"user_id": 2, "show_id": 2, "status": "approved", "delivery": "sent"},
            {"user_id": 3, "show_id": 3, "status": "approved", "delivery": None},
            {"user_id": 4, "show_id": 4, "status": "approved", "delivery": "delivered"},
            {"user_id": 5, "show_id": 1, "status": "approved", "delivery": "bounced"},
            
            # 1 RECHAZADO
            {"user_id": 6, "show_id": 2, "status": "rejected", "delivery": "sent"},
            
            # 4 ENVIADOS con diferentes resultados
            {"user_id": 1, "show_id": 3, "status": "sent", "delivery": "delivered"},
            {"user_id": 2, "show_id": 4, "status": "sent", "delivery": "failed"},
            {"user_id": 3, "show_id": 1, "status": "sent", "delivery": "bounced"},
            {"user_id": 7, "show_id": 2, "status": "sent", "delivery": "delivered"}
        ]
        
        for i, req_data in enumerate(requests_data, 1):
            request_id = str(uuid.uuid4())
            discount_code = f"INDIE{random.randint(1000, 9999)}"
            
            # Obtener datos del usuario y show
            self.cursor.execute("SELECT name, email FROM users WHERE id = ?", (req_data["user_id"],))
            user_name, user_email = self.cursor.fetchone()
            
            self.cursor.execute("SELECT title, artist FROM shows WHERE id = ?", (req_data["show_id"],))
            show_title, show_artist = self.cursor.fetchone()
            
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
            
            self.cursor.execute("""
                INSERT INTO supervision_queue (
                    id, request_id, user_email, user_name, show_description,
                    decision_type, decision_source, show_id, email_subject,
                    email_content, confidence_score, reasoning, processing_time,
                    status, email_delivery_status, created_at, reviewed_at,
                    reviewed_by, supervisor_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                i, request_id, user_email, user_name, f"{show_title} - {show_artist}",
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