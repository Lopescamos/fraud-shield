# Estado — api-gateway

## Resumen (una línea)
Puerta pública: autentica analistas con JWT (HS256), proxea hacia los 4 servicios internos vía httpx.AsyncClient, inyecta `analyst_id` en el assign de alertas y traduce JWT → API key interna hacia analytics.

## Último avance
- 2026-11-19: scaffold Poetry + Dockerfile + `.env.example` + `.importlinter` + `CLAUDE.md`.
- 2026-11-19: kernel reducido (`Result`/`ApplicationError`), domain (`AuthenticatedUser`), `AuthService` con puertos `UserRepository`/`PasswordHasher`/`TokenIssuer`, adaptadores `BcryptPasswordHasher` + `PyJwtIssuer` + `EnvUserRepository`.
- 2026-11-19: `ProxyClient` (httpx async, limpia hop-by-hop headers, traduce fallos a 502 Problem Details).
- 2026-11-19: dependencias FastAPI `require_user` (Bearer JWT) y `require_posting_api_key` (X-API-Key); `auth_controller` POST `/auth/token`; `proxy_router` con las 10+ rutas espejadas; `assign` reemplaza `analyst_id` del cliente por el del claim; `/analytics/*` inyecta `X-API-Key` y descarta el JWT externo.
- 2026-11-19: main.py arma todo; exception_handlers emiten Problem Details con `trace_id` autogenerado si no vino.
- 2026-11-19: tests — 6 unit de auth (login OK, usuario inexistente, password mal, verify tras login, token manipulado, EnvUserRepository parseando CSV y tolerando malformed), 10 interfaces/rest con stub de proxy (login, 401 sin JWT, GET alert proxea, POST transactions con API key de posting, assign inyecta analyst_id, analytics inyecta X-API-Key), 1 architecture (lint-imports 3/3). Total 17 passed.

## Pendiente (orden sugerido)
- [ ] Mover el `UserRepository` a un IdP real (Keycloak / Azure AD) cuando esté en infra.
- [ ] Rate limiting (p. ej. por `analyst_id`) a nivel del gateway.
- [ ] Observabilidad: propagar más headers de tracing (W3C `traceparent`) y métricas Prometheus de latencia por ruta.
- [ ] CI: añadir un job de `api-gateway` al pipeline (ruff + mypy + lint-imports + pytest). Se cubre con `feature/ci-matrix`.
- [ ] Rotar el secret JWT y las API keys desde un secrets manager.

## Bloqueos / dudas
- ninguno

## Decisiones locales
- 2026-11-19: **HS256** para el MVP; el secret vive en `GATEWAY_JWT_SECRET` (CSV estilo .env). En producción se migra a RS256 con JWKS.
- 2026-11-19: Usuarios en env var CSV `username:bcrypt_hash:analyst_uuid` (`GATEWAY_USERS`). Es el stub mínimo que permite testear el flujo completo sin depender de un IdP externo.
- 2026-11-19: El gateway **reemplaza** el `analyst_id` del body en `/assign` con el del claim JWT (lo que el cliente mande se descarta). Decisión de seguridad: el claim es la fuente de verdad.
- 2026-11-19: Para `/analytics/*` el gateway cambia el JWT por `X-API-Key` hacia analytics-service. Rationale: analytics ya tiene su middleware de API key que Power BI usa; no queremos tener dos modos de auth en analytics.
- 2026-11-19: El POST `/api/v1/transactions` **no** usa JWT: lo autentica una clave de posting (`GATEWAY_POSTING_API_KEY`), porque lo invoca un sistema upstream (no un humano).
- 2026-11-19: `ProxyClient` drop-ea hop-by-hop headers (connection, host, content-length, transfer-encoding, etc.) antes de reenviar; el content-type se fuerza a `application/json` cuando hay body.
