import gradio as gr
import json
from pathlib import Path
from PIL import Image
import os
import pandas as pd
from datetime import datetime
import re

# Cargar el historial de procesamiento
def cargar_datos():
    with open('result/historial_procesamiento.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# Cargar conflictos aceptados
def cargar_conflictos_aceptados():
    archivo_estado = Path('result/conflictos_aceptados.json')
    if archivo_estado.exists():
        try:
            with open(archivo_estado, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('conflictos_aceptados', []))
        except:
            return set()
    return set()

# Guardar conflictos aceptados
def guardar_conflictos_aceptados(conflictos_set):
    archivo_estado = Path('result/conflictos_aceptados.json')
    data = {
        'conflictos_aceptados': list(conflictos_set),
        'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    with open(archivo_estado, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Cargar recibos ignorados
def cargar_ignorados():
    archivo_ignorados = Path('result/recibos_ignorados.json')
    if archivo_ignorados.exists():
        try:
            with open(archivo_ignorados, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('ignorados', []))
        except:
            return set()
    return set()

# Guardar recibos ignorados
def guardar_ignorados(ignorados_set):
    archivo_ignorados = Path('result/recibos_ignorados.json')
    data = {
        'ignorados': list(ignorados_set),
        'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    with open(archivo_ignorados, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Cargar movimientos bancarios
def cargar_movimientos_bancarios():
    try:
        # Leer el archivo Excel
        df = pd.read_excel('img/bankmov/Detalle de Tarjeta ROC SKINCARE IBERIA SL.xlsx', skiprows=13)
        
        # Limpiar y procesar los datos
        df.columns = ['fecha', 'descripcion', 'metodo', 'importe']
        df = df[df['fecha'].notna()].copy()
        
        # Filtrar las filas de totales (que contienen "MES" o no tienen formato de fecha válido)
        df = df[~df['fecha'].astype(str).str.upper().str.contains('MES|SITUACIÓN|SITUACION|DICIEMBRE|ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE', na=False)].copy()
        
        # Procesar fechas
        df['fecha_procesada'] = pd.to_datetime(df['fecha'], format='%d.%m.%Y', errors='coerce')
        
        # Procesar importes (convertir a float positivo)
        def procesar_importe(importe):
            if pd.isna(importe):
                return None
            if isinstance(importe, (int, float)):
                return abs(float(importe))
            # Si es string, limpiar y convertir
            importe_str = str(importe).replace(',', '.').replace('-', '').strip()
            try:
                return abs(float(importe_str))
            except:
                return None
        
        df['importe_procesado'] = df['importe'].apply(procesar_importe)
        
        # Agregar campo para marcar si ya está asignado
        df['asignado_a'] = None
        
        return df
    except Exception as e:
        print(f"Error al cargar movimientos bancarios: {e}")
        return pd.DataFrame()

# Función para normalizar fechas
def normalizar_fecha(fecha_str):
    """Convierte diferentes formatos de fecha a un objeto datetime"""
    if not fecha_str or fecha_str == "":
        return None
    
    formatos = [
        '%d/%m/%Y',
        '%d.%m.%Y',
        '%Y-%m-%d',
        '%d/%m/%y',
        '%d %b %y',
        '%d %B %y',
        '%d %b %Y',
        '%d %B %Y',
    ]
    
    for formato in formatos:
        try:
            return datetime.strptime(str(fecha_str).strip(), formato)
        except:
            continue
    
    # Intentar extraer fecha con regex
    match = re.search(r'(\d{1,2})[/\.\-](\d{1,2})[/\.\-](\d{2,4})', str(fecha_str))
    if match:
        dia, mes, año = match.groups()
        if len(año) == 2:
            año = '20' + año
        try:
            return datetime(int(año), int(mes), int(dia))
        except:
            pass
    
    return None

# Función para normalizar importes
def normalizar_importe(importe_str):
    """Convierte diferentes formatos de importe a float"""
    if not importe_str or importe_str == "":
        return None
    
    try:
        # Si ya es número
        if isinstance(importe_str, (int, float)):
            return abs(float(importe_str))
        
        # Limpiar string
        importe_clean = str(importe_str).replace('€', '').replace(',', '.').strip()
        importe_clean = re.sub(r'[^\d\.]', '', importe_clean)
        
        if importe_clean:
            return abs(float(importe_clean))
    except:
        pass
    
    return None

# Buscar coincidencias
def buscar_coincidencias(ficha, df_movimientos):
    """Busca coincidencias de una ficha con los movimientos bancarios"""
    datos = ficha.get('datos_extraidos', {})
    
    # Obtener fecha y total de la ficha
    fecha_ficha_str = datos.get('fecha', '')
    total_ficha_str = datos.get('total', '')
    
    fecha_ficha = normalizar_fecha(fecha_ficha_str)
    total_ficha = normalizar_importe(total_ficha_str)
    
    resultado = {
        'coincide_importe': False,
        'coincide_fecha': False,
        'coincide_ambos': False,
        'movimiento_asignado': None,
        'detalles': ''
    }
    
    if df_movimientos.empty:
        return resultado
    
    # Buscar coincidencias
    coincidencias = []
    
    for idx, mov in df_movimientos.iterrows():
        coincide_importe = False
        coincide_fecha = False
        
        # Verificar importe (con tolerancia de 0.01)
        if total_ficha and mov['importe_procesado']:
            diferencia = abs(total_ficha - mov['importe_procesado'])
            if diferencia < 0.02:
                coincide_importe = True
        
        # Verificar fecha
        if fecha_ficha and mov['fecha_procesada'] and not pd.isna(mov['fecha_procesada']):
            if fecha_ficha.date() == mov['fecha_procesada'].date():
                coincide_fecha = True
        
        # Si hay alguna coincidencia y el movimiento no está asignado
        if (coincide_importe or coincide_fecha) and pd.isna(mov['asignado_a']):
            coincidencias.append({
                'idx': idx,
                'coincide_importe': coincide_importe,
                'coincide_fecha': coincide_fecha,
                'ambos': coincide_importe and coincide_fecha,
                'fecha': mov['fecha'],
                'descripcion': mov['descripcion'],
                'importe': mov['importe_procesado']
            })
    
    # Priorizar coincidencias: ambos > importe > fecha
    if coincidencias:
        # Ordenar por prioridad
        coincidencias.sort(key=lambda x: (x['ambos'], x['coincide_importe'], x['coincide_fecha']), reverse=True)
        mejor = coincidencias[0]
        
        resultado['coincide_importe'] = mejor['coincide_importe']
        resultado['coincide_fecha'] = mejor['coincide_fecha']
        resultado['coincide_ambos'] = mejor['ambos']
        resultado['movimiento_asignado'] = mejor['idx']
        resultado['detalles'] = f"{mejor['fecha']} - {mejor['descripcion']} - {mejor['importe']}€"
    
    return resultado

# Estado global
datos = cargar_datos()
movimientos_bancarios = cargar_movimientos_bancarios()
indice_actual = [0]  # Usamos lista para hacer mutable
conflictos_aceptados = cargar_conflictos_aceptados()  # Cargar conflictos ya aceptados
recibos_ignorados = cargar_ignorados()  # Cargar recibos ignorados

# Estado de filtros
filtros_activos = {
    'tipo': 'Todos',
    'coincidencia': 'Todas',
    'mostrar_ignorados': False  # Por defecto NO mostrar ignorados
}

# Calcular coincidencias para todas las fichas
coincidencias_cache = {}
for i, ficha in enumerate(datos):
    coincidencias_cache[i] = buscar_coincidencias(ficha, movimientos_bancarios)
    # Marcar el movimiento como asignado si hay coincidencia de ambos
    if coincidencias_cache[i]['movimiento_asignado'] is not None and coincidencias_cache[i]['coincide_ambos']:
        idx_mov = coincidencias_cache[i]['movimiento_asignado']
        movimientos_bancarios.at[idx_mov, 'asignado_a'] = ficha['archivo_resultado']

# Detectar conflictos: fichas con misma fecha e importe (excluyendo los ya aceptados)
conflictos_cache = {}
for i, ficha in enumerate(datos):
    archivo_resultado = ficha['archivo_resultado']
    
    # Si el conflicto ya fue aceptado, no marcarlo como conflicto
    if archivo_resultado in conflictos_aceptados:
        conflictos_cache[i] = False
        continue
    
    datos_i = ficha.get('datos_extraidos', {})
    fecha_i = normalizar_fecha(datos_i.get('fecha', ''))
    importe_i = normalizar_importe(datos_i.get('total', ''))
    
    if fecha_i and importe_i:
        tiene_conflicto = False
        for j, otra_ficha in enumerate(datos):
            if i != j:  # No comparar consigo misma
                datos_j = otra_ficha.get('datos_extraidos', {})
                fecha_j = normalizar_fecha(datos_j.get('fecha', ''))
                importe_j = normalizar_importe(datos_j.get('total', ''))
                
                if fecha_j and importe_j:
                    # Comparar fecha (mismo día)
                    if fecha_i.date() == fecha_j.date():
                        # Comparar importe con tolerancia
                        if abs(importe_i - importe_j) < 0.02:
                            tiene_conflicto = True
                            break
        conflictos_cache[i] = tiene_conflicto
    else:
        conflictos_cache[i] = False

def aceptar_conflicto(indice):
    """Acepta/resuelve un conflicto marcándolo como revisado"""
    if indice < 0 or indice >= len(datos):
        return "❌ Error: índice inválido", False
    
    ficha = datos[indice]
    archivo_resultado = ficha['archivo_resultado']
    
    # Verificar si tiene conflicto
    if not conflictos_cache.get(indice, False):
        return "⚠️ Esta ficha no tiene conflictos activos", False
    
    # Agregar a conflictos aceptados
    conflictos_aceptados.add(archivo_resultado)
    guardar_conflictos_aceptados(conflictos_aceptados)
    
    # Actualizar el caché
    conflictos_cache[indice] = False
    
    return f"✅ Conflicto aceptado para {archivo_resultado}", True

def ignorar_recibo(indice):
    """Marca un recibo como ignorado y lo excluye de las vistas normales"""
    if indice < 0 or indice >= len(datos):
        return "❌ Error: índice inválido", False
    
    ficha = datos[indice]
    archivo_resultado = ficha['archivo_resultado']
    
    # Verificar si ya está ignorado
    if archivo_resultado in recibos_ignorados:
        return "⚠️ Este recibo ya está en la lista de ignorados", False
    
    # Agregar a ignorados
    recibos_ignorados.add(archivo_resultado)
    guardar_ignorados(recibos_ignorados)
    
    # Recalcular coincidencias y conflictos si es necesario
    # Si este recibo tenía un movimiento asignado, liberarlo
    coincidencia = coincidencias_cache.get(indice, {})
    if coincidencia.get('movimiento_asignado') is not None:
        idx_mov = coincidencia['movimiento_asignado']
        if idx_mov < len(movimientos_bancarios):
            movimientos_bancarios.at[idx_mov, 'asignado_a'] = None
    
    # Recalcular coincidencias para todas las fichas
    for i, f in enumerate(datos):
        coincidencias_cache[i] = buscar_coincidencias(f, movimientos_bancarios)
        # Marcar movimiento como asignado si hay coincidencia de ambos
        if coincidencias_cache[i]['movimiento_asignado'] is not None and coincidencias_cache[i]['coincide_ambos']:
            idx_mov = coincidencias_cache[i]['movimiento_asignado']
            # Solo asignar si el archivo NO está ignorado
            if f['archivo_resultado'] not in recibos_ignorados:
                movimientos_bancarios.at[idx_mov, 'asignado_a'] = f['archivo_resultado']
    
    return f"✅ Recibo {archivo_resultado} marcado como ignorado", True

def guardar_cambio_tipo(indice, nuevo_tipo):
    """Guarda el cambio de tipo en el JSON y renombra el archivo de imagen"""
    if indice < 0 or indice >= len(datos):
        return "❌ Error: índice inválido"
    
    ficha = datos[indice]
    tipo_antiguo = ficha['tipo_deducido']
    
    # Si el tipo no ha cambiado, no hacer nada
    if tipo_antiguo == nuevo_tipo:
        return "⚠️ El tipo no ha cambiado"
    
    # Obtener el nombre del archivo antiguo
    archivo_antiguo = ficha['archivo_resultado']
    
    # Crear el nuevo nombre del archivo reemplazando el tipo antiguo por el nuevo
    # Patrón: FECHA_IMPORTE_TIPO.jpeg
    if '_' in archivo_antiguo:
        partes = archivo_antiguo.rsplit('_', 1)  # Dividir desde la derecha
        if len(partes) == 2:
            # partes[0] = "FECHA_IMPORTE", partes[1] = "TIPO.jpeg"
            tipo_con_ext = partes[1]  # "TIPO.jpeg"
            extension = tipo_con_ext.split('.')[-1]  # "jpeg"
            archivo_nuevo = f"{partes[0]}_{nuevo_tipo}.{extension}"
        else:
            return "❌ Error: formato de nombre de archivo no reconocido"
    else:
        return "❌ Error: formato de nombre de archivo no reconocido"
    
    # Renombrar el archivo físico
    ruta_antigua = Path('result') / archivo_antiguo
    ruta_nueva = Path('result') / archivo_nuevo
    
    try:
        # Verificar que el archivo antiguo existe
        if not ruta_antigua.exists():
            return f"❌ Error: el archivo {archivo_antiguo} no existe"
        
        # Verificar que el nuevo nombre no está en uso
        if ruta_nueva.exists():
            return f"❌ Error: el archivo {archivo_nuevo} ya existe"
        
        # Renombrar el archivo
        ruta_antigua.rename(ruta_nueva)
        
        # Actualizar el tipo y el nombre del archivo en los datos
        datos[indice]['tipo_deducido'] = nuevo_tipo
        datos[indice]['archivo_resultado'] = archivo_nuevo
        
        # Guardar en el archivo JSON
        with open('result/historial_procesamiento.json', 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        return f"✅ Tipo cambiado a '{nuevo_tipo}' y archivo renombrado a '{archivo_nuevo}'"
    except Exception as e:
        # Si hay un error, intentar revertir el cambio de nombre del archivo
        if ruta_nueva.exists() and not ruta_antigua.exists():
            try:
                ruta_nueva.rename(ruta_antigua)
            except:
                pass
        return f"❌ Error al guardar: {str(e)}"

def guardar_cambio_fecha(indice, nueva_fecha):
    """Guarda el cambio de fecha en el JSON y renombra el archivo de imagen"""
    if indice < 0 or indice >= len(datos):
        return "❌ Error: índice inválido"
    
    ficha = datos[indice]
    fecha_antigua = ficha.get('datos_extraidos', {}).get('fecha', '')
    
    # Si la fecha no ha cambiado, no hacer nada
    if fecha_antigua == nueva_fecha:
        return "⚠️ La fecha no ha cambiado"
    
    # Validar formato de fecha (DD/MM/YYYY o DD.MM.YYYY)
    fecha_obj = normalizar_fecha(nueva_fecha)
    if not fecha_obj:
        return "❌ Error: formato de fecha inválido. Use DD/MM/YYYY o DD.MM.YYYY"
    
    # Obtener el nombre del archivo antiguo
    archivo_antiguo = ficha['archivo_resultado']
    
    # Crear el nuevo nombre del archivo reemplazando la fecha
    # Patrón: FECHA_IMPORTE_TIPO.jpeg
    if '_' in archivo_antiguo:
        partes = archivo_antiguo.split('_')
        if len(partes) >= 3:
            # partes[0] = "FECHA", partes[1] = "IMPORTE", partes[2:] = "TIPO.jpeg"
            # Convertir la fecha a formato DDMMYY
            nueva_fecha_formato = fecha_obj.strftime('%d%m%y')
            partes[0] = nueva_fecha_formato
            archivo_nuevo = '_'.join(partes)
        else:
            return "❌ Error: formato de nombre de archivo no reconocido"
    else:
        return "❌ Error: formato de nombre de archivo no reconocido"
    
    # Renombrar el archivo físico
    ruta_antigua = Path('result') / archivo_antiguo
    ruta_nueva = Path('result') / archivo_nuevo
    
    try:
        # Verificar que el archivo antiguo existe
        if not ruta_antigua.exists():
            return f"❌ Error: el archivo {archivo_antiguo} no existe"
        
        # Verificar que el nuevo nombre no está en uso
        if ruta_nueva.exists():
            return f"❌ Error: el archivo {archivo_nuevo} ya existe"
        
        # Renombrar el archivo
        ruta_antigua.rename(ruta_nueva)
        
        # Actualizar la fecha y el nombre del archivo en los datos
        datos[indice]['datos_extraidos']['fecha'] = nueva_fecha
        datos[indice]['archivo_resultado'] = archivo_nuevo
        
        # Guardar en el archivo JSON
        with open('result/historial_procesamiento.json', 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        # Recalcular coincidencias y conflictos para esta ficha
        recalcular_coincidencias_y_conflictos(indice)
        
        return f"✅ Fecha cambiada a '{nueva_fecha}' y archivo renombrado a '{archivo_nuevo}'"
    except Exception as e:
        # Si hay un error, intentar revertir el cambio de nombre del archivo
        if ruta_nueva.exists() and not ruta_antigua.exists():
            try:
                ruta_nueva.rename(ruta_antigua)
            except:
                pass
        return f"❌ Error al guardar: {str(e)}"

def recalcular_coincidencias_y_conflictos(indice):
    """Recalcula coincidencias bancarias y conflictos para una ficha específica"""
    if indice < 0 or indice >= len(datos):
        return
    
    # Recalcular coincidencias bancarias
    ficha = datos[indice]
    coincidencias_cache[indice] = buscar_coincidencias(ficha, movimientos_bancarios)
    
    # Recalcular conflictos
    archivo_resultado = ficha['archivo_resultado']
    if archivo_resultado in conflictos_aceptados:
        conflictos_cache[indice] = False
    else:
        datos_i = ficha.get('datos_extraidos', {})
        fecha_i = normalizar_fecha(datos_i.get('fecha', ''))
        importe_i = normalizar_importe(datos_i.get('total', ''))
        
        if fecha_i and importe_i:
            tiene_conflicto = False
            for j, otra_ficha in enumerate(datos):
                if indice != j:
                    datos_j = otra_ficha.get('datos_extraidos', {})
                    fecha_j = normalizar_fecha(datos_j.get('fecha', ''))
                    importe_j = normalizar_importe(datos_j.get('total', ''))
                    
                    if fecha_j and importe_j:
                        if fecha_i.date() == fecha_j.date():
                            if abs(importe_i - importe_j) < 0.02:
                                tiene_conflicto = True
                                break
            conflictos_cache[indice] = tiene_conflicto
        else:
            conflictos_cache[indice] = False

def obtener_indices_filtrados():
    """Obtiene los índices de las fichas que cumplen con los filtros activos"""
    indices = []
    
    for i, ficha in enumerate(datos):
        # Filtro por tipo
        if filtros_activos['tipo'] != 'Todos':
            if ficha['tipo_deducido'] != filtros_activos['tipo']:
                continue
        
        # Filtro por coincidencia
        if filtros_activos['coincidencia'] != 'Todas':
            coincidencia = coincidencias_cache.get(i, {})
            if filtros_activos['coincidencia'] == "Con coincidencia completa":
                if not coincidencia.get('coincide_ambos'):
                    continue
            elif filtros_activos['coincidencia'] == "Con coincidencia parcial":
                if coincidencia.get('coincide_ambos') or coincidencia.get('movimiento_asignado') is None:
                    continue
            elif filtros_activos['coincidencia'] == "Sin coincidencia":
                if coincidencia.get('movimiento_asignado') is not None:
                    continue
            elif filtros_activos['coincidencia'] == "Conflictos":
                # Mostrar solo fichas con conflictos (misma fecha e importe)
                if not conflictos_cache.get(i, False):
                    continue
        
        indices.append(i)
    
    return indices

def obtener_mensaje_sin_resultados():
    """Genera mensaje cuando no hay fichas que coincidan con el filtro"""
    mensaje_html = """
    <div style='font-family: Arial; padding: 40px; background-color: #fff3cd; border-radius: 10px; border: 2px solid #ffc107; text-align: center;'>
        <h2 style='color: #856404; margin-bottom: 20px;'>⚠️ Sin resultados</h2>
        <p style='font-size: 1.2em; color: #856404;'>No hay fichas que coincidan con los filtros seleccionados.</p>
        <p style='color: #856404; margin-top: 10px;'>Por favor, ajusta los filtros para ver resultados.</p>
    </div>
    """
    # Retornar 10 valores: imagen (oculta), info_html, nav_info, slider_pos (1 para evitar error), slider_max (1 para evitar error), tipo_deducido (deshabilitado), indice, btn_aceptar_conflicto (oculto), fecha_editor (deshabilitado), btn_ignorar (oculto)
    return gr.update(value=None, visible=False), mensaje_html, "Sin resultados", 1, 1, gr.update(value=None, interactive=False), -1, gr.update(visible=False), gr.update(value="", interactive=False), gr.update(visible=False)

def obtener_info_ficha(indice, indices_filtrados=None):
    """Obtiene la información de una ficha específica"""
    if not datos or indice < 0 or indice >= len(datos):
        return None, "No hay datos disponibles", "", 0, len(datos), gr.update(value=None, interactive=False), -1, False, False
    
    ficha = datos[indice]
    coincidencias = coincidencias_cache.get(indice, {})
    
    # Si hay filtros aplicados, mostrar la posición dentro del filtro
    if indices_filtrados and len(indices_filtrados) > 0:
        try:
            pos_en_filtro = indices_filtrados.index(indice) + 1
            total_filtrado = len(indices_filtrados)
        except ValueError:
            pos_en_filtro = 1
            total_filtrado = len(indices_filtrados)
    else:
        pos_en_filtro = indice + 1
        total_filtrado = len(datos)
    
    # Cargar imagen
    ruta_imagen = Path('result') / ficha['archivo_resultado']
    if ruta_imagen.exists():
        imagen = Image.open(ruta_imagen)
    else:
        imagen = None
    
    # Símbolos de check
    check_verde = "✅"
    check_rojo = "❌"
    check_amarillo = "⚠️"
    
    # Verificar si tiene conflicto
    tiene_conflicto = conflictos_cache.get(indice, False)
    archivo_resultado = ficha['archivo_resultado']
    conflicto_fue_aceptado = archivo_resultado in conflictos_aceptados
    
    # Formatear información
    info_html = f"""
    <div style='font-family: Arial; padding: 20px; background-color: #f5f5f5; border-radius: 10px;'>
        <h2 style='color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;'>
            📄 Ficha {pos_en_filtro} de {total_filtrado}
        </h2>
    """
    
    # Agregar alerta de conflicto si existe (no aceptado)
    if tiene_conflicto:
        info_html += """
        <div style='background-color: #fff3cd; padding: 15px; margin: 10px 0; border-radius: 5px; border: 2px solid #ff9800;'>
            <h3 style='color: #ff6f00; margin-top: 0;'>⚠️ CONFLICTO DETECTADO</h3>
            <p style='margin: 5px 0; color: #856404;'><strong>Existe otra ficha con la misma fecha e importe.</strong></p>
            <p style='margin: 5px 0; font-size: 0.9em; color: #856404;'>Revisa para evitar duplicados y acepta el conflicto si es correcto.</p>
        </div>
        """
    elif conflicto_fue_aceptado:
        info_html += """
        <div style='background-color: #d4edda; padding: 15px; margin: 10px 0; border-radius: 5px; border: 2px solid #28a745;'>
            <h3 style='color: #155724; margin-top: 0;'>✅ CONFLICTO ACEPTADO</h3>
            <p style='margin: 5px 0; color: #155724;'><strong>Este conflicto fue revisado y aceptado.</strong></p>
        </div>
        """
    
    info_html += f"""
        <div style='background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px;'>
            <h3 style='color: #e74c3c; margin-top: 0;'>📁 Archivos</h3>
            <p><strong>Original:</strong> {ficha['archivo_original']}</p>
            <p><strong>Resultado:</strong> {ficha['archivo_resultado']}</p>
        </div>
        
        <div style='background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px;'>
            <h3 style='color: #27ae60; margin-top: 0;'>🏷️ Clasificación</h3>
            <p><strong>Tipo:</strong> <span style='background-color: #3498db; color: white; padding: 5px 10px; border-radius: 3px;'>{ficha['tipo_deducido']}</span></p>
            <p><strong>Estado:</strong> <span style='color: {"green" if ficha["procesado_exitoso"] else "red"};'>{"✓ Procesado exitosamente" if ficha["procesado_exitoso"] else "✗ Error en procesamiento"}</span></p>
        </div>
        
        <div style='background-color: {"#d4edda" if coincidencias.get("coincide_ambos") else "#fff3cd" if (coincidencias.get("coincide_importe") or coincidencias.get("coincide_fecha")) else "#f8d7da"}; padding: 15px; margin: 10px 0; border-radius: 5px; border: 2px solid {"#28a745" if coincidencias.get("coincide_ambos") else "#ffc107" if (coincidencias.get("coincide_importe") or coincidencias.get("coincide_fecha")) else "#dc3545"};'>
            <h3 style='color: #155724; margin-top: 0;'>🔍 Coincidencias Bancarias</h3>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px;'>
                <div style='background-color: white; padding: 10px; border-radius: 5px;'>
                    <p style='margin: 0;'><strong>Por Importe:</strong> {check_verde if coincidencias.get("coincide_importe") else check_rojo}</p>
                </div>
                <div style='background-color: white; padding: 10px; border-radius: 5px;'>
                    <p style='margin: 0;'><strong>Por Fecha:</strong> {check_verde if coincidencias.get("coincide_fecha") else check_rojo}</p>
                </div>
            </div>
    """
    
    if coincidencias.get('movimiento_asignado') is not None:
        info_html += f"""
            <div style='background-color: white; padding: 10px; margin-top: 10px; border-radius: 5px;'>
                <p style='margin: 0;'><strong>Movimiento Bancario:</strong></p>
                <p style='margin: 5px 0; font-size: 0.9em; color: #555;'>{coincidencias.get('detalles', '')}</p>
            </div>
        """
    else:
        info_html += f"""
            <div style='background-color: white; padding: 10px; margin-top: 10px; border-radius: 5px;'>
                <p style='margin: 0; color: #dc3545;'><strong>{check_amarillo} Sin coincidencia en movimientos bancarios</strong></p>
            </div>
        """
    
    info_html += """
        </div>
        
        <div style='background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px;'>
            <h3 style='color: #9b59b6; margin-top: 0;'>📊 Datos Extraídos</h3>
    """
    
    # Agregar datos extraídos
    datos_extraidos = ficha.get('datos_extraidos', {})
    for clave, valor in datos_extraidos.items():
        if valor and valor != "":
            # Formatear el nombre del campo
            nombre_campo = clave.replace('_', ' ').title()
            # Destacar el total y la fecha
            if clave == 'total':
                info_html += f"<p style='font-size: 1.2em;'><strong>💰 {nombre_campo}:</strong> <span style='color: #e74c3c; font-weight: bold;'>{valor} €</span></p>"
            elif clave == 'fecha':
                info_html += f"<p style='font-size: 1.1em;'><strong>📅 {nombre_campo}:</strong> <span style='color: #3498db; font-weight: bold;'>{valor}</span></p>"
            else:
                info_html += f"<p><strong>{nombre_campo}:</strong> {valor}</p>"
    
    info_html += """
        </div>
    </div>
    """
    
    # Información de navegación
    nav_info = f"Ficha {pos_en_filtro} de {total_filtrado}"
    
    # Calcular la posición del slider (1-indexed)
    if indices_filtrados and len(indices_filtrados) > 0:
        try:
            slider_pos = indices_filtrados.index(indice) + 1
        except ValueError:
            slider_pos = 1
        slider_max = len(indices_filtrados)
    else:
        slider_pos = indice + 1
        slider_max = len(datos)
    
    # Determinar si mostrar botón de aceptar conflicto
    mostrar_btn_conflicto = conflictos_cache.get(indice, False)
    
    # Determinar si mostrar botón de ignorar (ocultar si ya está ignorado)
    es_ignorado = archivo_resultado in recibos_ignorados
    mostrar_btn_ignorar = not es_ignorado
    
    # Obtener la fecha actual
    fecha_actual = datos_extraidos.get('fecha', '')
    
    # Retornar 10 valores: imagen (visible), info_html, nav_info, slider_pos, slider_max, tipo_deducido (habilitado), indice, btn_aceptar_conflicto, fecha_actual, btn_ignorar
    return (gr.update(value=imagen, visible=True), info_html, nav_info, slider_pos, slider_max, 
            gr.update(value=ficha['tipo_deducido'], interactive=True), indice, 
            gr.update(visible=mostrar_btn_conflicto), gr.update(value=fecha_actual, interactive=True),
            gr.update(visible=mostrar_btn_ignorar))

def siguiente_ficha(pos_slider_actual, filtro_tipo, filtro_coincidencia):
    """Avanza a la siguiente ficha respetando filtros"""
    indices_filtrados = obtener_indices_filtrados()
    
    if not indices_filtrados:
        result = obtener_mensaje_sin_resultados()
        # Añadir 7 valores adicionales para completar 17 (ahora result tiene 10)
        return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", "Todos", "")
    
    # Encontrar el siguiente índice en la lista filtrada
    pos_actual = min(pos_slider_actual - 1, len(indices_filtrados) - 1)
    pos_siguiente = min(pos_actual + 1, len(indices_filtrados) - 1)
    
    indice_real = indices_filtrados[pos_siguiente]
    result = obtener_info_ficha(indice_real, indices_filtrados)
    # result tiene 10 valores, añadir 7 más para total de 17
    tipo_valor = result[5].get('value') if isinstance(result[5], dict) else result[5]
    fecha_valor = result[8].get('value') if isinstance(result[8], dict) else result[8]
    return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", tipo_valor, fecha_valor)

def anterior_ficha(pos_slider_actual, filtro_tipo, filtro_coincidencia):
    """Retrocede a la ficha anterior respetando filtros"""
    indices_filtrados = obtener_indices_filtrados()
    
    if not indices_filtrados:
        result = obtener_mensaje_sin_resultados()
        # Añadir 7 valores adicionales para completar 17
        return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", "Todos", "")
    
    # Encontrar el índice anterior en la lista filtrada
    pos_actual = min(pos_slider_actual - 1, len(indices_filtrados) - 1)
    pos_anterior = max(pos_actual - 1, 0)
    
    indice_real = indices_filtrados[pos_anterior]
    result = obtener_info_ficha(indice_real, indices_filtrados)
    # result tiene 10 valores, añadir 7 más para total de 17
    tipo_valor = result[5].get('value') if isinstance(result[5], dict) else result[5]
    fecha_valor = result[8].get('value') if isinstance(result[8], dict) else result[8]
    return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", tipo_valor, fecha_valor)

def ir_a_ficha(pos_slider, filtro_tipo, filtro_coincidencia):
    """Va a una ficha específica desde el slider respetando filtros"""
    indices_filtrados = obtener_indices_filtrados()
    
    if not indices_filtrados:
        result = obtener_mensaje_sin_resultados()
        # Añadir 7 valores adicionales para completar 17
        return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", "Todos", "")
    
    # Convertir la posición del slider (1-indexed) a índice de la lista filtrada
    pos_filtrada = min(max(pos_slider - 1, 0), len(indices_filtrados) - 1)
    indice_real = indices_filtrados[pos_filtrada]
    
    result = obtener_info_ficha(indice_real, indices_filtrados)
    # result tiene 10 valores, añadir 7 más para total de 17
    tipo_valor = result[5].get('value') if isinstance(result[5], dict) else result[5]
    fecha_valor = result[8].get('value') if isinstance(result[8], dict) else result[8]
    return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", tipo_valor, fecha_valor)

def primera_ficha(filtro_tipo, filtro_coincidencia):
    """Va a la primera ficha respetando filtros"""
    indices_filtrados = obtener_indices_filtrados()
    
    if not indices_filtrados:
        result = obtener_mensaje_sin_resultados()
        # Añadir 7 valores adicionales para completar 17: btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual, fecha_actual
        return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", "Todos", "")
    
    indice_real = indices_filtrados[0]
    result = obtener_info_ficha(indice_real, indices_filtrados)
    # result tiene 10 valores, añadir 7 más: btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual, fecha_actual
    tipo_valor = result[5].get('value') if isinstance(result[5], dict) else result[5]
    fecha_valor = result[8].get('value') if isinstance(result[8], dict) else result[8]
    return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", tipo_valor, fecha_valor)

def ultima_ficha(filtro_tipo, filtro_coincidencia):
    """Va a la última ficha respetando filtros"""
    indices_filtrados = obtener_indices_filtrados()
    
    if not indices_filtrados:
        result = obtener_mensaje_sin_resultados()
        # Añadir 7 valores adicionales para completar 17: btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual, fecha_actual
        return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", "Todos", "")
    
    indice_real = indices_filtrados[-1]
    result = obtener_info_ficha(indice_real, indices_filtrados)
    # result tiene 10 valores, añadir 7 más: btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual, fecha_actual
    tipo_valor = result[5].get('value') if isinstance(result[5], dict) else result[5]
    fecha_valor = result[8].get('value') if isinstance(result[8], dict) else result[8]
    return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", tipo_valor, fecha_valor)

def buscar_por_tipo(tipo_seleccionado, filtro_coincidencia):
    """Filtra y muestra la primera ficha del tipo seleccionado"""
    filtros_activos['tipo'] = tipo_seleccionado
    indices_filtrados = obtener_indices_filtrados()
    
    if not indices_filtrados:
        result = obtener_mensaje_sin_resultados()
        # Añadir 7 valores adicionales para completar 17: btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual, fecha_actual
        return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", "Todos", "")
    
    indice_real = indices_filtrados[0]
    result = obtener_info_ficha(indice_real, indices_filtrados)
    # result tiene 10 valores, añadir 7 más: btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual, fecha_actual
    tipo_valor = result[5].get('value') if isinstance(result[5], dict) else result[5]
    fecha_valor = result[8].get('value') if isinstance(result[8], dict) else result[8]
    return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", tipo_valor, fecha_valor)

def buscar_por_coincidencia(filtro_tipo, filtro_coincidencia):
    """Filtra y muestra la primera ficha según el filtro de coincidencia"""
    filtros_activos['coincidencia'] = filtro_coincidencia
    indices_filtrados = obtener_indices_filtrados()
    
    if not indices_filtrados:
        result = obtener_mensaje_sin_resultados()
        # Añadir 7 valores adicionales para completar 17: btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual, fecha_actual
        return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", "Todos", "")
    
    indice_real = indices_filtrados[0]
    result = obtener_info_ficha(indice_real, indices_filtrados)
    # result tiene 10 valores, añadir 7 más: btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual, fecha_actual
    tipo_valor = result[5].get('value') if isinstance(result[5], dict) else result[5]
    fecha_valor = result[8].get('value') if isinstance(result[8], dict) else result[8]
    return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", tipo_valor, fecha_valor)

def generar_tabla_movimientos():
    """Genera un DataFrame con los movimientos bancarios y sus coincidencias"""
    if movimientos_bancarios.empty:
        return pd.DataFrame()
    
    # Crear copia del dataframe
    df_resultado = movimientos_bancarios.copy()
    
    # Agregar columnas de coincidencia
    df_resultado['coincidencia_fecha'] = 'No'
    df_resultado['tipo'] = ''
    df_resultado['empresa'] = ''
    df_resultado['nombre_imagen_resultado'] = ''
    
    # Buscar coincidencias inversas (desde movimientos a fichas)
    for idx, mov in df_resultado.iterrows():
        for i, ficha in enumerate(datos):
            coincidencia = coincidencias_cache.get(i, {})
            
            # Si este movimiento está asignado a esta ficha
            if coincidencia.get('movimiento_asignado') == idx:
                # Marcar coincidencia de fecha
                if coincidencia.get('coincide_fecha'):
                    df_resultado.at[idx, 'coincidencia_fecha'] = 'Sí'
                else:
                    df_resultado.at[idx, 'coincidencia_fecha'] = 'No'
                
                # Agregar tipo
                df_resultado.at[idx, 'tipo'] = ficha.get('tipo_deducido', '')
                
                # Agregar empresa
                datos_extraidos = ficha.get('datos_extraidos', {})
                df_resultado.at[idx, 'empresa'] = datos_extraidos.get('empresa', '')
                
                # Agregar nombre de imagen
                df_resultado.at[idx, 'nombre_imagen_resultado'] = ficha.get('archivo_resultado', '')
                
                break  # Solo una ficha por movimiento
    
    # Seleccionar y ordenar columnas
    columnas_finales = [
        'fecha',
        'descripcion',
        'importe',
        'metodo',
        'coincidencia_fecha',
        'tipo',
        'empresa',
        'nombre_imagen_resultado'
    ]
    
    # Filtrar solo las columnas que existen
    columnas_existentes = [col for col in columnas_finales if col in df_resultado.columns]
    df_resultado = df_resultado[columnas_existentes]
    
    # Renombrar columnas para mejor visualización
    df_resultado = df_resultado.rename(columns={
        'fecha': 'Fecha',
        'descripcion': 'Descripción',
        'importe': 'Importe',
        'metodo': 'Método',
        'coincidencia_fecha': 'Coincidencia Fecha',
        'tipo': 'Tipo Documento',
        'empresa': 'Empresa',
        'nombre_imagen_resultado': 'Imagen Resultado'
    })
    
    return df_resultado

def generar_resumen_movimientos():
    """Genera el HTML con el resumen de movimientos bancarios"""
    total_movimientos = len(movimientos_bancarios)
    movimientos_asignados = sum(1 for _, mov in movimientos_bancarios.iterrows() if not pd.isna(mov.get('asignado_a')))
    movimientos_sin_asignar = total_movimientos - movimientos_asignados
    
    return f"""
#### 📊 Resumen
- **Total de movimientos:** {total_movimientos}
- **Movimientos asignados:** {movimientos_asignados} ({movimientos_asignados/total_movimientos*100:.1f}%)
- **Movimientos sin asignar:** {movimientos_sin_asignar} ({movimientos_sin_asignar/total_movimientos*100:.1f}%)
"""

def generar_estadisticas_documentos():
    """Genera el HTML con las estadísticas de documentos"""
    total_coincidencias_ambos = sum(1 for c in coincidencias_cache.values() if c.get('coincide_ambos'))
    total_coincidencias_importe = sum(1 for c in coincidencias_cache.values() if c.get('coincide_importe'))
    total_coincidencias_fecha = sum(1 for c in coincidencias_cache.values() if c.get('coincide_fecha'))
    total_sin_coincidencia = sum(1 for c in coincidencias_cache.values() if c.get('movimiento_asignado') is None)
    total_conflictos = sum(1 for tiene_conflicto in conflictos_cache.values() if tiene_conflicto)
    
    return f"""
    <div style='background-color: #ecf0f1; padding: 20px; border-radius: 10px;'>
        <h3 style='color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;'>📄 Documentos Procesados</h3>
        <p style='font-size: 1.2em;'><strong>Total de fichas:</strong> {len(datos)}</p>
        <p style='font-size: 1.2em;'><strong>Procesadas con éxito:</strong> {sum(1 for f in datos if f['procesado_exitoso'])}</p>
        <hr style='margin: 15px 0;'>
        <h4 style='color: #27ae60;'>🔍 Coincidencias Bancarias</h4>
        <p style='color: #28a745; font-size: 1.1em;'><strong>✅ Coincidencias completas:</strong> {total_coincidencias_ambos}</p>
        <p style='color: #ffc107; font-size: 1.1em;'><strong>💰 Solo por importe:</strong> {total_coincidencias_importe - total_coincidencias_ambos}</p>
        <p style='color: #ffc107; font-size: 1.1em;'><strong>📅 Solo por fecha:</strong> {total_coincidencias_fecha - total_coincidencias_ambos}</p>
        <p style='color: #dc3545; font-size: 1.1em;'><strong>❌ Sin coincidencias:</strong> {total_sin_coincidencia}</p>
        <hr style='margin: 15px 0;'>
        <h4 style='color: #ff6f00;'>⚠️ Conflictos</h4>
        <p style='color: #ff6f00; font-size: 1.1em;'><strong>🔄 Fichas con conflictos:</strong> {total_conflictos}</p>
        <p style='font-size: 0.9em; color: #666;'>Fichas con misma fecha e importe</p>
    </div>
    """

def generar_estadisticas_tipos():
    """Genera el HTML con las estadísticas por tipo de documento"""
    tipos_unicos_stats = sorted(list(set([f['tipo_deducido'] for f in datos])))
    
    stats_tipos = """
    <div style='background-color: #ecf0f1; padding: 20px; border-radius: 10px;'>
        <h3 style='color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;'>📋 Tipos de Documentos</h3>
    """
    for tipo in tipos_unicos_stats:
        count = sum(1 for f in datos if f['tipo_deducido'] == tipo)
        porcentaje = (count / len(datos) * 100) if len(datos) > 0 else 0
        stats_tipos += f"<p style='font-size: 1.1em;'><strong>{tipo.capitalize()}:</strong> {count} ({porcentaje:.1f}%)</p>"
    stats_tipos += "</div>"
    return stats_tipos

# Crear interfaz Gradio
with gr.Blocks(title="Dashboard de Resultados") as demo:
    gr.Markdown("""
    # 📊 Dashboard de Procesamiento de Documentos
    ### Navegue por los resultados procesados y visualice toda la información extraída
    """)
    
    with gr.Tabs():
        with gr.Tab("📄 Fichas de Documentos"):
            with gr.Row():
                with gr.Column(scale=1):
                    # Filtros
                    gr.Markdown("### 🔍 Filtros")
                    tipos_unicos = ["Todos"] + sorted(list(set([f['tipo_deducido'] for f in datos])))
                    filtro_tipo = gr.Dropdown(
                        choices=tipos_unicos,
                        label="Filtrar por tipo",
                        value="Todos"
                    )
                    
                    filtro_coincidencia = gr.Dropdown(
                        choices=["Todas", "Con coincidencia completa", "Con coincidencia parcial", "Sin coincidencia", "Conflictos"],
                        label="Filtrar por coincidencia",
                        value="Todas"
                    )
        
            with gr.Column(scale=2):
                # Panel de visualización
                with gr.Accordion("🖼️ Imagen del Documento", open=True) as imagen_accordion:
                    imagen_output = gr.Image(
                        label="Documento procesado",
                        type="pil",
                        height=400,
                        visible=True
                    )
                
                # Panel de navegación
                gr.HTML("<p style='font-size: 0.9em; font-weight: bold; margin-bottom: 5px;'>🧭 Navegación</p>")
                
                slider_indice = gr.Slider(
                    minimum=1,
                    maximum=len(datos),
                    step=1,
                    value=1,
                    label="Seleccionar ficha",
                    interactive=True
                )
                
                nav_text = gr.Textbox(
                    label="Posición actual",
                    interactive=False,
                    value=f"Ficha 1 de {len(datos)}"
                )
                
                nav_buttons_column = gr.Column(visible=True)
                with nav_buttons_column:
                    with gr.Row():
                        btn_primera = gr.Button("⏮️ Primera", size="sm")
                        btn_anterior = gr.Button("◀️ Anterior", size="sm")
                        btn_siguiente = gr.Button("Siguiente ▶️", size="sm")
                        btn_ultima = gr.Button("Última ⏭️", size="sm")
                
                gr.Markdown("### 📋 Información Detallada")
                info_output = gr.HTML()
                
                # Editor de tipo (se mostrará después de la información)
                editor_column = gr.Column(visible=True)
                with editor_column:
                    with gr.Row():
                        fecha_editor = gr.Textbox(
                            label="📅 Editar fecha (DD/MM/YYYY)",
                            placeholder="DD/MM/YYYY",
                            interactive=True,
                            scale=2
                        )
                        btn_guardar_fecha = gr.Button("💾 Confirmar Fecha", variant="primary", visible=False, scale=1, size="sm")
                    
                    with gr.Row():
                        tipo_editor = gr.Dropdown(
                            choices=tipos_unicos[1:],  # Excluir "Todos"
                            label="✏️ Editar tipo de documento",
                            interactive=True,
                            scale=3
                        )
                        btn_guardar_tipo = gr.Button("💾 Confirmar Tipo", variant="primary", visible=False, scale=1, size="sm")
                
                # Botón para aceptar conflictos e ignorar recibos
                with gr.Row():
                    btn_aceptar_conflicto = gr.Button("✅ Aceptar Conflicto", variant="secondary", visible=False, size="sm")
                    btn_ignorar = gr.Button("🗑️ Ignorar Recibo", variant="stop", visible=True, size="sm")
                
                mensaje_guardado = gr.Textbox(label="", value="", visible=False, interactive=False, container=False)
                mensaje_fecha = gr.Textbox(label="", value="", visible=False, interactive=False, container=False)
                mensaje_conflicto = gr.Textbox(label="", value="", visible=False, interactive=False, container=False)
                mensaje_ignorado = gr.Textbox(label="", value="", visible=False, interactive=False, container=False)
                indice_hidden = gr.Number(value=0, visible=False)  # Campo oculto para almacenar el índice
                fecha_actual_ficha = gr.State(value="")  # Estado para mantener la fecha original
        
        with gr.Tab("🏦 Movimientos Bancarios"):
            gr.Markdown("""
            ### Lista de Movimientos Bancarios con Coincidencias
            Esta tabla muestra todos los movimientos bancarios con información sobre las coincidencias encontradas.
            """)
            
            # Generar la tabla de movimientos
            tabla_movimientos = gr.Dataframe(
                value=generar_tabla_movimientos(),
                label="Movimientos Bancarios",
                interactive=False,
                wrap=True,
                column_widths=["10%", "25%", "8%", "10%", "12%", "10%", "15%", "10%"]
            )
            
            # Agregar estadísticas
            resumen_movimientos = gr.Markdown(generar_resumen_movimientos())
        
        with gr.Tab("📈 Estadísticas"):
            gr.Markdown("### 📊 Estadísticas Generales")
            
            with gr.Row():
                with gr.Column():
                    stats_documentos = gr.HTML(generar_estadisticas_documentos())
                
                with gr.Column():
                    stats_tipos = gr.HTML(generar_estadisticas_tipos())
    
    # Estado para mantener el tipo original
    tipo_actual_ficha = gr.State(value="")
    
    # Conectar eventos
    btn_siguiente.click(
        fn=siguiente_ficha,
        inputs=[slider_indice, filtro_tipo, filtro_coincidencia],
        outputs=[imagen_output, info_output, nav_text, slider_indice, gr.Number(visible=False), tipo_editor, indice_hidden, btn_aceptar_conflicto, fecha_editor, btn_ignorar, btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual_ficha, fecha_actual_ficha]
    )
    
    btn_anterior.click(
        fn=anterior_ficha,
        inputs=[slider_indice, filtro_tipo, filtro_coincidencia],
        outputs=[imagen_output, info_output, nav_text, slider_indice, gr.Number(visible=False), tipo_editor, indice_hidden, btn_aceptar_conflicto, fecha_editor, btn_ignorar, btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual_ficha, fecha_actual_ficha]
    )
    
    btn_primera.click(
        fn=primera_ficha,
        inputs=[filtro_tipo, filtro_coincidencia],
        outputs=[imagen_output, info_output, nav_text, slider_indice, gr.Number(visible=False), tipo_editor, indice_hidden, btn_aceptar_conflicto, fecha_editor, btn_ignorar, btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual_ficha, fecha_actual_ficha]
    )
    
    btn_ultima.click(
        fn=ultima_ficha,
        inputs=[filtro_tipo, filtro_coincidencia],
        outputs=[imagen_output, info_output, nav_text, slider_indice, gr.Number(visible=False), tipo_editor, indice_hidden, btn_aceptar_conflicto, fecha_editor, btn_ignorar, btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual_ficha, fecha_actual_ficha]
    )
    
    slider_indice.change(
        fn=ir_a_ficha,
        inputs=[slider_indice, filtro_tipo, filtro_coincidencia],
        outputs=[imagen_output, info_output, nav_text, slider_indice, gr.Number(visible=False), tipo_editor, indice_hidden, btn_aceptar_conflicto, fecha_editor, btn_ignorar, btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual_ficha, fecha_actual_ficha]
    )
    
    filtro_tipo.change(
        fn=buscar_por_tipo,
        inputs=[filtro_tipo, filtro_coincidencia],
        outputs=[imagen_output, info_output, nav_text, slider_indice, gr.Number(visible=False), tipo_editor, indice_hidden, btn_aceptar_conflicto, fecha_editor, btn_ignorar, btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual_ficha, fecha_actual_ficha]
    )
    
    filtro_coincidencia.change(
        fn=buscar_por_coincidencia,
        inputs=[filtro_tipo, filtro_coincidencia],
        outputs=[imagen_output, info_output, nav_text, slider_indice, gr.Number(visible=False), tipo_editor, indice_hidden, btn_aceptar_conflicto, fecha_editor, btn_ignorar, btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual_ficha, fecha_actual_ficha]
    )
    
    # Evento para detectar cambios en el tipo y mostrar el botón de confirmar
    def mostrar_boton_guardar(tipo_nuevo, tipo_original):
        if tipo_nuevo != tipo_original:
            return gr.update(visible=True), gr.update(visible=False, value="")
        else:
            return gr.update(visible=False), gr.update(visible=False, value="")
    
    tipo_editor.change(
        fn=mostrar_boton_guardar,
        inputs=[tipo_editor, tipo_actual_ficha],
        outputs=[btn_guardar_tipo, mensaje_guardado]
    )
    
    # Evento para detectar cambios en la fecha y mostrar el botón de confirmar
    def mostrar_boton_guardar_fecha(fecha_nueva, fecha_original):
        if fecha_nueva != fecha_original:
            return gr.update(visible=True), gr.update(visible=False, value="")
        else:
            return gr.update(visible=False), gr.update(visible=False, value="")
    
    fecha_editor.change(
        fn=mostrar_boton_guardar_fecha,
        inputs=[fecha_editor, fecha_actual_ficha],
        outputs=[btn_guardar_fecha, mensaje_fecha]
    )
    
    # Evento para guardar cambios y actualizar la ficha
    def confirmar_cambio_tipo(indice, nuevo_tipo, filtro_t, filtro_c):
        mensaje = guardar_cambio_tipo(indice, nuevo_tipo)
        # Obtener la información actualizada de la ficha
        indices_filtrados = obtener_indices_filtrados()
        result = obtener_info_ficha(indice, indices_filtrados)
        # Regenerar las tablas y estadísticas
        tabla_actualizada = generar_tabla_movimientos()
        resumen_actualizado = generar_resumen_movimientos()
        stats_doc = generar_estadisticas_documentos()
        stats_tip = generar_estadisticas_tipos()
        # Retornar: info_html actualizado, botón invisible, mensaje visible, tipo actualizado, btn_aceptar_conflicto, fecha_editor, tabla, resumen, estadísticas
        return result[1], gr.update(visible=False), gr.update(visible=True, value=mensaje), result[5], result[7], result[8], tabla_actualizada, resumen_actualizado, stats_doc, stats_tip
    
    btn_guardar_tipo.click(
        fn=confirmar_cambio_tipo,
        inputs=[indice_hidden, tipo_editor, filtro_tipo, filtro_coincidencia],
        outputs=[info_output, btn_guardar_tipo, mensaje_guardado, tipo_actual_ficha, btn_aceptar_conflicto, fecha_editor, tabla_movimientos, resumen_movimientos, stats_documentos, stats_tipos]
    )
    
    # Evento para guardar cambio de fecha
    def confirmar_cambio_fecha(indice, nueva_fecha, filtro_t, filtro_c):
        mensaje = guardar_cambio_fecha(indice, nueva_fecha)
        # Obtener la información actualizada de la ficha
        indices_filtrados = obtener_indices_filtrados()
        result = obtener_info_ficha(indice, indices_filtrados)
        # Regenerar las tablas y estadísticas
        tabla_actualizada = generar_tabla_movimientos()
        resumen_actualizado = generar_resumen_movimientos()
        stats_doc = generar_estadisticas_documentos()
        stats_tip = generar_estadisticas_tipos()
        # Retornar: info_html actualizado, botón invisible, mensaje visible, fecha actualizada, btn_aceptar_conflicto, tabla, resumen, estadísticas
        return result[1], gr.update(visible=False), gr.update(visible=True, value=mensaje), result[8], result[7], tabla_actualizada, resumen_actualizado, stats_doc, stats_tip
    
    btn_guardar_fecha.click(
        fn=confirmar_cambio_fecha,
        inputs=[indice_hidden, fecha_editor, filtro_tipo, filtro_coincidencia],
        outputs=[info_output, btn_guardar_fecha, mensaje_fecha, fecha_actual_ficha, btn_aceptar_conflicto, tabla_movimientos, resumen_movimientos, stats_documentos, stats_tipos]
    )    
    # Evento para aceptar conflicto
    def confirmar_aceptar_conflicto(indice, filtro_t, filtro_c):
        mensaje, exito = aceptar_conflicto(indice)
        if exito:
            # Obtener la información actualizada de la ficha
            indices_filtrados = obtener_indices_filtrados()
            result = obtener_info_ficha(indice, indices_filtrados)
            # Regenerar estadísticas
            stats_doc = generar_estadisticas_documentos()
            # Retornar: info_html actualizado, botón invisible, mensaje visible, estadísticas
            return result[1], gr.update(visible=False), gr.update(visible=True, value=mensaje), stats_doc
        else:
            # Si hay error, solo mostrar mensaje
            return gr.update(), gr.update(), gr.update(visible=True, value=mensaje), gr.update()
    
    btn_aceptar_conflicto.click(
        fn=confirmar_aceptar_conflicto,
        inputs=[indice_hidden, filtro_tipo, filtro_coincidencia],
        outputs=[info_output, btn_aceptar_conflicto, mensaje_conflicto, stats_documentos]
    )
    
    # Evento para ignorar recibo
    def confirmar_ignorar_recibo(indice, filtro_t, filtro_c):
        mensaje, exito = ignorar_recibo(indice)
        if exito:
            # Obtener la siguiente ficha disponible después de ignorar
            indices_filtrados = obtener_indices_filtrados()
            
            if not indices_filtrados:
                # No hay más fichas que mostrar
                result = obtener_mensaje_sin_resultados()
                tabla_actualizada = generar_tabla_movimientos()
                resumen_actualizado = generar_resumen_movimientos()
                stats_doc = generar_estadisticas_documentos()
                # Retornar: result (10 valores) + btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_ignorado (visible), tabla, resumen, estadisticas
                return result + (gr.update(visible=False), gr.update(visible=False), "", "", gr.update(visible=True, value=mensaje), tabla_actualizada, resumen_actualizado, stats_doc)
            else:
                # Mostrar la primera ficha de la lista filtrada
                indice_siguiente = indices_filtrados[0]
                result = obtener_info_ficha(indice_siguiente, indices_filtrados)
                # Regenerar las tablas y estadísticas
                tabla_actualizada = generar_tabla_movimientos()
                resumen_actualizado = generar_resumen_movimientos()
                stats_doc = generar_estadisticas_documentos()
                tipo_valor = result[5].get('value') if isinstance(result[5], dict) else result[5]
                fecha_valor = result[8].get('value') if isinstance(result[8], dict) else result[8]
                # Retornar: result (10 valores) + btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_ignorado (visible), tipo_actual, fecha_actual, tabla, resumen, estadisticas
                return result + (gr.update(visible=False), gr.update(visible=False), "", "", gr.update(visible=True, value=mensaje), tipo_valor, fecha_valor, tabla_actualizada, resumen_actualizado, stats_doc)
        else:
            # Si hay error, solo mostrar mensaje
            return (gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), 
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), 
                    "", "", gr.update(visible=True, value=mensaje), gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
    
    btn_ignorar.click(
        fn=confirmar_ignorar_recibo,
        inputs=[indice_hidden, filtro_tipo, filtro_coincidencia],
        outputs=[imagen_output, info_output, nav_text, slider_indice, gr.Number(visible=False), tipo_editor, indice_hidden, btn_aceptar_conflicto, fecha_editor, btn_ignorar, btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_ignorado, tipo_actual_ficha, fecha_actual_ficha, tabla_movimientos, resumen_movimientos, stats_documentos]
    )
    
    # Cargar la primera ficha al inicio
    def cargar_primera_ficha():
        result = obtener_info_ficha(0, list(range(len(datos))))
        tipo_inicial = result[5].get('value') if isinstance(result[5], dict) else result[5]
        fecha_inicial = result[8].get('value') if isinstance(result[8], dict) else result[8]
        # result tiene 10 valores (incluyendo btn_ignorar), necesitamos añadir 7 más para coincidir con los outputs (total: 17)
        return result + (gr.update(visible=False), gr.update(visible=False), "", "", "", tipo_inicial, fecha_inicial)
    
    demo.load(
        fn=cargar_primera_ficha,
        inputs=[],
        outputs=[imagen_output, info_output, nav_text, slider_indice, gr.Number(visible=False), tipo_editor, indice_hidden, btn_aceptar_conflicto, fecha_editor, btn_ignorar, btn_guardar_tipo, btn_guardar_fecha, mensaje_guardado, mensaje_fecha, mensaje_conflicto, tipo_actual_ficha, fecha_actual_ficha]
    )

if __name__ == "__main__":
    print(f"🚀 Iniciando dashboard con {len(datos)} fichas procesadas...")
    demo.launch(share=False, server_name="127.0.0.1", server_port=7860, theme=gr.themes.Soft())
