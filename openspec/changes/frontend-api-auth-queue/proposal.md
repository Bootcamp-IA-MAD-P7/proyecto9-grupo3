# Propuesta: autenticación y cola real del frontend

## Problema

La primera vertical dejó una superficie visual útil, pero todavía usa datos mock, una sesión simulada y acciones locales. Una persona moderadora no puede autenticarse frente a la API ni consultar su cola real de comentarios pendientes.

## Usuario y objetivo

El usuario principal es la persona moderadora. El objetivo es permitirle iniciar sesión con la API real, consultar su cola protegida y cerrar sesión sin presentar el frontend como un sistema autónomo de decisión.

## Alcance incluido

- Tipos TypeScript para `LoginResponse`, `PublicUser`, `QueueItem` y `QueuePage`.
- Cliente HTTP centralizado configurado por `VITE_API_URL`.
- Login, usuario actual, logout y carga de `GET /comments?status=PENDING&page=1&page_size=20`.
- Token únicamente en memoria y cabecera `Authorization: Bearer <token>`.
- Estados explícitos de carga, error, sesión no autorizada y cola vacía, con reintento.
- Integración de la cola real con los componentes visuales de la primera vertical, sin mezclar mocks y API.
- Accesibilidad semántica, teclado, foco visible y responsive.

## Alcance excluido

- `GET /comments/{comment_id}` y texto completo de comentarios.
- `POST /comments/{comment_id}/review`, persistencia de decisiones o acciones de moderación.
- Importación, YouTube, eliminación, bloqueo o sanción automática.
- Persistencia del token en `localStorage`, `sessionStorage`, cookies o cualquier almacenamiento durable.

## Relación con la primera vertical

Se conserva la composición, la identidad visual, la explicación de que el riesgo es una señal y la responsabilidad humana. Se sustituyen solamente la fuente mock, la sesión simulada y las acciones locales por autenticación y lectura reales; el detalle con texto y las decisiones simuladas dejan de mostrarse porque no forman parte del contrato de esta vertical.
