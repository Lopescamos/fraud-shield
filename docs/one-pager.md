# FraudShield — One-pager

## Problema

Un banco o fintech procesa miles de operaciones por minuto y un analista no puede revisarlas a mano. Cuando aparece una operación sospechosa, hoy se descubre tarde, sin trazabilidad clara de la decisión y con alto costo para el cliente final y la entidad. Se necesita un sistema que priorice las operaciones sospechosas, explique por qué lo son y deje auditoría de cada decisión.

## Usuarios

- **Sistema de ingesta (cliente API del banco/fintech)** — envía transacciones en tiempo casi real para evaluación de riesgo.
- **Analista de fraude** — revisa alertas, cambia su estado y deja notas de investigación.
- **Administrador de riesgo** — gestiona reglas, modelos y umbrales; consulta el desempeño del motor.
- **Analista de negocio (Power BI)** — consume KPIs, series temporales y reportes operativos.

## Solución propuesta (MVP)

- Arquitectura orientada a eventos con cuatro microservicios (`transaction`, `scoring`, `alert`, `analytics`) y un `api-gateway`.
- Motor de scoring que combina reglas determinísticas, Isolation Forest y XGBoost, con explicación SHAP por cada puntaje.
- Alertas con ciclo de vida auditable y notificación automática por n8n.
- API de analítica de solo lectura `/bi/v1` como única vía de acceso para Power BI.
- Despliegue reproducible con Docker Compose y pipeline CI/CD en GitHub Actions.

## Fuera de alcance (por ahora)

- Entrenamiento continuo (reentrenamiento programado del modelo).
- Panel web propio de analista; la interacción es vía API y, opcionalmente, Postman/Thunder.
- Integración con sistemas de bloqueo o reversión automática de operaciones — el sistema **nunca** decide bloqueos por sí solo.
- Múltiples moneadas y zonas horarias simultáneas (se asume PEN y America/Lima).
- Alta disponibilidad multi-región.

## Métricas de éxito

- Tiempo entre recepción de una transacción y disponibilidad de su puntaje por debajo de dos segundos en el 95 % de los casos.
- Recall ≥ 0.80 y precisión ≥ 0.60 sobre el conjunto de validación etiquetado.
- Cobertura con explicación SHAP del 100 % de las alertas de nivel alto o crítico.
- Cero accesos directos de herramientas externas a la base de datos transaccional.

## Restricciones

- Proyecto de portafolio con presupuesto cero: todo corre en la máquina local con Docker Compose.
- Datos reales no disponibles; se trabaja con un dataset público y un simulador de tráfico propio.
- Python 3.12 como lenguaje principal; eventualmente un microservicio podría migrar a Java/Spring Boot.
- Power BI Desktop para el reporte; Power BI Service queda fuera por requerir hosting público.

## Riesgos / dudas abiertas

- Desbalance severo del dataset de entrenamiento — mitigado con `scale_pos_weight` y validación con PR-AUC.
- Deriva del modelo cuando entren operaciones nuevas — mitigado con degradación a solo reglas si el modelo falla.
- Dependencia de Kafka en local — un broker caído tumba el flujo asíncrono; se documenta el modo "solo reglas" para demos.
- Alcance realista frente a tiempo disponible — publicar el repositorio al terminar la fase 3 (semana 6) y seguir iterando en público.

## Aviso de alcance

Un puntaje alto no prueba fraude, es una señal para investigar. El sistema **nunca** bloquea cuentas por sí solo; solo genera alertas para un analista humano.
