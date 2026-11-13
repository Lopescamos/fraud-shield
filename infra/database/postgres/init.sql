-- ──────────────────────────────────────────────────────────────
-- FraudShield — inicialización de PostgreSQL
--
-- Se ejecuta una sola vez al crear el volumen `pgdata`.
-- Si editas este archivo después, debes borrar el volumen para que
-- vuelva a ejecutarse:
--     docker compose -f infra/docker-compose.yml down -v
--     docker compose -f infra/docker-compose.yml up -d
--
-- Crea:
--   - un esquema por microservicio
--   - un usuario por microservicio con permisos solo sobre su esquema
-- ──────────────────────────────────────────────────────────────

-- ── Esquemas ────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS tx;
CREATE SCHEMA IF NOT EXISTS scoring;
CREATE SCHEMA IF NOT EXISTS alerts;
CREATE SCHEMA IF NOT EXISTS analytics;

-- ── Usuarios por servicio ───────────────────────────────────
-- Las contraseñas vienen de variables de entorno del contenedor Postgres
-- (TX_USER_PASSWORD, SCORING_USER_PASSWORD, etc.), inyectadas vía
-- infra/.env. Uso \gexec para interpolarlas en el CREATE USER.

SELECT format(
    'CREATE USER tx_user WITH PASSWORD %L',
    current_setting('TX_USER_PASSWORD', true)
) WHERE current_setting('TX_USER_PASSWORD', true) IS NOT NULL
\gexec

SELECT format(
    'CREATE USER scoring_user WITH PASSWORD %L',
    current_setting('SCORING_USER_PASSWORD', true)
) WHERE current_setting('SCORING_USER_PASSWORD', true) IS NOT NULL
\gexec

SELECT format(
    'CREATE USER alerts_user WITH PASSWORD %L',
    current_setting('ALERTS_USER_PASSWORD', true)
) WHERE current_setting('ALERTS_USER_PASSWORD', true) IS NOT NULL
\gexec

SELECT format(
    'CREATE USER analytics_user WITH PASSWORD %L',
    current_setting('ANALYTICS_USER_PASSWORD', true)
) WHERE current_setting('ANALYTICS_USER_PASSWORD', true) IS NOT NULL
\gexec

-- Fallback si las variables no se expusieron (desarrollo local)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'tx_user') THEN
        CREATE USER tx_user WITH PASSWORD 'dev_tx';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'scoring_user') THEN
        CREATE USER scoring_user WITH PASSWORD 'dev_scoring';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'alerts_user') THEN
        CREATE USER alerts_user WITH PASSWORD 'dev_alerts';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'analytics_user') THEN
        CREATE USER analytics_user WITH PASSWORD 'dev_analytics';
    END IF;
END $$;

-- ── Permisos ────────────────────────────────────────────────
-- Cada usuario solo puede usar y crear objetos en su propio esquema.
GRANT USAGE, CREATE ON SCHEMA tx        TO tx_user;
GRANT USAGE, CREATE ON SCHEMA scoring   TO scoring_user;
GRANT USAGE, CREATE ON SCHEMA alerts    TO alerts_user;
GRANT USAGE, CREATE ON SCHEMA analytics TO analytics_user;

-- Fijar el search_path para que cada servicio escriba en su esquema
-- sin tener que calificar los nombres de tabla.
ALTER ROLE tx_user        SET search_path = tx;
ALTER ROLE scoring_user   SET search_path = scoring;
ALTER ROLE alerts_user    SET search_path = alerts;
ALTER ROLE analytics_user SET search_path = analytics;

-- ── Verificación rápida ─────────────────────────────────────
-- Al terminar, los esquemas y usuarios quedan creados. Para verificar:
--   docker exec -it fraudshield-database psql -U admin -d fraudshield \
--       -c "\dn+"       -- lista esquemas
--   docker exec -it fraudshield-database psql -U admin -d fraudshield \
--       -c "\du"        -- lista usuarios