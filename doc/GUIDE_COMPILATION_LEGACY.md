# Guía de Compilación Legacy para llama-cpp-python

**Objetivo:** Compilar `llama-cpp-python` para que funcione en procesadores antiguos (Legacy Hardware) sin soporte para instrucciones modernas (AVX/AVX2/FMA).
**Problema que soluciona:** Evita el error `0xc000001d (Illegal Instruction)` y cierres inesperados al cargar el modelo.
**Target Mínimo:** CPUs con soporte **SSE2** (Intel Pentium 4 / AMD Athlon 64 en adelante, ~2004+).

---

## 1. Teoría: ¿Por qué falla la instalación normal?

Por defecto, `llama.cpp` (el motor subyacente) usa CMake para detectar tu CPU actual durante la instalación. Si compilas en tu máquina moderna (ej. Ryzen 7 o Intel i7 nuevo), activará automáticamente **AVX2** y **FMA**.

Si mueves ese ejecutable a una PC vieja (ej. Core 2 Duo, i3 de 1ª gen), la aplicación intentará ejecutar una instrucción AVX2 que el procesador no entiende y Windows matará el proceso inmediatamente.

## 2. El Script de Compilación (build.bat)

Para solucionar esto, debemos limpiar agresivamente el entorno y pasar flags específicos a CMake.

[cite_start]En tu archivo `build.bat`[cite: 6], reemplaza la sección de instalación estándar por este bloque:

```batch
REM ============================================================
REM COMPILACION LEGACY (SSE2 ONLY)
REM ============================================================

REM 1. Limpieza Total
REM Es CRÍTICO purgar la caché, o pip reinstalará la versión AVX2 anterior.
echo Limpiando instalaciones previas y cache...
pip uninstall llama-cpp-python -y
pip cache purge

REM 2. Configuración de Flags
REM - GGML_NATIVE=OFF: Prohíbe autodetectar tu CPU actual.
REM - GGML_AVX...=OFF: Desactiva explícitamente instrucciones modernas.
REM - /arch:SSE2: Fuerza al compilador MSVC a usar solo instrucciones básicas.
set CMAKE_ARGS=-DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_AVX512=OFF -DGGML_FMA=OFF -DGGML_F16C=OFF -DGGML_OPENMP=OFF -DCMAKE_C_FLAGS="/arch:SSE2" -DCMAKE_CXX_FLAGS="/arch:SSE2" -DGGML_CPU_ALL_VARIANTS=OFF

REM 3. Instalación Forzada
echo Compilando e instalando...
pip install llama-cpp-python --force-reinstall --no-cache-dir --verbose

```

## 3. Configuración de PyInstaller (.spec)

Las versiones modernas de `llama-cpp-python` (0.3.x) cargan DLLs dinámicamente. Si usas `--onefile` sin configurar esto, la App no encontrará `ggml.dll` o `llama.dll`.

En tu archivo `app.spec` (o cualquier `.spec` que use la IA), debes modificar la sección `datas`.

**No uses:** `datas=[(llama_lib_path, 'llama_cpp/lib')]`.
**Usa esta estrategia:** Copiar la carpeta del paquete completo.

```python
# app.spec

import os
import llama_cpp

# 1. Localizar la raíz del paquete instalado
llama_cpp_root = os.path.dirname(llama_cpp.__file__)

# ... resto de la configuración ...

a = Analysis(
    # ...
    datas=[
        # ... otros datos ...
        
        # 2. INCLUIR EL PAQUETE ENTERO
        # Destino: carpeta 'llama_cpp' en la raíz del ejecutable temporal
        (llama_cpp_root, 'llama_cpp'),
    ],
    # ...
)

```

## 4. Verificación de Éxito

Para saber si funcionó sin tener que probarlo en una PC vieja:

