#!/bin/bash

echo "🔄 Reiniciando contenedor con mapeo de volumen..."

# Detener y remover contenedor existente
docker stop charro-backend 2>/dev/null || true
docker rm charro-backend 2>/dev/null || true

# Crear carpeta data si no existe
mkdir -p data

# Reconstruir imagen
echo "🏗️ Reconstruyendo imagen..."
docker build --no-cache -t charro-bot-backend .

# Ejecutar contenedor con volumen mapeado
echo "🚀 Ejecutando contenedor..."
docker run -d --name charro-backend -p 8000:8000 -v $(pwd)/data:/app/data charro-bot-backend

# Esperar que el contenedor se inicie
echo "⏳ Esperando que el contenedor se inicie..."
sleep 5

# Poblar base de datos
echo "📊 Poblando base de datos..."
docker exec charro-backend python -c "
import sys
sys.path.append('/app')
from app.core.database import engine
from app.models.database import Base, User, Show, EmailTemplate, SupervisionQueue
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

# Crear tablas
Base.metadata.create_all(bind=engine)

# Crear sesión
Session = sessionmaker(bind=engine)
session = Session()

# Limpiar datos existentes
session.query(SupervisionQueue).delete()
session.query(EmailTemplate).delete()
session.query(Show).delete()
session.query(User).delete()

# Crear usuarios
users = [
    User(name='Juan Pérez', email='juan@example.com', subscription_active=True, monthly_fee_current=True, registration_date=datetime.now()),
    User(name='María García', email='maria@example.com', subscription_active=True, monthly_fee_current=True, registration_date=datetime.now()),
    User(name='Carlos López', email='carlos@example.com', subscription_active=False, monthly_fee_current=False, registration_date=datetime.now()),
]

for user in users:
    session.add(user)

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
    session.add(show)

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
    session.add(template)

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
    session.add(item)

session.commit()
session.close()
print('✅ Base de datos creada y poblada exitosamente')
"

echo "✅ ¡Listo! Contenedor ejecutándose con base de datos mapeada"
echo "📍 Base de datos ubicada en: $(pwd)/data/charro_bot.db"
echo "🌐 Dashboard: http://localhost:8000/static/supervision.html"
echo "🌐 Landing: http://localhost:8000/static/request-discount.html" 