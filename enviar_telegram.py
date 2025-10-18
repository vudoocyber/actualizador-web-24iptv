import requests
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
# Eliminamos from locale import setlocale, LC_TIME ya que no es compatible
# y causa el error.

# --- Mapeo de meses para evitar errores de localidad ---
MESES_ESPANOL = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}

# --- Configuración de zona horaria y secretos ---
# Asumimos que el flujo de trabajo pasa la variable TZ.
MEXICO_TZ = ZoneInfo(os.environ.get("TZ", "America/Mexico_City")) 

URL_MENSAJE = os.environ.get("URL_MENSAJE_MENSAJERIA") 
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Bloque de setlocale eliminado para evitar el error

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
        
        # --- Lógica de Validación de Fecha Robusta y Corregida ---
        
        # 1. Buscamos el patrón de fecha: DD de Mes de AAAA (ej: 18 de Octubre de 2025)
        # El patrón incluye el mes para luego poder mapearlo.
        match = re.search(r'\d{1,2}\s+de\s+([a-zA-Z]+)\s+de\s+\d{4}', mensaje_puro, re.IGNORECASE)
        
        if not match:
            print("Validación de fecha fallida: No se encontró el patrón de fecha (DD de Mes de AAAA) en el mensaje.")
            return None

        # Cadena de fecha extraída (ej: '18 de Octubre de 2025')
        fecha_str_completa = match.group(0).strip()
        nombre_mes = match.group(1).lower()
        
        # 2. Reemplazamos el nombre del mes por su número (Mapeo)
        numero_mes = MESES_ESPANOL.get(nombre_mes)
        if not numero_mes:
            print(f"Validación de fecha fallida: Nombre de mes no reconocido o mal escrito: {nombre_mes}")
            return None
            
        # Creamos una nueva cadena de fecha en formato que no requiere localidad: DD/MM/AAAA
        fecha_str_formato_universal = re.sub(r'de\s+'+re.escape(match.group(1)), f'{numero_mes}', fecha_str_completa, flags=re.IGNORECASE).replace(" de ", "/")

        # Limpieza final para obtener DD/MM/AAAA
        # Ejemplo: "18 / 10 / 2025" -> "18/10/2025"
        fecha_str_formato_universal = re.sub(r'\s+/\s*', '/', fecha_str_formato_universal).replace(" / ", "/")

        # 3. Parseamos la cadena de fecha (sin depender de la localidad)
        try:
            # Formato de parseo: "%d/%m/%Y" (ej: "18/10/2025")
            fecha_mensaje = datetime.strptime(fecha_str_formato_universal, '%d/%m/%Y').date()
            
        except ValueError as e:
            print(f"Validación de fecha fallida: Error al parsear el formato universal '{fecha_str_formato_universal}'. Error: {e}")
            return None

        # 4. Comparamos con la fecha actual de Ciudad de México
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

# ... (El resto del script se mantiene igual)

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
