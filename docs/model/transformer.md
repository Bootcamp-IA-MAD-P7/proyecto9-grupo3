# Transformer ligero y comparación común

El tercer modelo utiliza `distilbert-base-uncased` para estimar `IsToxic`. Solo
recibe `Text`; `CommentId` alinea las salidas y `VideoId` valida el split. Las
etiquetas secundarias nunca se tokenizan ni entran al modelo.

El CSV esperado es `data/raw/youtoxic_english_1000.csv`. Es un insumo local y no
se versiona ni se descarga desde este repositorio. Si se dispone de una copia
autorizada en otra ubicación, se puede pasar con `--dataset RUTA_LOCAL.csv`.
No se deben usar datasets de ejemplo de scikit-learn ni generar métricas sin
ejecutar el pipeline con el dataset del proyecto.

## Entrenamiento

El proceso reutiliza `data/splits/common_split.csv`, ajusta todos los pesos con
las 580 filas de entrenamiento y usa las 219 filas de validación para escoger
el umbral más alto que alcanza al menos 80 % de recall. Por defecto no abre las
185 filas de test.

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev,model,transformer]'
.\.venv\Scripts\python.exe scripts/train_transformer.py
```

Si falta el CSV por defecto, el comando informa de la ruta exacta y recuerda
cómo indicar una ruta alternativa con `--dataset`; no crea resultados ficticios.
Hasta conectar un artefacto entrenado y validado, la API sigue usando
`SimulatedScorer` para el demo. Sus puntuaciones solo prueban el contrato de la
cola y no representan toxicidad.

La configuración reproducible usa semilla 42, longitud máxima 128, tres épocas,
lotes de 16, tasa de aprendizaje `2e-5` y la revisión de DistilBERT
`12040accade4e8a0f71eabdb258fecc2e7e948be`. El informe conserva además las
versiones del runtime. Los artefactos locales se guardan en
`data/local/transformer/`, que está excluido de Git:

- `model/`: pesos y tokenizador.
- `validation_predictions.csv`: probabilidades alineadas por `CommentId`.
- `metrics.json`: configuración, pérdidas, umbral y métricas.

Solo después de fijar y versionar el ensemble debe utilizarse
`--final-test --ensemble-config configs/ensemble.json`. El test no se
usa para escoger épocas, umbrales ni pesos.

## Comparación de los tres modelos

La comparación vuelve a calcular las decisiones de los tres modelos con la
misma regla de recall sobre validación. No confía en las predicciones binarias
exportadas previamente, que podrían proceder de umbrales diferentes. También
informa PR-AUC, Brier score y correlación entre probabilidades.

```powershell
.\.venv\Scripts\python.exe scripts/train_svm_tfidf.py
.\.venv\Scripts\python.exe scripts/compare_models.py `
  --logistic data/local/logistic_tfidf/validation_predictions.csv `
  --svm data/local/svm_tfidf/svm_tfidf_validation_results.csv `
  --transformer data/local/transformer/validation_predictions.csv
```

Los resultados quedan en `data/local/model_comparison/`. La correlación ayuda a
decidir si un modelo aporta errores distintos al ensemble; no basta con elegir
automáticamente el modelo con mayor F1.

## Primera validación con el dataset del proyecto

Ejecución local del 21 de septiembre de 2026 sobre las 219 filas de validación.
Los tres modelos usan el mismo objetivo de recall mínimo del 80 % y el test
permanece sellado.

| Modelo | Umbral | Precision | Recall | F1 | PR-AUC | Brier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Regresión logística | 0,3875 | 0,6689 | 0,8049 | 0,7306 | 0,7793 | 0,2166 |
| SVM lineal calibrado | 0,2695 | 0,6387 | 0,8049 | 0,7122 | 0,7398 | 0,2475 |
| DistilBERT | 0,4193 | 0,7734 | 0,8049 | 0,7888 | 0,8815 | 0,1859 |

DistilBERT detecta 99 de los 123 positivos, deja escapar 24 y genera 29 falsas
alarmas. Con el mismo recall, la regresión logística genera 49 falsas alarmas y
el SVM 56. DistilBERT también presenta el mejor ranking y el menor error de
probabilidad de los tres.

La correlación entre probabilidades es 0,819 entre los dos modelos clásicos,
0,554 entre regresión logística y DistilBERT, y 0,530 entre SVM y DistilBERT.
Una búsqueda exploratoria de pesos en pasos de 0,1 encontró que 10 % de
regresión logística y 90 % de DistilBERT alcanza PR-AUC 0,8822 y Brier 0,1782.
La mejora de PR-AUC frente a DistilBERT solo es 0,0007, por lo que debe tratarse
como una candidata de validación, no como evidencia concluyente. Añadir peso al
SVM no mejoró el mejor PR-AUC observado.
