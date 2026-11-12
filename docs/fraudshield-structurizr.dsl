workspace "FraudShield" "Plataforma de detección de fraude transaccional: microservicios Python/FastAPI, Kafka, PostgreSQL, scoring con reglas + ML y API de analítica para Power BI" {

    model {

        group "Actores del sistema" {
            ingestClient = person "Sistema de ingesta"   "Sistema del banco o fintech que envía transacciones en tiempo casi real para evaluación de riesgo." "IngestClient"
            analista     = person "Analista de fraude"   "Revisa alertas, cambia su estado y deja notas de investigación." "Analyst"
            admin        = person "Administrador"        "Gestiona reglas, modelos, usuarios y claves de API." "Admin"
            biAnalyst    = person "Analista de negocio"  "Consume KPIs y reportes operativos a través de Power BI." "BIAnalyst"
        }

        fraudshield = softwareSystem "FraudShield" "Plataforma de detección de fraude: ingesta por API, scoring explicable, alertas y analítica expuesta por API dedicada" "FraudShield" {

            gateway        = container "api-gateway"         "Único punto de entrada: autenticación JWT/API key, rate limiting, enrutamiento a servicios internos" "FastAPI / Python 3.12" "Gateway"
            transactionSvc = container "transaction-service" "Recibe transacciones, aplica idempotencia y Outbox, publica TransactionReceivedV1" "FastAPI / Python 3.12" "Service" {

                txDomain         = component "domain"          "Transaction (aggregate), AccountId, Money, Channel, DeviceId; comandos y puerto TransactionRepository" "Python puro" "Component"
                txApplication    = component "application"     "TransactionCommandService y TransactionQueryService; event handlers; puerto MessagePublisher" "Python" "Component"
                txInfrastructure = component "infrastructure"  "SQLAlchemy async, Outbox, AccountProfile para reglas de velocidad, adaptador Kafka" "Python" "Component"
                txInterfaces     = component "interfaces"      "TransactionsController (REST) y consumidores (ninguno en este servicio); endpoints /transactions" "FastAPI" "Component"
                txKernel         = component "kernel"          "Result, ApplicationError, base de agregado, IdempotentExecutor" "Python" "Component"
            }

            scoringSvc = container "scoring-service" "Consume TransactionReceivedV1, calcula el puntaje con reglas + ML + SHAP y publica TransactionScoredV1" "FastAPI / Python 3.12 + XGBoost / SHAP" "Service" {

                scoDomain         = component "domain"          "RiskAssessment (aggregate), RiskScore, RiskLevel, Explanation, RuleHit; puertos RiskModel, Explainer, RuleCatalog" "Python puro" "Component"
                scoApplication    = component "application"     "AssessmentCommandService combina reglas + modelos; puerto MessagePublisher" "Python" "Component"
                scoInfrastructure = component "infrastructure"  "XGBoostRiskModel, IsolationForestRiskModel, ShapExplainer, YamlRuleCatalog, Outbox" "Python + XGBoost + SHAP" "Component"
                scoInterfaces     = component "interfaces"      "ScoringController (REST) y TransactionRegisteredConsumer; endpoints /score/preview, /assessments/{id}, /models/active" "FastAPI" "Component"
                scoKernel         = component "kernel"          "Result, ApplicationError, base de agregado, IdempotentExecutor" "Python" "Component"
            }

            alertSvc = container "alert-service" "Consume TransactionScoredV1, crea alertas, publica AlertRaisedV1 y dispara notificaciones" "FastAPI / Python 3.12" "Service" {

                alDomain         = component "domain"          "FraudAlert (aggregate), AlertStatus, Severity, AnalystId, AlertNote; puerto AlertRepository" "Python puro" "Component"
                alApplication    = component "application"     "AlertCommandService (raise, change status, add note) y AlertQueryService; puerto NotificationSender" "Python" "Component"
                alInfrastructure = component "infrastructure"  "SQLAlchemy async, Outbox, N8nWebhookSender" "Python + httpx" "Component"
                alInterfaces     = component "interfaces"      "AlertsController (REST) y TransactionScoredConsumer; endpoints /alerts, /alerts/{id}/status, /alerts/{id}/notes" "FastAPI" "Component"
                alKernel         = component "kernel"          "Result, ApplicationError, base de agregado, IdempotentExecutor" "Python" "Component"
            }

            analyticsSvc = container "analytics-service" "Modelo de lectura en estrella alimentado por Kafka; expone /bi/v1 a Power BI" "FastAPI / Python 3.12" "Service" {

                anDomain         = component "domain"          "FactTransaction, FactAlert, DimDate, DimChannel, DimRiskLevel; consultas KpiQuery, TimeseriesQuery, AlertsQuery, ModelPerformanceQuery" "Python puro" "Component"
                anApplication    = component "application"     "AnalyticsQueryService: resuelve las consultas sobre el modelo de lectura" "Python" "Component"
                anInfrastructure = component "infrastructure"  "SQLAlchemy async, caché de KPIs, actualización por mensajes" "Python" "Component"
                anInterfaces     = component "interfaces"      "BiController (REST) y TransactionReceivedConsumer, TransactionScoredConsumer, AlertRaisedConsumer; endpoints /bi/v1/*" "FastAPI" "Component"
                anKernel         = component "kernel"          "Result, ApplicationError, IdempotentExecutor" "Python" "Component"
            }

            postgres = container "PostgreSQL" "Base relacional única con un esquema y un usuario por servicio; migraciones Alembic" "PostgreSQL 16" "Database"
            kafka    = container "Apache Kafka"  "Log de eventos en modo KRaft; tópicos versionados con DLQ" "Apache Kafka 3.x / KRaft" "Broker"
            sharedContracts = container "shared-contracts" "Paquete Python con los modelos Pydantic de los eventos (TransactionReceivedV1, TransactionScoredV1, AlertRaisedV1, AlertResolvedV1) y el Envelope común" "Python package" "Library"
        }

        powerBi   = softwareSystem "Power BI Desktop" "Consume /bi/v1 vía conector Web; carga el reporte de cuatro páginas" "ExternalSystem"
        n8n       = softwareSystem "n8n"              "Orquesta notificaciones ante alertas altas o críticas" "ExternalSystem"
        telegram  = softwareSystem "Telegram / Outlook" "Canal final de notificación (vía Power Automate si corresponde)" "ExternalSystem"

        # ── Actores → sistema ──────────────────────────────────────────────
        ingestClient -> gateway   "Envía transacciones"           "HTTPS / JSON + API key"
        analista     -> gateway   "Revisa y actualiza alertas"    "HTTPS / JSON + JWT"
        admin        -> gateway   "Gestiona reglas y modelos"     "HTTPS / JSON + JWT"
        biAnalyst    -> powerBi   "Abre el reporte"
        powerBi      -> gateway   "Consulta KPIs y series"        "HTTPS + API key (X-API-Key)"

        # ── Gateway → servicios internos ───────────────────────────────────
        gateway -> transactionSvc "Enruta /api/v1/transactions*"
        gateway -> scoringSvc     "Enruta /api/v1/score*, /models/active"
        gateway -> alertSvc       "Enruta /api/v1/alerts*"
        gateway -> analyticsSvc   "Enruta /bi/v1/*"

        # ── Servicios ↔ persistencia ───────────────────────────────────────
        transactionSvc -> postgres "Lee/escribe su esquema" "asyncpg"
        scoringSvc     -> postgres "Lee/escribe su esquema" "asyncpg"
        alertSvc       -> postgres "Lee/escribe su esquema" "asyncpg"
        analyticsSvc   -> postgres "Lee/escribe su esquema" "asyncpg"

        # ── Mensajería Kafka ───────────────────────────────────────────────
        transactionSvc -> kafka "Publica TransactionReceivedV1 (Outbox)" "AIOKafka"
        scoringSvc     -> kafka "Consume TransactionReceivedV1; publica TransactionScoredV1" "AIOKafka"
        alertSvc       -> kafka "Consume TransactionScoredV1; publica AlertRaisedV1 / AlertResolvedV1" "AIOKafka"
        analyticsSvc   -> kafka "Consume los tres tópicos para alimentar el modelo de lectura" "AIOKafka"

        # ── Shared contracts ───────────────────────────────────────────────
        transactionSvc -> sharedContracts "Usa contratos V1 al publicar"       "Pydantic"
        scoringSvc     -> sharedContracts "Usa contratos V1 al consumir/publicar" "Pydantic"
        alertSvc       -> sharedContracts "Usa contratos V1 al consumir/publicar" "Pydantic"
        analyticsSvc   -> sharedContracts "Usa contratos V1 al consumir"        "Pydantic"

        # ── Alertas → notificaciones ───────────────────────────────────────
        alertSvc -> n8n      "Dispara webhook con el payload de AlertRaisedV1" "HTTPS / JSON"
        n8n      -> telegram "Envía notificación enriquecida"                   "Bot API / HTTPS"

        # ── Componentes transaction-service ────────────────────────────────
        txInterfaces     -> txApplication    "Invoca commands y queries"
        txApplication    -> txDomain         "Opera sobre el aggregate y value objects"
        txApplication    -> txInfrastructure "Usa el repositorio y el MessagePublisher (puertos)"
        txInfrastructure -> postgres         "Persistencia" "SQLAlchemy async"
        txInfrastructure -> kafka            "Outbox relay" "AIOKafka"
        txKernel         -> txDomain         "Expone Result, errores y base de agregado"

        # ── Componentes scoring-service ────────────────────────────────────
        scoInterfaces     -> scoApplication    "Invoca commands y queries"
        scoApplication    -> scoDomain         "Usa RiskModel, Explainer y RuleCatalog (puertos)"
        scoApplication    -> scoInfrastructure "Usa adaptadores concretos"
        scoInfrastructure -> postgres          "Persistencia" "SQLAlchemy async"
        scoInfrastructure -> kafka             "Consume y publica" "AIOKafka"

        # ── Componentes alert-service ──────────────────────────────────────
        alInterfaces     -> alApplication    "Invoca commands y queries"
        alApplication    -> alDomain         "Opera sobre FraudAlert"
        alApplication    -> alInfrastructure "Usa el repositorio, Outbox y NotificationSender"
        alInfrastructure -> postgres         "Persistencia"
        alInfrastructure -> kafka            "Consume y publica"
        alInfrastructure -> n8n              "Dispara webhook"

        # ── Componentes analytics-service ──────────────────────────────────
        anInterfaces     -> anApplication    "Invoca queries"
        anApplication    -> anDomain         "Resuelve consultas"
        anApplication    -> anInfrastructure "Usa el repositorio del modelo de lectura"
        anInfrastructure -> postgres         "Lee el esquema analytics"
        anInfrastructure -> kafka            "Consume los tres tópicos"
    }

    views {

        systemContext fraudshield "Contexto" {
            include *
            autolayout lr
            description "C1 — Contexto: actores, el sistema y dependencias externas"
        }

        container fraudshield "Contenedores" {
            include *
            autolayout tb
            description "C2 — Contenedores: servicios, broker, base, shared-contracts y sistemas externos"
        }

        component transactionSvc "Componentes_Transaction" {
            include *
            autolayout lr
            description "C3 — Componentes del transaction-service (4 capas DDD + kernel)"
        }

        component scoringSvc "Componentes_Scoring" {
            include *
            autolayout lr
            description "C3 — Componentes del scoring-service (4 capas DDD + kernel)"
        }

        component alertSvc "Componentes_Alert" {
            include *
            autolayout lr
            description "C3 — Componentes del alert-service (4 capas DDD + kernel)"
        }

        component analyticsSvc "Componentes_Analytics" {
            include *
            autolayout lr
            description "C3 — Componentes del analytics-service (solo lectura)"
        }

        styles {
            element "Person" {
                shape person
                background #08427B
                color #ffffff
            }
            element "IngestClient" { background #1168BD }
            element "Analyst"      { background #0A3B70 }
            element "Admin"        { background #052755 }
            element "BIAnalyst"    { background #2E6DA4 }

            element "FraudShield" {
                background #438DD5
                color #ffffff
            }
            element "Gateway" {
                background #2E86DE
                color #ffffff
                shape WebBrowser
            }
            element "Service" {
                background #5DADE2
                color #ffffff
            }
            element "Component" {
                background #85BBF0
                color #000000
            }
            element "Database" {
                shape cylinder
                background #1E7C3A
                color #ffffff
            }
            element "Broker" {
                shape pipe
                background #A52714
                color #ffffff
            }
            element "Library" {
                shape folder
                background #F4B400
                color #000000
            }
            element "ExternalSystem" {
                background #999999
                color #ffffff
            }
        }
    }
}
