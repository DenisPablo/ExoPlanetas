# hgb_exoplanets.py
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix
import json
import joblib

class HGBExoplanetModel:
    """
    Entrena y evalúa un modelo HistGradientBoostingClassifier sobre datos KOI.
    Controla fugas de información y separa por estrella (kepid).
    """

    def __init__(self, csv_path, target="koi_disposition", group_col="kepid", seed=42,
                 learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=20, early_stopping=True):
        self.csv_path = csv_path
        self.target = target
        self.group_col = group_col
        self.seed = seed

        # --- Hiperparámetros expuestos ---
        self.learning_rate = learning_rate
        self.max_leaf_nodes = max_leaf_nodes
        self.min_samples_leaf = min_samples_leaf
        self.early_stopping = early_stopping

        self.model = None
        self.pipe = None
        self.X_train = self.X_test = None
        self.y_train = self.y_test = None
        self.groups_train = self.groups_test = None
        self.comparison = None

    # ------------------- 1) Carga -------------------
    def load_data(self):
        df = pd.read_csv(self.csv_path, comment="#")
        assert self.target in df.columns, f"Falta la columna objetivo {self.target}"
        assert self.group_col in df.columns, f"Falta {self.group_col} para agrupar por estrella"
        self.df = df
        print(f"[INFO] Dataset cargado: {len(df):,} filas")
        return df

    # ------------------- 2) Selección de features -------------------
    def prepare_features(self):
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
        groups = df[self.group_col].copy()

        print(f"[INFO] Features finales: {X_num.shape[1]} columnas")
        print("[INFO] Ejemplo de columnas:", ", ".join(X_num.columns[:15]), "...")
        self.X_num, self.y, self.groups = X_num, y, groups
        return X_num, y, groups

    # ------------------- 3) Split por estrella -------------------
    def split_data(self, test_size=0.3):
        gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=self.seed)
        (train_idx, test_idx), = gss.split(self.X_num, self.y, groups=self.groups)

        self.X_train, self.X_test = self.X_num.iloc[train_idx], self.X_num.iloc[test_idx]
        self.y_train, self.y_test = self.y.iloc[train_idx], self.y.iloc[test_idx]
        self.groups_train, self.groups_test = self.groups.iloc[train_idx], self.groups.iloc[test_idx]

        print(f"[INFO] Train: {self.X_train.shape} | Test: {self.X_test.shape}")

    # ------------------- 4) Entrenamiento -------------------
    def train_model(self):
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

    # ------------------- 5) Evaluación -------------------
    def evaluate(self):
        y_pred = self.pipe.predict(self.X_test)
        labels = ["CANDIDATE", "CONFIRMED", "FALSE POSITIVE"]

        print("\n=== Classification Report (HGB) ===")
        print(classification_report(self.y_test, y_pred, digits=3))

        cm = confusion_matrix(self.y_test, y_pred, labels=labels)
        cm_df = pd.DataFrame(cm,
                             index=[f"real_{l}" for l in labels],
                             columns=[f"pred_{l}" for l in labels]
                             )

        print("\n=== Confusion Matrix (rows=real, cols=pred) ===")
        print(cm_df)

        self.y_pred = y_pred
        return cm_df

    # ------------------- 6) Guardado de resultados -------------------
    def save_comparison(self, output_path="comparison_nasa_vs_model_hgb.csv"):
        comparison = self.X_test.copy()
        comparison[self.group_col] = self.groups_test.values
        comparison["true_disposition"] = self.y_test.values
        comparison["predicted_disposition"] = self.y_pred
        comparison["correct"] = comparison["true_disposition"] == comparison["predicted_disposition"]

        comparison.to_csv(output_path, index=False)
        print(f"\n[INFO] Guardado: {output_path}")
        self.comparison = comparison

    # ------------------- 7) Resumen de errores -------------------
    def error_summary(self):
        if self.comparison is None:
            raise RuntimeError("Debes ejecutar save_comparison() antes de obtener el resumen.")
        errors = self.comparison[~self.comparison["correct"]]
        if errors.empty:
            print("Sin errores 😊")
            return pd.DataFrame()
        error_summary = (errors.groupby(["true_disposition", "predicted_disposition"])
                         .size().reset_index(name="count")
                         .sort_values("count", ascending=False))
        print("\n=== Errores más comunes (true → predicted) ===")
        print(error_summary)
        return error_summary

    # ------------------- 8) Obtener hiperparámetros actuales -------------------
    def get_hyperparameters(self):
        return {
            "learning_rate": self.learning_rate,
            "max_leaf_nodes": self.max_leaf_nodes,
            "min_samples_leaf": self.min_samples_leaf,
            "early_stopping": self.early_stopping
        }

    # ------------------- 9) Pipeline completo -------------------
    def run(self):
        self.load_data()
        self.prepare_features()
        self.split_data()
        self.train_model()
        self.evaluate()
        self.save_comparison()
        self.error_summary()

    # ------------------- 10) Guardar modelo, métricas y matriz -------------------
    def save_model(self, model_name="hgb_exoplanet_model"):
        """
        Guarda el modelo entrenado, las métricas y la matriz de confusión en:
        models/<model_name>/{model.pkl, metrics/..., matrix/...}
        """
        if self.pipe is None or self.y_test is None:
            raise RuntimeError("El modelo aún no ha sido entrenado o evaluado. Ejecuta run() o evaluate() primero.")

        # --- Rutas base ---
        base_dir = os.path.join("models", model_name)
        metrics_dir = os.path.join(base_dir, "metrics")
        matrix_dir = os.path.join(base_dir, "matrix")

        # --- Crear carpetas ---
        os.makedirs(metrics_dir, exist_ok=True)
        os.makedirs(matrix_dir, exist_ok=True)

        # --- Guardar modelo ---
        model_path = os.path.join(base_dir, f"{model_name}.pkl")
        joblib.dump(self.pipe, model_path)

        # --- Guardar métricas ---
        y_pred = getattr(self, "y_pred", None)
        if y_pred is None:
            y_pred = self.pipe.predict(self.X_test)
            self.y_pred = y_pred

        metrics = classification_report(self.y_test, y_pred, output_dict=True)
        metrics_path = os.path.join(metrics_dir, "classification_report.json")
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=4)

        # --- Guardar matriz de confusión ---
        cm = confusion_matrix(self.y_test, y_pred)
        matrix_path = os.path.join(matrix_dir, "confusion_matrix.npy")
        np.save(matrix_path, cm)

        print(f"[INFO] Modelo guardado en: {model_path}")
        print(f"[INFO] Métricas guardadas en: {metrics_path}")
        print(f"[INFO] Matriz de confusión guardada en: {matrix_path}")

        return {
            "model_path": model_path,
            "metrics_path": metrics_path,
            "matrix_path": matrix_path
        }

# ------------------- Uso -------------------
if __name__ == "__main__":
    model = HGBExoplanetModel("datasets/kepler.csv")
    model.load_data()
    model.prepare_features()
    model.split_data()
    model.train_model()
    model.evaluate()
    model.save_model()