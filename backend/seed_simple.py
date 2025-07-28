from app.core.database import get_db
from app.models.database import User, Show, EmailTemplate
from datetime import datetime

db = next(get_db())

# Limpiar
try:
    db.query(EmailTemplate).delete()
    db.query(Show).delete() 
    db.query(User).delete()
except:
    pass

# Usuarios
u1 = User(name='Juan Pérez', email='juan@example.com', subscription_active=True, monthly_fee_current=True)
u2 = User(name='María García', email='maria@example.com', subscription_active=True, monthly_fee_current=True)
db.add(u1)
db.add(u2)

# Shows
s1 = Show(
    title='Tini en el Campo de Polo',
    code='TINI2024',
    max_discounts=5,
    artist='Tini Stoessel',
    show_date=datetime(2024, 12, 15),
    venue='Campo de Polo',
    other_data={'price': 15000, 'discount_details': '1. Mostrar email en boletería\n2. Descuento 2x1\n3. Solo entradas generales'}
)

s2 = Show(
    title='Abel Pintos Acústico',
    code='ABEL2024',
    max_discounts=3,
    artist='Abel Pintos',
    show_date=datetime(2024, 11, 20),
    venue='Luna Park',
    other_data={'price': 12000, 'discount_details': '1. Presentar email en taquilla\n2. 30% descuento\n3. Máximo 2 entradas'}
)

db.add(s1)
db.add(s2)

# Template
t1 = EmailTemplate(
    template_name='approval',
    subject='¡Tu descuento para {show_title} fue aprobado!',
    body='¡Hola {user_name}!\n\nTu descuento para {show_title} fue aprobado.\n\nSeguí los siguientes pasos:\n{discount_details}\n\nCódigo: {discount_code}\n\n- IndieHOY'
)

db.add(t1)

db.commit()
db.close()
print('Datos creados')
