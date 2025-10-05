"""
Configuración centralizada para el proyecto ExoPlanetas.
Maneja todas las rutas y parámetros del proyecto usando variables de entorno.
"""
import os
from pathlib import Path
from typing import Union

class Settings:
    """Configuración de la aplicación."""
    
    def __init__(self):
        # Directorio base del proyecto
        self.BASE_DIR = Path(__file__).parent
        
        # Rutas de datos
        self.DATASET_PATH = os.getenv("DATASET_PATH", "datasets/kepler.csv")
        self.OUTPUT_DIR = os.getenv("OUTPUT_DIR", "data/")
        self.MODELS_DIR = os.getenv("MODELS_DIR", "models/")
        
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
        
        # Configuración de logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
    def _ensure_directories(self) -> None:
        """Crear directorios necesarios si no existen."""
        directories = [self.OUTPUT_DIR, self.MODELS_DIR]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_model_path(self, model_name: str = "hgb_exoplanet_model") -> str:
        """Obtener ruta completa del modelo."""
        return str(Path(self.MODELS_DIR) / model_name / f"{model_name}.pkl")
    
    def get_output_path(self, filename: str) -> str:
        """Obtener ruta completa de archivo de salida."""
        return str(Path(self.OUTPUT_DIR) / filename)
    
    def get_dataset_path(self) -> str:
        """Obtener ruta completa del dataset."""
        return str(Path(self.DATASET_PATH))

# Instancia global de configuración
settings = Settings()
