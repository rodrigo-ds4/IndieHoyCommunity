#!/usr/bin/env python3
import sys
sys.path.append('/app')

from app.core.database import get_db
from app.models.database import User, Show, EmailTemplate, SupervisionQueue
from datetime import datetime

def populate_database():
    # Obtener sesión de DB
    db = next(get_db())
    
    try:
        # Limpiar datos existentes
        db.query(SupervisionQueue).delete()
        db.query(EmailTemplate).delete()
        db.query(Show).delete()
        db.query(User).delete()
        
        # Crear usuarios
        users = [
            User(name='Juan Pérez', email='juan@example.com', subscription_active=True, monthly_fee_current=True),
            User(name='María García', email='maria@example.com', subscription_active=True, monthly_fee_current=True),
            User(name='Carlos López', email='carlos@example.com', subscription_active=False, monthly_fee_current=False),
        ]
        
        for user in users:
            db.add(user)
        
        # Crear shows
        shows = [
            Show(
                title='Tini en el Campo de Polo',
                code='TINI2024',
                max_discounts=5,
                artist='Tini Stoessel',
                show_date=datetime(2024, 12, 15),
                venue='Campo de Polo',
                other_data={
                    'price': 15000,
                    'discount_details': '1. Mostrar este email en la boletería del Campo de Polo\n2. Indicar que tenés el descuento 2x1 para Tini\n3. Por cada entrada que compres, llevás otra gratis\n4. Válido solo para entradas generales\n5. No acumulable con otras promociones'
                }
            ),
            Show(
                title='Abel Pintos Acústico',
                code='ABEL2024',
                max_discounts=3,
                artist='Abel Pintos',
                show_date=datetime(2024, 11, 20),
                venue='Luna Park',
                other_data={
                    'price': 12000,
                    'discount_details': '1. Presentar este email en taquilla de Luna Park\n2. Mencionar código de descuento ABEL2024\n3. Obtener 30% de descuento en entradas\n4. Válido hasta agotar stock\n5. Máximo 2 entradas por persona'
                }
            ),
            Show(
                title='La Beriso en Obras',
                code='BERISO2024',
                max_discounts=10,
                artist='La Beriso',
                show_date=datetime(2024, 10, 30),
                venue='Estadio Obras',
                other_data={
                    'price': 8000,
                    'discount_details': '1. Ir a boletería de Estadio Obras con este email\n2. Solicitar descuento La Beriso IndieHOY\n3. Recibir 25% de descuento\n4. Válido para todas las ubicaciones\n5. Presentar DNI junto con este email'
                }
            ),
        ]
        
        for show in shows:
            db.add(show)
        
        # Crear templates de email
        templates = [
            EmailTemplate(
                template_name='approval',
                subject='✅ ¡Tu descuento para {show_title} fue aprobado!',
                body='¡Hola {user_name}!\n\nBuenas noticias. Tu solicitud de descuento para el show de {show_title} fue aprobada.\n\nSeguí los siguientes pasos:\n{discount_details}\n\nCódigo de Descuento: {discount_code}\n\nPresentá este email en la boletería para hacerlo válido. ¡Que lo disfrutes!\n\n- El equipo de IndieHOY.'
            ),
            EmailTemplate(
                template_name='rejection',
                subject='❌ Tu solicitud de descuento no fue aprobada',
                body='Hola {user_name},\n\nLamentamos informarte que tu solicitud de descuento para {show_title} no pudo ser aprobada en esta ocasión.\n\nRazón: {rejection_reason}\n\nTe invitamos a estar atento a nuestras próximas promociones.\n\n- El equipo de IndieHOY.'
            ),
        ]
        
        for template in templates:
            db.add(template)
        
        # Crear algunos casos de ejemplo en supervision queue
        queue_items = [
            SupervisionQueue(
                user_email='juan@example.com',
                user_name='Juan Pérez',
                show_id=1,
                show_description='Tini en el Campo de Polo',
                status='pending',
                email_subject='✅ ¡Tu descuento para Tini en el Campo de Polo fue aprobado!',
                email_content='¡Hola Juan Pérez!\n\nBuenas noticias. Tu solicitud de descuento para el show de Tini en el Campo de Polo fue aprobada.\n\nSeguí los siguientes pasos:\n1. Mostrar este email en la boletería del Campo de Polo\n2. Indicar que tenés el descuento 2x1 para Tini\n3. Por cada entrada que compres, llevás otra gratis\n4. Válido solo para entradas generales\n5. No acumulable con otras promociones\n\nCódigo de Descuento: TINI-DISC-001\n\nPresentá este email en la boletería para hacerlo válido. ¡Que lo disfrutes!\n\n- El equipo de IndieHOY.',
                discount_code='TINI-DISC-001',
                created_at=datetime.now()
            ),
            SupervisionQueue(
                user_email='maria@example.com',
                user_name='María García',
                show_id=2,
                show_description='Abel Pintos Acústico',
                status='approved',
                email_subject='✅ ¡Tu descuento para Abel Pintos Acústico fue aprobado!',
                email_content='¡Hola María García!\n\nBuenas noticias. Tu solicitud de descuento para el show de Abel Pintos Acústico fue aprobada.\n\nSeguí los siguientes pasos:\n1. Presentar este email en taquilla de Luna Park\n2. Mencionar código de descuento ABEL2024\n3. Obtener 30% de descuento en entradas\n4. Válido hasta agotar stock\n5. Máximo 2 entradas por persona\n\nCódigo de Descuento: ABEL-DISC-002\n\nPresentá este email en la boletería para hacerlo válido. ¡Que lo disfrutes!\n\n- El equipo de IndieHOY.',
                discount_code='ABEL-DISC-002',
                created_at=datetime.now(),
                reviewer='Supervisor',
                reviewed_at=datetime.now()
            ),
        ]
        
        for item in queue_items:
            db.add(item)
        
        db.commit()
        print('✅ Base de datos poblada exitosamente')
        print(f'✅ Creados {len(users)} usuarios')
        print(f'✅ Creados {len(shows)} shows')
        print(f'✅ Creados {len(templates)} templates')
        print(f'✅ Creados {len(queue_items)} items en supervision queue')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    populate_database() 