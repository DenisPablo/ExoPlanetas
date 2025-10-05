import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import List, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from modelo import HGBExoplanetModel

import joblib
import json

from fastapi import FastAPI, HTTPException
from typing import Dict, Any

import pandas as pd
import numpy as np

app = FastAPI(
	title="Exoplanet Classifier API",
	description="API REST para clasificación automática de exoplanetas usando ML/AI.",
	version="1.0.0"
)



CSV_PATH = "datasets/kepler.csv"

# Carpeta donde se guardarán los CSVs
OUTPUT_DIR = "data/"
os.makedirs(OUTPUT_DIR, exist_ok=True)

model = HGBExoplanetModel(CSV_PATH)
model.load_data()
model.prepare_features()
model.split_data()
model.train_model()

# --- ENDPOINTS SEGÚN SWAGGER ---


@app.get("/model/info", tags=["Model"])
def model_info():
	from sklearn.metrics import accuracy_score, classification_report
	y_pred = model.pipe.predict(model.X_test)
	acc = accuracy_score(model.y_test, y_pred)
	report = classification_report(model.y_test, y_pred, output_dict=True)
	return {
		"name": model.__class__.__name__,
		"version": "1.0.0",
		"trained_on": [str(CSV_PATH)],
		"classes": list(model.pipe.classes_),
		"accuracy": acc,
		"classification_report": report
	}

@app.post("/predict", tags=["Predict"])
def predict(data: Dict[str, List[Dict[str, float]]]):
	user_data = data["data"] if "data" in data else []
	if not user_data:
		raise HTTPException(status_code=400, detail="No se enviaron datos para predecir")
	import pandas as pd
	X_user = pd.DataFrame(user_data)
	# Asegurar que las columnas coincidan con el modelo
	model_features = model.X_num.columns
	X_user = X_user.reindex(columns=model_features, fill_value=np.nan)
	# Predecir
	y_pred = model.pipe.predict(X_user)
	y_proba = model.pipe.predict_proba(X_user)
	class_names = list(model.pipe.classes_)
	predictions = []
	for i, pred in enumerate(y_pred):
		probas = {class_names[j]: float(y_proba[i][j]) for j in range(len(class_names))}
		predictions.append({
			"class": pred,
			"probabilities": probas
		})
	return {"predictions": predictions}

@app.post("/predict/upload", tags=["Predict"])
async def predict_upload(file: UploadFile = File(...)):
    """
    Recibe un CSV en memoria, predice la clase de cada planeta,
    guarda el CSV con predicciones en el servidor y devuelve estadísticas + link de descarga.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Archivo debe ser CSV")

    try:
        await file.seek(0)
        df = pd.read_csv(file.file, comment="#", quotechar='"', engine="python")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el CSV: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV vacío")

    # Preparar datos para predicción
    X_user = df.reindex(columns=model.X_num.columns, fill_value=pd.NA)

    # Predicciones
    y_pred = model.pipe.predict(X_user)
    df["predicted_disposition"] = y_pred

    # Estadísticas
    stats = df["predicted_disposition"].value_counts().to_dict()
    total = len(df)

    # Guardar CSV en carpeta del servidor
    output_filename = f"{os.path.splitext(file.filename)[0]}_predictions.csv"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    df.to_csv(output_path, index=False)

    # Devolver estadísticas y URL de descarga
    download_url = f"/data/{output_filename}"
    return {
        "total_planets": total,
        "class_distribution": stats,
        "download_url": download_url
    }

@app.get("/download/{filename}", tags=["Predict"])
def download(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    from fastapi.responses import FileResponse
    return FileResponse(path=file_path, filename=filename, media_type='text/csv')

'''
@app.get("/predict/status/{job_id}", tags=["Predict"])
def predict_status(job_id: str):
	return {"status": "done", "results_url": f"/predict/results/{job_id}"}

@app.get("/predict/results/{job_id}", tags=["Predict"])
def predict_results(job_id: str):
	return {"predictions": [{"class": "confirmed"}]}
'''


@app.post("/train", tags=["Train"])
def train(data: Dict[str, Any]):
    # Si el JSON está vacío, devolver error
    if not data:
        raise HTTPException(
            status_code=400,
            detail="Debes enviar al menos un hiperparámetro para entrenar y sobrescribir el modelo."
        )

    # Inicializar modelo con valores actuales
    model = HGBExoplanetModel("kepler.csv")

    # Sobrescribir solo los parámetros que vienen en el JSON
    allowed_params = ["learning_rate", "max_leaf_nodes", "min_samples_leaf", "early_stopping"]
    for k, v in data.items():
        if k in allowed_params:
            setattr(model, k, v)

    # Entrenamiento completo
    model.run()

    return {
        "status": "completed",
        "model_version": "1.0.2",  # Podrías manejar versiones dinámicas
        "used_params": model.get_hyperparameters()
    }


# Ruta relativa (carpeta "models" en el mismo nivel que este archivo)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_MODELS_DIR = os.path.join(BASE_DIR, "models")

@app.get("/model-info/{model_name}", tags=["Model Info"])
def get_model_info(model_name: str):
    """
    Devuelve toda la información disponible del modelo:
    - métricas de rendimiento
    - matriz de confusión
    - rutas de los archivos generados
    """

    base_dir = os.path.join(BASE_MODELS_DIR, model_name)
    metrics_path = os.path.join(base_dir, "metrics", "classification_report.json")
    matrix_path = os.path.join(base_dir, "matrix", "confusion_matrix.npy")
    model_path = os.path.join(base_dir, f"{model_name}.pkl")

    # --- Validaciones ---
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail=f"Modelo '{model_name}' no encontrado en {model_path}")
    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail=f"Métricas no encontradas para '{model_name}'.")
    if not os.path.exists(matrix_path):
        raise HTTPException(status_code=404, detail=f"Matriz de confusión no encontrada para '{model_name}'.")

    # --- Cargar métricas ---
    with open(metrics_path, "r") as f:
        metrics = json.load(f)

    # --- Cargar matriz ---
    confusion_matrix = np.load(matrix_path).tolist()

    return {
        "model_name": model_name,
        "model_path": model_path,
        "metrics": metrics,
        "confusion_matrix": confusion_matrix,
        "files": {
            "metrics": metrics_path,
            "matrix": matrix_path
        }
    }


# Crear GET que consulte la carpeta una lista y devuelva URLs de descarga, Fecha.
# Posibilidad de Obtener la configuraciond de hiperparametros del modelo
#Obtener La posibilidad de modificar hiperparametros del modelo y reentrenar