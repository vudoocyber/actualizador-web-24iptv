import requests
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from locale import setlocale, LC_TIME # Necesario para parsear nombres de meses en español

# --- Configuración ---
URL_MENSAJE = os.environ.get("URL_MENSAJE_MENSAJERIA") 
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# Usamos America/Mexico_City como zona horaria de referencia
MEXICO_TZ = ZoneInfo(os.environ.get("TZ", "America/Mexico_City")) 

# Configuramos la localidad a español para que strptime pueda leer "Octubre"
try:
    setlocale(LC_TIME, 'es_ES.UTF-8')
except:
    try:
        # Intenta otra codificación común para español si la anterior falla
        setlocale(LC_TIME, 'es_ES')
    except:
        print("Advertencia: No se pudo configurar la localidad 'es' para la validación de fecha.")

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
        
        # 1. Buscamos el patrón de fecha: *Día Mes de Año*
        # El patrón es: *[texto]*
        match = re.search(r'\*\s*(Sabado|Domingo)\s+\d{1,2}\s+de\s+[a-zA-Z]+\s+de\s+\d{4}\s*\*', mensaje_puro, re.IGNORECASE)
        
        if not match:
            print("Validación de fecha fallida: No se encontró el patrón de fecha (*Dia DD de Mes de AAAA*) en el mensaje.")
            return None

        # Cadena de fecha extraída (ej: *Sabado 18 de Octubre de 2025*)
        fecha_str_completa = match.group(0).strip('*').strip()
        
        # 2. Parseamos la cadena de fecha a un objeto datetime
        # El formato debe coincidir con la cadena: %A (Día completo), %d (Día), %B (Mes completo), %Y (Año)
        # Ejemplo: 'Sabado 18 de Octubre de 2025'
        # Usamos %d de Month %Y
        try:
            # Quitamos el día de la semana para simplificar el parseo si locale falla
            # y usamos una forma más simple que es el "DD de Mes de AAAA"
            partes_fecha = fecha_str_completa.split(' de ')
            dia_mes_ano_str = partes_fecha[0].split(' ')[1] + ' de ' + partes_fecha[1] + ' de ' + partes_fecha[2]
            
            # Formato de parseo: "DD de Mes de AAAA" (ej: "18 de Octubre de 2025")
            fecha_mensaje = datetime.strptime(dia_mes_ano_str, '%d de %B de %Y').date()
            
        except ValueError as e:
            print(f"Validación de fecha fallida: Error al parsear la fecha '{fecha_str_completa}': {e}")
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

# El resto del script (enviar_mensaje_telegram y main) se mantiene igual.
# Asegúrate de que tu main en enviar_telegram.py use 'os.environ.get("TZ", "America/Mexico_City")'

def enviar_mensaje_telegram(token, chat_id, mensaje):
    # ... (código de enviar_mensaje_telegram)
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
