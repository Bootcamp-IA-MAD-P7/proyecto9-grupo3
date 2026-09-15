# Visión de producto: MVP de moderación asistida

## Objetivo del MVP

Construir una herramienta de apoyo para que una persona moderadora pueda priorizar y revisar comentarios potencialmente tóxicos de un conjunto de textos en inglés. El MVP debe reducir el tiempo necesario para encontrar los casos de mayor riesgo sin sustituir el criterio humano ni presentar la clasificación automática como una decisión definitiva.

## Problema e hipótesis

### Problema

La revisión manual de grandes volúmenes de comentarios dificulta detectar pronto los casos que requieren más atención. Una lista sin priorización obliga a revisar los textos en un orden poco eficiente y hace más difícil mantener una decisión consistente.

### Hipótesis

Si la herramienta ordena los comentarios por riesgo estimado de toxicidad y ofrece el texto completo junto con una interfaz clara para su revisión, la persona moderadora podrá identificar antes los casos prioritarios y tomar decisiones finales con menos esfuerzo, manteniendo la responsabilidad en la revisión humana.

## Persona y tarea central

### Persona moderadora

Persona encargada de revisar comentarios de una comunidad digital. Necesita trabajar con rapidez, entender por qué un texto aparece en una posición prioritaria y registrar una decisión trazable sin depender de conocimientos técnicos sobre modelos de lenguaje.

### Tarea central

Revisar una cola de comentarios en inglés, empezando por los casos con mayor riesgo estimado de toxicidad, analizar manualmente cada texto en su contexto disponible y decidir qué acción corresponde dentro del flujo de moderación definido por el equipo.

## Principios del MVP

- **IsToxic como objetivo inicial:** el primer objetivo del modelo es estimar si un texto puede ser tóxico, como señal de priorización.
- **La cola prioriza, no decide:** los comentarios se ordenan por riesgo estimado de toxicidad, pero la posición en la cola no constituye una decisión de moderación.
- **Orden estable en empates:** cuando dos comentarios tienen el mismo riesgo estimado, se conserva el orden original de entrada para que el resultado sea reproducible y auditable.
- **Revisión humana:** el análisis manual del texto en inglés y la decisión final pertenecen a la persona moderadora.
- **Decisión final humana:** la salida del MVP sirve como apoyo; la persona moderadora confirma, cambia o descarta la decisión antes de cerrar la revisión.

## Alcance

### Incluido

- Carga y visualización de un conjunto de comentarios en inglés.
- Estimación inicial de toxicidad mediante el objetivo `IsToxic`.
- Cola ordenada de mayor a menor riesgo estimado.
- Desempate con orden estable y conservando el orden de entrada.
- Vista del texto completo para análisis manual.
- Registro de la decisión final de la persona moderadora.
- Estados de carga visibles mientras se prepara la cola y errores recuperables, con opción de reintentar sin perder el contexto de la revisión.
- Medición de resultados de producto, experiencia de usuario, modelo y seguridad.

### Fuera de alcance

- Publicar, ocultar, borrar o responder automáticamente a contenido en YouTube u otras plataformas.
- Clasificar sentimiento o presentar esa dimensión como resultado del MVP.
- Presentar una puntuación como certeza o como verdad sobre el contenido.
- Tratar infracciones de políticas como una salida fiable del sistema.
- Usar subcategorías automáticas como resultados fiables para decidir por sí solas.
- Sustituir la revisión humana, resolver ambigüedades contextuales o inferir la intención de quien escribió el comentario.
- Diseño visual definitivo en Figma durante esta etapa.

## Datos y limitaciones del dataset

El dataset puede no representar la diversidad real de idiomas, dialectos, comunidades, temas, longitudes, ironía o contexto conversacional. La cobertura de ejemplos tóxicos y no tóxicos puede estar desbalanceada, y las etiquetas humanas pueden contener desacuerdos o sesgos de anotación. Los comentarios aislados no siempre permiten interpretar referencias, bromas, citas o conversaciones previas. Por ello, el riesgo estimado debe entenderse como una señal para priorizar la revisión, no como una evaluación completa del comentario.

## Métricas de éxito

### Producto

- Porcentaje de sesiones en las que se completa la revisión de la cola.
- Tiempo mediano desde la apertura de la cola hasta la primera decisión.
- Tiempo total mediano por comentario revisado.
- Porcentaje de comentarios priorizados que reciben una decisión final humana.

### UX

- Tiempo hasta encontrar el primer caso que la persona moderadora considera prioritario.
- Tasa de finalización de la tarea central.
- Errores de comprensión de la cola, del riesgo estimado o del estado de revisión.
- Valoración cualitativa de claridad, control y confianza calibrada durante pruebas moderadas.

### Modelo

- Precisión, recall y F1 de `IsToxic` sobre un conjunto de evaluación separado.
- Precision@K y recall@K para los primeros elementos de la cola.
- Curva de cobertura frente a revisión manual para distintos umbrales de priorización.
- Rendimiento desglosado por longitud y por segmentos disponibles del dataset, sin interpretar esos cortes como garantía de comportamiento futuro.

### Seguridad y operación

- Tasa de falsos negativos en los casos revisados como de alto riesgo.
- Tasa de falsos positivos que añade carga innecesaria a la moderación.
- Porcentaje de decisiones finales humanas que contradicen la priorización automática.
- Trazabilidad de la entrada, el riesgo estimado, el orden aplicado y la decisión final.
- Ausencia de acciones externas automáticas y capacidad de detener o revisar el flujo antes de cualquier acción posterior.

## Benchmark competitivo

El benchmark comparará el MVP con tres referencias: revisión manual en orden de llegada, revisión manual con una priorización básica y una herramienta de apoyo de moderación existente disponible para evaluación. La comparación se hará sobre el mismo conjunto de comentarios y con personas moderadoras o un protocolo equivalente.

Se observarán tiempo hasta el primer caso prioritario, tiempo total de revisión, Precision@K, recall@K, tasa de correcciones humanas y claridad percibida. El benchmark no tratará ninguna referencia como autoridad: su propósito es conocer cuándo la cola priorizada aporta valor y en qué casos el criterio humano sigue siendo determinante.

## Validación pendiente

La visión y el flujo del MVP quedan pendientes de validar con **Gabriela, Fernanda y Miguel**. La validación deberá comprobar la utilidad de la cola, la comprensión de `IsToxic`, la claridad del riesgo estimado, la facilidad para revisar texto en inglés y la confianza calibrada en la decisión final humana.

El diseño en **Figma queda temporalmente diferido** hasta recoger esta validación y confirmar los requisitos del flujo.

## Criterio de salida de SP-7

La evidencia de SP-7 queda preparada con esta visión de producto, sus límites explícitos y un plan de validación pendiente. El cierre de SP-7 en Jira queda fuera de este cambio.
