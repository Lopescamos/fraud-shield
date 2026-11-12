# ADR-002: Apache Kafka como broker, detrás de `MessagePublisher`

- Estado: Aceptada
- Fecha: 2026-11-10

## Contexto

Los microservicios se comunican de forma asíncrona. Necesitamos un broker que soporte orden por clave, reentrega controlada, DLQ y, deseable para un sistema de fraude, la capacidad de **releer eventos pasados** para auditar o reentrenar.

## Decisión

Usamos **Apache Kafka 3.x en modo KRaft** como broker, corriendo en Docker Compose. El código de los servicios **no depende de Kafka directamente**: publica a través del puerto `MessagePublisher` (en `application`) y el adaptador concreto `KafkaMessagePublisher` vive en `infrastructure/messaging/kafka/`. Los consumidores son funciones sin anotaciones de broker; la configuración de tópicos, grupos y DLQ vive en `application.yml`/variables de entorno.

## Alternativas consideradas

- **RabbitMQ**. Más simple de operar y suficiente para colas de trabajo. Descartado como primera opción porque no permite releer histórico (los mensajes consumidos se borran salvo que uses streams) y en fraude el replay es una capacidad relevante para portafolio.
- **Google Pub/Sub** u otros brokers cloud. Descartados por costo y porque atan el proyecto a un proveedor.

## Consecuencias

- Operación más pesada que RabbitMQ en local (Kafka necesita más memoria), aceptable para un proyecto de portafolio.
- Los mensajes pueden releerse para reentrenar o auditar — ventaja real demostrable.
- Al estar detrás del puerto `MessagePublisher`, **cambiar de broker toca solo el adaptador y la configuración**, no el dominio ni la aplicación. Esta propiedad se debe mantener en toda evolución futura.
- La clave de partición por defecto es `account_id_hash` para preservar el orden por cuenta.
