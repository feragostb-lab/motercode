from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler
import base64
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
import time
from PIL import Image
import io

# Definir tipos de recibos y preguntas específicas
TIPOS = [
    "coche",
    "comidas",
    "envio postal",
    "estacionamiento",
    "hoteles",
    "peaje",
    "taxis",
    "telefono/celular/internet",
    "tren",
    "vuelos",
]

# Preguntas específicas por tipo de recibo
PREGUNTAS_POR_TIPO = {
    "taxis": {
        "empresa": "¿Cuál es el nombre de la empresa de taxi o el servicio?",
        "total": "¿Cuál es el importe total del trayecto o el import taxim?",
        "fecha": "¿Cuál es la fecha del servicio?",
        "hora": "¿A qué hora finalizó el trayecto?",
        "origen": "¿Cuál es el punto de origen del trayecto?",
        "destino": "¿Cuál es el punto de destino del trayecto?",
        "distancia": "¿Cuántos kilómetros recorrió?",
        "matricula": "¿Cuál es la matrícula del vehículo?"
    },
    "comidas": {
        "empresa": "¿Cuál es el nombre del restaurante o establecimiento?",
        "total": "¿Cuál es el importe total?",
        "fecha": "¿Cuál es la fecha del recibo?",
        "hora": "¿A qué hora se realizó el servicio?",
    },
    "hoteles": {
        "empresa": "¿Cuál es el nombre del hotel?",
        "total": "¿Cuál es el importe total?",
        "fecha": "¿Cuál es la fecha de la factura?",
        "hora": "¿Cuál es la fecha de check-out?",
    },
    "estacionamiento": {
        "empresa": "¿Cuál es el nombre del parking?",
        "total": "¿Cuál es el importe total?",
        "fecha": "¿Cuál es la fecha de la factura?",
        "hora": "¿Cuál es la hora de entrada o salida?",
        "ciudad": "¿En qué ciudad se encuentra el parking?"
    },
    # Preguntas comunes por defecto para otros tipos
    "default": {
        "empresa": "¿Cuál es el nombre de la empresa proveedora del servicio?",
        "total": "¿Cuál es el valor total del servicio?",
        "fecha": "¿Cuál es la fecha del servicio?",
        "hora": "¿A qué hora se realizó el servicio?",
    }
}

# 1. Función para procesar la imagen
def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# 1b. Función para redimensionar imagen si es muy grande
def redimensionar_imagen_si_necesario(imagen_path, max_kb=150):
    """
    Redimensiona la imagen si supera el tamaño máximo.
    Retorna la ruta de la imagen (original o temporal redimensionada)
    """
    tamano_kb = imagen_path.stat().st_size / 1024
    
    if tamano_kb <= max_kb:
        return str(imagen_path), False
    
    # Redimensionar imagen
    img = Image.open(imagen_path)
    
    # Reducir calidad y tamaño
    factor = 0.7
    nuevo_tamano = (int(img.width * factor), int(img.height * factor))
    img_redimensionada = img.resize(nuevo_tamano, Image.Resampling.LANCZOS)
    
    # Guardar en archivo temporal
    temp_path = f"temp_{imagen_path.name}"
    img_redimensionada.save(temp_path, quality=85, optimize=True)
    
    return temp_path, True

# 1c. Función para logging con timestamp
def log_con_tiempo(mensaje):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {mensaje}")

# 2. Función para normalizar fecha (DD/MM/YY o DD/MM/YYYY → DD/MM/YYYY)
def normalizar_fecha(fecha):
    if not fecha:
        return "01/01/2000"
    
    partes = fecha.strip().split('/')
    if len(partes) == 3:
        dia, mes, anio = partes
        # Si el año tiene 2 dígitos, convertir a 4 dígitos
        if len(anio) == 2:
            # Asumimos que 00-49 son años 2000-2049 y 50-99 son años 1950-1999
            anio_int = int(anio)
            if anio_int >= 50:
                anio = f"19{anio}"
            else:
                anio = f"20{anio}"
        return f"{dia}/{mes}/{anio}"
    
    return fecha

# 3. Función para normalizar importe (eliminar moneda y dejar solo número con coma)
def normalizar_importe(importe):
    if not importe:
        return "0,00"
    
    # Eliminar símbolos de moneda comunes y espacios
    importe_limpio = importe.strip()
    importe_limpio = importe_limpio.replace(" EUR", "").replace("EUR", "")
    importe_limpio = importe_limpio.replace(" €", "").replace("€", "")
    importe_limpio = importe_limpio.replace(" ", "").strip()
    
    return importe_limpio

