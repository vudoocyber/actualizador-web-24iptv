import requests
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from locale import setlocale, LC_TIME 

# --- Configuración de zona horaria y secretos ---
# Asumimos que el flujo de trabajo pasa la variable TZ.
MEXICO_TZ = ZoneInfo(os.environ.get("TZ", "America/Mexico_City")) 

URL_MENSAJE = os.environ.get("URL_MENSAJE_MENSAJERIA") 
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 1. Configurar la localidad a español para que strptime pueda leer nombres de meses como "Octubre"
# Se intenta configurar la localidad más común para español en entornos de servidor.
try:
    setlocale(LC_TIME, 'es_ES.UTF-8')
except Exception:
    try:
        setlocale(LC_TIME, 'es_ES')
    except Exception:
        setlocale(LC_TIME, 'es')
        
def obtener_mensaje_web(url):
    """
    Descarga el contenido de la URL del mensaje y valida que la fecha sea la actual.
    """
    if not url:
        print("Error: La URL del mensaje no está configurada en los Secrets.")
        return None
        
    try:
        respuesta = requests.get(url)
        respuesta.raise_for_status()
        
        mensaje_puro = respuesta.text.strip()
        mensaje_puro = mensaje_puro.replace('<pre>', '').replace('</pre>', '').strip()
        
        # --- Lógica de Validación de Fecha Robusta ---
        
        # 1. Buscamos el patrón de fecha: DD de Mes de AAAA (ej: 18 de Octubre de 2025)
        # Este patrón es el que necesitamos para parsear correctamente.
        match = re.search(r'\d{1,2}\s+de\s+[a-zA-Z]+\s+de\s+\d{4}', mensaje_puro, re.IGNORECASE)
        
        if not match:
            print("Validación de fecha fallida: No se encontró el patrón de fecha (DD de Mes de AAAA) en el mensaje.")
            return None

        # Cadena de fecha extraída (ej: '18 de Octubre de 2025')
        fecha_str_extraida = match.group(0).strip()
        
        # 2. Parseamos la cadena de fecha a un objeto datetime
        try:
            # Formato de parseo: "%d de %B de %Y" (DD de Mes_Completo de AAAA)
            fecha_mensaje = datetime.strptime(fecha_str_extraida, '%d de %B de %Y').date()
            
        except ValueError as e:
            print(f"Validación de fecha fallida: Error de formato o localidad al parsear '{fecha_str_extraida}'. Error: {e}")
            return None

        # 3. Comparamos con la fecha actual de Ciudad de México
        hoy_mx = datetime.now(MEXICO_TZ).date()
        
        if fecha_mensaje == hoy_mx:
            print(f"Validación de fecha exitosa: El mensaje corresponde a la fecha actual ({hoy_mx}).")
            return mensaje_puro
        else:
            print(f"Validación de fecha fallida: Mensaje desactualizado. Mensaje: {fecha_mensaje} | Hoy: {hoy_mx}.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener el mensaje de la web desde {url}: {e}")
        return None
    except Exception as e:
        print(f"Error durante el proceso de validación: {e}")
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
        respuesta = requests.post(url_api, data=payload)
        respuesta.raise_for_status()
        print(f"Mensaje enviado a Telegram con éxito. Respuesta: {respuesta.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar el mensaje a Telegram: {e}")
        return False

def main():
    mensaje = obtener_mensaje_web(URL_MENSAJE)
    
    if mensaje:
        print(f"Mensaje obtenido (Longitud: {len(mensaje)}). Enviando a Telegram...")
        enviar_mensaje_telegram(BOT_TOKEN, CHAT_ID, mensaje)
    else:
        print("No se pudo obtener el mensaje para enviar.")

if __name__ == "__main__":
    main()
