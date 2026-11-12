# ADR-008: Power BI consume una API dedicada, no la base de datos

- Estado: Aceptada
- Fecha: 2026-11-10

## Contexto

Power BI puede conectarse a PostgreSQL directamente mediante un conector nativo. Sin embargo, abrir ese puerto y compartir credenciales con una herramienta externa implica: exponer el modelo interno, perder control sobre qué se consulta, saturar la base transaccional con queries de BI y quedarse sin auditoría de quién consultó qué.

## Decisión

Power BI **no se conecta a PostgreSQL**. Consume el servicio `analytics-service` por HTTPS a través del `api-gateway`, en el prefijo `/bi/v1`, usando una **API key con rol `bi_reader`**.

### Controles

- Autenticación con `X-API-Key` (clave hasheada en BD, rotable).
- Paginación obligatoria con `page_size` máximo 1,000.
- Rate limiting por clave (60 req/min, configurable).
- Caché de 60 s en los endpoints de KPIs.
- Auditoría de cada llamada: clave, endpoint, parámetros, `trace_id`.
- Sin PII: las cuentas aparecen seudonimizadas; los montos se pueden agrupar por rango.
- Origen de datos: solo el esquema `analytics`, alimentado por eventos. Nunca las tablas transaccionales.

### Qué se expone

Cinco endpoints paginados (`/bi/v1/kpis`, `/timeseries`, `/risk-distribution`, `/alerts`, `/model-performance`) con esquemas estables y versionados (`/bi/v1 → /bi/v2` cuando haya cambios incompatibles).

## Alternativas consideradas

- **Conexión directa Power BI → PostgreSQL con usuario `bi_reader` read-only y vistas.** Más simple de montar, pero expone el motor, no tiene rate limiting por query y los cambios de esquema rompen los reportes.
- **Exportaciones programadas a CSV/Parquet.** Pierde "tiempo casi real" y añade pipeline de archivos.

## Consecuencias

- La base de datos **nunca** queda al alcance de herramientas externas, un punto fuerte para presentar en entrevista.
- El esquema interno puede cambiar sin romper reportes: el contrato es la API.
- El reporte Power BI se conecta con el conector Web (Power Query en M) enviando la clave en la cabecera; la clave entra como parámetro del informe, no escrita en las consultas.
- En Power BI Service se necesita una API con dominio público y HTTPS para refrescos programados; para el portafolio basta con Power BI Desktop y capturas.
