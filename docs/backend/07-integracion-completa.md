# Paso 7: integración completa local

## Qué une este paso

El navegador, la API y SQLite forman ahora un recorrido local. El supervisor
importa comentarios, el puntuador asigna una prioridad, el moderador reclama
un comentario, revela su texto y guarda una decisión humana. El historial y la
supervisión muestran la evolución posterior. No se ejecuta ninguna acción en
YouTube.

`GET /comments/queue` devuelve páginas de pendientes sin texto. La ruta previa
`GET /comments` conserva el mismo contrato paginado para los consumidores
existentes. El texto solo se
entrega por `GET /comments/{id}/content` al titular de una asignación activa.

## Probarlo

Desde la raíz, con Python 3.12:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
$env:MODERATION_DATABASE_PATH = "data/local/demo-integration.db"
.venv\Scripts\python -m app.seed_demo_users
.venv\Scripts\python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Abre `http://127.0.0.1:8000/ui/`. Entra como `supervisor` con la contraseña que
acabaste de introducir. En **Importar ejemplos**, escribe una línea como
`C-100 | VIDEO-1 | Texto sintético de ejemplo`. Actualiza la cola, selecciona
el comentario, tómalo, muestra el texto y guarda una revisión con motivo. Mira
su historial. Si recargas la pestaña antes de decidir, vuelve a entrar y abre
el comentario desde **Mis asignaciones**. El historial de cualquier comentario
se puede consultar por ID. Para una escalación, elige **Escalar** y actualiza la lista de
supervisión. El campo de recomendación de retirada solo registra una
recomendación humana; no retira contenido.

La contraseña nunca se añade al repositorio. La sesión se conserva solo en la
memoria de la pestaña. Al recargar la página hay que entrar de nuevo. La
interfaz usa `textContent` para presentar valores del servidor.

## Puntuación real opcional

El modo predeterminado usa un valor determinista **simulado**; no debe
interpretarse como una predicción de toxicidad. Para conectar una pipeline
TF-IDF + regresión logística entrenada y confiable:

```powershell
.venv\Scripts\python -m pip install -e ".[model]"
$env:MODERATION_SCORER_MODE = "model"
$env:MODERATION_MODEL_PATH = "data/local/logistic_tfidf/logistic_tfidf.joblib"
$env:MODERATION_MODEL_VERSION = "tfidf-logistic-regression-v1"
```

Reinicia Uvicorn después del cambio. El archivo debe ser una pipeline sklearn
con `predict_proba` y clase positiva `1`. Solo carga un `.joblib` de origen
confiable: su deserialización puede ejecutar código. Si falta el archivo, el
servidor falla al iniciar; nunca pasa en silencio a puntuación simulada.

La prueba de esta integración ajusta una pequeña pipeline con frases
sintéticas y comprueba la forma de la respuesta. **No** mide calidad del modelo.
El dataset crudo y el artefacto entrenado no están disponibles en este worktree;
la validación real, el análisis de errores, sesgos y umbrales quedan pendientes
de esos insumos.

## Por qué versión 5 de SQLite

La antigua cola y la supervisión utilizaron el número 3 para esquemas
distintos. La migración reconoce la forma de sus columnas. Adopta las tablas de
revisión/supervisión como base, copia la cola antigua y añade incertidumbre y
origen de puntuación. Todo sucede en una transacción; una forma desconocida se
rechaza sin alterar la base. Para datos importantes, realiza una copia del
archivo SQLite antes de abrirlo con esta versión. Una asignación `IN_REVIEW`
antigua conserva su revisor y recibe un nuevo plazo de 15 minutos, ya que el
esquema antiguo no guardaba cuándo vencía. Una relación histórica fuera de
`IN_REVIEW` se conserva como asignación cerrada. Un `IN_REVIEW` antiguo sin
responsable vuelve a `PENDING` para que el sistema pueda arrancar y reasignarlo.

## Estado de verificación

Las pruebas automáticas cubren permisos, importación, cola, asignación,
revelación, revisión, reapertura, supervisión y migración. Los avisos de
deprecación de `httpx`/Starlette en la suite proceden de dependencias. La
interfaz es una demostración local; no se ha desplegado ni revisado por otro
miembro del equipo.
