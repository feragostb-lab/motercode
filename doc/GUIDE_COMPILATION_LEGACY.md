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