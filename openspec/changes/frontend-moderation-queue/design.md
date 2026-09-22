# Diseño: frontend de cola de moderación

## Arquitectura inicial

Se usará React + Vite + TypeScript en `frontend/`, con una aplicación de una sola pantalla y componentes pequeños. La primera versión usa datos mock locales, pero sus tipos reflejan los contratos actuales de FastAPI. `VITE_API_URL` queda documentada para una futura capa de cliente HTTP.

## Estructura prevista

```text
frontend/
  src/
    components/   # cabecera, cola, tarjeta, detalle y estados
    data/         # datos mock separados de la vista
    types/        # contratos y tipos de dominio
    App.tsx
    main.tsx
    styles.css
  index.html
  package.json
  tsconfig*.json
  vite.config.ts
```

## Componentes y estado

`App` coordina únicamente el estado de carga, error, comentario seleccionado y feedback. `ModerationQueue` presenta la lista; `QueueItem` presenta una fila sin texto; `CommentDetail` muestra el detalle autorizado simulado; `ReviewActions` registra una transición local. No habrá estado global ni base de datos frontend.

## Datos y futura API

Los mocks incluyen `QueueItem` sin `text` y `CommentDetail` con `text`, respetando la privacidad de `GET /comments` y `GET /comments/{comment_id}`. La futura integración podrá implementar `GET /comments?status=PENDING&page=1&page_size=20`, `GET /comments/{comment_id}` y `POST /comments/{comment_id}/review` mediante `VITE_API_URL`, sin mover decisiones al frontend.

## Responsive y accesibilidad

En escritorio se usa una composición de dos columnas; en móvil se apila la cola y el detalle sin scroll horizontal. Se emplean `header`, `main`, `section`, `article`, botones nativos, etiquetas visibles, `aria-live` para feedback y foco visible. Los colores no son el único canal para comunicar riesgo o estado.

## Decisiones visuales

La interfaz será sobria y profesional: fondo neutro, tarjetas con bordes, densidad útil, tipografía legible y acentos reservados para riesgo y acciones. No copiará logotipo ni identidad de YouTube. La jerarquía visual prioriza la cola, pero cada vista repetirá que riesgo es una señal y que la decisión es humana.

## Estados y límites

La aplicación modela carga, vacío, error recuperable y éxito de acción aunque la demo comience con datos locales. Una acción simulada cambia el estado visual y conserva el caso en la lista. El frontend no calcula riesgo, no decide toxicidad, no elimina contenido y no sustituye autorización, validación o persistencia de la API.
