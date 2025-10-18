import requests
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import random 

# --- Mapeo de meses para evitar errores de localidad ---
MESES_ESPANOL = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}

# --- CONFIGURACIÓN Y SECRETS ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
URL_VALIDACION = os.environ.get("URL_EVENTOS_JSON") 
URL_RANKING = os.environ.get("URL_RANKING_JSON")     
MEXICO_TZ = ZoneInfo(os.environ.get("TZ", "America/Mexico_City")) 
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; Script/1.0)'}


# --- DICCIONARIO DE PLANTILLAS POR DEPORTE ---
# Emojis clave: ⚽, 🏈, ⚾, 🏀, 🥊, 🏎️, ⭐ (Genérico)
PLANTILLAS_POR_DEPORTE = {
    # PLANTILLAS PARA FÚTBOL / SOCCER (⚽) - 5 VARIANTES
    "⚽": [
        {
            "titulo": "⚽ *¡EL CLÁSICO DEL FIN DE SEMANA!* ⚽",
            "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Estadio: {detalle_partido}\n⏰ Horario: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "⚡ *¡A rodar el balón!* Mira la acción aquí:\n"
        },
        {
            "titulo": "🚨 *ALERTA DE GOLAZOS* 🚨",
            "cuerpo": "*{organizador}*\n🆚 Partido: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕓 Hora CDMX/MEX: *{horarios}*\n📡 Cobertura: _{canales}_",
            "cierre": "📲 No te quedes fuera. ¡Sintoniza ya!:\n"
        },
        {
            "titulo": "🔥 *FIEBRE DE FÚTBOL EN VIVO* 🔥",
            "cuerpo": "🏟️ Sede: {detalle_partido}\n🏅 Duelo Clave: *{competidores}*\n🕒 Inicio: *{horarios}*\n📺 Míralo en: _{canales}_",
            "cierre": "👇 Todos los detalles y links:\n"
        },
        {
            "titulo": "🏆 *JORNADA CRUCIAL* 🏆",
            "cuerpo": "*{organizador}*\n⚔️ ¡Batalla! *{competidores}*\n⏰ Hora de inicio: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "👉 No te pierdas este partido decisivo:\n"
        },
        {
            "titulo": "🎯 *GUÍA RÁPIDA: PARTIDO DEL DÍA* 🎯",
            "cuerpo": "⚽ *{competidores}* — Hoy\n⏱️ Horarios: *{horarios}*\n🎥 Dónde Verlo: _{canales}_",
            "cierre": "🔗 Consulta toda la jornada aquí:\n"
        },
    ],
    # PLANTILLAS PARA FÚTBOL AMERICANO (🏈) - 4 VARIANTES
    "🏈": [
        {
            "titulo": "🏈 *¡DÍA DE TOUCHDOWN!* 🏈",
            "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Estadio: {detalle_partido}\n🕒 Kickoff: *{horarios}*\n📺 Cobertura Nacional: _{canales}_",
            "cierre": "💪 *¡A romper las tacleadas!* Mira la acción aquí:\n"
        },
        {
            "titulo": "🚨 *ALERTA NFL / NCAA* 🚨",
            "cuerpo": "*{organizador}*\n⚔️ Enfrentamiento: *{competidores}*\n🕓 Hora CDMX/MEX: *{horarios}*\n📡 Transmisión: _{canales}_",
            "cierre": "📲 No te pierdas este épico duelo de emparrillado:\n"
        },
        {
            "titulo": "🔥 *MÁXIMA TENSIÓN EN EL CAMPO* 🔥",
            "cuerpo": "🏅 Duelo: *{competidores}*\n📍 Ubicación: {detalle_partido}\n⏰ Inicio: *{horarios}*\n🎥 Canales: _{canales}_",
            "cierre": "🔗 Todos los pases y jugadas en vivo:\n"
        },
        {
            "titulo": "📰 *HOY: JUEGO CLAVE* 📰",
            "cuerpo": "*{organizador}* - *{competidores}*\n⏱️ Horario Principal: *{horarios}*\n📺 Múltiples Canales: _{canales}_",
            "cierre": "🌐 Guía completa y noticias:\n"
        },
    ],
    # PLANTILLAS PARA BÉISBOL (⚾) - 4 VARIANTES
    "⚾": [
        {
            "titulo": "⚾ *¡HOME RUN! EL PARTIDO DE HOY* ⚾",
            "cuerpo": "🏆 Duelo: *{competidores}*\n🏟️ Estadio: {detalle_partido}\n🕓 Primera Bola: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "🤩 *¡Pásala!* Mira el partido completo aquí:\n"
        },
        {
            "titulo": "🔔 *RECORDATORIO MLB* 🔔",
            "cuerpo": "*{organizador}*\n⚔️ Encuentro: *{competidores}*\n⏰ Hora CDMX/MEX: *{horarios}*\n📡 Cobertura: _{canales}_",
            "cierre": "📲 Conéctate al juego y las estadísticas:\n"
        },
        {
            "titulo": "🔥 *NOCHE DE BATAZOS* 🔥",
            "cuerpo": "🏅 Evento: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕒 Inicio: *{horarios}*\n🎥 Canales: _{canales}_",
            "cierre": "🔗 Sigue todas las entradas en vivo:\n"
        },
        {
            "titulo": "⭐ *SERIE CLAVE DEL DÍA* ⭐",
            "cuerpo": "*{organizador}* - *{competidores}*\n⏱️ Horario Principal: *{horarios}*\n📺 Múltiples Canales: _{canales}_",
            "cierre": "🌐 Guía y resultados actualizados:\n"
        },
    ],
    # PLANTILLAS PARA BALONCESTO (🏀) - 4 VARIANTES
    "🏀": [
        {
            "titulo": "🏀 *¡ACCIÓN EN LA CANCHA!* 🏀",
            "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Sede: {detalle_partido}\n🕓 Hora de Salto: *{horarios}*\n📺 Canales: _{canales}_",
            "cierre": "⚡ *¡Máxima velocidad!* Mira el partido aquí:\n"
        },
        {
            "titulo": "🚨 *ALERTA NBA / WNBA* 🚨",
            "cuerpo": "*{organizador}*\n⚔️ Duelo: *{competidores}*\n⏰ Horario: *{horarios}*\n📡 Cobertura: _{canales}_",
            "cierre": "📲 No te pierdas este épico tiro de tres:\n"
        },
        {
            "titulo": "🔥 *SHOWTIME EN EL TABLERO* 🔥",
            "cuerpo": "🏅 Evento: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕒 Inicio: *{horarios}*\n🎥 Canales: _{canales}_",
            "cierre": "🔗 Sigue los mejores highlights:\n"
        },
        {
            "titulo": "⭐ *PARTIDO DESTACADO* ⭐",
            "cuerpo": "*{organizador}* - *{competidores}*\n⏱️ Horario Principal: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "🌐 Guía completa de la jornada de baloncesto:\n"
        },
    ],
    # PLANTILLAS PARA COMBATE (🥊) - 3 VARIANTES
    "🥊": [
        {
            "titulo": "🥊 *¡NOCHE DE NOQUEOS!* 🥊",
            "cuerpo": "*{organizador}*\n👊 Duelo: *{competidores}*\n🏟️ Sede: {detalle_partido}\n⏱️ Comienza: *{horarios}*\n📺 PPV/Canal: _{canales}_",
            "cierre": "🔥 *¡Máxima adrenalina!* Mira el combate aquí:\n"
        },
        {
            "titulo": "💥 *DUELO ESTELAR DE COMBATE* 💥",
            "cuerpo": "*{organizador}*\n⚔️ Enfrentamiento: *{competidores}*\n📍 Lugar: {detalle_partido}\n⏰ Horario Principal: *{horarios}*\n🎥 Dónde Verlo: _{canales}_",
            "cierre": "🔗 Acceso directo y previa:\n"
        },
        {
            "titulo": "🚨 *ALERTA UFC / BOX* 🚨",
            "cuerpo": "🏅 Pelea: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕓 Hora de la cartelera: *{horarios}*\n📡 Transmisión: _{canales}_",
            "cierre": "📲 Sigue el evento completo:\n"
        }
    ],
    # PLANTILLAS PARA CARRERAS / AUTOMOVILISMO (🏎️) - 3 VARIANTES
    "🏎️": [
        {
            "titulo": "🏁 *¡ARRANCAN LOS MOTORES!* 🏎️",
            "cuerpo": "*{organizador}*\n🛣️ Evento: *{competidores}*\n📍 Circuito: {detalle_partido}\n⏱️ Hora de Salida: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "💨 ¡Velocidad pura! Mira la carrera aquí:\n"
        },
        {
            "titulo": "🚦 *LUZ VERDE PARA LA ACCIÓN* 🚦",
            "cuerpo": "*{organizador}*\n🏆 Competencia: *{competidores}*\n🌎 Zona Horaria: *{horarios}*\n📡 Cobertura total: _{canales}_",
            "cierre": "➡️ Guía completa y horarios locales:\n"
        },
        {
            "titulo": "🚨 *ATENCIÓN FÓRMULA 1 / NASCAR* 🚨",
            "cuerpo": "🏅 Evento: *{competidores}*\n⏰ Horario: *{horarios}*\n🎥 Canales: _{canales}_",
            "cierre": "🔗 Acceso directo a la transmisión:\n"
        },
    ],
    # PLANTILLAS GENÉRICAS (⭐) - 6 VARIANTES (Para Golf, Ciclismo, Tenis, etc.)
    "⭐": [
        {
            "titulo": "⭐ *DESTACADO DEL DÍA* ⭐",
            "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Sede: {detalle_partido}\n⏰ Horario: *{horarios}*\n📺 Canales: _{canales}_",
            "cierre": "➡️ ¡No te lo pierdas! Mira la acción aquí:\n"
        },
        {
            "titulo": "📰 *HOY EN EL DEPORTE* 📰",
            "cuerpo": "*{organizador}*\n🏅 Evento: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕒 Inicio: *{horarios}*\n📺 Cobertura: _{canales}_",
            "cierre": "🌐 Toda la programación:\n"
        },
        {
            "titulo": "🔔 *RECORDATORIO DE EVENTO* 🔔",
            "cuerpo": "*{organizador}*\n⏱️ Horarios: *{horarios}*\n🎥 Dónde Verlo: _{canales}_",
            "cierre": "🔗 Todos los detalles en nuestra web:\n"
        },
        {
            "titulo": "🔥 *EVENTO EN VIVO* 🔥",
            "cuerpo": "🏆 Competencia: *{competidores}*\n⌚ ¡Prepara el reloj! *{horarios}*\n📡 Transmisión: _{canales}_",
            "cierre": "📲 ¡Sintoniza ya!:\n"
        },
        {
            "titulo": "📺 *GUÍA RÁPIDA DE TRANSMISIÓN* 📺",
            "cuerpo": "*{organizador}* - *{competidores}*\n🕐 Horario: *{horarios}*\n🥇 Canales destacados: _{canales}_",
            "cierre": "👇 Haz click para ver la guía completa:\n"
        },
        {
            "titulo": "🎯 *PROGRAMACIÓN ESPECIAL* 🎯",
            "cuerpo": "🏅 Duelo: *{competidores}*\n⏰ Horario Principal: *{horarios}*\n📺 Múltiples Canales: _{canales}_",
            "cierre": "🔗 Acceso directo y horarios locales:\n"
        }
    ]
}


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
        
        # Buscamos la clave 'eventos_relevantes'
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
    Crea un mensaje atractivo en formato Markdown para Telegram, seleccionando una 
    plantilla de mensaje aleatoria basada en el tipo de deporte.
    """
    # Escapamos caracteres especiales de Markdown
    def escape_markdown(text):
        return re.sub(r'([\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

    # Obtenemos la información del primer partido (que es el evento rankeado)
    if evento.get('partidos'):
        partido_principal = evento['partidos'][0]
    else:
        partido_principal = evento 

    # Extracción y limpieza segura de datos (aplicando escape al extraer)
    horarios = escape_markdown(partido_principal.get('horarios', 'Sin hora'))
    canales = escape_markdown(", ".join(partido_principal.get('canales', ['Canal Desconocido'])))
    competidores = escape_markdown(" vs ".join(partido_principal.get('competidores', ['Competidores'])))
    organizador = escape_markdown(evento.get('evento_principal', 'Evento Deportivo'))
    detalle_partido = escape_markdown(partido_principal.get('detalle_partido', 'Ubicación Desconocida'))
    
    # 1. DETECCIÓN DEL TIPO DE DEPORTE
    tipo_deporte = "⭐" # Valor por defecto (Genérico)
    evento_principal_texto = evento.get('evento_principal', '')
    
    # Busca el emoji que define el deporte en el campo 'evento_principal' (Emojis clave en el diccionario)
    match_emoji = re.search(r'([\U0001F3C1\U0001F3C6\U0001F3BE\U0001F94A\U0001F3D0\u26BD\u26BE\U0001F3C0\U0001F3C8\U0001F3CE\U0001F3D3\U0001F3F8\u26BE\u26BD\u26F3]+)', evento_principal_texto)
    
    if match_emoji:
        emoji_detectado = match_emoji.group(0)
        
        # Mapeo por el emoji detectado
        if "⚽" in emoji_detectado or "\u26BD" in emoji_detectado:
            tipo_deporte = "⚽"
        elif "🏈" in emoji_detectado or "\U0001F3C8" in emoji_detectado:
            tipo_deporte = "🏈"
        elif "⚾" in emoji_detectado or "\u26BE" in emoji_detectado:
            tipo_deporte = "⚾"
        elif "🏀" in emoji_detectado or "\U0001F3C0" in emoji_detectado:
            tipo_deporte = "🏀"
        elif "🥊" in emoji_detectado or "\U0001F94A" in emoji_detectado or "🤼" in emoji_detectado:
             tipo_deporte = "🥊"
        elif "🏎️" in emoji_detectado or "\U0001F3CE" in emoji_detectado:
             tipo_deporte = "🏎️"
             
    # 2. SELECCIONAR PLANTILLA ALEATORIA
    plantillas_disponibles = PLANTILLAS_POR_DEPORTE.get(tipo_deporte, PLANTILLAS_POR_DEPORTE["⭐"])
    plantilla = random.choice(plantillas_disponibles)
    
    # 3. CONSTRUIR CUERPO DEL MENSAJE (Sustitución de placeholders)
    cuerpo_dinamico = plantilla["cuerpo"].format(
        organizador=organizador,
        competidores=competidores,
        detalle_partido=detalle_partido,
        horarios=horarios,
        canales=canales
    )
    
    # 4. CONSTRUCCIÓN FINAL
    mensaje = (
        f"{plantilla['titulo']}\n\n"
        f"{cuerpo_dinamico}\n\n"
        f"{plantilla['cierre']}"
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