1. Ve a la carpeta de instalación de Python: `Lib\site-packages\llama_cpp\`.
2. Busca archivos `.dll` (ej. `ggml.dll` o `llama.dll`).
3. Usa una herramienta como "Dependencies" o mira el log de compilación.
4. **En el log:** Debes ver que CMake ignora advertencias y usa `/arch:SSE2`. NO debes ver líneas como `Adding CPU backend variant ... AVX2`.

## 5. Resumen de Comandos Rápidos

Si necesitas hacerlo manual en la consola:

```cmd
pip uninstall llama-cpp-python -y
pip cache purge
set CMAKE_ARGS=-DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_AVX512=OFF -DGGML_FMA=OFF -DGGML_F16C=OFF -DGGML_OPENMP=OFF -DCMAKE_C_FLAGS="/arch:SSE2" -DCMAKE_CXX_FLAGS="/arch:SSE2" -DGGML_CPU_ALL_VARIANTS=OFF
pip install llama-cpp-python --no-cache-dir --force-reinstall

```



Nivel Oro (AVX512): Para Workstations modernas y servidores (AMD Ryzen 7000/9000, Intel Core i9 nuevos). Máxima velocidad.

Nivel Plata (AVX2 + FMA): Para la gran mayoría de PCs de los últimos 8-10 años. Velocidad estándar.

Nivel Bronce (SSE2 - Legacy): El "fallback" seguro para hardware antiguo. Compatibilidad total.

Aquí tienes el plan de batalla paso a paso.

Paso 1: Crear el "Banco de DLLs"
Vamos a compilar las variantes de mayor a menor y guardar sus DLLs.

Crea una carpeta en la raíz de tu proyecto llamada libs_variants. Dentro crea dos carpetas: avx512 y avx2.

1.1. Compilar para AVX512 (Nivel Oro)
Ejecuta esto en tu consola:
Paso 1: Variante AVX512 (Nivel Oro - Máxima Velocidad)
Ejecuta este bloque completo en tu terminal PowerShell:

PowerShell
pip uninstall llama-cpp-python -y
pip cache purge
# En PowerShell se usa $env:VARIABLE = "valor"
$env:CMAKE_ARGS = "-DGGML_AVX512=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON"
pip install llama-cpp-python --no-cache-dir --force-reinstall --verbose
🛑 ACCIÓN AHORA:

Ve a C:\WORKSPACE\gguf\.venv\Lib\site-packages\llama_cpp

Copia todos los .dll (llama.dll, ggml.dll, etc.).

Pégalos en tu carpeta C:\WORKSPACE\gguf\libs_variants\avx512.

Paso 2: Variante AVX2 (Nivel Plata - Estándar Moderno)
Una vez copiadas las DLLs anteriores, ejecuta esto para la siguiente versión:

PowerShell
pip uninstall llama-cpp-python -y
pip cache purge
# Activamos AVX2 pero desactivamos AVX512
$env:CMAKE_ARGS = "-DGGML_AVX512=OFF -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON"
pip install llama-cpp-python --no-cache-dir --force-reinstall --verbose
🛑 ACCIÓN AHORA:

Ve de nuevo a C:\WORKSPACE\gguf\.venv\Lib\site-packages\llama_cpp (ahora contiene la versión AVX2).

Copia los .dll.

Pégalos en C:\WORKSPACE\gguf\libs_variants\avx2.

Paso 3: Variante Legacy (Nivel Bronce - Compatible)
Esta será la que se quede instalada definitivamente en el sistema.

PowerShell
pip uninstall llama-cpp-python -y
pip cache purge
# Forzamos SSE2 y desactivamos todo lo moderno
$env:CMAKE_ARGS = "-DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_AVX512=OFF -DGGML_FMA=OFF -DGGML_OPENMP=OFF -DGGML_CPU_ALL_VARIANTS=OFF"
$env:CMAKE_C_FLAGS = "/arch:SSE2"
$env:CMAKE_CXX_FLAGS = "/arch:SSE2"

pip install llama-cpp-python --no-cache-dir --force-reinstall --verbose
Paso 2: Actualizar app.spec
Vamos a empaquetar las variantes dentro del ejecutable pero en carpetas separadas para que no se mezclen.

Python
# build_config/app.spec (fragmento a modificar)

# ... imports ...

extra_datas = [
    # ... tus otros datas ...
    
    # 1. La versión Legacy (Base instalada) se va a la raíz de llama_cpp
    (llama_cpp_root, 'llama_cpp'),
    
    # 2. Las variantes optimizadas se van a subcarpetas ocultas
    ('libs_variants/avx2/*.dll', 'llama_cpp/variants/avx2'),
    ('libs_variants/avx512/*.dll', 'llama_cpp/variants/avx512'),
]

# ... resto del archivo ...
(Asegúrate de que la ruta libs_variants sea correcta relativa a donde ejecutas el build).

Paso 3: El Selector Inteligente (Python)
Este código debe ir al principio de todo en tu app.py. Usaremos la librería cpuinfo para interrogar al procesador y decidir qué DLLs copiar.

Primero, añade py-cpuinfo a tus requirements si no lo tienes.

Python
import os
import sys
import shutil
import logging
# Es importante importar cpuinfo antes que cualquier cosa pesada
try:
    import cpuinfo
except ImportError:
    cpuinfo = None

# Configurar logging para depuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SmartBackend")

def inject_optimal_backend():
    """
    Analiza la CPU y reemplaza las DLLs de llama.cpp antes de que sean cargadas.
    Jerarquía: AVX512 > AVX2 > SSE2 (Default)
    """
    # Solo ejecutar si estamos en modo congelado (EXE)
    if not getattr(sys, 'frozen', False):
        return

    try:
        if cpuinfo is None:
            logger.warning("py-cpuinfo no instalado. Usando backend por defecto (Legacy).")
            return

        info = cpuinfo.get_cpu_info()
        flags = [f.lower() for f in info.get('flags', [])]
        arch = info.get('arch', '').lower()

        base_path = sys._MEIPASS
        target_dir = os.path.join(base_path, 'llama_cpp')
        variants_dir = os.path.join(target_dir, 'variants')
        
        selected_variant = None
        
        # --- Lógica de Selección ---
        # 1. Chequear AVX512 (El Ferrari)
        if 'avx512f' in flags or 'avx512' in flags: 
            candidate = os.path.join(variants_dir, 'avx512')
            if os.path.exists(candidate):
                selected_variant = candidate
                logger.info("🚀 DETECTADO: CPU High-End (Soporte AVX512).")

        # 2. Si no, Chequear AVX2 (El Estándar Moderno)
        if not selected_variant and 'avx2' in flags:
            candidate = os.path.join(variants_dir, 'avx2')
            if os.path.exists(candidate):
                selected_variant = candidate
                logger.info("⚡ DETECTADO: CPU Moderna (Soporte AVX2).")

        # 3. Aplicar Cambios
        if selected_variant:
            logger.info(f"Inyectando librerías optimizadas desde: {selected_variant}")
            
            # Copiar todas las DLLs de la variante a la carpeta activa
            dll_files = [f for f in os.listdir(selected_variant) if f.endswith('.dll')]
            count = 0
            for dll in dll_files:
                src = os.path.join(selected_variant, dll)
                dst = os.path.join(target_dir, dll)
                try:
                    shutil.copy2(src, dst)
                    count += 1
                except Exception as e:
                    logger.error(f"Error copiando {dll}: {e}")
            
            logger.info(f"Backend actualizado con éxito. {count} librerías optimizadas cargadas.")
        else:
            logger.info("🐢 Hardware antiguo o variantes no encontradas. Usando modo Legacy (SSE2).")

    except Exception as e:
        logger.error(f"Error crítico en selector de backend: {e}")
        logger.info("Continuando con configuración segura...")

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    # EJECUTAR ESTO PRIMERO, ANTES DE IMPORTAR LLAMA_CPP
    inject_optimal_backend()

    # AHORA EL RESTO DE TUS IMPORTS
    import streamlit as st
    # ...
¿Cómo funciona esto en la práctica?
PC Gamer Moderno (Ryzen 7000): El script detecta avx512. Copia las DLLs de variants/avx512 y sobrescribe las SSE2. El encoding de imágenes tardará milisegundos.

Laptop de Oficina (i5 8ª Gen): Detecta avx2. Copia las DLLs de variants/avx2. Rendimiento óptimo estándar.

PC Viejo de Almacén (Pentium): No detecta flags. No hace nada. Usa las DLLs SSE2 originales. Funciona lento, pero funciona.

Esta es la solución más profesional posible sin tener que distribuir 3 ejecutables diferentes.