# 4. Función para generar el nombre del archivo
def generar_nombre_archivo(fecha, importe_total, tipo, extension):
    # Convertir fecha de DD/MM/YYYY a YYMMDD
    partes_fecha = fecha.split('/')
    if len(partes_fecha) == 3:
        dia, mes, anio = partes_fecha
        # Tomar solo los últimos 2 dígitos del año
        anio_corto = anio[-2:] if len(anio) >= 2 else anio
        fecha_formateada = f"{anio_corto}{mes}{dia}"
    else:
        fecha_formateada = "000000"
    
    # Eliminar la coma decimal
    importe_limpio = importe_total.replace(",", "").replace(".", "").strip()
    
    # Normalizar tipo para el nombre del archivo (sin espacios ni caracteres especiales)
    tipo_limpio = tipo.replace(" ", "_").replace("/", "_")
    
    return f"{fecha_formateada}_{importe_limpio}_{tipo_limpio}{extension}"

# 5. Función para obtener nombre único (con ordinal si existe)
def obtener_nombre_unico(directorio, nombre_base, extension):
    ruta_completa = os.path.join(directorio, f"{nombre_base}{extension}")
    
    if not os.path.exists(ruta_completa):
        return f"{nombre_base}{extension}"
    
    # Si existe, añadir ordinal
    ordinal = 1
    while True:
        nombre_con_ordinal = f"{nombre_base}({ordinal}){extension}"
        ruta_completa = os.path.join(directorio, nombre_con_ordinal)
        if not os.path.exists(ruta_completa):
            return nombre_con_ordinal
        ordinal += 1

# 6. Función para deducir el tipo de recibo según campos completados
def deducir_tipo_recibo(datos):
    """
    Deduce el tipo de recibo según qué campos están completos.
    Prioriza campos específicos sobre genéricos.
    """
    # Campos específicos por tipo
    if datos.get("origen") or datos.get("destino") or datos.get("matricula"):
        return "taxis"
    elif datos.get("ciudad_parking"):
        return "estacionamiento"
    elif datos.get("nombre_hotel"):
        return "hoteles"
    elif datos.get("nombre_restaurante"):
        return "comidas"
    elif datos.get("compañia_aerea"):
        return "vuelos"
    elif datos.get("empresa_ferroviaria"):
        return "tren"
    elif datos.get("compañia_telefonia"):
        return "telefono/celular/internet"
    elif datos.get("estacion_peaje"):
        return "peaje"
    elif datos.get("empresa_mensajeria"):
        return "envio postal"
    elif datos.get("empresa_alquiler"):
        return "coche"
    else:
        return "default"

# Crear directorio result si no existe
os.makedirs("result", exist_ok=True)

# 8. Inicializar el Handler Visual (Indispensable para VL)
chat_handler = Llava15ChatHandler(clip_model_path="mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf")

# 9. Cargar el modelo en RAM (CPU) - Configuración optimizada para 64GB RAM
# n_threads: pon el número de núcleos reales de tu procesador
llm = Llama(
  model_path="Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf",
  chat_handler=chat_handler,
  n_ctx=32768,      # Aumentado significativamente para aprovechar RAM disponible
  n_batch=2048,     # Procesar más tokens en paralelo (mayor uso de RAM pero más rápido)
  n_threads=12,     # Aumentar threads para mejor paralelización
  n_gpu_layers=35,   # Usar solo CPU, establecer a 35-40 si tienes GPU NVIDIA
  verbose=False     # Reducir output para mejor rendimiento
)

# 10. Procesar todas las imágenes en ./img
img_dir = Path("img")
imagenes = list(img_dir.glob("*.jpeg")) + list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png"))

print(f"Encontradas {len(imagenes)} imágenes para procesar\n")

# Historial de procesamiento para exportar a JSON
historial_procesamiento = []

