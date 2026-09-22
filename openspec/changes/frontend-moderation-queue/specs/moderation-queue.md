# Especificación: cola de moderación

## Requirement: Visualización de la cola

### Scenario: La persona moderadora abre la pantalla
- GIVEN que existen comentarios pendientes
- WHEN se carga la superficie de moderación
- THEN se muestra una cola con contador, riesgo, incertidumbre y estado de cada comentario
- AND el texto completo no aparece en la fila de la cola

## Requirement: Orden por riesgo estimado

### Scenario: La cola tiene varios comentarios
- GIVEN comentarios con distintos `risk_score`
- WHEN se renderiza la cola
- THEN los comentarios se ordenan por `risk_score` descendente
- AND la interfaz indica que el orden es una priorización, no una decisión

## Requirement: Visualización de incertidumbre

### Scenario: Se presenta una señal del modelo
- GIVEN un comentario con `uncertainty`
- WHEN aparece en la cola o en el detalle
- THEN se muestra la incertidumbre con una etiqueta legible
- AND se explica que representa ambigüedad o cercanía al umbral del modelo

## Requirement: Separación entre riesgo y decisión humana

### Scenario: La persona interpreta una puntuación alta
- GIVEN un comentario con riesgo alto
- WHEN la persona observa sus indicadores
- THEN la interfaz aclara que el riesgo no es una verdad ni una decisión de toxicidad
- AND la decisión final permanece en los controles humanos

## Requirement: Selección de comentario

### Scenario: La persona elige un caso
- GIVEN una cola visible
- WHEN activa una fila mediante ratón o teclado
- THEN el comentario queda seleccionado y se muestra el panel de detalle

## Requirement: Lectura del detalle

### Scenario: Se autoriza el detalle
- GIVEN un comentario seleccionado
- WHEN se abre su panel de detalle
- THEN se muestra el texto completo junto con sus señales y estado
- AND el texto se mantiene fuera de la lista resumida

## Requirement: Estados de revisión

### Scenario: Un comentario cambia de estado
- GIVEN un comentario en `PENDING`, `IN_REVIEW` o `REVIEWED`
- WHEN se muestra o actualiza el caso
- THEN el estado se presenta con texto visible
- AND la transición simulada respeta `PENDING` → `IN_REVIEW` y después `REVIEWED`

## Requirement: Acciones humanas

### Scenario: La persona registra una revisión
- GIVEN un comentario seleccionado
- WHEN elige `NEEDS_REVIEW`, `CONFIRMED_TOXIC` o `NOT_TOXIC`
- THEN se muestra feedback de la acción y el estado resultante
- AND la acción se identifica como decisión de la persona moderadora

## Requirement: Prohibición de acciones automáticas

### Scenario: Se revisa el conjunto de controles
- GIVEN cualquier estado o puntuación del comentario
- WHEN se muestran las acciones disponibles
- THEN no existe control para eliminar, bloquear o sancionar automáticamente
- AND la aplicación no ejecuta ninguna acción externa contra el comentario

## Requirement: Responsive

### Scenario: Se usa una pantalla móvil
- GIVEN un viewport estrecho
- WHEN se abre la herramienta
- THEN la cola y el detalle se apilan sin scroll horizontal accidental
- AND todas las acciones siguen siendo utilizables

## Requirement: Accesibilidad

### Scenario: Se navega sin ratón
- GIVEN la interfaz cargada
- WHEN la persona usa Tab, Enter o la barra espaciadora
- THEN puede recorrer, seleccionar y accionar la cola
- AND las regiones, botones y estados tienen nombres y etiquetas semánticas
