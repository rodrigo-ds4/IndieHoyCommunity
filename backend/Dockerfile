# Dockerfile para el Backend API (FastAPI + LangChain)
FROM python:3.11-slim

# Configurar directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear directorio de datos (la DB se poblará al iniciar la app)
RUN mkdir -p /app/data

# Hacer el script de entrada ejecutable
RUN chmod +x start.sh

# Exponer puerto para FastAPI
EXPOSE 8000

# Usar script de entrada que maneja PORT correctamente
CMD ["./start.sh"] 