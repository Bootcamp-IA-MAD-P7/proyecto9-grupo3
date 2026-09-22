# Frontend de cola de moderación

Superficie interna para que una persona moderadora se autentique y consulte la cola real de comentarios pendientes de FastAPI. El riesgo es una señal de priorización; no es una decisión automática.

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

Endpoints utilizados: `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` y `GET /comments?status=PENDING&page=1&page_size=20`.

La cola no contiene texto completo ni acciones de revisión. El frontend muestra estados de carga, error, sesión no autorizada y cola vacía.
