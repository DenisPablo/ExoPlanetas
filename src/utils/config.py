"""
Configuración centralizada para el proyecto ExoPlanetas.
"""
import os
from pathlib import Path
from typing import Union

class Settings:
    """Configuración de la aplicación."""
    
    def __init__(self):
        # Directorio base del proyecto (raíz)
        self.BASE_DIR = Path(__file__).parent.parent.parent
        
        # Rutas relativas desde la raíz
        self.DATASET_PATH = self.BASE_DIR / "datasets" / "kepler.csv"
        self.OUTPUT_DIR = self.BASE_DIR / "data"
        self.MODELS_DIR = self.BASE_DIR / "models"
        
        # Crear directorios si no existen
        self._ensure_directories()
        
        # Parámetros del modelo
        self.DEFAULT_LEARNING_RATE = float(os.getenv("LEARNING_RATE", "0.05"))
        self.DEFAULT_MAX_LEAF_NODES = int(os.getenv("MAX_LEAF_NODES", "31"))
        self.DEFAULT_MIN_SAMPLES_LEAF = int(os.getenv("MIN_SAMPLES_LEAF", "20"))
        self.DEFAULT_EARLY_STOPPING = os.getenv("EARLY_STOPPING", "true").lower() == "true"
        
        # Configuración de la API
        self.APP_NAME = os.getenv("APP_NAME", "Exoplanet Classifier API")
        self.APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        
    def _ensure_directories(self) -> None:
        """Crear directorios necesarios si no existen."""
        directories = [self.OUTPUT_DIR, self.MODELS_DIR]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_model_path(self, model_name: str, version: str = "latest") -> Path:
        """Obtener ruta del modelo."""
        if version == "latest":
            latest_link = self.MODELS_DIR / model_name / "latest"
            if latest_link.exists():
                return latest_link / "model.pkl"
            else:
                # Buscar la versión más reciente
                model_dir = self.MODELS_DIR / model_name
                if model_dir.exists():
                    versions = [d for d in model_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
                    if versions:
                        latest_version = sorted(versions)[-1]
                        return latest_version / "model.pkl"
                # Si no hay versiones, devolver None
                return None
        else:
            return self.MODELS_DIR / model_name / version / "model.pkl"
    
    def get_output_path(self, filename: str) -> Path:
        """Obtener ruta de archivo de salida."""
        return self.OUTPUT_DIR / filename
    
    def get_dataset_path(self) -> Path:
        """Obtener ruta del dataset."""
        return self.DATASET_PATH
    
    def get_latest_version(self, model_name: str) -> str:
        """Obtener la versión más reciente del modelo."""
        model_dir = self.MODELS_DIR / model_name
        if not model_dir.exists():
            return "v1.0.0"
        
        versions = [d.name for d in model_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
        if versions:
            return sorted(versions)[-1]
        return "v1.0.0"
    
    def get_all_versions(self, model_name: str) -> list:
        """Obtener todas las versiones disponibles de un modelo."""
        model_dir = self.MODELS_DIR / model_name
        if not model_dir.exists():
            return []
        
        versions = [d.name for d in model_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
        return sorted(versions)
    
    def version_exists(self, model_name: str, version: str) -> bool:
        """Verificar si una versión específica existe."""
        version_dir = self.MODELS_DIR / model_name / version
        return version_dir.exists() and version_dir.is_dir()
    
    def get_version_paths(self, model_name: str, version: str) -> dict:
        """Obtener rutas de archivos para una versión específica."""
        version_dir = self.MODELS_DIR / model_name / version
        return {
            "model_path": version_dir / "model.pkl",
            "metrics_path": version_dir / "metrics" / "classification_report.json",
            "matrix_path": version_dir / "matrix" / "confusion_matrix.npy"
        }
    
    def get_available_models(self) -> list:
        """Obtener lista de todos los modelos disponibles."""
        if not self.MODELS_DIR.exists():
            return []
        
        models = []
        for item in self.MODELS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Verificar que tiene al menos una versión
                versions = [d for d in item.iterdir() if d.is_dir() and d.name.startswith("v")]
                if versions:
                    models.append(item.name)
        
        return sorted(models)

# Instancia global de configuración
settings = Settings()
