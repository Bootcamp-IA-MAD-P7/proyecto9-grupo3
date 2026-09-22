<div align="center">

# Moderación asistida de comentarios

### NLP clásico para priorizar la revisión humana de contenido potencialmente tóxico

[![Project harness](https://github.com/Bootcamp-IA-MAD-P7/proyecto9-grupo3/actions/workflows/harness.yml/badge.svg?branch=dev)](https://github.com/Bootcamp-IA-MAD-P7/proyecto9-grupo3/actions/workflows/harness.yml)
![Status](https://img.shields.io/badge/status-foundations_complete-1f883d)
![Approach](https://img.shields.io/badge/approach-human--in--the--loop-0969da)
![Language](https://img.shields.io/badge/MVP-English_comments-8250df)

Una herramienta de apoyo para que una persona moderadora identifique antes los
comentarios que requieren atención, sin delegar la decisión final en el modelo.

</div>

---

## Estado del proyecto

| Área | Estado | Evidencia actual |
| --- | :---: | --- |
| Problema, persona y alcance del MVP | ✅ | [Visión de producto](docs/product-vision.md) |
| Flujo Jira, Git y pull requests | ✅ | [Guía de contribución](CONTRIBUTING.md) |
| SDD, OpenSpec y project harness | ✅ | [Project harness](docs/HARNESS.md) |
| Controles de calidad y seguridad | ✅ | Harness automático y protección de ramas |
| Base del backend | ✅ | API local con `/health`, documentación y pruebas; [guía del paso 1](docs/backend/01-primer-endpoint.md) |
| Persistencia del backend | ✅ | SQLite guarda usuarios y comentarios; [guía del paso 2](docs/backend/02-base-de-datos.md) |
| Autenticación y permisos | ✅ | Login, sesiones SQLite, hashes Argon2id y guard de roles; [guía del paso 3](docs/backend/03-autenticacion-y-permisos.md) |
| Carga y cola priorizada | ✅ | Lotes validados, puntuación simulada y cola paginada sin texto; [guía del paso 4](docs/backend/04-carga-y-cola-priorizada.md) |
| Modelos y ensemble | ✅ | Tres modelos y ensemble ponderado evaluados; configuración, comparación y test final documentados en [su guía](docs/model/ensemble.md) |
| Vertical funcional y demo | ⏳ | Pendiente de implementación |
| Arquitectura y despliegue AWS | ⏳ | Se decidirán con las necesidades del vertical |

> **Estado verificable:** la API local, la persistencia SQLite, el login y la
> cola con puntuaciones simuladas están operativos. La revisión humana, el
> modelo evaluado y el despliegue todavía no están implementados.

## Ejecutar la primera API

Desde la raíz del repositorio, con Python 3.12 o superior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c backend/constraints.txt -e '.[dev]'
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Abre [la documentación local](http://127.0.0.1:8000/docs) y prueba `GET /health`.
La [guía del primer endpoint](docs/backend/01-primer-endpoint.md) explica cada
archivo, cómo ejecutar las pruebas y qué construiremos en las siguientes entregas.

La [guía de persistencia](docs/backend/02-base-de-datos.md) explica las tablas,
las transacciones y cómo inspeccionarlas con datos sintéticos. La base local se
guarda en `data/local/moderation.db` y queda fuera de Git.

Para probar autenticación, carga los usuarios `moderator` y `supervisor` con
contraseñas elegidas por ti:

```powershell
.\.venv\Scripts\python.exe -m app.seed_demo_users
```

La [guía de autenticación y permisos](docs/backend/03-autenticacion-y-permisos.md)
recorre login, autorización en Swagger y logout.

La [guía de carga y cola](docs/backend/04-carga-y-cola-priorizada.md) muestra
cómo importar comentarios sintéticos y recorrer páginas sin exponer su texto.

## Demo local de la API

La API actual funciona sin dataset ni modelo entrenado: usa `SimulatedScorer`,
un scorer determinista para demostrar importación, permisos y orden de la cola.
Sus puntuaciones no son probabilidades de toxicidad y no deben usarse para
decisiones reales de moderación.

Desde otra terminal, prepara usuarios con contraseñas locales elegidas por ti,
inicia la API y abre Swagger:

```powershell
.\.venv\Scripts\python.exe -m app.seed_demo_users
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

En <http://127.0.0.1:8000/docs>:

1. Comprueba `GET /health`.
2. Ejecuta `POST /auth/login` como `supervisor` y usa el `access_token` en
   **Authorize**.
3. Importa dos comentarios sintéticos con `POST /comments/import`.
4. Consulta `GET /comments` como `supervisor` y como `moderator`; la respuesta
   muestra la cola priorizada sin devolver `text`.
5. Comprueba que `moderator` puede consultar la cola pero recibe `403` al
   importar, mientras que `supervisor` recibe `201`.

La base SQLite del demo se guarda en `data/local/` y está excluida de Git.
No uses comentarios reales, credenciales compartidas ni datos privados.

## Dataset y entrenamiento del Transformer

El entrenamiento espera el CSV local `data/raw/youtoxic_english_1000.csv`. Ese
archivo no se versiona ni se descarga automáticamente. Si está autorizado y
disponible en otra ruta, indícala explícitamente:

```powershell
.\.venv\Scripts\python.exe scripts/train_transformer.py --dataset RUTA_LOCAL.csv
```

Si no existe el archivo esperado ni una copia autorizada con nombre alternativo,
el comando termina con un mensaje claro y no genera métricas. En este entorno la
copia local disponible es `data/raw/youtoxic_english_1000 (1).csv`; se ejecuta
pasándola explícitamente con `--dataset`. No sustituyas el dataset del proyecto
por datasets de ejemplo de scikit-learn.
La guía completa del modelo está en [docs/model/transformer.md](docs/model/transformer.md);
el test permanece cerrado salvo que se use `--final-test` con la configuración
congelada requerida.

## Estado real del Transformer

El pipeline de DistilBERT está implementado y ya fue entrenado con el dataset
local `data/raw/youtoxic_english_1000 (1).csv`. El threshold se selecciona
exclusivamente con validation; test no se usa para ajustar hiperparámetros y
permanece cerrado en esta auditoría.

La línea base validada antes de la primera regularización fue:

| Métrica | Train | Validation |
| --- | ---: | ---: |
| F1 | 0,9639 | 0,7888 |
| Precision | 0,9524 | 0,7734 |
| Recall | 0,9756 | 0,8049 |
| PR-AUC | 0,9933 | 0,8815 |
| Brier score | 0,0231 | 0,1859 |

El gap F1 train-validation fue de **17,51 puntos porcentuales**, una señal clara
de overfitting. La primera hipótesis de reducción (`weight_decay` 0,01 y early
stopping por F1 de validation, con paciencia 2 y recuperación del mejor estado)
ya fue ejecutada. La nueva ejecución produjo:

| Métrica | Train nuevo | Validation nueva |
| --- | ---: | ---: |
| F1 | 0,9640 | 0,7734 |
| Precision | 0,9488 | 0,7444 |
| Recall | 0,9797 | 0,8049 |
| PR-AUC | 0,9936 | 0,8767 |
| Brier score | 0,0323 | 0,2060 |

El nuevo gap es de **19,06 puntos porcentuales**: `weight_decay` más early
stopping no mejoraron el overfitting en esta ejecución. El requisito train-test
menor del 5 % no está demostrado ni cumplido para el Transformer porque test
continúa cerrado. El Transformer queda como experimento evaluado y no se usará
como modelo productivo principal en la demo. No se continuará con Optuna por
falta de tiempo y porque primero hay que resolver el sobreajuste.

El dataset y todos los artefactos de `data/local/` no se versionan. El siguiente
El siguiente experimento deberá probar otra estrategia explicable y comparar
train y validation; no se abrirá test hasta una evaluación final autorizada.

## El problema

Revisar comentarios en orden de llegada puede hacer que contenido potencialmente
dañino espere mientras se atienden casos de menor riesgo. El proyecto explora si
una cola priorizada permite decidir antes qué comentario revisar.

## La propuesta

El MVP procesará comentarios en inglés y estimará el **riesgo de toxicidad** para
el objetivo inicial `IsToxic`. La señal servirá para ordenar la revisión; no será
un veredicto, una medida de gravedad ni una interpretación de las políticas de
YouTube.

| El sistema ayuda a… | El sistema no… |
| --- | --- |
| Priorizar comentarios por riesgo estimado | Elimina, bloquea, denuncia o sanciona |
| Revisar manualmente texto en inglés | Se conecta a YouTube ni opera en tiempo real |
| Mantener un orden estable en los empates | Clasifica sentimiento o español |
| Mostrar resultados y errores comprensibles | Presenta probabilidades como certezas |
| Conservar la decisión humana final | Sustituye el criterio de moderación |

## Recorrido previsto del MVP

```mermaid
flowchart LR
    A[Comentario en inglés] --> B[Validación de entrada]
    B --> C[Pipeline NLP versionado]
    C --> D[Riesgo estimado de IsToxic]
    D --> E[Cola priorizada]
    E --> F[Revisión humana]
    F --> G[Decisión final fuera del modelo]

    classDef input fill:#f6f8fa,stroke:#57606a,color:#24292f;
    classDef system fill:#ddf4ff,stroke:#0969da,color:#0550ae;
    classDef human fill:#dafbe1,stroke:#1a7f37,color:#116329;
    class A input;
    class B,C,D,E system;
    class F,G human;
```

El pipeline técnico previsto utilizará técnicas clásicas y reproducibles:

```text
Dataset → validación → split reproducible → preprocesamiento → TF-IDF
        → clasificador → evaluación → artefacto versionado → inferencia
```

Las métricas se publicarán únicamente cuando hayan sido generadas por el pipeline
de evaluación: `precision`, `recall`, `F1`, matriz de confusión, resultados de
train/test y comprobación de posible fuga mediante `VideoId`.

## Cómo trabajamos

El proyecto aplica Specification-Driven Development con una cadena de trazabilidad
ligera. Cada capa tiene una responsabilidad concreta:

| Capa | Responsabilidad |
| --- | --- |
| Jira | Prioridad, responsable, estado y criterios de aceptación |
| OpenSpec | Comportamiento verificable, diseño técnico y tareas |
| Git y PR | Implementación, revisión, pruebas y evidencias |
| Harness | Reglas automáticas que evitan desviaciones del proceso |
| AWS | Evidencia futura de ejecución, no sustituto de la especificación |

```mermaid
flowchart LR
    J[Jira SP-XX] --> S[OpenSpec cuando aplica]
    S --> B[Rama desde dev]
    B --> I[Implementación y evidencia]
    I --> P[Pull request hacia dev]
    P --> Q[Checks + revisión independiente]
    Q --> M[Squash merge]
    M --> D[dev]
    D -->|release aceptada| R[main]
```

### Controles aplicados

- Ramas `feature/`, `fix/`, `docs/`, `test/`, `ci/` o `chore/` con clave Jira.
- Conventional Commits y títulos de PR normalizados en inglés.
- Plantilla de PR con Jira, OpenSpec, criterios, pruebas, evidencias y rollback.
- Revisión independiente y check `validate` obligatorios antes del merge.
- `dev` como rama de integración; `main` reservada para releases aceptadas.
- Squash merge, historial lineal y bloqueo del push directo.
- Exclusión de credenciales, `.env`, claves y rutas locales de datos sensibles.
- Tags y releases diferidos hasta que exista el primer vertical funcional.

## Validación local

El repositorio no necesita dependencias adicionales para comprobar su estructura:

```powershell
python -m unittest tests.test_validate_harness
python scripts/validate_harness.py
git diff --check
```

## Estructura actual

```text
.
├── .agents/                  # Skills reutilizables para agentes
├── .github/                  # CODEOWNERS, PR template y workflow
├── backend/                  # API FastAPI, pruebas y dependencias verificadas
├── docs/                     # Visión, discovery, harness y estándares
├── openspec/changes/         # Propuestas, diseño, specs y tareas verificables
├── scripts/                  # Validadores ligeros del repositorio
├── tests/                    # Pruebas automáticas del harness
├── AGENTS.md                 # Punto de entrada para agentes
├── CONTRIBUTING.md           # Guía breve de contribución
├── pyproject.toml            # Paquete Python y configuración de pruebas
└── README.md                 # Visión general y estado verificable
```

La API, la base de datos, la autenticación y la cola simulada están implementadas.
La revisión humana, el modelo evaluado y la infraestructura se añadirán después.

## Documentación

| Documento | Propósito |
| --- | --- |
| [Visión de producto](docs/product-vision.md) | Problema, persona, alcance, métricas y límites del MVP |
| [Project charter](docs/product/PROJECT_CHARTER.md) | Encargo, contexto y criterio de éxito |
| [Discovery](docs/product/DISCOVERY.md) | Evidencia e hipótesis de producto |
| [Estándares base](docs/base-standards.md) | Fuente única de verdad para las normas del equipo |
| [Project harness](docs/HARNESS.md) | Ciclo SDD, controles y puertas humanas |
| [Guía de contribución](CONTRIBUTING.md) | Entrada breve al flujo de trabajo |
| [OpenSpec](openspec/changes/) | Contratos versionados y escenarios verificables |

## Próximos hitos

1. Auditar el dataset y construir una línea base reproducible para `IsToxic`.
2. Definir los contratos entre modelo, API e interfaz.
3. Implementar y verificar un vertical completo de comentario a predicción.
4. Validar la experiencia, desplegar una demo autorizada y preparar evidencias.
5. Promover la primera versión aceptada de `dev` a `main` y publicar su release.

## Equipo

Proyecto desarrollado por **Gabriela Granja**, **Fernanda Trk** y
**Miguel Redondo** durante el bootcamp de Inteligencia Artificial de
Factoría F5.

Las decisiones se registran en Jira, se especifican en OpenSpec cuando son
materiales y se demuestran mediante código, pruebas y revisiones en GitHub.
