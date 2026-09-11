# Carta del proyecto

## Estado

Documento inicial. Las hipótesis de producto deben validarse durante Discovery.

## Equipo

Gabriela, Miguel y Fernanda comparten responsabilidad de producto, desarrollo,
calidad y documentación. Los roles rotan por historia para distribuir aprendizaje
y evitar silos.

## Plazo y restricciones

- 7 días hábiles.
- Repositorio Git existente y entorno `.venv` ya creado.
- Despliegue temprano en AWS mediante la infraestructura facilitada por Miguel.
- Jira será el sistema de seguimiento; Git será la fuente de verdad técnica.

## Resultado buscado

Entregar un producto de análisis de sentimientos que resuelva un problema de
usuario validado, comunique con claridad la confianza y las limitaciones del
modelo, y pueda demostrarse en un entorno AWS.

## Principios

1. Descubrir antes de ampliar alcance.
2. Una historia entrega valor observable de extremo a extremo.
3. Una especificación aprobada precede al código de producción.
4. La calidad se demuestra con evidencia automática y UX revisable.
5. Cada integrante debe poder explicar el sistema completo.

## Métricas iniciales

- Producto: porcentaje de usuarios de prueba que completa la tarea sin ayuda.
- UX: tiempo y errores durante la tarea principal.
- Modelo: macro F1, métricas por clase, matriz de confusión y casos ambiguos.
- Operación: disponibilidad de la demo y tiempo de respuesta p95.
- Aprendizaje: cada integrante presenta una decisión de producto, una técnica y
  una de calidad con evidencia.

## Riesgos a resolver pronto

- Caso de uso o usuario insuficientemente concreto.
- Dataset sesgado, pequeño o con licencia inadecuada.
- Mostrar predicciones como certezas cuando el lenguaje es ambiguo.
- Dependencia tardía de AWS o de credenciales de terceros.
- Alcance excesivo para siete días.

