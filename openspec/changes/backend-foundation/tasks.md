# Tasks

**Goal:** entregar una primera API local, ejecutable y explicada para aprender.
**Architecture:** una aplicación FastAPI ensamblada mediante una factoría,
configuración validada y un router de salud. Las siguientes entregas añadirán
las capas de negocio y persistencia cuando tengan comportamiento real.
**Tech stack:** Python 3.12+, FastAPI, Uvicorn, Pydantic Settings, pytest, HTTPX.
**Spec:** `specs/backend-foundation/spec.md`; decisiones en `design.md`.

## Global constraints

Identificadores en inglés; explicación en español. Sin datos reales,
credenciales, moderación externa o despliegue. Jira omitido por instrucción
expresa del usuario. No se cambia el contrato de reapertura en esta entrega.

## 1. Runtime and contract

- [x] 1.1 Configurar el paquete editable en `pyproject.toml` y registrar dependencias probadas en `backend/constraints.txt`; verificar instalación y `python -m pip check`.
- [x] 1.2 Implementar `backend/app/main.py`, `config.py` y `health.py` después de observar fallos por funcionalidad ausente; verificar los nueve casos de `backend/tests/test_foundation.py`.

Interfaces: `create_app() -> FastAPI`, `Settings` con `app_name` y
`docs_enabled`, y `HealthResponse` con `status: Literal["ok"]`.

Secuencia verificable de 1.2:

1. Ejecutar `.venv/Scripts/python.exe -m pytest backend/tests -q` antes del código.
2. Confirmar que los fallos son por ausencia de `app`, no dependencias rotas.
3. Añadir `app/__init__.py` y una factoría que configure documentación e incluya
   el router de salud. El núcleo observable del router será:

   ```python
   class HealthResponse(BaseModel):
       status: Literal["ok"] = "ok"

   @router.get("/health", response_model=HealthResponse)
   def get_health() -> HealthResponse:
       return HealthResponse()
   ```

4. Construir `Settings` dentro de la factoría, con `env_prefix="MODERATION_"`,
   `env_file=".env"` y `extra="ignore"`. Desactivar las tres URLs documentales
   mediante `None` cuando `docs_enabled` sea falso.
5. Repetir pytest y comprobar el contrato HTTP, título, precedencia de entorno,
   desactivación de documentación y rechazo de configuración inválida.

## 2. Learning and integration

- [x] 2.1 Escribir `docs/backend/01-primer-endpoint.md`, `.env.example` y la entrada del README; verificar los comandos, referencias y el recorrido hasta `/docs`.
- [x] 2.2 Verificar toda la suite, el contrato OpenSpec, `git diff --check` y HTTP real con Uvicorn; registrar resultados y la excepción Jira en `evidence.md`.

La guía debe mostrar el recorrido HTTP, explicar cada archivo y el comando de
arranque, proponer un ejercicio de configuración y distinguir lo entregado de
la futura persistencia, autenticación, cola, auditoría y supervisión.

Comandos de cierre desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/validate_harness.py
git diff --check
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Comprobar `/health`, `/docs` y `/openapi.json` por HTTP antes de dar por
completada la entrega. El validador de ramas exige Jira; registrar ese resultado
concreto sin cambiar el validador ni fingir que ha pasado.
