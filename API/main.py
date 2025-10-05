"""
API FastAPI refactorizada para clasificación de exoplanetas.
"""
import os
import json
from typing import List, Dict, Any

import pandas as pd
import numpy as np

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse

from src.models.hgb_exoplanet import HGBExoplanetModel
from src.utils.config import settings


# Inicializar aplicación
app = FastAPI(
    title=settings.APP_NAME,
    description="API REST para clasificación automática de exoplanetas usando HistGradientBoostingClassifier. Permite entrenar modelos, realizar predicciones individuales y batch, y gestionar versiones de modelos.",
    version=settings.APP_VERSION,
    openapi_tags=[
        {
            "name": "Model",
            "description": "Información del modelo actual y versiones disponibles",
        },
        {
            "name": "Predict", 
            "description": "Predicciones de nuevos datos de exoplanetas",
        },
        {
            "name": "Train",
            "description": "Reentrenamiento de modelos con nuevos hiperparámetros",
        },
        {
            "name": "Model Info",
            "description": "Información detallada de modelos específicos con métricas",
        },
        {
            "name": "Model Versions",
            "description": "Gestión de versiones de modelos",
        },
    ]
)

# Cargar modelo al iniciar
model = HGBExoplanetModel()
try:
    model.load_model()
    print("[INFO] Modelo cargado desde archivo")
except FileNotFoundError:
    print("[INFO] Modelo no encontrado, entrenando nuevo modelo...")
    model.run()


def format_csv_output(df: pd.DataFrame, model_instance: HGBExoplanetModel) -> pd.DataFrame:
    """
    Formatea el DataFrame para generar un CSV legible y bien estructurado.
    
    Args:
        df: DataFrame con datos originales y predicciones
        model_instance: Instancia del modelo usado para las predicciones
        
    Returns:
        DataFrame formateado con columnas ordenadas y valores redondeados
    """
    # Crear una copia para no modificar el original
    formatted_df = df.copy()
    
    # Definir columnas de identificación (prioridad alta)
    id_columns = ['kepid', 'kepoi_name', 'kepler_name', 'koi_disposition', 'koi_pdisposition', 'koi_score']
    
    # Definir columnas de predicción (nuevas)
    prediction_columns = ['prediction_label', 'confidence']
    
    # Obtener columnas numéricas del modelo (excluyendo las de identificación y predicción)
    model_columns = [col for col in model_instance.X_num.columns if col not in id_columns + prediction_columns]
    
    # Obtener otras columnas del dataset original
    other_columns = [col for col in df.columns if col not in id_columns + model_columns + prediction_columns + ['predicted_disposition']]
    
    # Ordenar columnas: identificación, modelo, otras, predicción
    ordered_columns = []
    
    # 1. Columnas de identificación (las que existen)
    for col in id_columns:
        if col in formatted_df.columns:
            ordered_columns.append(col)
    
    # 2. Columnas del modelo
    for col in model_columns:
        if col in formatted_df.columns:
            ordered_columns.append(col)
    
    # 3. Otras columnas del dataset
    for col in other_columns:
        if col not in ordered_columns:
            ordered_columns.append(col)
    
    # 4. Columnas de predicción
    for col in prediction_columns:
        if col in formatted_df.columns:
            ordered_columns.append(col)
    
    # Reordenar DataFrame
    formatted_df = formatted_df[ordered_columns]
    
    # Redondear valores numéricos a 3 decimales
    numeric_columns = formatted_df.select_dtypes(include=[np.number]).columns
    for col in numeric_columns:
        if col not in ['kepid', 'koi_score']:  # No redondear IDs y scores
            formatted_df[col] = formatted_df[col].round(3)
    
    return formatted_df


