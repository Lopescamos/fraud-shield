# api-gateway — CLAUDE.md

## 1. Rol en el sistema
Única puerta pública de la plataforma. Autentica a los analistas con **JWT** (HS256), inyecta el `analyst_id` en cada request hacia `alert-service` y traduce el JWT a la **API key** interna cuando enruta hacia `analytics-service`. Los sistemas upstream que publican transacciones usan una **API key de posting** aparte, porque no son humanos.

## 2. Diferencia con los otros servicios
No tiene base de datos ni eventos de dominio: es un proxy REST con lógica de auth y de composición de headers. `kernel/` solo trae `Result`/`ApplicationError`. `domain/` contiene el value object `AuthenticatedUser` y nada más.

## 3. Endpoints (prefijo `/`)
- `POST /auth/token` — emite JWT (`{username, password}` → `{access_token, expires_in}`).
- `POST /api/v1/transactions` — protegido por `X-API-Key` de posting; proxy a transaction-service.
- `GET /api/v1/transactions/{id}` — protegido por JWT; proxy.
- `POST /api/v1/scores`, `GET /api/v1/scores/{id}` — protegido por JWT; proxy a scoring-service.
- `GET /api/v1/alerts`, `GET /api/v1/alerts/{id}` — JWT; proxy a alert-service.
- `PATCH /api/v1/alerts/{id}/assign` — JWT; el gateway **reemplaza/inyecta** `analyst_id` del claim; cuerpo del cliente no puede sobreescribirlo.
- `PATCH /api/v1/alerts/{id}/resolve|dismiss` — JWT; proxy.
- `GET /analytics/*` — JWT; el gateway agrega `X-API-Key` hacia analytics-service con la clave configurada.
- `GET /health`, `GET /ready` — públicos.

## 4. Reglas específicas
- JWT: HS256 por defecto. Secret en `GATEWAY_JWT_SECRET` (≥32 chars). TTL por `GATEWAY_JWT_TTL_SECONDS`.
- Usuarios: `GATEWAY_USERS` CSV `username:bcrypt_hash:analyst_uuid`. En producción se migra a un IdP real; MVP lo resuelve con env.
- El gateway **no escribe** datos; cualquier mutación delega al servicio dueño.
- Problem Details RFC 7807 para 401/403/422/5xx.
- Cada request propaga `X-Trace-Id` (lo genera si no viene).

## 5. Referencias
- Historias: US-15 (login analista), US-16 (routing unificado), US-17 (analytics con JWT en vez de API key).
- ADRs: ADR-008 (Power BI via API).
