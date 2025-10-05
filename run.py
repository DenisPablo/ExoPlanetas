"""
Script principal para ejecutar la aplicación.
"""
import sys
from pathlib import Path

# Agregar src al path para imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    import os
    import uvicorn
    from API.main import app
    
    # Usar el puerto de Render o 8000 por defecto
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
