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

def obtener_url_resultado_gemini(descripcion_partido, fecha_evento):
    if not GEMINI_API_KEY: return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Actúa como un asistente de búsqueda. Tu única tarea es generar la URL de búsqueda de Google más probable para encontrar el resultado final del siguiente partido que se jugó en la fecha indicada.
        
        PARTIDO: "{descripcion_partido}"
        FECHA DEL PARTIDO: "{fecha_evento}"

        Responde ÚNICAMENTE con la URL. No añadas explicaciones ni ningún otro texto.
        Ejemplo de respuesta: https://www.google.com/search?q=resultado+final+{descripcion_partido.replace(" ", "+")}+{fecha_evento.replace(" ", "+")}
        """
        
        response = model.generate_content(prompt, request_options={'timeout': 90})
        url_resultado = response.text.strip()
        if url_resultado.startswith("http"):
            print(f"  > URL de Gemini para '{descripcion_partido}': {url_resultado}")
            return url_resultado
        return None
    except Exception as e:
        print(f"  > ERROR al contactar con Gemini para '{descripcion_partido}': {e}")
        return None

# --- 3. FUNCIÓN PRINCIPAL ---
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
        fecha_extraida = re.sub('<[^<]+?>', '', titulo_guia).split(',')[-1].strip()
        if not lista_eventos_original or not fecha_extraida:
            raise ValueError("El archivo events.json está vacío o no contiene una fecha en el título.")
        print(f"Archivo events.json leído. Fecha de la guía: {fecha_extraida}")
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    print("2. Identificando partidos finalizados y buscando URLs de resultados...")
    resultados_finales = []
    
    hora_actual_mexico = datetime.now(mexico_city_tz)
    hora_actual_float = hora_actual_mexico.hour + (hora_actual_mexico.minute / 60.0)
    print(f"Hora actual (Ciudad de México): {hora_actual_mexico.strftime('%I:%M %p %Z')}")

    for evento in lista_eventos_original:
        if "partido_relevante" in evento: continue
        for partido in evento.get("partidos", []):
            horario_str = partido.get("horarios", "")
            hora_centro_str = extraer_hora_centro(horario_str)
            if not hora_centro_str: continue
            hora_ct_24 = convertir_hora_a_24h(hora_centro_str)
            if hora_ct_24 is None: continue
            
            if hora_actual_float > hora_ct_24 + 1.5:
                print(f"- Partido finalizado detectado: {partido['descripcion']}")
                url = obtener_url_resultado_gemini(partido['descripcion'], fecha_extraida)
                if url:
                    resultados_finales.append({
                        "descripcion": partido["descripcion"],
                        "estado": "Finalizado",
                        "url_resultado": url
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
