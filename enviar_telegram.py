import requests
import json
import os
from datetime import datetime
import pytz # Usamos pytz para consistencia con los otros scripts

# --- CONFIGURACIÓN Y SECRETS ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json" # URL del JSON principal
URL_MENSAJE_TXT = os.environ.get("URL_MENSAJE_TELEGRAM_TXT") 
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MEXICO_TZ = pytz.timezone("America/Mexico_City") 


def obtener_mensaje_web(url):
    """
    Descarga el contenido del archivo de texto plano.
    La validación de fecha ya no se hace aquí.
    """
    if not url:
        print("Error: La URL del mensaje TXT no está configurada.")
        return None
        
    try:
        respuesta = requests.get(url)
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
        'parse_mode': 'Markdown' 
    }
    
    try:
        respuesta = requests.post(url_api, json=payload) 
        respuesta.raise_for_status()
        print(f"Mensaje enviado a Telegram con éxito.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar el mensaje a Telegram: {e}")
        print(f"Respuesta del servidor: {respuesta.text}")
        return False

def main():
    print("Iniciando proceso de envío de mensaje a Telegram...")
    
    try:
        print(f"1. Descargando {URL_JSON_FUENTE} para validar fecha...")
        respuesta = requests.get(URL_JSON_FUENTE, params={'v': datetime.now().timestamp()}, timeout=20)
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
