"""
ROC Skincare - Quick Start Setup Script
Initializes database with ROC-specific extensions
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_config
from src.core.database import get_database
from src.services.worker_service import WorkerService


def setup_rocskincare():
    """Initialize ROC Skincare environment."""
    print("=" * 60)
    print("ROC SKINCARE - CONFIGURACIÓN INICIAL")
    print("=" * 60)
    print()
    
    # Load config
    print("📋 Cargando configuración...")
    config = get_config()
    
    # Initialize database (get_database already creates tables via _ensure_database_exists)
    print("🗄️  Inicializando base de datos...")
    db = get_database(config.paths.get('database'))
    print("   ✅ Base de datos inicializada")
    
    # Create base directories
    print()
    print("📁 Creando estructura de directorios...")
    
    directories = [
        './workers',
        './img',
        './result',
        './exports',
        './models',
        './temp',
        './logs',
        './backups'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")
    
    # Offer to create sample worker
    print()
    print("=" * 60)
    print("¿Deseas crear un trabajador de prueba?")
    print("=" * 60)
    
    create_sample = input("Crear trabajador 'demo' (s/n): ").strip().lower()
    
    if create_sample == 's':
        try:
            worker_service = WorkerService(config)
            worker = worker_service.create_worker('demo')
            print(f"   ✅ Trabajador 'demo' creado (ID: {worker.id})")
            print(f"   📁 Directorio: ./workers/demo/")
        except ValueError as e:
            print(f"   ⚠️  {e}")
    
    # Summary
    print()
    print("=" * 60)
    print("✅ CONFIGURACIÓN COMPLETADA")
    print("=" * 60)
    print()
    print("🚀 Siguiente paso:")
    print("   streamlit run app_rocskincare.py")
    print()
    print("📖 Lee README_ROCSKINCARE.md para guía completa de uso")
    print()


if __name__ == "__main__":
    setup_rocskincare()
