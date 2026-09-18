# Registro global del equipo

Última actualización: 18/09/2026. Registro acumulado de avances y acuerdos
del equipo.
Actualizar este archivo, sin crear uno por día.

## Equipo y objetivo

- Gabriela y Fernanda continúan como integrantes activas del proyecto.
- Cada integrante mantiene un foco principal; revisión, pairing y participación transversal rotan por historia.
- Proyecto de siete días hábiles, con prioridad en aprendizaje, UX/UI y Product Discovery.
- Repositorio y entorno .venv creados; Jira disponible y utilizado desde esta conversación.

## Producto: acuerdos vigentes

- Herramienta de apoyo a moderadores de comentarios de YouTube.
- Única persona operativa: moderador; decisiones siempre humanas.
- Cola priorizada confirmada como flujo principal.
- MVP basado en el dataset, sin importación ni acciones reales sobre YouTube.
- Objetivo del primer modelo: IsToxic; toxicidad no equivale a sentimiento, discurso de odio ni infracción de políticas.
- Decisión humana: marca local y reversible de revisado y eventual corrección de clasificación; no eliminación ni bloqueo automático.
- Inglés como alcance inicial de trabajo por el dataset disponible; español como ampliación, no requisito del MVP.
- Incertidumbre, ambigüedad y falta de contexto: revisión humana propuesta; abstención y umbrales concretos requieren validación.
- Subcategorías de daño, reportes e integración YouTube: posibles evoluciones, no capacidades implementadas.
- La arquitectura y el despliegue en AWS todavía no están definidos.

## Organización y entrega

- Git conserva el código y la evidencia técnica; Jira puede utilizarse para coordinar tareas cuando resulte útil.
- `dev` es la rama de integración y `main` queda reservada para versiones estables.
- El equipo eliminó el Harness y su validación obligatoria porque estaban bloqueando la entrega sin aportar suficiente valor al proyecto.
- OpenSpec deja de ser un requisito de aceptación o merge.
- Se mantiene la revisión humana como práctica recomendada, sin convertirla en burocracia adicional.
- No credenciales, .env ni texto sensible en logs o tests; fixtures sintéticas.
- Decisión más reciente para desbloquear SP-21: CSV local e ignorado, no versionado en el árbol actual. Sustituye el acuerdo anterior de CSV en dev pero no en main.
- El CSV ya publicado permanece en commits anteriores; retirarlo del árbol no borra su historial. Licencia de redistribución sin confirmar.
- Tags y releases pendientes del primer vertical funcional.

## Datos y modelo

- Dataset: youtoxic_english_1000.csv; 1.000 filas, 15 columnas.
- Columnas mínimas de extracción: CommentId, VideoId, Text e IsToxic.
- IsToxic: 538 no tóxicos y 462 tóxicos; acepta representación binaria 0/1 o booleana.
- La extracción no transforma textos ni divide datos ni entrena modelos.
- El EDA fue integrado en `dev` mediante el PR #25 y documenta limpieza, duplicados y riesgos de fuga de información.
- SP-20: brecha objetivo train/test inicialmente inferior a 5 puntos porcentuales; si se supera, documentar sobreajuste y decidir con evidencia si bloquea.

## Gabriela

- SP-7 / PR #1: visión de producto, persona moderadora, cola priorizada y vínculo desde README.
- PR #1 probada según confirmación de Fernanda; no se verificó aquí su cierre actual.
- PR #25: EDA del dataset integrado en `dev`.

## Contribuciones históricas

- Miguel participó en la organización inicial, documentación y configuración del repositorio.
- Desde el 18/09/2026 ya no forma parte del bootcamp ni del equipo activo del proyecto.

## Fernanda

- Refinó alcance y SDD: cola priorizada, objetivo IsToxic y revisión humana.
- SP-21: extracción de 1.000 filas y 15 columnas, validaciones y dependencias registradas.
- Evidencias: 9 tests aprobados y comprobaciones de whitespace aprobadas.
- PR #14 de extracción y validación del dataset integrado en `dev`.
- CSV retirado del versionado actual y conservado localmente; permanece en commits anteriores.
- Registró avances y daily en Jira SP-21.

## Pendientes de cierre y continuación

- Definir y congelar un split común para los tres modelos del ensemble.
- Entrenar regresión logística, SVM y transformer sobre el mismo split.
- Guardar probabilidades alineadas por `CommentId` para soft voting y weighted voting.
- Mantener el CSV raw local e ignorado por Git.

Fuentes: conversación del equipo, historial consultado de origin/dev y ejecución local de SP-21. Los avances son acumulados, no todos del mismo día. Cada integrante puede completar trabajo no registrado; no se atribuyen implementaciones sin evidencia.
