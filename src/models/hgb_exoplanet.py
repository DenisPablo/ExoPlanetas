"""
Modelo HGBExoplanetModel refactorizado con versionado automático.
"""
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix

from ..utils.config import settings


class HGBExoplanetModel:
    """
    Modelo de clasificación de exoplanetas usando HistGradientBoostingClassifier.
    Incluye versionado automático y gestión de métricas.
    """

    def __init__(
        self, 
        csv_path: Optional[Path] = None,
        target: str = "koi_disposition", 
        group_col: str = "kepid", 
        seed: int = 42,
        learning_rate: Optional[float] = None,
        max_leaf_nodes: Optional[int] = None,
        min_samples_leaf: Optional[int] = None,
        early_stopping: Optional[bool] = None
    ):
        self.csv_path = csv_path or settings.get_dataset_path()
        self.target = target
        self.group_col = group_col
        self.seed = seed

        # Hiperparámetros con valores por defecto
        self.learning_rate = learning_rate if learning_rate is not None else settings.DEFAULT_LEARNING_RATE
        self.max_leaf_nodes = max_leaf_nodes if max_leaf_nodes is not None else settings.DEFAULT_MAX_LEAF_NODES
        self.min_samples_leaf = min_samples_leaf if min_samples_leaf is not None else settings.DEFAULT_MIN_SAMPLES_LEAF
        self.early_stopping = early_stopping if early_stopping is not None else settings.DEFAULT_EARLY_STOPPING

        # Estado del modelo
        self.model = None
        self.pipe = None
        self.X_train = self.X_test = None
        self.y_train = self.y_test = None
        self.groups_train = self.groups_test = None
        self.comparison = None
        self.y_pred = None
        self.version = None

    def load_data(self) -> pd.DataFrame:
        """Carga datos desde CSV."""
        df = pd.read_csv(self.csv_path, comment="#")
        assert self.target in df.columns, f"Falta la columna objetivo {self.target}"
        assert self.group_col in df.columns, f"Falta {self.group_col} para agrupar por estrella"
        self.df = df
        print(f"[INFO] Dataset cargado: {len(df):,} filas")
        return df

    def prepare_features(self) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """Prepara features eliminando columnas problemáticas."""
        leak_or_meta = [
            "koi_pdisposition", "koi_score", "koi_tce_delivname",
            "kepler_name", "kepoi_name"
        ]
        df = self.df.copy()

        X_all = df.drop(columns=[self.target] + [c for c in leak_or_meta if c in df.columns], errors="ignore")
        X_num = X_all.select_dtypes(include=[np.number]).copy()

        # Quitar columnas completamente nulas
        all_null = X_num.columns[X_num.isna().all()].tolist()
        if all_null:
            X_num = X_num.drop(columns=all_null)

        # Quitar RA/DEC y el id de grupo
        for c in ["ra", "dec", self.group_col]:
            if c in X_num.columns:
                X_num = X_num.drop(columns=[c])

        y = df[self.target].copy()
        
        # Transformar etiquetas de español a inglés
        label_mapping = {
            "FALSE POSITIVE": "FALSE_POSITIVE"
        }
        y = y.replace(label_mapping)
        
        groups = df[self.group_col].copy()

        print(f"[INFO] Features finales: {X_num.shape[1]} columnas")
        print("[INFO] Ejemplo de columnas:", ", ".join(X_num.columns[:15]), "...")
        self.X_num, self.y, self.groups = X_num, y, groups
        return X_num, y, groups

    def split_data(self, test_size: float = 0.3) -> None:
        """Divide datos por estrella para evitar data leakage."""
        gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=self.seed)
        (train_idx, test_idx), = gss.split(self.X_num, self.y, groups=self.groups)

        self.X_train, self.X_test = self.X_num.iloc[train_idx], self.X_num.iloc[test_idx]
        self.y_train, self.y_test = self.y.iloc[train_idx], self.y.iloc[test_idx]
        self.groups_train, self.groups_test = self.groups.iloc[train_idx], self.groups.iloc[test_idx]

        print(f"[INFO] Train: {self.X_train.shape} | Test: {self.X_test.shape}")

    def train_model(self) -> None:
        """Entrena el modelo HistGradientBoostingClassifier."""
        self.pipe = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("hgb", HistGradientBoostingClassifier(
                learning_rate=self.learning_rate,
                max_leaf_nodes=self.max_leaf_nodes,
                min_samples_leaf=self.min_samples_leaf,
                early_stopping=self.early_stopping,
                random_state=self.seed
            ))
        ])
        self.pipe.fit(self.X_train, self.y_train)
        print("[INFO] Modelo entrenado correctamente")

    def evaluate(self) -> pd.DataFrame:
        """Evalúa el modelo y genera métricas."""
        self.y_pred = self.pipe.predict(self.X_test)
        labels = ["CANDIDATE", "CONFIRMED", "FALSE_POSITIVE"]

        print("\n=== Classification Report (HGB) ===")
        print(classification_report(self.y_test, self.y_pred, digits=3))

        cm = confusion_matrix(self.y_test, self.y_pred, labels=labels)
        cm_df = pd.DataFrame(cm,
                             index=[f"real_{l}" for l in labels],
                             columns=[f"pred_{l}" for l in labels])

        print("\n=== Confusion Matrix (rows=real, cols=pred) ===")
        print(cm_df)

        return cm_df

    def save_model(self, model_name: str = "hgb_exoplanet_model", version: Optional[str] = None) -> Dict[str, str]:
        """
        Guarda el modelo con versionado automático.
        """
        if self.pipe is None or self.y_test is None:
            raise RuntimeError("El modelo aún no ha sido entrenado o evaluado.")

        # Generar versión automáticamente si no se proporciona
        if version is None:
            version = self._generate_version(model_name)
        
        self.version = version

        # Rutas del modelo
        model_dir = settings.MODELS_DIR / model_name / version
        metrics_dir = model_dir / "metrics"
        matrix_dir = model_dir / "matrix"

        # Crear directorios
        model_dir.mkdir(parents=True, exist_ok=True)
        metrics_dir.mkdir(exist_ok=True)
        matrix_dir.mkdir(exist_ok=True)

        # Guardar modelo
        model_path = model_dir / "model.pkl"
        joblib.dump(self.pipe, model_path)

        # Guardar métricas
        metrics = classification_report(self.y_test, self.y_pred, output_dict=True)
        metrics_path = metrics_dir / "classification_report.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=4)

        # Guardar matriz de confusión
        cm = confusion_matrix(self.y_test, self.y_pred)
        matrix_path = matrix_dir / "confusion_matrix.npy"
        np.save(matrix_path, cm)

        # Crear/enlazar symlink latest
        latest_link = settings.MODELS_DIR / model_name / "latest"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(version)

        print(f"[INFO] Modelo guardado en: {model_path}")
        print(f"[INFO] Versión: {version}")

        return {
            "model_path": str(model_path),
            "metrics_path": str(metrics_path),
            "matrix_path": str(matrix_path),
            "version": version
        }

    def _generate_version(self, model_name: str) -> str:
        """Genera una nueva versión basada en las existentes."""
        model_dir = settings.MODELS_DIR / model_name
        if not model_dir.exists():
            return "v1.0.0"
        
        versions = [d.name for d in model_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
        if not versions:
            return "v1.0.0"
        
        # Extraer números de versión y incrementar
        latest_version = sorted(versions)[-1]
        version_parts = latest_version[1:].split(".")
        major, minor, patch = map(int, version_parts)
        
        # Incrementar patch
        patch += 1
        return f"v{major}.{minor}.{patch}"

    def load_model(self, model_name: str = "hgb_exoplanet_model", version: str = "latest") -> None:
        """Carga un modelo desde archivo."""
        model_path = settings.get_model_path(model_name, version)
        
        if model_path is None or not model_path.exists():
            raise FileNotFoundError(f"Modelo no encontrado: {model_path}")
        
        self.pipe = joblib.load(model_path)
        self.version = version
        
        # Cargar datos para tener X_num disponible
        if not hasattr(self, 'X_num'):
            self.load_data()
            self.prepare_features()
        
        print(f"[INFO] Modelo cargado: {model_path}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Realiza predicciones."""
        if self.pipe is None:
            raise RuntimeError("Modelo no cargado. Ejecuta load_model() primero.")
        
        # Asegurar que las columnas coincidan
        X_aligned = X.reindex(columns=self.X_num.columns, fill_value=0.0)
        return self.pipe.predict(X_aligned)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Realiza predicciones con probabilidades."""
        if self.pipe is None:
            raise RuntimeError("Modelo no cargado. Ejecuta load_model() primero.")
        
        # Asegurar que las columnas coincidan
        X_aligned = X.reindex(columns=self.X_num.columns, fill_value=0.0)
        return self.pipe.predict_proba(X_aligned)

    def get_hyperparameters(self) -> Dict[str, Any]:
        """Obtiene hiperparámetros actuales."""
        return {
            "learning_rate": self.learning_rate,
            "max_leaf_nodes": self.max_leaf_nodes,
            "min_samples_leaf": self.min_samples_leaf,
            "early_stopping": self.early_stopping
        }

    def run(self) -> None:
        """Pipeline completo de entrenamiento."""
        self.load_data()
        self.prepare_features()
        self.split_data()
        self.train_model()
        self.evaluate()
        self.save_model()