for idx, imagen_path in enumerate(imagenes, 1):
    print(f"\n{'='*60}")
    log_con_tiempo(f"[{idx}/{len(imagenes)}] Procesando: {imagen_path.name}")
    tamano_original = imagen_path.stat().st_size / 1024
    print(f"Tamaño original: {tamano_original:.2f} KB")
    print(f"{'='*60}")
    
    imagen_temporal = None
    tiempo_inicio = time.time()
    
    try:
        # Redimensionar imagen si es muy grande
        log_con_tiempo("→ Verificando tamaño de imagen...")
        ruta_imagen, es_temporal = redimensionar_imagen_si_necesario(imagen_path, max_kb=150)
        
        if es_temporal:
            imagen_temporal = ruta_imagen
            tamano_nuevo = Path(ruta_imagen).stat().st_size / 1024
            log_con_tiempo(f"→ Imagen redimensionada: {tamano_original:.2f} KB → {tamano_nuevo:.2f} KB")
        
        # Preparar imagen
        log_con_tiempo("→ Codificando imagen en base64...")
        data_uri = f"data:image/jpeg;base64,{image_to_base64(ruta_imagen)}"
        
        # Crear prompt simplificado - hacer todas las preguntas a la vez
        prompt_completo = """Extrae los datos del recibo. Completa solo los campos que encuentres:

{
  "empresa": "Nombre de la empresa",
  "total": "Importe total con moneda",
  "fecha": "Fecha del servicio",
  "hora": "Hora del servicio",
  "origen": "Punto de origen (si es taxi)",
  "destino": "Punto de destino (si es taxi)",
  "distancia": "Kilómetros (si es taxi)",
  "matricula": "Matrícula vehículo (si es taxi)",
  "ciudad_parking": "Ciudad (si es parking)",
  "nombre_hotel": "Nombre hotel (si es hotel)",
  "nombre_restaurante": "Nombre restaurante (si es comida)",
  "empresa_alquiler": "Empresa alquiler (si es coche alquiler)",
  "compañia_aerea": "Compañía aérea (si es vuelo)",
  "empresa_ferroviaria": "Empresa tren (si es tren)",
  "compañia_telefonia": "Compañía teléfono (si es teléfono)",
  "estacion_peaje": "Estación peaje (si es peaje)",
  "empresa_mensajeria": "Empresa mensajería (si es envío)"
}

Responde SOLO en formato JSON. Omite campos vacíos."""
        
        # Una sola llamada al modelo con límites
        log_con_tiempo("→ Iniciando inferencia del modelo...")
        t_inferencia = time.time()
        
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": "Eres un experto en extracción de datos de recibos."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_completo},
                        {"type": "image_url", "image_url": data_uri}
                    ]
                }
            ],
            max_tokens=512,  # Limitar tokens de respuesta para evitar colgarse
            temperature=0.1,  # Más determinista
            top_p=0.9
        )
        
        duracion_inferencia = time.time() - t_inferencia
        log_con_tiempo(f"→ Inferencia completada en {duracion_inferencia:.2f}s")
        
        resultado_texto = response["choices"][0]["message"]["content"]
        print(f"  → Resultado: {resultado_texto[:200]}...")  # Mostrar solo primeros 200 caracteres
        
        # Limpiar bloques de código markdown si existen
        texto_limpio = resultado_texto
        if "```json" in texto_limpio:
            # Extraer solo el contenido entre ```json y ```
            inicio_bloque = texto_limpio.find("```json") + 7
            fin_bloque = texto_limpio.find("```", inicio_bloque)
            if fin_bloque != -1:
                texto_limpio = texto_limpio[inicio_bloque:fin_bloque].strip()
        elif "```" in texto_limpio:
            # Extraer contenido entre ``` genéricos
            inicio_bloque = texto_limpio.find("```") + 3
            fin_bloque = texto_limpio.find("```", inicio_bloque)
            if fin_bloque != -1:
                texto_limpio = texto_limpio[inicio_bloque:fin_bloque].strip()
        
        # Extraer JSON del resultado limpio
        inicio_json = texto_limpio.find('{')
        fin_json = texto_limpio.find('}') + 1
        
        if inicio_json != -1 and fin_json > inicio_json:
            json_texto = texto_limpio[inicio_json:fin_json]
            datos = json.loads(json_texto)
            
            # Deducir el tipo según los campos completados
            tipo_recibo = deducir_tipo_recibo(datos)
            print(f"  → Tipo deducido: {tipo_recibo}")
            print(f"  → Campos extraídos: {', '.join([k for k, v in datos.items() if v])}")
            
            # Normalizar los datos extraídos
            # Buscar fecha en diferentes claves posibles
            fecha_original = datos.get("fecha", datos.get("Fecha", "01/01/2000"))
            # Buscar importe total en diferentes claves posibles
            importe_original = datos.get("total", datos.get("Total", datos.get("Importe Total", "0")))
            
            fecha_normalizada = normalizar_fecha(fecha_original)
            importe_normalizado = normalizar_importe(importe_original)
            
            # Actualizar el diccionario con valores normalizados
            datos["fecha"] = fecha_normalizada
            datos["total"] = importe_normalizado
            
            print(f"  → Normalizado - Fecha: {fecha_normalizada}, Importe: {importe_normalizado}")
            
            # Generar nombre del archivo con datos normalizados y tipo
            extension = imagen_path.suffix
            
            nombre_base = generar_nombre_archivo(fecha_normalizada, importe_normalizado, tipo_recibo, "").rstrip("_")
            nombre_final = obtener_nombre_unico("result", nombre_base, extension)
            
            # Copiar archivo con el nuevo nombre
            ruta_destino = os.path.join("result", nombre_final)
            shutil.copy2(str(imagen_path), ruta_destino)
            
            print(f"  ✓ Guardado como: {nombre_final}")
            
            # Guardar en historial
            historial_procesamiento.append({
                "archivo_original": imagen_path.name,
                "archivo_resultado": nombre_final,
                "tipo_deducido": tipo_recibo,
                "datos_extraidos": datos,
                "procesado_exitoso": True
            })
        else:
            print(f"  ✗ No se pudo extraer JSON del resultado")
            historial_procesamiento.append({
                "archivo_original": imagen_path.name,
                "archivo_resultado": None,
                "tipo_deducido": None,
                "datos_extraidos": None,
                "procesado_exitoso": False,
                "error": "No se pudo extraer JSON del resultado"
            })
        
        # IMPORTANTE: Resetear el contexto del modelo para liberar memoria
        log_con_tiempo("→ Reseteando contexto del modelo...")
        llm.reset()
        
        # Limpiar imagen temporal si existe
        if imagen_temporal and os.path.exists(imagen_temporal):
            os.remove(imagen_temporal)
        
        duracion_total = time.time() - tiempo_inicio
        log_con_tiempo(f"✓ Procesado en {duracion_total:.2f}s total")
    
    except json.JSONDecodeError as e:
        duracion_error = time.time() - tiempo_inicio
        log_con_tiempo(f"✗ Error JSON después de {duracion_error:.2f}s: {e}")
        try:
            print(f"     Texto extraído: {json_texto[:200]}...")
        except:
            pass
        historial_procesamiento.append({
            "archivo_original": imagen_path.name,
            "archivo_resultado": None,
            "tipo_deducido": None,
            "datos_extraidos": None,
            "procesado_exitoso": False,
            "error": f"Error JSON: {str(e)}"
        })
        llm.reset()
        if imagen_temporal and os.path.exists(imagen_temporal):
            os.remove(imagen_temporal)
    
    except RuntimeError as e:
        duracion_error = time.time() - tiempo_inicio
        log_con_tiempo(f"✗✗✗ ERROR CRÍTICO después de {duracion_error:.2f}s: {e}")
        log_con_tiempo("→ Intentando resetear el modelo...")
        historial_procesamiento.append({
            "archivo_original": imagen_path.name,
            "archivo_resultado": None,
            "tipo_deducido": None,
            "datos_extraidos": None,
            "procesado_exitoso": False,
            "error": f"Error crítico: {str(e)}"
        })
        try:
            llm.reset()
            log_con_tiempo("→ Modelo reseteado, continuando con siguiente imagen...")
        except Exception as reset_error:
            log_con_tiempo(f"✗ No se pudo resetear el modelo: {reset_error}")
            log_con_tiempo("→ Saltando esta imagen y continuando...")
        
        if imagen_temporal and os.path.exists(imagen_temporal):
            os.remove(imagen_temporal)
    
    except Exception as e:
        duracion_error = time.time() - tiempo_inicio
        log_con_tiempo(f"✗✗✗ ERROR INESPERADO después de {duracion_error:.2f}s: {type(e).__name__}: {e}")
        log_con_tiempo("→ Continuando con siguiente imagen...")
        historial_procesamiento.append({
            "archivo_original": imagen_path.name,
            "archivo_resultado": None,
            "tipo_deducido": None,
            "datos_extraidos": None,
            "procesado_exitoso": False,
            "error": f"{type(e).__name__}: {str(e)}"
        })
        try:
            llm.reset()
        except:
            pass
        
        if imagen_temporal and os.path.exists(imagen_temporal):
            os.remove(imagen_temporal)

# Guardar historial en archivo JSON
archivo_historial = os.path.join("result", "historial_procesamiento.json")
with open(archivo_historial, "w", encoding="utf-8") as f:
    json.dump(historial_procesamiento, f, ensure_ascii=False, indent=2)

print(f"\nProcesamiento completado!")
print(f"Historial guardado en: {archivo_historial}")
print(f"Total procesados: {len(historial_procesamiento)}")
print(f"Exitosos: {sum(1 for x in historial_procesamiento if x['procesado_exitoso'])}")
print(f"Con errores: {sum(1 for x in historial_procesamiento if not x['procesado_exitoso'])}")