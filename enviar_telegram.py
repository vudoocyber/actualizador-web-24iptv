import requests
import json
import os
from datetime import datetime
import pytz 

# --- CONFIGURACIÓN Y SECRETS ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json" 
URL_MENSAJE_TXT = os.environ.get("URL_MENSAJE_TELEGRAM_TXT") 
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MEXICO_TZ = pytz.timezone("America/Mexico_City") 

# --- HEADERS ANTI-BLOQUEO (CRÍTICO) ---
# Sin esto, el servidor devuelve error 403
HEADERS_SEGURIDAD = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/json,xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Referer': 'https://24hometv.xyz/',
    'Connection': 'keep-alive'
}

def obtener_mensaje_web(url):
    """
    Descarga el contenido del archivo de texto plano.
    """
    if not url:
        print("Error: La URL del mensaje TXT no está configurada.")
        return None
        
    try:
        # AGREGAMOS HEADERS AQUÍ
        respuesta = requests.get(url, headers=HEADERS_SEGURIDAD, timeout=20)
        respuesta.raise_for_status()
        respuesta.encoding = 'utf-8' 
        return respuesta.text.strip()

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener el mensaje de la web desde {url}: {e}")
        return None

def enviar_mensaje_telegram(token, chat_id, mensaje):
    """
    Envía el mensaje de texto a Telegram.
    """
    if not token or not chat_id:
        print("Error: El token del bot o el ID del chat no están configurados.")
        return False
    
    url_api = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': mensaje,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True # Opcional: evita que genere vistas previas de enlaces
    }
    
    try:
        # Telegram no necesita los headers de seguridad del servidor web, pero sí un timeout
        respuesta = requests.post(url_api, json=payload, timeout=20) 
        respuesta.raise_for_status()
        print(f"Mensaje enviado a Telegram con éxito.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar el mensaje a Telegram: {e}")
        try:
            print(f"Respuesta del servidor: {respuesta.text}")
        except:
            pass
        return False

def main():
    print("Iniciando proceso de envío de mensaje a Telegram...")
    
    try:
        print(f"1. Descargando {URL_JSON_FUENTE} para validar fecha...")
        # AGREGAMOS HEADERS AQUÍ TAMBIÉN
        respuesta = requests.get(URL_JSON_FUENTE, headers=HEADERS_SEGURIDAD, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        # --- LÓGICA DE VALIDACIÓN DE FECHA ---
        fecha_guia_str = datos.get("fecha_guia")
        if not fecha_guia_str:
            print("ERROR: No se encontró la etiqueta 'fecha_guia' en events.json. Proceso detenido.")
            return

        hoy_mexico_str = datetime.now(MEXICO_TZ).strftime('%Y-%m-%d')

        if fecha_guia_str != hoy_mexico_str:
            print(f"ADVERTENCIA: La fecha de la guía ({fecha_guia_str}) no es la de hoy ({hoy_mexico_str}). No se enviará el mensaje.")
            return
        
        print(f"Fecha de la guía ({fecha_guia_str}) confirmada. Procediendo a enviar mensaje.")
        # --- FIN DE LA LÓGICA DE VALIDACIÓN ---

    except Exception as e:
        print(f"ERROR FATAL al leer o validar el archivo JSON: {e}")
        return

    # Si la validación de fecha fue exitosa, continuamos
    mensaje = obtener_mensaje_web(URL_MENSAJE_TXT)
    
    if mensaje:
        print(f"Mensaje obtenido (Longitud: {len(mensaje)}). Enviando a Telegram...")
        enviar_mensaje_telegram(BOT_TOKEN, CHAT_ID, mensaje)
    else:
        print("No se pudo obtener el mensaje para enviar.")

if __name__ == "__main__":
    main()
    print("--- Proceso de Telegram finalizado ---")
