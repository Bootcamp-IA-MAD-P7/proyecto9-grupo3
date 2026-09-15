## Why

SP-21 necesita cargar el dataset de forma reproducible y segura antes de comenzar su transformación, análisis y entrenamiento.

## What Changes

- Cargar el CSV desde una ruta configurable.
- Validar existencia, columnas y valores esenciales.
- Producir errores comprensibles para entradas inválidas.
- Evitar logs con comentarios reales.
- Mantener el dataset fuera del repositorio.

### Validated facts

- El dataset tiene 1.000 comentarios y 15 columnas.
- El objetivo inicial es `IsToxic`.
- El archivo está disponible localmente.

### Assumptions

- La ruta se proporcionará mediante `DATASET_PATH`.

### Open questions

- La licencia de redistribución continúa pendiente.

### Non-goals

- Transformación de texto.
- División train/test.
- Entrenamiento del modelo.
- Subir el CSV al repositorio.

## Capabilities

### New Capabilities

- `dataset-extraction`: Carga y validación segura del dataset local.

### Modified Capabilities

None.

## Impact

Afectará al módulo de datos, sus tests y la dependencia utilizada para leer CSV. No modifica API, interfaz ni AWS.