#!/bin/bash
# Script de entrada para Railway
# Maneja la variable PORT correctamente

# Usar PORT de Railway o 8000 por defecto
PORT=${PORT:-8000}

echo "🚀 Starting server on port $PORT"

# Ejecutar uvicorn con el puerto correcto
exec uvicorn main:app --host 0.0.0.0 --port $PORT 