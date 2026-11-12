# ADR-009: Microservicios en vez de monolito modular

- Estado: Aceptada
- Fecha: 2026-11-10

## Contexto

Para un sistema de este tamaño y para un portafolio, el enfoque conservador es un **monolito modular** con bounded contexts como carpetas. FraudShield se parece a los proyectos anteriores del autor (SkillSwap, CreditoTiendas) pero busca mostrar explícitamente competencia con mensajería, eventos, DDD distribuido, idempotencia y Outbox.

## Decisión

El sistema se construye como **cuatro microservicios** (`transaction`, `scoring`, `alert`, `analytics`) más un `api-gateway`. Cada servicio es su propio bounded context, con su esquema de base y su despliegue independiente. La comunicación entre servicios es **por eventos Kafka** por defecto; HTTP síncrono solo como excepción (ningún endpoint síncrono entre servicios en el MVP).

## Alternativas consideradas

- **Monolito modular** con módulos por BC dentro del mismo proyecto. Más simple de operar y suficiente para el dominio. Descartado porque el objetivo de portafolio es mostrar competencia con sistemas distribuidos: Kafka, Outbox, idempotencia, DDD por servicio, aislamiento real.
- **Monolito modular con Kafka interno** (publica eventos aunque todo esté en un proceso). Híbrido raro que no muestra las propiedades reales de un sistema distribuido.

## Consecuencias

- La operación en local es más pesada (varios contenedores), aceptable con Docker Compose.
- El aislamiento es real: ningún servicio importa código de otro; solo comparten `shared-contracts`.
- Los temas que suma al portafolio están cubiertos: eventos, DLQ, idempotencia, Outbox, consistencia eventual, modelos de lectura locales.
- Si en algún momento el sistema se simplifica, un servicio puede absorber a otro reempacando su módulo; el camino al revés (monolito a microservicios) suele ser más caro.

## Relación con la guía

Este ADR aplica la guía de "Arquitectura por capas + DDD + Bounded Contexts" en su forma distribuida: un servicio = un BC, dentro cada uno sigue las mismas cuatro capas (domain, application, infrastructure, interfaces).
