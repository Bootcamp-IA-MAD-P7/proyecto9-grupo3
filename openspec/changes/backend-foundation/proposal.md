# Proposal

## Why

El proyecto tiene contratos de producto, pero todavía no tiene una API ejecutable.
La primera entrega permitirá aprender el recorrido de una petición HTTP y
comprobar una base funcional antes de añadir persistencia y moderación.

## What Changes

- Crear una aplicación Python con FastAPI, configuración validada y `GET /health`.
- Publicar el contrato OpenAPI de esta entrega y documentación interactiva local.
- Añadir pruebas de contrato, instrucciones reproducibles y una guía en español.
- Trabajar por entregas que el usuario pueda ejecutar y comprender.

## Capabilities

### New Capabilities

- `backend-foundation`: API ejecutable, salud del proceso y documentación configurable.

### Modified Capabilities

Ninguna. Esta entrega no modifica el comportamiento de revisión de SP-2.

## Impact

Código en `backend/`, configuración Python en `pyproject.toml`, guía en
`docs/backend/` y enlace desde el README. Dependencias: FastAPI, Uvicorn,
Pydantic Settings; pytest y HTTPX para desarrollo.

## Facts, assumptions and authorization

- Hecho: se ha leído `back1.txt`, facilitado por el usuario, y la documentación
  de producto y estándares del repositorio.
- Hecho: el usuario ha autorizado continuar sin exigir una historia Jira.
  Esta excepción corresponde a este trabajo; no cambia las normas del equipo.
- Supuesto operativo: comenzar con una entrega local pequeña facilita el
  aprendizaje solicitado. El objetivo completo sigue siendo el backend del portal.
- Alcance de esta entrega: infraestructura de la API; no decide las reglas de reapertura.

## Non-goals and open questions

Autenticación, base de datos, predicciones, ingestión y moderación se abordarán
en entregas posteriores. Antes de implementar reaperturas hay que conciliar
el undo de SP-2 con la autorización del supervisor descrita en `back1.txt`.
También hay que concretar transferencias, contexto insuficiente y recuperación
de reservas abandonadas. No se ejecutan acciones en YouTube ni despliegues.
