"""
Script principal para ejecutar la aplicación.
"""
import sys
from pathlib import Path

# Agregar src al path para imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    import uvicorn
    from API.main import app
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
