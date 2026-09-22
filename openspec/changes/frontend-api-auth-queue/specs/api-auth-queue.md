# Especificación: autenticación y cola de moderación

## Requirement: Login correcto

### Scenario: La persona moderadora inicia sesión
- GIVEN que `VITE_API_URL` está configurada y la API acepta las credenciales
- WHEN se envía `POST /auth/login` con usuario y contraseña válidos
- THEN se guarda el `access_token` únicamente en memoria
- AND se muestra la cola real protegida

## Requirement: Credenciales incorrectas

### Scenario: La API rechaza el login
- GIVEN que la API responde `401` a `POST /auth/login`
- WHEN la persona envía credenciales incorrectas
- THEN se muestra un mensaje claro de credenciales no válidas
- AND no se crea una sesión ni se muestra la cola

## Requirement: Error de red

### Scenario: La API no está disponible
- GIVEN que la petición de login o cola no puede alcanzar la API
- WHEN se produce un error de red
- THEN se muestra un error comprensible
- AND la interfaz ofrece reintentar sin ocultar el fallo

## Requirement: Token Bearer

### Scenario: Se consulta un recurso protegido
- GIVEN que existe un token en la sesión en memoria
- WHEN se solicita `/auth/me`, `/auth/logout` o `/comments`
- THEN se envía `Authorization: Bearer <access_token>`

## Requirement: Token solo en memoria

### Scenario: Se cierra o recarga la página
- GIVEN que la sesión contiene un token
- WHEN el documento se desmonta o se recarga
- THEN el token no se recupera desde ningún almacenamiento persistente

## Requirement: No usar localStorage

### Scenario: Se inspecciona el almacenamiento del navegador
- GIVEN que la aplicación inicia sesión o cierra sesión
- WHEN se revisan `localStorage` y `sessionStorage`
- THEN no contienen el token ni credenciales

## Requirement: Carga de la cola real

### Scenario: Login seguido de carga
- GIVEN que el login ha sido correcto
- WHEN se solicita la cola
- THEN se llama `GET /comments?status=PENDING&page=1&page_size=20`
- AND se presentan los elementos de `QueuePage` sin datos mock

## Requirement: Cola sin texto completo

### Scenario: Se presenta un elemento de cola
- GIVEN que un `QueueItem` no contiene `text`
- WHEN aparece en la interfaz
- THEN se muestran sus metadatos disponibles
- AND no se inventa, solicita ni muestra texto completo

## Requirement: Respuesta 401

### Scenario: La sesión expira
- GIVEN que una petición protegida responde `401`
- WHEN se procesa la respuesta
- THEN se elimina el token de memoria
- AND se muestra un estado de sesión no autorizada con acceso al login

## Requirement: Cola vacía

### Scenario: No hay comentarios pendientes
- GIVEN que `QueuePage.items` es una lista vacía
- WHEN termina la carga
- THEN se muestra un mensaje de cola vacía
- AND no se muestra un detalle ficticio ni se considera un error

## Requirement: Logout

### Scenario: La persona cierra sesión
- GIVEN que existe una sesión autenticada
- WHEN activa cerrar sesión
- THEN se llama `POST /auth/logout` con Bearer cuando es posible
- AND se elimina siempre el token de memoria
- AND se muestra el formulario de login

## Requirement: Accesibilidad del formulario

### Scenario: Se usa el login con teclado
- GIVEN que se muestra el formulario
- WHEN la persona navega con Tab y envía con Enter
- THEN puede enfocar usuario, contraseña y botón en orden lógico
- AND los campos tienen etiquetas visibles, foco visible y errores anunciables

## Requirement: Responsive

### Scenario: Se usa un viewport móvil
- GIVEN que la aplicación se muestra en una pantalla estrecha
- WHEN la persona inicia sesión y consulta la cola
- THEN el contenido se adapta sin scroll horizontal accidental
- AND los controles permanecen utilizables con teclado y tacto
