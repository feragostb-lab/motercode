"""
Test para verificar normalización de importes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal
from src.utils.formatters import normalizar_monto


def test_normalizar_monto():
    """Probar normalización de importes con diferentes formatos."""
    
    print("\n" + "=" * 60)
    print("TEST: Normalización de importes")
    print("=" * 60)
    
    test_cases = [
        # (input, expected_output)
        ("9.60", Decimal("9.60")),
        ("9,60", Decimal("9.60")),
        ("1.234,56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        ("€9.60", Decimal("9.60")),
        ("€9,60", Decimal("9.60")),
        ("9.60€", Decimal("9.60")),
        ("9,60€", Decimal("9.60")),
        (9.60, Decimal("9.60")),
        (9, Decimal("9")),
        ("", None),
        (None, None),
    ]
    
    passed = 0
    failed = 0
    
    for input_val, expected in test_cases:
        result = normalizar_monto(input_val)
        
        if result == expected:
            print(f"✅ PASS: {repr(input_val):20s} -> {result}")
            passed += 1
        else:
            print(f"❌ FAIL: {repr(input_val):20s} -> {result} (esperado: {expected})")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESUMEN: {passed} pasados, {failed} fallidos")
    print("=" * 60)
    
    return failed == 0


def test_decimal_to_string():
    """Probar conversión de Decimal a string."""
    
    print("\n" + "=" * 60)
    print("TEST: Conversión de Decimal a String")
    print("=" * 60)
    
    test_cases = [
        Decimal("9.60"),
        Decimal("9.6"),
        Decimal("1234.56"),
        Decimal("0.99"),
        Decimal("100"),
    ]
    
    for dec_val in test_cases:
        str_val = str(dec_val)
        print(f"  Decimal({dec_val}) -> '{str_val}'")
        
        # Verificar que no contenga comas
        if ',' in str_val:
            print(f"    ❌ ERROR: Contiene coma!")
            return False
        else:
            print(f"    ✅ OK: Usa punto decimal")
    
    print("\n" + "=" * 60)
    print("✅ Todos los Decimals se convierten con punto decimal")
    print("=" * 60)
    
    return True


def main():
    """Ejecutar todos los tests."""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE NORMALIZACIÓN DE IMPORTES")
    print("=" * 60)
    
    test1_ok = test_normalizar_monto()
    test2_ok = test_decimal_to_string()
    
    print("\n" + "=" * 60)
    print("RESULTADO FINAL")
    print("=" * 60)
    
    if test1_ok and test2_ok:
        print("✅ TODOS LOS TESTS PASARON")
        print("\nLos importes se normalizarán correctamente:")
        print("  - Entrada: Acepta tanto '9.60' como '9,60'")
        print("  - Procesamiento: Convierte a Decimal internamente")
        print("  - Salida: Siempre usa punto decimal '9.60'")
        print("  - Base de datos: Almacena con punto decimal")
        return 0
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        return 1


if __name__ == '__main__':
    exit(main())
