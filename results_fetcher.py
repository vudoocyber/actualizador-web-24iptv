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
MEXICO_TZ = pytz.timezone('America/Mexico_City')

# --- 2. FUNCIONES AUXILIARES ---
def identificar_deporte(evento_principal):
    texto = evento_principal.lower()
    if any(keyword in texto for keyword in ["fútbol", "liga", "copa", "championship", "eredivise", "superliga", "⚽"]): return "futbol"
    if any(keyword in texto for keyword in ["nfl", "cfl", "🏈"]): return "futbol_americano"
    if any(keyword in texto for keyword in ["mlb", "beisbol", "⚾"]): return "beisbol"
    if any(keyword in texto for keyword in ["nba", "wnba", "cibacopa", "🏀"]): return "baloncesto"
    if any(keyword in texto for keyword in ["ufc", "box", "wrestling", "🤼", "🥊"]): return "combate"
    if any(keyword in texto for keyword in ["tenis", "open", "🎾"]): return "tenis"
    if any(keyword in texto for keyword in ["nascar", "racing", "🏎️"]): return "carreras"
    if any(keyword in texto for keyword in ["golf", "pga", "liv", "⛳"]): return "golf"
    if any(keyword in texto for keyword in ["voleybol", "volleyball", "🏐"]): return "voleibol"
    if any(keyword in texto for keyword in ["rugby", "🏉"]): return "rugby"
    if any(keyword in texto for keyword in ["nhl", "hockey", "🏒"]): return "hockey"
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

def obtener_url_resultado_gemini(busqueda_precisa, fecha_evento):
    if not GEMINI_API_KEY: return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Actúa como un asistente de búsqueda. Tu única tarea es generar la URL de búsqueda de Google más probable para encontrar el resultado final del siguiente evento que se jugó en la fecha indicada.
        BÚSQUEDA: "{busqueda_precisa}"
        FECHA DEL EVENTO: "{fecha_evento}"
        Responde ÚNICAMENTE con la URL.
        Ejemplo: https://www.google.com/search?q=resultado+{busqueda_precisa.replace(" ", "+")}+{fecha_evento.replace(" ", "+")}
        """
        response = model.generate_content(prompt, request_options={'timeout': 90})
        url_resultado = response.text.strip()
        if url_resultado.startswith("http"):
            print(f"  > URL de Gemini generada: {url_resultado}")
            return url_resultado
        return None
    except Exception as e:
        print(f"  > ERROR al contactar con Gemini: {e}")
        return None

# --- 3. FUNCIÓN PRINCIPAL (CON VALIDACIÓN DE FECHA) ---
def main():
    print(f"Iniciando proceso de búsqueda de resultados...")
    
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        respuesta = requests.get(URL_JSON_FUENTE, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()

        # --- INICIO DE LA NUEVA LÓGICA DE VALIDACIÓN ---
        fecha_guia_str = datos.get("fecha_guia")
        if not fecha_guia_str:
            print("ERROR: La etiqueta 'fecha_guia' no fue encontrada en events.json. Proceso detenido.")
            return

        hoy_mexico_str = datetime.now(MEXICO_TZ).strftime('%Y-%m-%d')

        if fecha_guia_str != hoy_mexico_str:
            print(f"ADVERTENCIA: La fecha de la guía ({fecha_guia_str}) no es la de hoy ({hoy_mexico_str}). No se buscarán resultados.")
            return # Detiene la ejecución si las fechas no coinciden
        
        print(f"Fecha de la guía ({fecha_guia_str}) confirmada. Continuando con la búsqueda de resultados.")
        # --- FIN DE LA NUEVA LÓGICA DE VALIDACIÓN ---

        lista_eventos_original = datos.get("eventos", [])
        titulo_guia = datos.get("titulo_guia", "")
        fecha_extraida_para_busqueda = re.sub('<[^<]+?>', '', titulo_guia).split(',')[-1].strip().replace(str(datetime.now().year), "").strip()

    except Exception as e:
        print(f"ERROR FATAL al leer o validar el archivo JSON: {e}")
        return

    print("2. Identificando partidos finalizados y buscando URLs de resultados...")
    resultados_finales = []
    
    duracion_por_deporte = {
        "futbol": 1.9, "futbol_americano": 3.3, "beisbol": 2.7, "baloncesto": 2.3,
        "combate": 3.0, "tenis": 2.5, "carreras": 3.5, "golf": 4.5,
        "voleibol": 2.0, "rugby": 2.0, "hockey": 2.5, "default": 3.0
    }

    hora_actual_mexico = datetime.now(MEXICO_TZ)
    hora_actual_float = hora_actual_mexico.hour + (hora_actual_mexico.minute / 60.0)
    print(f"Hora actual (Ciudad de México): {hora_actual_mexico.strftime('%I:%M %p %Z')}")

    emoji_pattern = re.compile("[" u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF" u"\U0001F680-\U0001F6FF" u"\U0001F1E0-\U0001F1FF" u"\u2600-\u26FF" u"\u2700-\u27BF" "]+", flags=re.UNICODE)

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
                print(f"- Partido finalizado detectado ({deporte_actual}, espera: {tiempo_de_espera}h): {partido['descripcion']}")
                
                evento_principal_limpio = emoji_pattern.sub('', evento['evento_principal']).strip()
                busqueda_precisa = f"{evento_principal_limpio} {partido['descripcion']}"
                if "resultado" not in busqueda_precisa.lower():
                    busqueda_precisa = f"Resultado {busqueda_precisa}"
                
                url = obtener_url_resultado_gemini(busqueda_precisa, fecha_extraida_para_busqueda)
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
