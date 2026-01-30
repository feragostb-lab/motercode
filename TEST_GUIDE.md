# Test Suite Guide

## Overview

El sistema incluye una suite completa de tests automatizados usando **pytest** con cobertura de código.

## 📁 Estructura de Tests

```
tests/
├── conftest.py                    # Fixtures y configuración pytest
├── unit/                          # Tests unitarios (rápidos, aislados)
│   ├── test_bank_matching_service.py
│   ├── test_conflict_resolution.py
│   ├── test_export_service.py
│   ├── test_queue_service.py
│   ├── test_receipt_service.py
│   └── test_statistics_service.py
├── integration/                   # Tests de integración
│   └── test_repositories.py
└── test_amount_normalization.py   # Tests funcionales

old/                               # Scripts de test legacy/manual
├── test_receipt_processing.py     # Test manual E2E con OCR real
├── test_transaction_id_preservation.py
├── test_csv_reload_ids.py
└── test_excel_row_numbers.py

pytest.ini                         # Configuración pytest
run_tests.bat                      # Ejecutor principal de tests
```

## 🚀 Ejecución de Tests

### Opción 1: Usando el script (Recomendado)

```batch
.\run_tests.bat
```

Este script:
- ✅ Activa el entorno virtual
- ✅ Verifica dependencias
- ✅ Ejecuta toda la suite pytest
- ✅ Genera reporte de cobertura en `htmlcov/`

### Opción 2: Pytest directo

```bash
# Todos los tests
pytest

# Solo tests unitarios
pytest tests/unit/

# Solo tests de integración
pytest tests/integration/

# Con verbose y sin cobertura
pytest -v --no-cov

# Un archivo específico
pytest tests/unit/test_bank_matching_service.py

# Un test específico
pytest tests/unit/test_bank_matching_service.py::test_exact_match
```

### Opción 3: Tests manuales/legacy

Estos scripts están en `old/` y son útiles para validaciones específicas:

```bash
# Test manual E2E con OCR real (requiere imágenes)
python old/test_receipt_processing.py

# Validación de IDs de transacciones
python old/test_transaction_id_preservation.py
python old/test_csv_reload_ids.py
python old/test_excel_row_numbers.py
```

## 📊 Cobertura de Tests

La suite pytest incluye tests para:

### ✅ Servicios (Unit Tests)
- **BankMatchingService**: Matching de recibos con transacciones
  - Match exacto por fecha y monto
  - Match parcial (solo fecha o solo monto)
  - Detección de conflictos
  - Resolución de conflictos
  
- **ReceiptService**: Gestión de recibos
  - Creación y actualización
  - Marcado como ignorados
  - Filtros y búsquedas
  
- **QueueService**: Cola de procesamiento
  - Encolado de items
  - Actualización de estados
  - Estadísticas
  
- **StatisticsService**: Métricas y estadísticas
  - Conteos por tipo
  - Tasas de éxito
  - Distribuciones
  
- **ExportService**: Exportación de datos
  - Exportación a Excel/CSV
  - Múltiples formatos

### ✅ Repositorios (Integration Tests)
- CRUD operations
- Consultas complejas
- Integridad de datos

### ✅ Funcionalidad
- Normalización de importes
- Manejo de conflictos
- Comportamiento con items ignorados

## 📈 Reporte de Cobertura

Después de ejecutar los tests, se genera un reporte HTML:

```bash
# Ver el reporte de cobertura
start htmlcov\index.html  # Windows
open htmlcov/index.html   # Mac
xdg-open htmlcov/index.html  # Linux
```

El reporte muestra:
- 📊 Porcentaje de cobertura por módulo
- 🔍 Líneas cubiertas/no cubiertas
- 📝 Funciones testeadas
- ⚠️ Código sin tests

## 🎯 Mejores Prácticas

### Escribir nuevos tests

```python
import pytest
from src.services.my_service import MyService

class TestMyService:
    """Tests para MyService."""
    
    def test_something(self, test_config):
        """Test description."""
        service = MyService(test_config)
        result = service.do_something()
        assert result == expected
```

### Usar fixtures

Los fixtures comunes están en `tests/conftest.py`:
- `test_db`: Base de datos temporal
- `test_config`: Configuración de test
- `temp_dir`: Directorio temporal

### Marcar tests

```python
@pytest.mark.unit
def test_unit():
    pass

@pytest.mark.integration
def test_integration():
    pass

@pytest.mark.slow
def test_slow_operation():
    pass
```

## 🔧 Troubleshooting

### "ModuleNotFoundError"
```bash
# Asegúrate de estar en el entorno virtual
.venv\Scripts\activate
```

### "No module named pytest"
```bash
pip install pytest pytest-cov
```

### Tests fallan por base de datos
```bash
# Los tests usan bases de datos temporales
# Si hay problemas, verifica que test_db fixture funcione
pytest tests/conftest.py -v
```

### Ver más detalles
```bash
# Más verbose
pytest -vv

# Mostrar print statements
pytest -s

# Modo debug
pytest --pdb
```

## 📝 Tests Legacy/Manual

Los scripts en `old/` son útiles para casos específicos:

### test_receipt_processing.py
Test manual END-TO-END que:
- Carga el modelo VLM real
- Procesa imágenes de `tests/receipt_test_examples/`
- Genera logs detallados
- Útil para demos y debugging

**Cuándo usar**: Validar pipeline completo con OCR real

**Requisitos**: 
- Imágenes de recibos en `tests/receipt_test_examples/`
- Modelo VLM descargado en `models/`

### test_transaction_id_preservation.py
Valida que IDs de transacciones se preserven correctamente.

**Cuándo usar**: Validar comportamiento de IDs tras cambios en CSV loading

### test_csv_reload_ids.py
Valida múltiples cargas de CSV.

**Cuándo usar**: Verificar que IDs se reasignen correctamente

### test_excel_row_numbers.py
Simula carga de Excel con skiprows=13.

**Cuándo usar**: Validar casos específicos de formato Excel

---

## 📋 Ejemplo: Salida de pytest

```
================== test session starts ==================
platform win32 -- Python 3.11.0, pytest-7.4.3
collected 45 items

tests/unit/test_bank_matching_service.py ........  [ 17%]
tests/unit/test_conflict_resolution.py ....      [ 26%]
tests/unit/test_export_service.py .....          [ 37%]
tests/unit/test_queue_service.py ......          [ 50%]
tests/unit/test_receipt_service.py ......        [ 63%]
tests/unit/test_statistics_service.py .......    [ 78%]
tests/integration/test_repositories.py .....     [ 89%]
tests/test_amount_normalization.py .....         [100%]

---------- coverage: platform win32 ----------
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
src/core/config.py                         45      2    96%
src/core/database.py                       38      1    97%
src/models/domain.py                       65      0   100%
src/repositories/bank_repository.py        89      3    97%
src/repositories/receipt_repository.py     95      4    96%
src/services/bank_matching_service.py     156      8    95%
src/services/export_service.py             78      5    94%
src/services/queue_service.py              67      2    97%
src/services/receipt_service.py            84      6    93%
src/services/statistics_service.py        112      7    94%
-----------------------------------------------------------
TOTAL                                     829     38    95%

Coverage HTML written to htmlcov/index.html

=============== 45 passed in 12.34s ================
```

## 🎓 Recursos

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-cov Plugin](https://pytest-cov.readthedocs.io/)
- Coverage Report: `htmlcov/index.html` (después de ejecutar tests)
- Project README: [README.md](README.md)