def load_model_by_version(model_name: str = "hgb_exoplanet_model", version: str = "latest") -> HGBExoplanetModel:
    """
    Carga un modelo específico por versión.
    
    Args:
        model_name: Nombre del modelo
        version: Versión específica o 'latest'
        
    Returns:
        HGBExoplanetModel cargado
        
    Raises:
        HTTPException: Si la versión no existe
    """
    try:
        # Verificar que la versión existe
        if version != "latest" and not settings.version_exists(model_name, version):
            available_versions = settings.get_all_versions(model_name)
            raise HTTPException(
                status_code=404, 
                detail=f"Versión '{version}' no encontrada para el modelo '{model_name}'. Versiones disponibles: {available_versions}"
            )
        
        # Crear nueva instancia del modelo
        model_instance = HGBExoplanetModel()
        
        # Cargar el modelo específico
        model_instance.load_model(model_name, version)
        
        return model_instance
        
    except HTTPException:
        # Re-lanzar HTTPException sin modificar
        raise
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404, 
            detail=f"Modelo no encontrado: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error cargando modelo: {str(e)}"
        )


@app.get("/model/info", tags=["Model"], summary="Información de todos los modelos disponibles")
def model_info():
    """
    Obtiene información de todos los modelos disponibles en el sistema.
    
    Returns:
        - available_models: Lista de nombres de modelos disponibles
        - total_models: Número total de modelos
        - current_model: Información del modelo actualmente cargado
        - models_summary: Resumen de cada modelo con su última versión
    """
    try:
        # Obtener todos los modelos disponibles
        available_models = settings.get_available_models()
        
        # Información del modelo actualmente cargado
        current_model_info = None
        if model.pipe is not None:
            current_model_info = {
                "name": model.__class__.__name__,
                "version": model.version or "unknown",
                "trained_on": [str(settings.get_dataset_path())],
                "classes": list(model.pipe.classes_) if model.pipe else []
            }
        
        # Resumen de cada modelo
        models_summary = []
        for model_name in available_models:
            try:
                latest_version = settings.get_latest_version(model_name)
                versions = settings.get_all_versions(model_name)
                
                # Obtener métricas de la última versión
                metrics_path = settings.MODELS_DIR / model_name / latest_version / "metrics" / "classification_report.json"
                accuracy = None
                if metrics_path.exists():
                    with open(metrics_path, "r") as f:
                        metrics = json.load(f)
                        accuracy = metrics.get("accuracy")
                
                models_summary.append({
                    "model_name": model_name,
                    "latest_version": latest_version,
                    "total_versions": len(versions),
                    "versions": versions,
                    "accuracy": accuracy
                })
            except Exception as e:
                # Si hay error con un modelo específico, continuar con los demás
                models_summary.append({
                    "model_name": model_name,
                    "latest_version": "unknown",
                    "total_versions": 0,
                    "versions": [],
                    "accuracy": None,
                    "error": str(e)
                })
        
        return {
            "available_models": available_models,
            "total_models": len(available_models),
            "current_model": current_model_info,
            "models_summary": models_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo información de modelos: {str(e)}")


@app.post("/predict", tags=["Predict"], summary="Predicción individual de exoplanetas")
def predict(
    data: Dict[str, List[Dict[str, float]]],
    model_name: str = Query("hgb_exoplanet_model", description="Nombre del modelo a usar"),
    version: str = Query("latest", description="Versión específica del modelo o 'latest'")
):
    """
    Realiza predicciones individuales para uno o más exoplanetas usando una versión específica del modelo.
    
    Args:
        data: Diccionario con lista de objetos de exoplanetas, cada uno con características numéricas
        model_name: Nombre del modelo a usar (default: hgb_exoplanet_model)
        version: Versión específica del modelo o 'latest' (default: latest)
        
    Returns:
        Lista de predicciones con clase y probabilidades para cada exoplaneta
        
    Example:
        ```json
        {
            "data": [
                {
                    "koi_period": 10.5,
                    "koi_duration": 2.1,
                    "koi_depth": 0.001,
                    "koi_prad": 1.2,
                    "koi_steff": 5778,
                    "koi_slogg": 4.4
                }
            ]
        }
        ```
    """
    user_data = data.get("data", [])
    if not user_data:
        raise HTTPException(status_code=400, detail="No se enviaron datos para predecir")
    
    try:
        # Cargar modelo específico por versión
        model_instance = load_model_by_version(model_name, version)
        
        X_user = pd.DataFrame(user_data)
        # Asegurar que las columnas coincidan con el modelo
        X_user = X_user.reindex(columns=model_instance.X_num.columns, fill_value=0.0)
        
        # Predicciones
        y_pred = model_instance.predict(X_user)
        y_proba = model_instance.predict_proba(X_user)
        class_names = list(model_instance.pipe.classes_)
        
        predictions = []
        for i, pred in enumerate(y_pred):
            probas = {class_names[j]: float(y_proba[i][j]) for j in range(len(class_names))}
            predictions.append({
                "class": pred,
                "probabilities": probas
            })
        
        return {
            "predictions": predictions,
            "model_info": {
                "model_name": model_name,
                "version": model_instance.version,
                "used_model": f"{model_name}:{model_instance.version}"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en predicción: {str(e)}")


@app.post("/predict/upload", tags=["Predict"], summary="Predicción batch via archivo CSV")
async def predict_upload(
    file: UploadFile = File(...),
    model_name: str = Query("hgb_exoplanet_model", description="Nombre del modelo a usar"),
    version: str = Query("latest", description="Versión específica del modelo o 'latest'")
):
    """
    Realiza predicciones batch subiendo un archivo CSV con datos de exoplanetas usando una versión específica del modelo.
    Genera un CSV formateado y legible con predicciones enriquecidas.
    
    Args:
        file: Archivo CSV con columnas de características de exoplanetas
        model_name: Nombre del modelo a usar (default: hgb_exoplanet_model)
        version: Versión específica del modelo o 'latest' (default: latest)
        
    Returns:
        - total_planets: Número total de exoplanetas procesados
        - class_distribution: Distribución de clases predichas
        - download_url: URL para descargar el CSV con predicciones
        - model_info: Información del modelo utilizado
        - csv_info: Información sobre el formato del CSV generado
        
    CSV Output Features:
        - Columnas ordenadas lógicamente: identificación, modelo, otras, predicción
        - prediction_label: Clase predicha (CONFIRMED, CANDIDATE, FALSE POSITIVE)
        - confidence: Porcentaje de confianza de la predicción
        - generated_at: Marca de tiempo de generación
        - Formato UTF-8 con separador de coma
        - Valores numéricos redondeados a 3 decimales
        - Compatible con Excel y Google Sheets
        
    Note:
        El archivo CSV debe contener las columnas de características numéricas
        que el modelo espera (koi_period, koi_duration, koi_depth, etc.)
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Archivo debe ser CSV")

    try:
        # Cargar modelo específico por versión
        model_instance = load_model_by_version(model_name, version)
        
        # Leer archivo
        content = await file.read()
        import io
        df = pd.read_csv(io.BytesIO(content), comment="#", quotechar='"', engine="python")
        
        if df.empty:
            raise HTTPException(status_code=400, detail="El archivo CSV está vacío. Por favor, verifique que el archivo contenga datos.")

        # Verificar columnas necesarias para predicción
        missing_columns = [col for col in model_instance.X_num.columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Faltan columnas necesarias para la predicción: {missing_columns[:5]}{'...' if len(missing_columns) > 5 else ''}. "
                       f"El archivo debe contener al menos las columnas: {list(model_instance.X_num.columns[:10])}{'...' if len(model_instance.X_num.columns) > 10 else ''}"
            )

        # Preparar datos para predicción
        X_user = df.reindex(columns=model_instance.X_num.columns, fill_value=0.0)

        # Predicciones
        y_pred = model_instance.predict(X_user)
        
        # Obtener probabilidades si el modelo las soporta
        try:
            y_proba = model_instance.predict_proba(X_user)
            # Obtener la probabilidad máxima (confianza)
            confidence = np.max(y_proba, axis=1) * 100  # Convertir a porcentaje
        except AttributeError:
            # Si el modelo no soporta predict_proba
            confidence = [np.nan] * len(y_pred)

        # Agregar columnas de predicción
        df["prediction_label"] = y_pred
        df["confidence"] = confidence
        
        # Agregar marca de tiempo
        from datetime import datetime
        df["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Formatear CSV para salida
        formatted_df = format_csv_output(df, model_instance)

        # Estadísticas
        stats = df["prediction_label"].value_counts().to_dict()
        total = len(df)

        # Guardar CSV formateado con información de versión
        output_filename = f"{os.path.splitext(file.filename)[0]}_predictions_{model_instance.version}.csv"
        output_path = settings.get_output_path(output_filename)
        
        # Guardar con formato UTF-8 y separador de coma
        formatted_df.to_csv(output_path, index=False, encoding='utf-8', sep=',')

        return {
            "total_planets": total,
            "class_distribution": stats,
            "download_url": f"/download/{output_filename}",
            "model_info": {
                "model_name": model_name,
                "version": model_instance.version,
                "used_model": f"{model_name}:{model_instance.version}"
            },
            "csv_info": {
                "columns": len(formatted_df.columns),
                "formatted": True,
                "encoding": "UTF-8",
                "separator": ",",
                "decimal_places": 3
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error procesando archivo: {str(e)}")


@app.get("/download/{filename}", tags=["Predict"], summary="Descargar archivo de predicciones")
def download(filename: str):
    """
    Descarga un archivo de predicciones generado por el endpoint /predict/upload.
    
    Args:
        filename: Nombre del archivo a descargar
        
    Returns:
        Archivo CSV con las predicciones
        
    Raises:
        404: Si el archivo no existe
    """
    file_path = settings.get_output_path(filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path=file_path, filename=filename, media_type='text/csv')


@app.post("/train", tags=["Train"], summary="Reentrenar modelo con nuevos hiperparámetros")
def train(data: Dict[str, Any]):
    """
    Reentrena el modelo con nuevos hiperparámetros y crea una nueva versión.
    
    Args:
        data: Diccionario con hiperparámetros opcionales:
            - learning_rate: Tasa de aprendizaje (float)
            - max_leaf_nodes: Número máximo de nodos hoja (int)
            - min_samples_leaf: Mínimo de muestras por hoja (int)
            - early_stopping: Habilitar parada temprana (bool)
        
    Returns:
        - status: Estado del entrenamiento
        - model_version: Nueva versión del modelo creada
        - used_params: Parámetros utilizados en el entrenamiento
        
    Example:
        ```json
        {
            "learning_rate": 0.1,
            "max_leaf_nodes": 50
        }
        ```
    """
    if not data:
        raise HTTPException(
            status_code=400,
            detail="Debes enviar al menos un hiperparámetro para entrenar y sobrescribir el modelo."
        )

    try:
        # Crear nuevo modelo con parámetros actualizados
        new_model = HGBExoplanetModel(
            learning_rate=data.get("learning_rate", settings.DEFAULT_LEARNING_RATE),
            max_leaf_nodes=data.get("max_leaf_nodes", settings.DEFAULT_MAX_LEAF_NODES),
            min_samples_leaf=data.get("min_samples_leaf", settings.DEFAULT_MIN_SAMPLES_LEAF),
            early_stopping=data.get("early_stopping", settings.DEFAULT_EARLY_STOPPING)
        )

        # Entrenamiento completo
        new_model.run()

        # Actualizar modelo global
        global model
        model = new_model

        return {
            "status": "completed",
            "model_version": model.version,
            "used_params": model.get_hyperparameters()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en entrenamiento: {str(e)}")


@app.get("/model-info/{model_name}", tags=["Model Info"], summary="Información detallada de un modelo específico")
def get_model_info(model_name: str):
    """
    Obtiene información detallada de un modelo específico incluyendo métricas y matriz de confusión.
    
    Args:
        model_name: Nombre del modelo a consultar
        
    Returns:
        - model_name: Nombre del modelo
        - version: Versión del modelo consultado
        - model_path: Ruta del archivo del modelo
        - metrics: Métricas de clasificación detalladas
        - confusion_matrix: Matriz de confusión del modelo
        - files: Rutas de archivos de métricas y matriz
        
    Raises:
        404: Si el modelo, métricas o matriz no existen
    """
    try:
        # Obtener versión más reciente
        version = settings.get_latest_version(model_name)
        
        # Rutas de archivos
        model_path = settings.get_model_path(model_name, version)
        metrics_path = settings.MODELS_DIR / model_name / version / "metrics" / "classification_report.json"
        matrix_path = settings.MODELS_DIR / model_name / version / "matrix" / "confusion_matrix.npy"

        # Validaciones
        if not model_path.exists():
            raise HTTPException(status_code=404, detail=f"Modelo '{model_name}' no encontrado")
        if not metrics_path.exists():
            raise HTTPException(status_code=404, detail=f"Métricas no encontradas para '{model_name}'")
        if not matrix_path.exists():
            raise HTTPException(status_code=404, detail=f"Matriz de confusión no encontrada para '{model_name}'")

        # Cargar métricas
        with open(metrics_path, "r") as f:
            metrics = json.load(f)

        # Cargar matriz de confusión
        confusion_matrix = np.load(matrix_path).tolist()

        return {
            "model_name": model_name,
            "version": version,
            "model_path": str(model_path),
            "metrics": metrics,
            "confusion_matrix": confusion_matrix,
            "files": {
                "metrics": str(metrics_path),
                "matrix": str(matrix_path)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo información del modelo: {str(e)}")


@app.get("/model-versions/{model_name}", tags=["Model Versions"], summary="Listar todas las versiones de un modelo")
def get_model_versions(model_name: str):
    """
    Obtiene todas las versiones disponibles de un modelo específico.
    
    Args:
        model_name: Nombre del modelo a consultar
        
    Returns:
        - model_name: Nombre del modelo consultado
        - versions: Lista de versiones ordenadas de menor a mayor
        - total_versions: Número total de versiones
        - latest_version: Versión más reciente
        
    Raises:
        404: Si el modelo no existe
    """
    try:
        # Verificar que el modelo existe
        model_dir = settings.MODELS_DIR / model_name
        if not model_dir.exists():
            raise HTTPException(status_code=404, detail=f"Modelo '{model_name}' no encontrado")
        
        # Obtener todas las versiones
        versions = settings.get_all_versions(model_name)
        
        if not versions:
            raise HTTPException(status_code=404, detail=f"No se encontraron versiones para el modelo '{model_name}'")
        
        # Obtener la versión más reciente
        latest_version = settings.get_latest_version(model_name)
        
        return {
            "model_name": model_name,
            "versions": versions,
            "total_versions": len(versions),
            "latest_version": latest_version
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo versiones del modelo: {str(e)}")


@app.get("/model-info/{model_name}/{version}", tags=["Model Versions"], summary="Información detallada de una versión específica")
def get_model_version_info(model_name: str, version: str):
    """
    Obtiene información detallada de una versión específica de un modelo.
    
    Args:
        model_name: Nombre del modelo a consultar
        version: Versión específica del modelo (ej: v1.0.0)
        
    Returns:
        - model_name: Nombre del modelo
        - version: Versión consultada
        - metrics: Métricas de clasificación
        - confusion_matrix: Matriz de confusión
        - files: Rutas relativas de los archivos
        
    Raises:
        404: Si el modelo, versión o archivos no existen
    """
    try:
        # Verificar que el modelo existe
        model_dir = settings.MODELS_DIR / model_name
        if not model_dir.exists():
            raise HTTPException(status_code=404, detail=f"Modelo '{model_name}' no encontrado")
        
        # Verificar que la versión existe
        if not settings.version_exists(model_name, version):
            raise HTTPException(status_code=404, detail=f"Versión '{version}' no encontrada para el modelo '{model_name}'")
        
        # Obtener rutas de archivos
        paths = settings.get_version_paths(model_name, version)
        
        # Validar que los archivos necesarios existen
        if not paths["metrics_path"].exists():
            raise HTTPException(status_code=404, detail=f"Métricas no encontradas para '{model_name}' versión '{version}'")
        
        if not paths["matrix_path"].exists():
            raise HTTPException(status_code=404, detail=f"Matriz de confusión no encontrada para '{model_name}' versión '{version}'")
        
        # Cargar métricas
        with open(paths["metrics_path"], "r") as f:
            metrics = json.load(f)
        
        # Cargar matriz de confusión
        confusion_matrix = np.load(paths["matrix_path"]).tolist()
        
        # Verificar si el modelo existe (opcional)
        model_exists = paths["model_path"].exists()
        
        return {
            "model_name": model_name,
            "version": version,
            "metrics": metrics,
            "confusion_matrix": confusion_matrix,
            "files": {
                "model": str(paths["model_path"].relative_to(settings.BASE_DIR)) if model_exists else None,
                "metrics": str(paths["metrics_path"].relative_to(settings.BASE_DIR)),
                "matrix": str(paths["matrix_path"].relative_to(settings.BASE_DIR))
            },
            "model_exists": model_exists
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo información de la versión: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
