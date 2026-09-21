# Línea base de Arnaldo: regresión logística + TF-IDF

Este modelo estima `IsToxic` para ordenar comentarios que revisará una persona.
No toma decisiones de moderación. Usa únicamente `Text` como entrada e
`IsToxic` como etiqueta. `CommentId` solo alinea resultados; `VideoId` solo
verifica la partición. Las etiquetas secundarias no entran al modelo.

## Datos y partición

El CSV original se mantiene local y fuera de Git. La ejecución requiere el
manifiesto `data/splits/common_split.csv`: 580 filas de entrenamiento, 219 de
validación y 185 de test, agrupadas por vídeo. Las 16 filas `#NAME?` quedan
fuera de la comparación principal. El programa comprueba IDs únicos, cobertura
de los vídeos conocidos, coincidencia de `VideoId`, separación de vídeos y
ausencia de textos equivalentes entre particiones, normalizando mayúsculas y
espacios igual que el vectorizador. Lee los identificadores como cadenas para conservar
ceros iniciales y rechaza IDs vacíos. Los textos numéricos y el literal `NA`
se conservan como texto.

## Entrenar y revisar validación

Desde la raíz, con Python 3.12 o superior, instala las dependencias del backend,
las pruebas y este modelo mediante el extra `model`. No requiere instalar
PyTorch ni transformers:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c backend/constraints.txt -e '.[dev,model]'
.\.venv\Scripts\python.exe -m pytest tests/models/test_logistic_tfidf.py -q
.\.venv\Scripts\python.exe scripts/train_logistic_tfidf.py --dataset data/raw/youtoxic_english_1000.csv
```

El CSV debe existir en la ruta indicada; el manifiesto no contiene el texto ni
las etiquetas y no permite entrenar por sí solo. Las pruebas usan datos
sintéticos: verifican el funcionamiento, no la calidad predictiva real.

TF-IDF y regresión logística forman un único pipeline. El vectorizador convierte
el texto a minúsculas y utiliza n-gramas de caracteres dentro de los límites de
cada palabra (`char_wb`, de 3 a 5 caracteres, `min_df=2` y frecuencia sublineal).
Esta representación tolera mejor variaciones, puntuación y palabras no vistas.
TF-IDF aprende su vocabulario solo de train. La regresión logística usa `C=3`,
`class_weight="balanced"`, `liblinear`, `max_iter=1000` y `random_state=42`.

Los archivos se guardan por defecto en `data/local/logistic_tfidf/`, fuera de
Git:

- `logistic_tfidf.joblib`: pipeline entrenado. Cargarlo solo si procede de una
  fuente confiable.
- `validation_predictions.csv`: `CommentId`, `IsToxic`, `probability`,
  `prediction`, en el orden del manifiesto.
- `metrics.json`: umbral seleccionado, precision, recall, F1, matriz de
  confusión, PR-AUC calculada como *average precision*, Brier score y métricas
  de ranking para los primeros 10, 20, 50 y 100 comentarios.

El programa selecciona en validación el umbral más alto que alcanza al menos
80 % de recall. Esta regla busca detectar cuatro de cada cinco positivos con la
menor cola compatible con ese objetivo. El test no participa en la selección.

## Evaluación final

Cuando el equipo haya aceptado la configuración y la regla de recall, ejecutar
una sola evaluación final:

```powershell
.\.venv\Scripts\python.exe scripts/train_logistic_tfidf.py --dataset data/raw/youtoxic_english_1000.csv --final-test
```

Esto añade `test_predictions.csv` y las métricas de test a `metrics.json`. El
umbral se vuelve a obtener exclusivamente de validación y después se aplica al
test. No usar esos resultados para ajustar el modelo, el umbral o los pesos del
ensemble. La exportación contiene probabilidades alineadas por `CommentId` para
compararlas con SVM y transformer.

El conjunto es pequeño y contiene solo 12 vídeos identificados, por lo que
los resultados dependerán de los vídeos reservados y no demostrarán desempeño
general en YouTube.

## Primera validación con el dataset del proyecto

Ejecución local del 21 de septiembre de 2026 con el CSV proporcionado por
Arnaldo, copiado sin modificaciones a `data/raw/youtoxic_english_1000.csv`.
El CSV, el pipeline entrenado y las predicciones quedan excluidos de Git.

- SHA-256 del CSV: `933d8401a140756cf87c6db2781bd268489f506621486f4b8acc55667ea94526`.
- SHA-256 del manifiesto: `0b2b01364d072382419d4331efe23cea1aedb75f0f9700d9294777eb915e287b`.
- Entorno: Python 3.12.10, pandas 3.0.6, NumPy 2.5.3,
  scikit-learn 1.9.1 y joblib 1.6.0.
- Partición utilizada: 580 filas para entrenar y 219 para validar.
  Las 185 filas de test quedan reservadas sin evaluación predictiva;
  se excluyen las 16 filas con vídeo `#NAME?`.

Resultados de validación para `IsToxic=1`, con el umbral `0,3875` seleccionado
para alcanzar al menos 80 % de recall:

| Métrica | Resultado |
| --- | ---: |
| Precision | 0,6689 |
| Recall | 0,8049 |
| F1 | 0,7306 |
| PR-AUC (average precision) | 0,7793 |
| Brier score | 0,2166 |

La matriz de confusión, con filas reales y columnas predichas en orden
`[0, 1]`, es `[[47, 49], [24, 99]]`. El modelo detecta 99 de los 123 casos
tóxicos de validación; deja pasar 24 y genera 49 falsas alarmas. Frente a la
primera línea base a umbral 0,5, el recall sube de 0,0894 a 0,8049 y PR-AUC de
0,6807 a 0,7793. La comparación combina un modelo mejor y una política de umbral
distinta, por lo que cada efecto también debe revisarse por separado.

| Tramo de la cola | Precision@K | Recall@K | Tóxicos encontrados |
| ---: | ---: | ---: | ---: |
| 10 | 1,00 | 0,0813 | 10 |
| 20 | 0,95 | 0,1545 | 19 |
| 50 | 0,84 | 0,3415 | 42 |
| 100 | 0,71 | 0,5772 | 71 |

Estos resultados favorecen el uso como cola priorizada: los primeros puestos
concentran positivos, aunque revisar el 80 % exige aceptar más carga manual.
Los ajustes deben hacerse en validación, conservando el test para la evaluación
final.

Se verificó que el pipeline guardado reproduce las 219 probabilidades
exportadas y su alineación por `CommentId`, que el vocabulario de 13 135 términos
procede exclusivamente de train y que el optimizador converge en 4 iteraciones.
Los resultados completos están en `data/local/logistic_tfidf/metrics.json`.

## Integración con el backend

El backend todavía utiliza `SimulatedScorer`. Entrenar este pipeline no cambia
las puntuaciones de la API: falta conectar un adaptador que cargue el artefacto
evaluado y marque sus resultados como `MODEL`. La cola actual sirve para
comprobar importación, permisos y orden, no para medir toxicidad.
