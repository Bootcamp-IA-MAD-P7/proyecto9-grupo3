# Ensemble ponderado para priorización

El ensemble combina las probabilidades alineadas de regresión logística, SVM y
DistilBERT mediante *soft voting*. No entrena otro clasificador ni utiliza texto,
vídeo o etiquetas secundarias: recibe únicamente una probabilidad por modelo y
`CommentId` para conservar la alineación.

## Configuración congelada

La configuración versionada está en `configs/ensemble.json`. Se obtuvo solo con
las 219 filas de validación y el manifiesto común. Los pesos suman uno:

| Modelo | Peso |
| --- | ---: |
| Regresión logística | 0,10 |
| SVM calibrado | 0,00 |
| DistilBERT | 0,90 |

El SVM permanece en el contrato y en las salidas de auditoría, pero no contribuye
a la probabilidad final porque darle peso redujo PR-AUC en validación. El umbral
congelado es `0,4128293386`, elegido para alcanzar al menos 80 % de recall.

## Resultado de validación

| Métrica | Resultado |
| --- | ---: |
| Precision | 0,7674 |
| Recall | 0,8049 |
| F1 | 0,7857 |
| PR-AUC | 0,8822 |
| Brier score | 0,1782 |

La matriz de confusión es `[[66, 30], [24, 99]]`. Frente a DistilBERT solo, el
ensemble mejora PR-AUC en aproximadamente 0,0007 y Brier score en 0,0077, pero
produce una falsa alarma adicional. La mejora de ranking es pequeña; DistilBERT
se conserva como control de referencia.

## Congelar la configuración en validación

```powershell
.\.venv\Scripts\python.exe scripts/run_ensemble.py fit `
  --logistic data/local/logistic_tfidf/validation_predictions.csv `
  --svm data/local/svm_tfidf/svm_tfidf_validation_results.csv `
  --transformer data/local/transformer/validation_predictions.csv
```

El comando exige exactamente los IDs de validación del manifiesto, vuelve a
alinear por `CommentId` y guarda hashes SHA-256 de todas las entradas. Produce
`validation_predictions.csv` y `validation_metrics.json` dentro de
`data/local/ensemble/`, además de la configuración versionable.

## Evaluación final única

Después de revisar y versionar la configuración, se generan las tres salidas de
test con `--final-test --ensemble-config configs/ensemble.json`. Cada script
rechaza una configuración no seguida por Git o distinta de `HEAD`, y crea un
sidecar de procedencia con el modelo, el split, las columnas y hashes SHA-256.
El ensemble se aplica con el subcomando `final-test`:

```powershell
.\.venv\Scripts\python.exe scripts/run_ensemble.py final-test `
  --logistic data/local/logistic_tfidf/test_predictions.csv `
  --svm data/local/svm_tfidf/svm_tfidf_test_results.csv `
  --transformer data/local/transformer/test_predictions.csv
```

Este comando exige exactamente los 185 IDs de test, comprueba que el manifiesto
coincide con el usado para congelar la configuración, valida los sidecars y
aplica los pesos y el umbral sin recalcularlos. Un sello exclusivo y escrituras
atómicas impiden repetir o sobrescribir una evaluación final existente.
Los resultados de test sirven solo para informar desempeño final, nunca para
cambiar pesos, umbral o modelos.
