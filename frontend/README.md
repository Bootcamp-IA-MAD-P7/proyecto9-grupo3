# Frontend de cola de moderación

Superficie interna para que una persona moderadora se autentique, consulte la cola real de comentarios pendientes y registre una revisión humana persistente. El riesgo es una señal de priorización; no es una decisión automática.

## Desarrollo

```bash
npm install
npm run dev
```

Configura `VITE_API_URL` en un archivo `.env` local, por ejemplo `http://localhost:8000`. El token solo vive en memoria y se envía como `Authorization: Bearer <token>`; no se usa `localStorage` ni `sessionStorage`.

Validación:

```bash
npm run build
npm run lint
```

Endpoints utilizados: `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`, `GET /comments?status=PENDING&page=1&page_size=20`, `GET /comments/{comment_id}` y `POST /comments/{comment_id}/review`.

El texto completo solo aparece en el detalle autorizado. La revisión humana admite `NEEDS_REVIEW`, `CONFIRMED_TOXIC` y `NOT_TOXIC`, con confirmación para decisiones finales, notas opcionales y feedback accesible. No se ejecutan acciones externas automáticas.

La implementación está orientada a EN 301 549 v3.2.1 y WCAG 2.1 AA; requiere auditoría manual con navegador, teclado, lector de pantalla, zoom al 200%, contraste y una API disponible. Los tokens permanecen en memoria y nunca se guardan en almacenamiento del navegador.
