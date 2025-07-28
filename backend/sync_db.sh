#!/bin/bash
echo "🔄 Actualizando base de datos..."
docker cp charro-backend:/app/charro_bot.db ./charro_bot.db
echo "✅ Base de datos actualizada. Refresca DB Browser (F5)"
