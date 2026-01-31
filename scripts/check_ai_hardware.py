import psutil
import platform
import cpuinfo # Requiere: pip install py-cpuinfo
import torch    # Para verificar soporte CUDA/GPU
import os
import multiprocessing # Necesario para PyInstaller en Windows

def check_ai_hardware_compatibility():
    print("=== DIAGNÓSTICO DE HARDWARE PARA IA LOCAL ===")
    
    # 1. Información de la CPU y SET DE INSTRUCCIONES (Crítico para error 0xc000001d)
    info = cpuinfo.get_cpu_info()
    cpu_arch = info.get('arch_string_raw', 'Desconocida')
    flags = info.get('flags', [])
    
    print(f"\n[CPU] Modelo: {info['brand_raw']}")
    print(f"[CPU] Arquitectura: {cpu_arch}")
    
    # Verificación de AVX2 (Requisito común para binarios modernos de llama-cpp)
    has_avx2 = 'avx2' in flags
    has_avx = 'avx' in flags
    
    if has_avx2:
        print("✅ Soporte AVX2: Detectado. (Óptimo para inferencia)")
    elif has_avx:
        print("⚠️ Soporte AVX: Detectado pero sin AVX2. Podría fallar con binarios pre-compilados estándar.")
    else:
        print("❌ Soporte AVX/AVX2: NO DETECTADO. Esta es la causa probable del error 0xc000001d.")

    # 2. Memoria RAM
    ram = psutil.virtual_memory()
    total_gb = ram.total / (1024**3)
    print(f"\n[RAM] Total: {total_gb:.2f} GB")
    if total_gb < 16:
        print("⚠️ Advertencia: Menos de 16GB puede limitar modelos VLM complejos.")

    # 3. Soporte de GPU (CUDA)
    print("\n[GPU] Verificando aceleración por hardware:")
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            print(f"✅ GPU {i}: {props.name}")
            print(f"   - VRAM: {props.total_memory / (1024**3):.2f} GB")
            print(f"   - Compute Capability: {props.major}.{props.minor}")
    else:
        print("ℹ️ No se detectó GPU compatible con CUDA. El sistema usará solo CPU.")

    # 4. Verificación de entorno de ejecución (Rutas de logs)
    # En tus logs fallaba la escritura por archivos cerrados [cite: 113, 116]
    log_path = "logs/unified_app.log"
    print(f"\n[SISTEMA] Verificando permisos de escritura en: {os.path.abspath(log_path)}")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            f.write("\n-- Test de diagnóstico ejecutado --")
        print("✅ Permisos de log: OK")
    except Exception as e:
        print(f"❌ Error de permisos/ruta: {e}")

if __name__ == "__main__":
    multiprocessing.freeze_support() # CRITICO para PyInstaller en Windows: evita bucles infinitos de procesos
    check_ai_hardware_compatibility()
