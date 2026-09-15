# Guía de contribución

Esta guía ayuda a realizar cambios pequeños, trazables y revisables. Las reglas
completas del equipo están en los [estándares base](docs/base-standards.md), que
son la fuente única de verdad, y el ciclo SDD se describe en el
[project harness](docs/HARNESS.md).

## Antes de empezar

1. Selecciona una tarea de [Jira](https://miguel-redondo.atlassian.net/jira/software/projects/SP/boards/199/backlog)
   con clave `SP-XX` y confirma su alcance y criterios de aceptación.
2. Aclara con el equipo cualquier ambigüedad antes de implementar.
3. Crea o actualiza `openspec/changes/<jira-key>-<slug>/` si el cambio afecta
   comportamiento, datos, modelo, API, seguridad, despliegue o reglas del harness.

## Flujo Git

- Crea una rama de trabajo desde `dev` y abre su pull request hacia `dev`.
- `main` se reserva para releases finales aceptadas y promovidas desde `dev`.
- No hagas push directo a `dev` ni a `main`.
- Un cambio pequeño y aprobado se integra mediante squash merge.

### Ramas

Usa una clave real de Jira y una descripción corta en inglés:

```text
feature/SP-XX-short-description
fix/SP-XX-short-description
docs/SP-XX-short-description
test/SP-XX-short-description
ci/SP-XX-short-description
chore/SP-XX-short-description
```

### Commits

Usa Conventional Commits en inglés:

```text
feat: add toxicity prediction endpoint
fix: reject empty comment input
docs: document Git and Jira workflow
test: cover text preprocessing
ci: add repository quality workflow
chore: configure project tooling
```

## Pull requests y revisión

Usa la [plantilla de pull request](.github/pull_request_template.md). Cada PR
debe enlazar su tarea Jira e incluir resumen, criterios de aceptación, pruebas,
evidencias y, cuando aplique, la ruta de OpenSpec.

Otra persona del equipo debe revisar la evidencia antes del merge. La protección
técnica de ramas, las aprobaciones obligatorias y los checks configurados se
gestionan en sus subtareas específicas.

## Validación mínima

Ejecuta antes de solicitar revisión:

```powershell
python scripts\validate_harness.py
git diff --check
```

Añade las pruebas específicas del cambio cuando existan.

## Seguridad

No incluyas credenciales, archivos `.env`, datos personales, texto sensible ni
comentarios reales del dataset en commits, logs o evidencias.

## Referencias

- [Jira del proyecto](https://miguel-redondo.atlassian.net/jira/software/projects/SP/boards/199/backlog)
- [Estándares base](docs/base-standards.md)
- [Project harness y ciclo SDD](docs/HARNESS.md)
- [OpenSpec](openspec/)
- [Plantilla de pull request](.github/pull_request_template.md)
