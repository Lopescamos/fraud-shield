# ADR-007: Scoring híbrido reglas + XGBoost + Isolation Forest + SHAP

- Estado: Aceptada
- Fecha: 2026-11-10

## Contexto

El puntaje de fraude debe cubrir tres necesidades: detectar **patrones conocidos** (reglas del negocio), detectar **anomalías no vistas** antes y **explicar cada decisión** a un analista humano. Ningún enfoque solo cumple las tres.

## Decisión

El puntaje final combina **tres señales**:

- **Capa 1 — Reglas determinísticas.** Suma puntos y registra qué reglas se activaron. Configurables desde un YAML, no quemadas en código. Cubren velocidad, monto atípico, dispositivo nuevo, viaje imposible, horario inusual y fraccionamiento.
- **Capa 2a — Isolation Forest (no supervisado).** Detecta transacciones raras sin necesitar etiquetas. Cubre lo que ninguna regla prevé.
- **Capa 2b — XGBoost (supervisado).** Clasifica usando el dataset etiquetado con `scale_pos_weight` para el desbalance.

La combinación es:
```
score = w_r * R + w_x * p_xgb + w_i * a_iso    con w_r + w_x + w_i = 1
```
`R` son los puntos de reglas (0-100), `p_xgb` la probabilidad XGBoost (0-1), `a_iso` la anomalía Isolation Forest normalizada (0-1). Pesos iniciales 0.4 / 0.4 / 0.2, a ajustar con validación. Umbrales de nivel: 0-39 LOW, 40-69 MEDIUM, 70-89 HIGH, 90-100 CRITICAL.

Para **explicabilidad**, cada evaluación guarda los **tres factores SHAP** con mayor impacto del modelo XGBoost (vía `TreeExplainer`) y las reglas activadas.

Degradación: si el modelo ML falla o no carga, el sistema **sigue operando con solo reglas** y marca `degraded_mode=true`.

## Alternativas consideradas

- **Solo reglas.** Fácil de defender pero no detecta patrones nuevos.
- **Solo ML.** Potente, pero una "caja negra" sin explicación no se acepta en entornos regulados.
- **Red neuronal + LIME.** Más costoso de entrenar y servir; no aporta sobre XGBoost + SHAP para este tamaño de dataset.

## Consecuencias

- Los puertos del dominio (`RiskModel`, `Explainer`, `RuleCatalog`) viven en `domain/services/` porque son el corazón del negocio; sus adaptadores concretos viven en `infrastructure`.
- El `scoring-service` carga el modelo al arrancar y versiona en `model_registry`; `/api/v1/models/active` expone versión y métricas.
- La métrica principal es **PR-AUC** (precision-recall), no accuracy, por el desbalance severo.
- Debe medirse el aporte del ML vs la línea base de solo reglas; se reporta en el README del repo.
