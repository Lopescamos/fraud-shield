# infra/

Infraestructura local de FraudShield. Levanta la base de datos (y, más adelante, el broker y n8n) con un solo comando.

## Primera vez

1. Copia el ejemplo de variables y ajusta lo necesario:

   ```powershell
   cp .env.example .env
   ```

2. Levanta la base de datos:

   ```powershell
   docker compose -f infra/docker-compose.yml up -d
   ```

3. Verifica que PostgreSQL está arriba:

   ```powershell
   docker compose -f infra/docker-compose.yml ps
   docker exec -it fraudshield-database psql -U admin -d fraudshield -c "\dn+"
   ```

   Deberías ver los esquemas `tx`, `scoring`, `alerts` y `analytics`.

## Apagar y limpiar

```powershell
# Apagar sin borrar datos
docker compose -f infra/docker-compose.yml down

# Apagar y borrar todos los datos (vuelve a correr init.sql la próxima vez)
docker compose -f infra/docker-compose.yml down -v
```

## Qué contiene

| Carpeta / archivo | Qué guarda |
| --- | --- |
| `docker-compose.yml` | Stack local (database, broker, notifier) |
| `.env.example` | Variables de entorno de ejemplo (se versiona) |
| `.env` | Tus variables reales (ignorado por git) |
| `database/postgres/init.sql` | Esquemas y usuarios por servicio |
| `broker/kafka/` | Configuración y topics iniciales (cuando se habilite Kafka) |
| `notifications/n8n/` | Flujos exportados (cuando se habilite n8n) |

## Servicios comentados

El `docker-compose.yml` trae `broker` (Kafka) y `notifier` (n8n) **comentados**. Se habilitan cuando el proyecto llegue a la fase que los necesita (publicación de eventos y notificaciones).
