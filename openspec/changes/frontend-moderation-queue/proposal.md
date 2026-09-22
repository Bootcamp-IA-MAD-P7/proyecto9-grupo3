# Propuesta: primera vertical frontend de la cola de moderación

## Problema

La API ya puede entregar una cola priorizada de comentarios, pero todavía no existe una superficie de trabajo para que una persona moderadora interprete esa señal, abra un caso y registre su revisión. La primera pantalla debe reducir el tiempo necesario para encontrar los casos prioritarios sin presentar el modelo como una autoridad.

## Usuario y contexto

El usuario principal es una persona moderadora. Se trata de una herramienta interna de apoyo para revisar comentarios, no de una interfaz pública ni de un sistema autónomo de aplicación de políticas.

## Objetivo de la primera vertical

Construir una cola de moderación usable en escritorio y móvil que muestre casos priorizados, explique riesgo e incertidumbre, permita seleccionar un comentario, leer su detalle y registrar una decisión humana simulada.

## Incluido

- Fundación React + Vite + TypeScript.
- Cola mock tipada y ordenada por `risk_score` descendente.
- Indicadores de riesgo, incertidumbre y estado.
- Panel de detalle con el texto solo después de seleccionar un caso.
- Acciones simuladas `NEEDS_REVIEW`, `CONFIRMED_TOXIC` y `NOT_TOXIC`.
- Estados de carga, vacío, error y feedback de acción.
- Diseño responsive y navegación accesible por teclado.

## Fuera de alcance

- Autenticación, persistencia o conexión real con FastAPI.
- Importación, paginación real, búsqueda o filtros avanzados.
- Conexión con YouTube.
- Eliminación, bloqueo, sanción o cualquier acción automática.
- Clasificación de sentimiento o detector definitivo de odio o violencia.

## Por qué empezar por la cola priorizada

La cola es el punto donde la señal del modelo aporta valor operativo: ayuda a decidir qué revisar primero. Empezar por ella permite validar el flujo humano completo —priorizar, inspeccionar y decidir— manteniendo explícitamente la responsabilidad final en la persona moderadora.
