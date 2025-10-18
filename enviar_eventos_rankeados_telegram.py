import requests
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import re

# --- Mapeo de meses para evitar errores de localidad ---
MESES_ESPANOL = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}

# --- CONFIGURACIÓN Y SECRETS ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
URL_VALIDACION = os.environ.get("URL_EVENTOS_JSON") # events.json para fecha
URL_RANKING = os.environ.get("URL_RANKING_JSON")     # eventos-relevantes.json
MEXICO_TZ = ZoneInfo(os.environ.get("TZ", "America/Mexico_City")) 
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; Script/1.0)'}


def validar_fecha_actualizacion(url_json):
    """
    Descarga el JSON de eventos principal y verifica que la fecha_actualizacion 
    corresponda al día de hoy en la Ciudad de México.
    """
    try:
        respuesta = requests.get(url_json, headers=HEADERS, timeout=10)
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        fecha_str = datos.get("fecha_actualizacion")
        
        if not fecha_str:
            print("Validación fallida: El campo 'fecha_actualizacion' no se encontró en el JSON.")
            return False

        # Parseamos la fecha ISO: "2025-10-18T22:17:57.638086"
        fecha_actualizacion = datetime.fromisoformat(fecha_str).date()
        
        # Obtenemos la fecha de hoy en CDMX para la comparación
        hoy_mx = datetime.now(MEXICO_TZ).date()
        
        if fecha_actualizacion == hoy_mx:
            print(f"Validación de fecha exitosa: {fecha_actualizacion} coincide con hoy ({hoy_mx}).")
            return True
        else:
            print(f"Validación de fecha fallida: Mensaje desactualizado. JSON: {fecha_actualizacion} | Hoy: {hoy_mx}.")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Error al acceder al JSON de validación en {url_json}: {e}")
        return False
    except Exception as e:
        print(f"Error durante la validación de fecha: {e}")
        return False


def obtener_eventos_rankeados(url_ranking):
    """
    Descarga el JSON de ranking y devuelve la lista de eventos, usando la clave correcta.
    """
    try:
        respuesta = requests.get(url_ranking, headers=HEADERS, timeout=10)
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        # CORRECCIÓN: Buscamos la clave 'eventos_relevantes'
        eventos = datos.get("eventos_relevantes", []) 
        
        print(f"Obtenidos {len(eventos)} eventos rankeados.")
        return eventos

    except requests.exceptions.RequestException as e:
        print(f"Error al acceder al JSON de ranking en {url_ranking}: {e}")
        return []
    except Exception as e:
        print(f"Error al parsear el JSON de ranking: {e}")
        return []


def formatear_mensaje_telegram(evento):
    """
    Crea un mensaje atractivo en formato Markdown para Telegram.
    """
    # Escapamos caracteres especiales de Markdown (., -, !, #, (, ), etc.)
    def escape_markdown(text):
        return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)

    # El evento rankeado es un objeto complejo (tiene "partidos")
    if evento.get('partidos'):
        partido_principal = evento['partidos'][0]
    else:
        # Fallback si la estructura es plana
        partido_principal = evento 

    # Extracción segura de datos
    desc = partido_principal.get('descripcion', 'Evento no especificado')
    horarios = partido_principal.get('horarios', 'Sin hora')
    canales = ", ".join(partido_principal.get('canales', ['Canal Desconocido']))
    competidores = " vs ".join(partido_principal.get('competidores', ['Competidores']))
    organizador = evento.get('evento_principal', 'Evento Deportivo')
    detalle_partido = partido_principal.get('detalle_partido', 'Ubicación Desconocida')
    
    # Asignamos un emoji basado en el contenido del organizador
    emoji = "⭐"
    if "BOX" in organizador or "UFC" in organizador:
        emoji = "🥊"
    elif "MX" in organizador or "Liga" in organizador or "⚽" in organizador:
        emoji = "⚽"
    elif "NFL" in organizador or "🏈" in organizador:
        emoji = "🏈"
    elif "NBA" in organizador or "WNBA" in organizador or "🏀" in organizador:
        emoji = "🏀"
    elif "MLB" in organizador or "⚾" in organizador:
        emoji = "⚾"
        
    # Construcción del mensaje en Markdown (usamos un formato simple para máxima compatibilidad)
    mensaje = (
        f"{emoji} *¡EVENTO IMPERDIBLE DEL DÍA!* {emoji}\n\n"
        f"*{escape_markdown(organizador)}*\n"
        f"ðŸ† Encuentro: *{escape_markdown(competidores)}*\n"
        f"ðŸš Sede: {escape_markdown(detalle_partido)}\n"
        f"â° Horario: *{escape_markdown(horarios)}*\n"
        f"ðŸ“º Canales: _{escape_markdown(canales)}_\n\n"
        f"âš¡ï¸ ¡No te lo pierdas! Mira la acción completa aquí:\n"
        f"https://24hometv.xyz/"
    )
    return mensaje


def enviar_mensaje_telegram(token, chat_id, mensaje):
    """
    Envía un mensaje individual a Telegram.
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
        # Usamos 'json=payload' para la codificación UTF-8
        respuesta = requests.post(url_api, json=payload) 
        respuesta.raise_for_status()
        
        if respuesta.json().get('ok'):
            print("Mensaje enviado a Telegram con éxito.")
            return True
        else:
             print(f"Fallo al enviar mensaje: {respuesta.json().get('description')}")
             return False
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar el mensaje a Telegram: {e}")
        return False


def main():
    if not (BOT_TOKEN and CHAT_ID and URL_VALIDACION and URL_RANKING):
        print("ERROR CRÍTICO: Faltan secretos de configuración (Telegram/URLs). Proceso detenido.")
        return

    print("--- INICIANDO PROCESO DE ENVÍO DE EVENTOS RANKADOS ---")
    
    # 1. VALIDACIÓN DE FECHA
    if not validar_fecha_actualizacion(URL_VALIDACION):
        print("La fecha del JSON principal no es la de hoy. Deteniendo el envío.")
        return
    
    # 2. OBTENCIÓN DE EVENTOS
    eventos = obtener_eventos_rankeados(URL_RANKING)
    
    if not eventos:
        print("No se encontraron eventos rankeados para enviar. Proceso finalizado.")
        return
        
    # 3. ENVÍO DE MENSAJES INDIVIDUALES
    print(f"Encontrados {len(eventos)} eventos. Iniciando envío...")
    
    mensajes_enviados = 0
    for i, evento in enumerate(eventos[:3]): # Limitamos a los 3 primeros
        mensaje_markdown = formatear_mensaje_telegram(evento)
        
        print(f"Enviando Evento {i+1}...")
        if enviar_mensaje_telegram(BOT_TOKEN, CHAT_ID, mensaje_markdown):
            mensajes_enviados += 1
        else:
            print(f"Fallo en el envío del evento {i+1}.")
            
    print(f"--- PROCESO FINALIZADO. Mensajes enviados: {mensajes_enviados} ---")


if __name__ == "__main__":
    main()
