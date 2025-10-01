import requests
import json
import os
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import pytz
import re
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA = "results.json"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- 2. FUNCIONES AUXILIARES ---
def identificar_deporte(evento_principal):
    # ... (código sin cambios)
def extraer_hora_centro(horario_str):
    # ... (código sin cambios)
def convertir_hora_a_24h(hora_str):
    # ... (código sin cambios)
def obtener_url_resultado_gemini(busqueda_precisa, fecha_evento):
    # ... (código sin cambios)

# --- 3. FUNCIÓN PRINCIPAL ---
def main():
    print(f"Iniciando proceso de búsqueda de resultados...")
    mexico_city_tz = pytz.timezone("America/Mexico_City")
    
    try:
        # ... (código de descarga de JSON sin cambios)
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    print("2. Identificando partidos finalizados y buscando URLs de resultados...")
    resultados_finales = []
    
    duracion_por_deporte = {
        "futbol": 2.0, "futbol_americano": 3.5, "beisbol": 3.0, "baloncesto": 2.5,
        "combate": 3.0, "tenis": 2.5, "carreras": 3.5, "golf": 4.5,
        "voleibol": 2.0, "rugby": 2.0, "hockey": 2.5, "default": 3.0
    }

    hora_actual_mexico = datetime.now(mexico_city_tz)
    hora_actual_float = hora_actual_mexico.hour + (hora_actual_mexico.minute / 60.0)
    print(f"Hora actual (Ciudad de México): {hora_actual_mexico.strftime('%I:%M %p %Z')}")
    
    emoji_pattern = re.compile("[" u"\U0001F600-\U0001F64F" ... "]+", flags=re.UNICODE)

    for evento in lista_eventos_original:
        if "partido_relevante" in evento: continue
        
        deporte_actual = identificar_deporte(evento.get("evento_principal", ""))
        tiempo_de_espera = duracion_por_deporte.get(deporte_actual, 3.0)

        for partido in evento.get("partidos", []):
            horario_str = partido.get("horarios", "")
            
            hora_centro_str = extraer_hora_centro(horario_str)
            if not hora_centro_str: continue

            hora_ct_24 = convertir_hora_a_24h(hora_centro_str)
            if hora_ct_24 is None: continue
            
            if hora_actual_float > hora_ct_24 + tiempo_de_espera:
                print(f"- Partido finalizado detectado ({deporte_actual}): {partido['descripcion']}")
                
                # --- INICIO DE LA CORRECCIÓN ---
                evento_principal_limpio = emoji_pattern.sub('', evento['evento_principal']).strip()
                # Se elimina la palabra "Resultado" de aquí para evitar duplicados
                busqueda_precisa = f"{evento_principal_limpio} {partido['descripcion']}"
                # --- FIN DE LA CORRECCIÓN ---
                
                url = obtener_url_resultado_gemini(busqueda_precisa, fecha_extraida)
                if url:
                    resultados_finales.append({
                        "descripcion": partido["descripcion"],
                        "estado": "Finalizado",
                        "url_resultado": url
                    })

    # ... (El resto del script para guardar y subir no cambia)
