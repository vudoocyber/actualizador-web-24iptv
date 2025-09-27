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
    if "fútbol" in texto or "liga" in texto or "copa" in texto or "championship" in texto or "eredivise" in texto or "superliga" in texto or "⚽" in texto: return "futbol"
    if "nfl" in texto or "cfl" in texto or "🏈" in texto: return "futbol_americano"
    if "mlb" in texto or "beisbol" in texto or "⚾" in texto: return "beisbol"
    if "nba" in texto or "wnba" in texto or "cibacopa" in texto or "🏀" in texto: return "baloncesto"
    if "ufc" in texto or "box" in texto or "wrestling" in texto or "🤼" in texto or "🥊" in texto: return "combate"
    if "tenis" in texto or "open" in texto or "🎾" in texto: return "tenis"
    if "nascar" in texto or "racing" in texto or "🏎️" in texto: return "carreras"
    if "golf" in texto or "pga" in texto or "liv" in texto or "⛳" in texto: return "golf"
    if "voleybol" in texto or "volleyball" in texto or "🏐" in texto: return "voleibol"
    if "rugby" in texto or "🏉" in texto: return "rugby"
    if "nhl" in texto or "hockey" in texto or "🏒" in texto: return "hockey"
    return "default"

def extraer_hora_centro(horario_str):
    match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:a\.m\.|p\.m\.|am|pm))\s+Centro', horario_str, re.IGNORECASE)
    if match: return match.group(1)
    return None

def convertir_hora_a_24h(hora_str):
    if not hora_str: return None
    hora_str = hora_str.lower().replace('.', '')
    match = re.search(r'(\d+)(?::\d+))?\s*(am|pm)', hora_str)
    if not match: return None
    hora, minuto, periodo = match.groups()
    hora = int(hora)
    minuto = int(minuto) if minuto else 0
    if periodo == 'pm' and hora != 12: hora += 12
    if periodo == 'am' and hora == 12: hora = 0
    return hora + (minuto / 60.0)

def obtener_resultados_en_lote(partidos_finalizados, fecha_eventos):
    if not GEMINI_API_KEY: return []
    if not partidos_finalizados: return []
    print(f"Contactando a Gemini para buscar resultados de {len(partidos_finalizados)} partidos...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # --- CAMBIO IMPORTANTE: Usamos el modelo que SÍ está en tu lista ---
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        lista_para_prompt = "\n".join(partidos_finalizados)
        prompt = f"""
        Actúa como un asistente de resultados deportivos. Te daré una lista de partidos que ya finalizaron en la fecha: {fecha_eventos}. Para cada partido, busca el resultado final.
        Devuelve tu respuesta como un array JSON válido y nada más. Cada objeto debe tener "partido" y "resultado".
        Si no encuentras un resultado, omítelo del array.
        Ejemplo: [{{"partido": "Equipo A vs Equipo B", "resultado": "2-1"}}]
        LISTA DE PARTIDOS A BUSCAR:
        {lista_para_prompt}
        """
        response = model.generate_content(prompt, request_options={'timeout': 180})
        respuesta_limpia = response.text.strip().replace("```json", "").replace("```", "").strip()
        print(f"Respuesta JSON de Gemini recibida:\n{respuesta_limpia}")
        return json.loads(respuesta_limpia)
    except Exception as e:
        print(f"ERROR al contactar o procesar la respuesta de Gemini: {e}")
        return []

def main():
    print(f"Iniciando proceso de búsqueda de resultados...")
    mexico_city_tz = pytz.timezone("America/Mexico_City")
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        respuesta = requests.get(URL_JSON_FUENTE, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        lista_eventos_original = datos.get("eventos", [])
        titulo_guia = datos.get("titulo_guia", "")
        fecha_extraida = re.sub('<[^<]+?>', '', titulo_guia).split(',')[-1].strip().replace(str(datetime.now().year), "").strip()
        if not lista_eventos_original or not fecha_extraida:
            raise ValueError("El archivo events.json está vacío o no contiene una fecha en el título.")
        print(f"Archivo events.json leído. Fecha de la guía: {fecha_extraida}")
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    print("2. Identificando todos los partidos finalizados...")
    partidos_a_consultar = []
    
    duracion_por_deporte = {
        "futbol": 2.0, "futbol_americano": 3.5, "beisbol": 3.0, "baloncesto": 2.5,
        "combate": 3.0, "tenis": 2.5, "carreras": 3.5, "golf": 4.5,
        "voleibol": 2.0, "rugby": 2.0, "hockey": 2.5, "default": 3.0
    }

    hora_actual_mexico = datetime.now(mexico_city_tz)
    hora_actual_float = hora_actual_mexico.hour + (hora_actual_mexico.minute / 60.0)
    print(f"Hora actual (Ciudad de México): {hora_actual_mexico.strftime('%I:%M %p %Z')}")

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
                partidos_a_consultar.append(partido['descripcion'])

    print(f"Se encontraron {len(partidos_a_consultar)} partidos finalizados para consultar.")
    resultados_de_gemini = obtener_resultados_en_lote(partidos_a_consultar, fecha_extraida)
    mapa_resultados = {res["partido"]: res["resultado"] for res in resultados_de_gemini}
    
    resultados_finales = []
    for descripcion, resultado in mapa_resultados.items():
        resultados_finales.append({
            "descripcion": descripcion,
            "resultado": resultado,
            "estado": "Finalizado"
        })

    json_salida = {"fecha_actualizacion": hora_actual_mexico.isoformat(), "resultados": resultados_finales}

    print(f"3. Guardando archivo local '{NOMBRE_ARCHIVO_SALIDA}' con {len(resultados_finales)} resultados...")
    with open(NOMBRE_ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(json_salida, f, indent=4, ensure_ascii=False)
    print("Archivo local guardado.")
    
    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return
    
    print(f"4. Subiendo '{NOMBRE_ARCHIVO_SALIDA}' al servidor FTP...")
    try:
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.set_pasv(True)
            ftp.cwd(RUTA_REMOTA_FTP)
            with open(NOMBRE_ARCHIVO_SALIDA, 'rb') as file:
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_SALIDA}', file)
            print("¡Archivo de resultados subido exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso de búsqueda de resultados finalizado ---")
