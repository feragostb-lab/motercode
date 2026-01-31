"""Test para verificar que los importes siempre usan punto como separador decimal."""
import sys
from pathlib import Path
from decimal import Decimal

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.formatters import normalizar_monto, formatear_monto


def test_normalizar_monto():
    """Verificar que normalizar_monto convierte correctamente ambos formatos."""
    print("\n=== TEST: normalizar_monto ===")
    
    casos = [
        ("9,60", Decimal("9.60")),
        ("9.60", Decimal("9.60")),
        ("1.234,56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        ("€9.60", Decimal("9.60")),
        ("€9,60", Decimal("9.60")),
        ("15,50", Decimal("15.50")),
    ]
    
    for entrada, esperado in casos:
        resultado = normalizar_monto(entrada)
        exito = "✓" if resultado == esperado else "✗"
        print(f"{exito} '{entrada}' -> {resultado} (esperado: {esperado})")
        assert resultado == esperado, f"Falló para {entrada}: obtuvo {resultado}, esperaba {esperado}"
    
    print("✓ Todos los casos pasaron")


def test_formatear_monto():
    """Verificar que formatear_monto siempre usa punto como separador decimal."""
    print("\n=== TEST: formatear_monto ===")
    
    casos = [
        (Decimal("9.60"), "9.60€"),
        (Decimal("9.5"), "9.50€"),
        (Decimal("1234.56"), "1234.56€"),
        (Decimal("0.99"), "0.99€"),
        (Decimal("15.50"), "15.50€"),
    ]
    
    for entrada, esperado in casos:
        resultado = formatear_monto(entrada)
        exito = "✓" if resultado == esperado else "✗"
        print(f"{exito} {entrada} -> '{resultado}' (esperado: '{esperado}')")
        assert resultado == esperado, f"Falló para {entrada}: obtuvo '{resultado}', esperaba '{esperado}'"
        # Verificar que SIEMPRE contiene punto y NUNCA coma
        assert '.' in resultado, f"El resultado '{resultado}' debería contener punto"
        assert ',' not in resultado, f"El resultado '{resultado}' NO debería contener coma"
    
    print("✓ Todos los casos pasaron - siempre usa punto (.)")


def test_ciclo_completo():
    """Verificar ciclo completo: entrada con coma -> normalización -> formateo con punto."""
    print("\n=== TEST: Ciclo completo ===")
    
    # Simular entrada de usuario con coma (formato europeo)
    entrada_usuario = "15,50"
    print(f"Entrada usuario: '{entrada_usuario}'")
    
    # Normalizar (convertir a Decimal interno)
    valor_normalizado = normalizar_monto(entrada_usuario)
    print(f"Normalizado: {valor_normalizado} (tipo: {type(valor_normalizado).__name__})")
    
    # Formatear para mostrar
    valor_formateado = formatear_monto(valor_normalizado)
    print(f"Formateado: '{valor_formateado}'")
    
    # Verificar que el valor formateado usa punto
    assert '.' in valor_formateado, "El valor formateado debe usar punto"
    assert ',' not in valor_formateado, "El valor formateado NO debe usar coma"
    assert valor_formateado == "15.50€", f"Esperaba '15.50€', obtuvo '{valor_formateado}'"
    
    print("✓ Ciclo completo exitoso: entrada con coma -> salida con punto")


def test_almacenamiento_db():
    """Verificar que al convertir Decimal a string se usa punto."""
    print("\n=== TEST: Almacenamiento DB ===")
    
    valores = [
        Decimal("9.60"),
        Decimal("15.50"),
        Decimal("1234.56"),
    ]
    
    for valor in valores:
        # Simular cómo se guarda en la DB
        valor_db = str(valor)
        print(f"Decimal {valor} -> DB: '{valor_db}'")
        
        # Verificar que usa punto
        assert '.' in valor_db, f"El valor en DB '{valor_db}' debe usar punto"
        assert ',' not in valor_db, f"El valor en DB '{valor_db}' NO debe usar coma"
    
    print("✓ Almacenamiento en DB siempre usa punto")


if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICACIÓN DE FORMATO DECIMAL CON PUNTO (.)")
    print("=" * 60)
    
    try:
        test_normalizar_monto()
        test_formatear_monto()
        test_ciclo_completo()
        test_almacenamiento_db()
        
        print("\n" + "=" * 60)
        print("✓✓✓ TODOS LOS TESTS PASARON ✓✓✓")
        print("=" * 60)
        print("\nCONCLUSIÓN:")
        print("- Los importes se normalizan correctamente desde cualquier formato")
        print("- Los importes se ALMACENAN en DB con PUNTO (.) como separador")
        print("- Los importes se MUESTRAN con PUNTO (.) como separador")
        print("- No hay ambigüedad: el sistema usa SIEMPRE punto (.)")
        
    except AssertionError as e:
        print(f"\n✗ TEST FALLÓ: {e}")
        sys.exit(1)
