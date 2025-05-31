# Análisis de Comportamientos Atípicos en la Demanda de Uber

## Descripción del Proyecto
Este repositorio alberga un proyecto orientado a detectar patrones de demanda anómalos en el servicio de transporte Uber en la ciudad de Nueva York. Utilizando técnicas de machine learning no supervisado (IsolationForest), se identifican picos inusuales y caídas inesperadas en el volumen de viajes, con el fin de optimizar la asignación de unidades y mejorar la calidad del servicio.

## Estructura del Repositorio
```text
├── data/  
│   ├── raw/                 # Datos originales sin modificar (descargados de Kaggle)  
│   └── processed/           # Datos transformados listos para modelado  
├── notebooks/               # Cuadernos de Jupyter y Colab para EDA y desarrollo
|   |── eda.ipynb            # Script para análisis exploratorio de datos  
├── src/                     # Código fuente del proyecto  
│   ├── preprocessing.py     # Funciones de limpieza y transformación de datos
│   ├── train_model.py       # Entrenamiento del modelo IsolationForest  
│   ├── evaluate.py          # Cálculo de métricas de detección de anomalías  
│   └── predict.py           # Utilidad para hacer inferencias con el modelo entrenado  
├── deployment/              # Archivos de configuración para Kubeflow y Kubernetes  
├── requirements.txt         # Dependencias de Python  
└── README.md                # Documento principal (este archivo)
```

## Requisitos
- Python 3.8 o superior  
- Google Colab (opcional, para ejecutar notebooks en la nube)  
- Kubeflow (para despliegue en Kubernetes)  
- Paquetes listados en `requirements.txt`

## Instalación y Configuración
1. Clonar este repositorio:  
   ```bash
   git clone https://github.com/jhonmetal/uberunspvml.git
   cd uberunspvml
   ```
2. Crear y activar un entorno virtual (recomendado):  
   ```bash
   python -m venv venv
   source venv/bin/activate   # En Linux/macOS  
   venv\Scripts\activate      # En Windows  
   ```
3. Instalar dependencias:  
   ```bash
   pip install -r requirements.txt
   ```
4. Descargar el dataset de Kaggle y colocarlo en `data/raw/`. El archivo principal debe llamarse `uber-raw-data.csv` u otro nombre que se ajuste al script de preprocesamiento.

## Uso

### 1. Análisis Exploratorio de Datos (EDA)  
Ejecutar el notebook `notebooks/eda.ipynb` para visualizar:  
- Histogramas de conteo de viajes por hora  
- Series temporales diarias/semanales de volumen de viajes  
- Mapas de densidad geográfica de recogidas  
- Boxplots de conteo de viajes por día de la semana  

### 2. Preparación de Datos  
```bash
python src/preprocessing.py --input data/raw/uber-raw-data.csv --output data/processed/uber-processed.csv
```

### 3. Entrenamiento del Modelo  
```bash
python src/train_model.py --input data/processed/uber-processed.csv --model_path models/isolation_forest.pkl
```

### 4. Evaluación del Modelo  
```bash
python src/evaluate.py --input data/processed/uber-processed.csv --model_path models/isolation_forest.pkl --metrics_output reports/metrics.json
```
Las métricas calculadas incluyen:
- Precisión, recall y F1-score  
- ROC AUC  
- Curva de precisión-recall  

### 5. Inferencia (Detección de Anomalías)  
```bash
python src/predict.py --input data/processed/uber-processed_new.csv --model_path models/isolation_forest.pkl --output results/anomalies.csv
```

## Despliegue con Kubeflow
En la carpeta `deployment/` se encuentran los siguientes archivos:
- `pipeline.yaml`: Definición del flujo de trabajo para Kubeflow Pipelines  
- `k8s_deployment.yaml`: Manifiestos de Kubernetes para desplegar el servicio de inferencia como un microservicio

### Flujo de despliegue (resumen)
1. Crear un namespace en Kubernetes (por ejemplo, `uber-anomaly`)  
2. Aplicar los manifiestos:  
   ```bash
   kubectl apply -f deployment/k8s_deployment.yaml -n uber-anomaly
   kubectl apply -f deployment/pipeline.yaml -n uber-anomaly
   ```
3. Acceder a la interfaz de Kubeflow Pipelines para ejecutar el pipeline completo de preprocesamiento, entrenamiento y despliegue

## Buenos Hábitos de Desarrollo
- Mantener la rama principal (`main`) siempre funcional y documentada  
- Crear ramas para nuevas funcionalidades o experimentos y generar Pull Requests para revisión de código  
- Documentar cada módulo y función en el código fuente  
- Facilitar la reproducción de resultados agregando ejemplos de uso y muestras de datos en el README

## Licencia y Contacto
- **Licencia:** Commons Clause + MIT / Apache 2.0
- **Equipo:**
  - [Jhonathan Pauca](mailto:jhonathan.pauca@unmsm.edu.pe), [jhonmetal](https://github.com/jhonmetal/)
  - [Fernando Flores](mailto:fernando.floresr@unmsm.edu.pe), [fnfloresra](https://github.com/fnfloresra)
  - [Melissa Rodriguez](mailto:melissa.rodriguezs@unmsm.edu.pe), [Melissadrrs](https://github.com/Melissadrrs)
  - [Heber Hualpa](mailto:heber.hualpa@unmsm.edu.pe), [hheber](https://github.com/hheber/)
  - [Marco Candia](mailto:marco.candia@unmsm.edu.pe)

> Este README servirá como base para futuras ampliaciones, incorporando descripciones detalladas de cada componente, ejemplos de ejecución con resultados esperados y enlaces a dashboards de visualización de métricas.

---

**requirements.txt (ejemplo)**  
```txt
pandas
numpy
scikit-learn
matplotlib
seaborn
kubeflow-pipelines
tensorflow
```
