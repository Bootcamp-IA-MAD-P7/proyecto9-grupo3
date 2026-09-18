# Proposal

## Why

El usuario solicita continuar con el paso 3: login, contraseñas con hash y
permisos MODERATOR/SUPERVISOR, con explicaciones para aprender. El paso 2 ya
persiste usuarios y comentarios; necesitamos añadir sesiones para que
la autenticación sobreviva a reinicios y funcione entre instancias locales.

## What Changes

- Implementar `POST /auth/login`, `GET /auth/me` y `POST /auth/logout`.
- Guardar usuarios con contraseñas Argon2id y sesiones temporales con token opaco.
- Consultar el rol en el servidor y ofrecer una dependencia reutilizable de permisos.
- Migrar SQLite de versión 1 a 2 y añadir un comando de carga de demo.
- Limitar intentos de login por nombre de usuario y evitar exponer credenciales en errores.
- Explicar el flujo y proporcionar pruebas verificables y ejemplos locales.

## Capabilities

### New Capabilities

- `backend-auth`: autenticación persistente y autorización por rol.

### Modified Capabilities

Ninguna: `/health` sigue siendo una comprobación pública de liveness.

## Impact

Cambios en backend, configuración, dependencias y guía de aprendizaje. La base
de datos vive por defecto en `data/local/moderation.db`, excluido de Git.

## Authorization and boundaries

El usuario autoriza continuar sin Jira en esta conversación. El documento
`back1.txt` aporta dos roles y usuarios precargados; no autoriza registro público,
administración de usuarios ni acciones externas. La persistencia añadida es la
necesaria para autenticación; usuarios y comentarios del paso 2 se conservan.
Las reglas de reapertura siguen pendientes del paso 6.
