#!/bin/bash
# Este script para, elimina, reconstruye y reinicia el backend de forma limpia.
set -e

echo "--- Navegando a la carpeta backend... ---"
cd backend

CONTAINER_NAME="charro-backend"
IMAGE_NAME="charro-backend:latest"

echo "--- Paso 1: Parando y eliminando contenedor antiguo (si existe)... ---"
# El '|| true' evita que el script falle si el contenedor no existe
docker stop $CONTAINER_NAME || true
docker rm $CONTAINER_NAME || true

echo "--- Paso 2: Eliminando imagen de Docker antigua para forzar reconstrucción... ---"
docker rmi -f $IMAGE_NAME || true

echo "--- Paso 3: Reconstruyendo la imagen de Docker desde cero SIN CACHÉ... ---"
# CORRECCIÓN: Añadiendo --no-cache para forzar que copie los nuevos archivos __init__.py
docker build --no-cache -t $IMAGE_NAME .

echo "--- Paso 4: Iniciando el nuevo contenedor... ---"
docker run -d -p 8000:8000 --name $CONTAINER_NAME $IMAGE_NAME

echo "--- Esperando 10 segundos a que el servidor se inicie... ---"
sleep 10

echo "--- Paso 5: Cargando datos (seeding) en la base de datos... ---"
docker exec $CONTAINER_NAME python -m app.core.seeder

echo "--- ¡Listo! El servidor está corriendo en http://localhost:8000/request y los datos han sido cargados. ---"