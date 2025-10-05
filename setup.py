from setuptools import setup, find_packages

setup(
    name="exoplanetas-api",
    version="1.0.0",
    description="FastAPI application for exoplanet classification",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.0",
        "joblib>=1.3.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "python-dotenv>=1.0.0",
        "scikit-learn>=1.3.0",
        "uvicorn>=0.24.0",
    ],
)
