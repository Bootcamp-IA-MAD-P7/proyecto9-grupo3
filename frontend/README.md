# Frontend de cola de moderación

Primera vertical del MVP: una superficie interna para priorizar la revisión humana de comentarios. La aplicación usa datos mock tipados y no conecta todavía con FastAPI.

## Desarrollo

```bash
npm install
npm run dev
```

Validación:

```bash
npm run build
npm run lint
```

`VITE_API_URL` queda reservado para la futura integración con la API. La cola no muestra el texto completo; el detalle simula la respuesta autorizada de `GET /comments/{comment_id}`. Las acciones solo actualizan el estado local y nunca eliminan, bloquean ni sancionan comentarios.
