# Diseño: autenticación y cola real

## Arquitectura

La aplicación React + Vite + TypeScript se separa en tres capas:

1. `src/api/`: cliente HTTP tipado y funciones de contrato.
2. `src/auth/` o estado equivalente en `App`: sesión en memoria, usuario, token y logout.
3. Componentes de presentación: login, cola y estados de interfaz.

El cliente lee `import.meta.env.VITE_API_URL`, elimina una barra final y construye las rutas relativas. Si la variable no existe, devuelve un error de configuración comprensible antes de intentar una petición.

## Contratos y flujo

`POST /auth/login` recibe `{ username, password }` y produce `LoginResponse`. Tras guardar el token solamente en el estado de React, se carga la cola protegida. `GET /auth/me` puede validar la sesión al restaurar el flujo dentro de la vida de la página. `POST /auth/logout` revoca el token en la API y el frontend lo elimina siempre, incluso si la petición falla.

`GET /comments?status=PENDING&page=1&page_size=20` produce `QueuePage`. Sus elementos no contienen `text`; por ello la interfaz únicamente muestra identificador, vídeo, riesgo, incertidumbre, versión, fuente y estado. No se inventa ni se mezcla detalle mock.

## Seguridad y errores

Cada petición protegida añade `Authorization: Bearer <token>`. El token vive únicamente en memoria: no se usa `localStorage`, `sessionStorage`, cookies ni logs. Un `401` limpia la sesión y muestra estado de sesión no autorizada; otros errores de API y de red se muestran claramente y ofrecen reintento cuando procede. Los mensajes no exponen credenciales ni tokens.

## Estados

- Configuración ausente: error explicativo de `VITE_API_URL`.
- Login: formulario, validación básica, envío y error de credenciales/red.
- Cola: loading, error recuperable, unauthorized, ready con elementos y empty.
- Logout: limpieza inmediata del estado y retorno al login.

## Integración visual

Se conservan el encabezado, la paleta, la composición y el aviso de control humano de la primera vertical. Se reemplazan el panel de texto y las acciones de revisión por un resumen de metadatos autorizado del elemento de cola y una acción de cerrar sesión. El componente de cola sigue siendo seleccionable con teclado, aunque la selección no solicita texto no disponible.

## Accesibilidad y responsive

El login usa `form`, `label`, `autocomplete`, botón nativo y mensajes asociados con `aria-live`. Los estados tienen títulos legibles y el foco permanece visible. La cola conserva regiones `main` y `section`, controles operables con teclado y el layout apilado en viewport estrecho sin scroll horizontal.

## Límites

El frontend no calcula riesgo, no autoriza roles, no decide toxicidad, no almacena secretos y no ejecuta acciones sobre comentarios. La API sigue siendo responsable de autenticación, autorización, validación y revocación.
