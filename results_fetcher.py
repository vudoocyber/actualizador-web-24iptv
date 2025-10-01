import requests
import json
import os
from ftplib import FTP
from datetime import datetime
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
    texto = evento_principal.lower()
    if any(keyword in texto for keyword in ["fútbol", "liga", "copa", "championship", "eredivise", "superliga", "⚽"]):
        return "futbol"
    if any(keyword in texto for keyword in ["nfl", "cfl", "🏈"]):
        return "futbol_americano"
    # ... (resto de la función sin cambios)
    return "default"

def extraer_hora_centro(horario_str):
    match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:a\.m\.|p\.m\.|am|pm))\s+Centro', horario_str, re.IGNORECASE)
    if match: return match.group(1)
    return None

def convertir_hora_a_24h(hora_str):
    if not hora_str: return None
    hora_str = hora_str.lower().replace('.', '')
    match = re.search(r'(\d+)(?::(\d+))?\s*(am|pm)', hora_str)
    if not match: return None
    hora, minuto, periodo = match.groups()
    hora = int(hora)
    minuto = int(minuto) if minuto else 0
    if periodo == 'pm' and hora != 12: hora += 12
    if periodo == 'am' and hora == 12: hora = 0
    return hora + (minuto / 60.0)

# --- FUNCIÓN DE IA ACTUALIZADA ---
def obtener_resultados_en_lote(partidos_finalizados, fecha_eventos):
    if not GEMINI_API_KEY: return []
    if not partidos_finalizados: return []
    print(f"Contactando a Gemini para buscar resultados de {len(partidos_finalizados)} partidos...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        lista_para_prompt = "\n".join(partidos_finalizados)
        prompt = f"""
        Actúa como un asistente de resultados deportivos. Te daré una lista de partidos que ya finalizaron en la fecha: {fecha_eventos}. Para cada partido, busca el resultado final.
        Devuelve tu respuesta como un array JSON válido y nada más. Cada objeto debe tener "partido" y "resultado".
        Si no encuentras el resultado para un partido, omítelo del array.
        Ejemplo de respuesta:
        [
          {{"partido": "Estoril vs Estrela", "resultado": "1-0"}},
          {{"partido": "Porto vs Vitoria Guimaraes", "resultado": "2-2"}}
        ]
        LISTA DE PARTIDOS A BUSCAR:
        {lista_para_prompt}
        """
        response = model.generate_content(prompt, request_options={'timeout': 180})
        respuesta_cruda = response.text.strip()
        print(f"Respuesta CRUDA de Gemini recibida:\n{respuesta_cruda}")
        
        # --- LÓGICA DE EXTRACCIÓN INTELIGENTE ---
        # Busca el inicio del array '[' y el final ']'
        inicio_json = respuesta_cruda.find('[')
        fin_json = respuesta_cruda.rfind(']')
        
        if inicio_json != -1 and fin_json != -1:
            json_str = respuesta_cruda[inicio_json : fin_json + 1]
            return json.loads(json_str)
        else:
            print("  > [ERROR] No se encontró un array JSON válido en la respuesta de la IA.")
            return []
        # --- FIN DE LA LÓGICA ---

    except Exception as e:
        print(f"ERROR al contactar o procesar la respuesta de Gemini: {e}")
        return []

# --- 3. FUNCIÓN PRINCIPAL ---
def main():
    # ... (El resto del código de 'main' se mantiene exactamente igual)
