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
ausencia de textos idénticos entre particiones.

## Entrenar y revisar validación

Desde la raíz, con `pandas`, `numpy`, `scikit-learn` y `joblib` instalados:

```powershell
python scripts/train_logistic_tfidf.py --dataset data/raw/youtoxic_english_1000.csv
```

TF-IDF y regresión logística forman un único pipeline. Se quitan espacios al
inicio y al final. Se conservan mayúsculas, palabras cortas y signos de
puntuación; la tokenización separa por espacios. TF-IDF aprende su vocabulario
solo de train. La regresión logística usa `C=1`, `liblinear`, `max_iter=1000`
y `random_state=42`. Son parámetros fijos de esta primera línea base, sin
búsqueda de hiperparámetros.

Los archivos se guardan por defecto en `data/local/logistic_tfidf/`, fuera de
Git:

- `logistic_tfidf.joblib`: pipeline entrenado. Cargarlo solo si procede de una
  fuente confiable.
- `validation_predictions.csv`: `CommentId`, `IsToxic`, `probability`,
  `prediction`, en el orden del manifiesto.
- `metrics.json`: precision, recall, F1, matriz de confusión, PR-AUC calculada
  como *average precision*, y Brier score.

La columna `prediction` utiliza 0,5 únicamente como umbral descriptivo. Un
umbral de uso real debe acordarse según el coste de falsas alarmas y casos no
detectados y elegirse en validación. El test no participa en esa decisión.

## Evaluación final

Cuando el equipo haya fijado la configuración y el umbral, ejecutar una sola
evaluación final:

```powershell
python scripts/train_logistic_tfidf.py --dataset data/raw/youtoxic_english_1000.csv --final-test
```

Esto añade `test_predictions.csv` y las métricas de test a `metrics.json`.
No usar esos resultados para ajustar el modelo, el umbral o los pesos del
ensemble. La exportación contiene probabilidades alineadas por `CommentId`
para compararlas con SVM y transformer.

El conjunto es pequeño y contiene solo 12 vídeos identificados, por lo que
los resultados dependerán de los vídeos reservados y no demostrarán desempeño
general en YouTube.
