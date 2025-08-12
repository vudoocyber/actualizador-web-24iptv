import requests
import json
import os
from ftplib import FTP
from datetime import datetime
import pytz # <-- Nueva librería
import re
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA = "results.json"
# ... (resto de la configuración igual)
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- (Las funciones auxiliares como 'extraer_hora_centro', etc., no cambian) ---
def extraer_hora_centro(horario_str): # ...
def convertir_hora_a_24h(hora_str): # ...
def obtener_url_resultado_gemini(descripcion_partido): # ...

# --- FUNCIÓN PRINCIPAL (MODIFICADA) ---
def main():
    # ... (La primera parte de la función para leer el JSON no cambia) ...
    
    # --- LÓGICA DE TIEMPO AHORA USA LA ZONA HORARIA DE MÉXICO ---
    mexico_city_tz = pytz.timezone("America/Mexico_City")
    hora_actual_mexico = datetime.now(mexico_city_tz)
    hora_actual_float = hora_actual_mexico.hour + (hora_actual_mexico.minute / 60.0)
    print(f"Hora actual (Ciudad de México): {hora_actual_mexico.strftime('%I:%M %p %Z')}")

    for evento in lista_eventos_original:
        # ... (La lógica para detectar partidos finalizados y llamar a Gemini no cambia) ...
    
    # --- LA FECHA DE ACTUALIZACIÓN AHORA ES LA DE MÉXICO ---
    json_salida = {
        "fecha_actualizacion": hora_actual_mexico.isoformat(),
        "resultados": resultados_finales
    }

    # ... (El resto de la función para guardar y subir por FTP no cambia) ...
