from app.core.database import SessionLocal, engine, Base
from app.models.database import User, Show, EmailTemplate
from datetime import datetime, timedelta

print('Creando tablas...')
Base.metadata.create_all(bind=engine)
print('Tablas creadas!')

db = SessionLocal()

print('Cargando usuarios...')
users = [
    User(name='Juan Perez', email='juan.perez@test.com', subscription_active=True, monthly_fee_current=True, join_date=datetime.now() - timedelta(days=100)),
    User(name='Maria Garcia', email='maria.garcia@test.com', subscription_active=True, monthly_fee_current=False, join_date=datetime.now() - timedelta(days=200)),
    User(name='Ana Martinez', email='ana.martinez@test.com', subscription_active=True, monthly_fee_current=True, join_date=datetime.now() - timedelta(days=30)),
]
db.add_all(users)

print('Cargando shows...')
shows = [
    Show(name='Tini en el Campo de Polo', code='TINI2024', max_discounts=5, artist='Tini Stoessel', show_date=datetime(2024, 12, 15), other_data={'price': 15000, 'discount_details': '2x1 en entradas generales presentado este codigo en boleteria.'}),
    Show(name='Duki en River', code='DUKI2024', max_discounts=10, artist='Duki', show_date=datetime(2024, 11, 20), other_data={'price': 25000, 'discount_details': '15% de descuento en campo delantero. No acumulable.'}),
    Show(name='La Renga en La Plata', code='RENGALP', max_discounts=20, artist='La Renga', show_date=datetime(2025, 2, 1), other_data={'price': 20000, 'discount_details': 'Acceso preferencial y consumicion gratuita.'}),
]
db.add_all(shows)

print('Cargando plantillas de email...')
templates = [
    EmailTemplate(template_name='approval', subject='Tu descuento fue aprobado!', body='Hola! Tu solicitud fue aprobada. Detalles: {discount_details}'),
    EmailTemplate(template_name='rejection', subject='Informacion sobre tu solicitud', body='Hola, tu solicitud fue rechazada. Motivo: {rejection_reason}'),
]
db.add_all(templates)

db.commit()
db.close()
print('Datos cargados exitosamente!')
