#!/usr/bin/env python3
"""
Simple test script to verify the application works
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all imports work"""
    try:
        from API.main import app
        print("✅ API.main import successful")
        
        from src.models.hgb_exoplanet import HGBExoplanetModel
        print("✅ HGBExoplanetModel import successful")
        
        from src.utils.config import settings
        print("✅ Settings import successful")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_model_loading():
    """Test that the model can be loaded"""
    try:
        from src.models.hgb_exoplanet import HGBExoplanetModel
        
        model = HGBExoplanetModel()
        print("✅ Model initialization successful")
        
        # Check if dataset exists
        dataset_path = Path("datasets/kepler.csv")
        if dataset_path.exists():
            print("✅ Dataset file exists")
        else:
            print("❌ Dataset file not found")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Model loading error: {e}")
        return False

def test_fastapi_app():
    """Test that FastAPI app can be created"""
    try:
        from API.main import app
        print("✅ FastAPI app creation successful")
        return True
    except Exception as e:
        print(f"❌ FastAPI app error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing application components...")
    print()
    
    tests = [
        ("Import Test", test_imports),
        ("Model Loading Test", test_model_loading),
        ("FastAPI App Test", test_fastapi_app)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        result = test_func()
        results.append(result)
        print()
    
    if all(results):
        print("🎉 All tests passed! Application should work correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Check the errors above.")
        sys.exit(1)
