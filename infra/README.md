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

## Kafka

El broker arranca con `docker compose up -d`. Un contenedor `topics-init` corre una sola vez al terminar el healthcheck y crea los topics del proyecto (idempotente con `--if-not-exists`):

| Topic | Particiones | DLQ |
| --- | --- | --- |
| `transactions.received.v1` | 6 | `transactions.received.v1.dlq` |
| `transactions.scored.v1`   | 6 | `transactions.scored.v1.dlq` |
| `alerts.raised.v1`         | 3 | `alerts.raised.v1.dlq` |
| `alerts.resolved.v1`       | 3 | `alerts.resolved.v1.dlq` |

Verificar:

```powershell
docker exec -it fraudshield-broker /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker:9092 --list
```

### Cómo apuntar los servicios

- **Desde la red docker** (cuando los servicios corran en el mismo compose): `broker:9092`.
- **Desde tu host** (cuando corras `uvicorn` local): `localhost:29092` (puerto `KAFKA_HOST_PORT`).

Ejemplo de encendido:

```powershell
$env:TRANSACTION_KAFKA_BOOTSTRAP_SERVERS="localhost:29092"
$env:TRANSACTION_OUTBOX_RELAY_ENABLED="true"
poetry run uvicorn transaction.main:app --port 8001
```

Mismo patrón con `SCORING_*`, `ALERT_*` y `ANALYTICS_*` + sus switches `*_CONSUMER_ENABLED`.

## Servicios comentados

Queda `notifier` (n8n) **comentado**; se habilita en la fase de notificaciones.
