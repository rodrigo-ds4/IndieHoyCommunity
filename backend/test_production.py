#!/usr/bin/env python3
"""
Script para probar el modo producción
Cambia temporalmente ENVIRONMENT=production y reinicia el servidor
"""
import os
import subprocess
import time

print("🔧 Configurando modo PRODUCCIÓN...")

# Crear archivo .env temporal con ENVIRONMENT=production
env_content = """ENVIRONMENT=production
DEBUG=false
"""

with open('.env', 'w') as f:
    f.write(env_content)

print("✅ Archivo .env creado con ENVIRONMENT=production")

# Reconstruir y ejecutar contenedor
print("🐳 Reconstruyendo contenedor...")
subprocess.run([
    "docker", "stop", "charro-backend"
], capture_output=True)

subprocess.run([
    "docker", "rm", "charro-backend"
], capture_output=True)

subprocess.run([
    "docker", "build", "--no-cache", "-t", "charro-bot-backend", "."
], capture_output=True)

subprocess.run([
    "docker", "run", "-d", "--name", "charro-backend", 
    "-p", "8000:8000", "-v", f"{os.getcwd()}/data:/app/data", 
    "charro-bot-backend"
], capture_output=True)

print("⏳ Esperando que el servidor inicie...")
time.sleep(5)

# Probar endpoints
print("\n🧪 PROBANDO ENDPOINTS EN PRODUCCIÓN:")

# Test /docs (debería dar 404)
result = subprocess.run([
    "curl", "-s", "-I", "http://localhost:8000/docs"
], capture_output=True, text=True)

if "404" in result.stdout:
    print("✅ /docs correctamente oculto (404)")
else:
    print(f"❌ /docs no está oculto: {result.stdout.split()[1] if result.stdout else 'Error'}")

# Test /redoc (debería dar 404)
result = subprocess.run([
    "curl", "-s", "-I", "http://localhost:8000/redoc"
], capture_output=True, text=True)

if "404" in result.stdout:
    print("✅ /redoc correctamente oculto (404)")
else:
    print(f"❌ /redoc no está oculto: {result.stdout.split()[1] if result.stdout else 'Error'}")

# Test endpoint público (debería funcionar)
result = subprocess.run([
    "curl", "-s", "-I", "http://localhost:8000/api/v1/health"
], capture_output=True, text=True)

if "200" in result.stdout:
    print("✅ /api/v1/health funciona correctamente (200)")
else:
    print(f"❌ /api/v1/health no funciona: {result.stdout.split()[1] if result.stdout else 'Error'}")

print("\n🔄 Para volver a desarrollo, ejecuta:")
print("rm .env && docker restart charro-backend") 