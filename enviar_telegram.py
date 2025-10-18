import requests
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

# --- Mapeo de meses para evitar errores de localidad ---
MESES_ESPANOL = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}

# --- CONFIGURACIÓN Y SECRETS ---
URL_MENSAJE = os.environ.get("URL_MENSAJE_TELEGRAM_TXT") 
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MEXICO_TZ = ZoneInfo(os.environ.get("TZ", "America/Mexico_City")) 


def obtener_mensaje_web(url):
    """
    Descarga el contenido del archivo de texto plano y valida que la fecha sea la actual.
    """
    if not url:
        print("Error: La URL del mensaje TXT no está configurada en los Secrets.")
        return None
        
    try:
        # Petición GET para descargar el contenido del mensaje
        respuesta = requests.get(url)
        respuesta.raise_for_status()
        
        # CORRECCIÓN DE CODIFICACIÓN: Forzar la codificación UTF-8 para evitar caracteres raros (mojibake)
        respuesta.encoding = 'utf-8' 
        
        # Leemos el texto puro.
        mensaje_puro = respuesta.text.strip()
        
        # --- Lógica de Validación de Fecha ---
        
        # 1. Buscamos el patrón de fecha: DD de Mes de AAAA (ej: 18 de Octubre de 2025)
        match_fecha = re.search(
            r'(\d{1,2})\s+de\s+([a-zA-Z]+)\s+de\s+(\d{4})', 
            mensaje_puro, 
            re.IGNORECASE
        )
        
        if not match_fecha:
            print("Validación de fecha fallida: No se encontró el patrón de fecha (DD de Mes de AAAA) en el mensaje.")
            return None

        # Componentes de la fecha
        dia = match_fecha.group(1).zfill(2)
        nombre_mes = match_fecha.group(2).lower()
        anio = match_fecha.group(3)
        
        # 2. Mapeamos el nombre del mes a número
        numero_mes = MESES_ESPANOL.get(nombre_mes)
        if not numero_mes:
            print(f"Validación de fecha fallida: Nombre de mes no reconocido: {nombre_mes}")
            return None
            
        # 3. Construimos la cadena en formato universal DD/MM/AAAA
        fecha_str_universal = f"{dia}/{numero_mes}/{anio}" 

        # 4. Parseamos y comparamos
        try:
            fecha_mensaje = datetime.strptime(fecha_str_universal, '%d/%m/%Y').date()
        except ValueError as e:
            print(f"Validación de fecha fallida: Error al parsear el formato universal '{fecha_str_universal}'. Error: {e}")
            return None

        # 5. Comparamos con la fecha actual de Ciudad de México
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
        # Usamos 'json=payload' para forzar Content-Type: application/json; charset=utf-8,
        # lo cual es crucial para la codificación UTF-8.
        respuesta = requests.post(url_api, json=payload) 
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
