import requests
import os
import json
from datetime import datetime, date
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
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID") # Chat público
URL_VALIDACION = os.environ.get("URL_EVENTOS_JSON") 
URL_RANKING = os.environ.get("URL_RANKING_JSON")     
TELEGRAM_ALERT_CHAT_ID = os.environ.get("TELEGRAM_ALERT_CHAT_ID") # Chat privado/alerta (NUEVO)
MEXICO_TZ = ZoneInfo(os.environ.get("TZ", "America/Mexico_City")) 
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; Script/1.0)'}


# --- DICCIONARIO DE PLANTILLAS POR DEPORTE (SE MANTIENE IGUAL) ---
PLANTILLAS_POR_DEPORTE = {
    "⚽": [
        {
            "titulo": "⚽ *¡EL CLÁSICO DEL FIN DE SEMANA!* ⚽",
            "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Estadio: {detalle_partido}\n⏰ Horario: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "⚡ *¡A rodar el balón!* Mira la acción aquí:\n",
            "ESPECIAL_FIN_SEMANA": True 
        },
        {
            "titulo": "🚨 *ALERTA DE GOLAZOS EN VIVO* 🚨",
            "cuerpo": "*{organizador}*\n🆚 Partido: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕓 Hora CDMX/MEX: *{horarios}*\n📡 Cobertura: _{canales}_",
            "cierre": "📲 No te quedes fuera. ¡Sintoniza ya!:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🔥 *FIEBRE DE FÚTBOL EN VIVO* 🔥",
            "cuerpo": "🏟️ Sede: {detalle_partido}\n🏅 Duelo Clave: *{competidores}*\n🕒 Inicio: *{horarios}*\n📺 Míralo en: _{canales}_",
            "cierre": "👇 Todos los detalles y links:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏆 *JORNADA CRUCIAL* 🏆",
            "cuerpo": "*{organizador}*\n⚔️ ¡Batalla! *{competidores}*\n⏰ Hora de inicio: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "👉 No te pierdas este partido decisivo:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🎯 *GUÍA RÁPIDA: PARTIDO DEL DÍA* 🎯",
            "cuerpo": "⚽ *{competidores}* — Hoy\n⏱️ Horarios: *{horarios}*\n🎥 Dónde Verlo: _{canales}_",
            "cierre": "🔗 Consulta toda la jornada aquí:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "📣 *ÚLTIMA HORA: PARTIDO ESTELAR* 📣",
            "cuerpo": "*{organizador}*\n💥 Enfrentamiento: *{competidores}*\n⏰ Horario Principal: *{horarios}*\n📺 Cobertura: _{canales}_",
            "cierre": "🌐 Guía completa y noticias:\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],
    "🏈": [
        {
            "titulo": "🏈 *¡DÍA DE TOUCHDOWN!* 🏈",
            "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Estadio: {detalle_partido}\n🕒 Kickoff: *{horarios}*\n📺 Cobertura Nacional: _{canales}_",
            "cierre": "💪 *¡A romper las tacleadas!* Mira la acción aquí:\n",
            "ESPECIAL_FIN_SEMANA": True 
        },
        {
            "titulo": "🚨 *ALERTA NFL / NCAA EN VIVO* 🚨",
            "cuerpo": "*{organizador}*\n⚔️ Enfrentamiento: *{competidores}*\n🕓 Hora CDMX/MEX: *{horarios}*\n📡 Transmisión: _{canales}_",
            "cierre": "📲 No te pierdas este épico duelo de emparrillado:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🔥 *MÁXIMA TENSIÓN EN EL CAMPO* 🔥",
            "cuerpo": "🏅 Duelo: *{competidores}*\n📍 Ubicación: {detalle_partido}\n⏰ Inicio: *{horarios}*\n🎥 Canales: _{canales}_",
            "cierre": "🔗 Todos los pases y jugadas en vivo:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "📰 *HOY: JUEGO CLAVE* 📰",
            "cuerpo": "*{organizador}* - *{competidores}*\n⏱️ Horario Principal: *{horarios}*\n📺 Múltiples Canales: _{canales}_",
            "cierre": "🌐 Guía completa y noticias:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏟️ *NUEVA JORNADA DE FÚTBOL AMERICANO* 🏟️",
            "cuerpo": "*{organizador}*\n💥 Enfrentamiento: *{competidores}*\n🕒 Comienza: *{horarios}*\n📡 Cobertura: _{canales}_",
            "cierre": "👉 Pases, yardas y más:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🚨 *IMPERDIBLE: EL DUELO DE LA SEMANA* 🚨",
            "cuerpo": "🏆 Partido: *{competidores}*\n📍 Desde {detalle_partido}\n⏰ Kickoff: *{horarios}*\n📺 Canales: _{canales}_",
            "cierre": "🔗 Mira el partido en nuestra web:\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],
    "⚾": [
        {
            "titulo": "⚾ *¡HOME RUN! EL PARTIDO DE HOY* ⚾",
            "cuerpo": "🏆 Duelo: *{competidores}*\n🏟️ Estadio: {detalle_partido}\n🕓 Primera Bola: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "🤩 *¡Pásala!* Mira el partido completo aquí:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🔔 *RECORDATORIO MLB* 🔔",
            "cuerpo": "*{organizador}*\n⚔️ Encuentro: *{competidores}*\n⏰ Hora CDMX/MEX: *{horarios}*\n📡 Cobertura: _{canales}_",
            "cierre": "📲 Conéctate al juego y las estadísticas:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🔥 *NOCHE DE BATAZOS* 🔥",
            "cuerpo": "🏅 Evento: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕒 Inicio: *{horarios}*\n🎥 Canales: _{canales}_",
            "cierre": "🔗 Sigue todas las entradas en vivo:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "⭐ *SERIE CLAVE DEL DÍA* ⭐",
            "cuerpo": "*{organizador}* - *{competidores}*\n⏱️ Horario Principal: *{horarios}*\n📺 Múltiples Canales: _{canales}_",
            "cierre": "🌐 Guía y resultados actualizados:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏟️ *ÚLTIMA ENTRADA: BÉISBOL* 🏟️",
            "cuerpo": "💥 Duelo: *{competidores}*\n⚾ Primera Bola: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "👉 Todos los partidos de la jornada:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🎯 *GUÍA RÁPIDA: PARTIDO MLB/LMP* 🎯",
            "cuerpo": "*{organizador}*\n⚾ Enfrentamiento: *{competidores}*\n⏰ Hora de inicio: *{horarios}*\n🎥 Dónde Verlo: _{canales}_",
            "cierre": "🔗 Revisa nuestra guía completa:\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],
    "🏀": [
        {
            "titulo": "🏀 *¡ACCIÓN EN LA CANCHA!* 🏀",
            "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Sede: {detalle_partido}\n🕓 Hora de Salto: *{horarios}*\n📺 Canales: _{canales}_",
            "cierre": "⚡ *¡Máxima velocidad!* Mira el partido aquí:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🚨 *ALERTA NBA* 🚨",
            "cuerpo": "*{organizador}*\n⚔️ Duelo: *{competidores}*\n⏰ Horario: *{horarios}*\n📡 Cobertura: _{canales}_",
            "cierre": "📲 No te pierdas este épico tiro de tres:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🔥 *SHOWTIME EN EL TABLERO* 🔥",
            "cuerpo": "🏅 Evento: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕒 Inicio: *{horarios}*\n🎥 Canales: _{canales}_",
            "cierre": "🔗 Sigue los mejores highlights:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "⭐ *PARTIDO DESTACADO* ⭐",
            "cuerpo": "*{organizador}* - *{competidores}*\n⏱️ Horario Principal: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "🌐 Guía completa de la jornada de baloncesto:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🎯 *DUELO DE GIGANTES* 🎯",
            "cuerpo": "🏆 Partido: *{competidores}*\n🕓 Salto Inicial: *{horarios}*\n📺 Dónde Verlo: _{canales}_",
            "cierre": "🚀 Accede al link de transmisión:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "📰 *HOY EN EL BALONCESTO* 📰",
            "cuerpo": "*{organizador}*\n🏀 Enfrentamiento: *{competidores}*\n⏰ Hora de inicio: *{horarios}*\n📡 Cobertura: _{canales}_",
            "cierre": "👉 Toda la acción de la liga:\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],
    "🥊": [
        {
            "titulo": "🥊 *¡NOCHE DE NOQUEOS!* 🥊",
            "cuerpo": "*{organizador}*\n👊 Duelo: *{competidores}*\n🏟️ Sede: {detalle_partido}\n⏱️ Comienza: *{horarios}*\n📺 PPV/Canal: _{canales}_",
            "cierre": "🔥 *¡Máxima adrenalina!* Mira el combate aquí:\n",
            "ESPECIAL_FIN_SEMANA": True
        },
        {
            "titulo": "💥 *DUELO ESTELAR DE COMBATE* 💥",
            "cuerpo": "*{organizador}*\n⚔️ Enfrentamiento: *{competidores}*\n📍 Lugar: {detalle_partido}\n⏰ Horario Principal: *{horarios}*\n🎥 Dónde Verlo: _{canales}_",
            "cierre": "🔗 Acceso directo y previa:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🚨 *ALERTA UFC / BOX* 🚨",
            "cuerpo": "🏅 Pelea: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕓 Hora de la cartelera: *{horarios}*\n📡 Transmisión: _{canales}_",
            "cierre": "📲 Sigue el evento completo:\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],
    "🏎️": [
        {
            "titulo": "🏁 *¡ARRANCAN LOS MOTORES!* 🏎️",
            "cuerpo": "*{organizador}*\n🛣️ Evento: *{competidores}*\n📍 Circuito: {detalle_partido}\n⏱️ Hora de Salida: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "💨 ¡Velocidad pura! Mira la carrera aquí:\n",
            "ESPECIAL_FIN_SEMANA": True
        },
        {
            "titulo": "🚦 *LUZ VERDE PARA LA ACCIÓN* 🚦",
            "cuerpo": "*{organizador}*\n🏆 Competencia: *{competidores}*\n🌎 Zona Horaria: *{horarios}*\n📡 Cobertura total: _{canales}_",
            "cierre": "➡️ Guía completa y horarios locales:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🚨 *ATENCIÓN FÓRMULA 1 / NASCAR* 🚨",
            "cuerpo": "🏅 Evento: *{competidores}*\n⏰ Horario: *{horarios}*\n🎥 Canales: _{canales}_",
            "cierre": "🔗 Acceso directo a la transmisión:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
    ],
    "🎾": [
        {
            "titulo": "🎾 *DUELO EN LA CANCHA CENTRAL* 🎾",
            "cuerpo": "*{organizador}*\n⚔️ Partido: *{competidores}*\n📍 Torneo: {detalle_partido}\n⏱️ Comienza: *{horarios}*\n📺 Transmisión: _{canales}_",
            "cierre": "👉 Sigue el marcador en vivo:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🔔 *ALERTA: TENIS PROFESIONAL* 🔔",
            "cuerpo": "🏆 Evento: *{competidores}*\n⏰ Horario: *{horarios}*\n🎥 Dónde Verlo: _{canales}_",
            "cierre": "🌐 Guía y resultados actualizados:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
    ],
    "⭐": [
        {
            "titulo": "⭐ *DESTACADO DEL DÍA* ⭐",
            "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Sede: {detalle_partido}\n⏰ Horario: *{horarios}*\n📺 Canales: _{canales}_",
            "cierre": "➡️ ¡No te lo pierdas! Mira la acción aquí:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "📰 *HOY EN EL DEPORTE* 📰",
            "cuerpo": "*{organizador}*\n🏅 Evento: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕒 Inicio: *{horarios}*\n📺 Cobertura: _{canales}_",
            "cierre": "🌐 Toda la programación:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🔔 *RECORDATORIO DE EVENTO* 🔔",
            "cuerpo": "*{organizador}*\n⏱️ Horarios: *{horarios}*\n🎥 Dónde Verlo: _{canales}_",
            "cierre": "🔗 Todos los detalles en nuestra web:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🔥 *EVENTO EN VIVO* 🔥",
            "cuerpo": "🏆 Competencia: *{competidores}*\n⌚ ¡Prepara el reloj! *{horarios}*\n📡 Transmisión: _{canales}_",
            "cierre": "📲 ¡Sintoniza ya!:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "📺 *GUÍA RÁPIDA DE TRANSMISIÓN* 📺",
            "cuerpo": "*{organizador}* - *{competidores}*\n🕐 Horario: *{horarios}*\n🥇 Canales destacados: _{canales}_",
            "cierre": "👇 Haz click para ver la guía completa:\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🎯 *PROGRAMACIÓN ESPECIAL* 🎯",
            "cuerpo": "🏅 Duelo: *{competidores}*\n⏰ Horario Principal: *{horarios}*\n📺 Múltiples Canales: _{canales}_",
            "cierre": "🔗 Acceso directo y horarios locales:\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ]
}


# --- FUNCIÓN DE ALERTA INDEPENDIENTE (NUEVA) ---
def enviar_alerta_telegram(token, mensaje):
    """
    Envía un mensaje de alerta al chat personal del administrador.
    Utiliza TELEGRAM_ALERT_CHAT_ID.
    """
    if not token or not TELEGRAM_ALERT_CHAT_ID:
        print("ADVERTENCIA: No se pudo enviar la alerta. El Token o el Chat ID de alerta no están configurados.")
        return False
    
    url_api = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Preparamos el mensaje de alerta para Telegram
    # Reemplazamos los caracteres especiales para Markdown para asegurar que la alerta se muestre correctamente.
    def escape_for_alert(text):
        return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)
        
    alerta_cuerpo = escape_for_alert(mensaje)

    payload = {
        'chat_id': TELEGRAM_ALERT_CHAT_ID,
        'text': f"🚨 *ALERTA CRÍTICA DE AUTOMATIZACIÓN* 🚨\n\n{alerta_cuerpo}",
        'parse_mode': 'Markdown' 
    }
    
    try:
        respuesta = requests.post(url_api, json=payload) 
        respuesta.raise_for_status()
        print("Alerta crítica enviada a la cuenta personal.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Falló el envío de la alerta. Causa: {e}")
        return False

# --- El resto de funciones (es_fin_de_semana, es_evento_femenino, etc.) se mantiene igual ---

def es_fin_de_semana():
    """
    Verifica si la ejecución es Sábado (5) o Domingo (6) en la zona horaria de CDMX.
    """
    hoy = datetime.now(MEXICO_TZ).weekday() 
    return hoy >= 5 


def es_evento_femenino(evento):
    """
    Verifica si el evento debe ser excluido (Regla 1).
    """
    organizador = evento.get('evento_principal', '').upper()
    
    if evento.get('partidos') and evento['partidos']:
        descripcion = evento['partidos'][0].get('descripcion', '').upper()
    else:
        descripcion = ''

    # Excluir basado en palabras clave específicas: 'FEMENIL', 'WNBA', 'NWSL', etc.
    if 'FEMENIL' in organizador or 'WNBA' in organizador or 'NWSL' in organizador or \
       'FEMENIL' in descripcion or 'WNBA' in descripcion or 'NWSL' in descripcion:
        return True
    return False


def validar_fecha_actualizacion(url_json):
    """
    Descarga el JSON de eventos principal y verifica que la fecha_actualizacion 
    corresponde al día de hoy en la Ciudad de México.
    """
    try:
        respuesta = requests.get(url_json, headers=HEADERS, timeout=10)
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        fecha_str = datos.get("fecha_actualizacion")
        
        if not fecha_str:
            print("Validación fallida: El campo 'fecha_actualizacion' no se encontró en el JSON.")
            return False

        fecha_actualizacion = datetime.fromisoformat(fecha_str).date()
        hoy_mx = datetime.now(MEXICO_TZ).date()
        
        if fecha_actualizacion == hoy_mx:
            print(f"Validación de fecha exitosa: {fecha_actualizacion} coincide con hoy ({hoy_mx}).")
            return True
        else:
            print(f"Validación de fecha fallida: Mensaje desactualizado. JSON: {fecha_actualizacion} | Hoy: {hoy_mx}.")
            return False

    except requests.exceptions.RequestException as e:
        # Propagamos la excepción para ser capturada en main y enviar la alerta
        raise Exception(f"Fallo de Conexión. JSON no accesible: {e}")
    except Exception as e:
        raise Exception(f"Fallo al procesar el JSON de validación: {e}")


def obtener_eventos_rankeados(url_ranking):
    """
    Descarga el JSON de ranking y devuelve la lista de eventos, aplicando el filtro femenino.
    """
    try:
        respuesta = requests.get(url_ranking, headers=HEADERS, timeout=10)
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        eventos = datos.get("eventos_relevantes", []) 
        
        # APLICACIÓN DE LA REGLA 1: Filtrar eventos femeninos
        eventos_filtrados = [e for e in eventos if not es_evento_femenino(e)]
        
        if len(eventos) != len(eventos_filtrados):
            print(f"Advertencia: {len(eventos) - len(eventos_filtrados)} eventos femeninos fueron filtrados.")
        
        print(f"Obtenidos {len(eventos_filtrados)} eventos rankeados.")
        return eventos_filtrados

    except requests.exceptions.RequestException as e:
        raise Exception(f"Fallo de Conexión. Ranking JSON no accesible: {e}")
    except Exception as e:
        raise Exception(f"Error al parsear el JSON de ranking: {e}")


def formatear_mensaje_telegram(evento):
    """
    Crea un mensaje atractivo en formato Markdown para Telegram, seleccionando una 
    plantilla de mensaje aleatoria basada en el tipo de deporte y el día de la semana.
    """
    def escape_markdown(text):
        return re.sub(r'([\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

    if evento.get('partidos'):
        partido_principal = evento['partidos'][0]
    else:
        partido_principal = evento 

    # Extracción y limpieza segura de datos
    horarios = escape_markdown(partido_principal.get('horarios', 'Sin hora'))
    canales = escape_markdown(", ".join(partido_principal.get('canales', ['Canal Desconocido'])))
    competidores = escape_markdown(" vs ".join(partido_principal.get('competidores', ['Competidores'])))
    organizador = escape_markdown(evento.get('evento_principal', 'Evento Deportivo'))
    detalle_partido = escape_markdown(partido_principal.get('detalle_partido', 'Ubicación Desconocida'))
    
    # 1. DETECCIÓN DEL TIPO DE DEPORTE
    tipo_deporte = "⭐"
    evento_principal_texto = evento.get('evento_principal', '')
    
    # Expresión regular para detectar emojis clave
    match_emoji = re.search(r'([\U0001F3C1\U0001F3C6\U0001F3BE\U0001F94A\U0001F3D0\u26BD\u26BE\U0001F3C0\U0001F3C8\U0001F3CE\U0001F3D3\U0001F3F8\u26BE\u26BD\u26F3\U0001F3BE]+)', evento_principal_texto)
    
    if match_emoji:
        emoji_detectado = match_emoji.group(0)
        
        if "⚽" in emoji_detectado or "\u26BD" in emoji_detectado: tipo_deporte = "⚽"
        elif "🏈" in emoji_detectado or "\U0001F3C8" in emoji_detectado: tipo_deporte = "🏈"
        elif "⚾" in emoji_detectado or "\u26BE" in emoji_detectado: tipo_deporte = "⚾"
        elif "🏀" in emoji_detectado or "\U0001F3C0" in emoji_detectado: tipo_deporte = "🏀"
        elif "🎾" in emoji_detectado or "\U0001F3BE" in emoji_detectado: tipo_deporte = "🎾"
        elif "🥊" in emoji_detectado or "\U0001F94A" in emoji_detectado or "🤼" in emoji_detectado: tipo_deporte = "🥊"
        elif "🏎️" in emoji_detectado or "\U0001F3CE" in emoji_detectado: tipo_deporte = "🏎️"
             
    # 2. SELECCIÓN DE PLANTILLA ALEATORIA (Regla 2: Filtro de Fin de Semana)
    es_weekend = es_fin_de_semana()
    
    plantillas_disponibles_total = PLANTILLAS_POR_DEPORTE.get(tipo_deporte, PLANTILLAS_POR_DEPORTE["⭐"])
    
    if es_weekend:
        plantillas_filtradas = [p for p in plantillas_disponibles_total]
    else:
        plantillas_filtradas = [p for p in plantillas_disponibles_total if p.get("ESPECIAL_FIN_SEMANA") is not True]
    
    if not plantillas_filtradas:
        plantillas_a_usar = PLANTILLAS_POR_DEPORTE["⭐"]
    else:
        plantillas_a_usar = plantillas_filtradas

    plantilla = random.choice(plantillas_a_usar)
    
    # 3. CONSTRUCCIÓN DEL MENSAJE
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
    # 1. VERIFICACIÓN CRÍTICA DE SECRETS
    if not (BOT_TOKEN and CHAT_ID and URL_VALIDACION and URL_RANKING and TELEGRAM_ALERT_CHAT_ID):
        error_msg = "ERROR CRÍTICO: Faltan secretos de configuración (Telegram/URLs/Alertas). Proceso detenido."
        print(error_msg)
        enviar_alerta_telegram(BOT_TOKEN, f"*{error_msg}*\n\nRevisa los secrets de GitHub: TELEGRAM\_BOT\_TOKEN, TELEGRAM\_ALERT\_CHAT\_ID, URL\_VALIDACION, URL\_RANKING.")
        return

    print("--- INICIANDO PROCESO DE ENVÍO DE EVENTOS RANKADOS ---")
    
    # 2. VALIDACIÓN DE FECHA Y CONEXIÓN
    try:
        if not validar_fecha_actualizacion(URL_VALIDACION):
            error_msg = f"ERROR: La fecha del JSON principal no es la de hoy ({datetime.now(MEXICO_TZ).date()}). Deteniendo el envío."
            print(error_msg)
            enviar_alerta_telegram(BOT_TOKEN, error_msg)
            return
    except Exception as e:
        error_msg = f"ERROR: Fallo de red/JSON al validar la fecha. {e.__class__.__name__}: {e}"
        print(error_msg)
        enviar_alerta_telegram(BOT_TOKEN, error_msg)
        return

    # 3. OBTENCIÓN Y FILTRADO DE EVENTOS
    try:
        eventos = obtener_eventos_rankeados(URL_RANKING)
    except Exception as e:
        error_msg = f"ERROR: Fallo de red/JSON al obtener eventos rankeados. {e.__class__.__name__}: {e}"
        print(error_msg)
        enviar_alerta_telegram(BOT_TOKEN, error_msg)
        return
    
    if not eventos:
        print("No se encontraron eventos rankeados para enviar. Proceso finalizado.")
        return
        
    # 4. ENVÍO DE MENSAJES INDIVIDUALES
    print(f"Encontrados {len(eventos)} eventos. Iniciando envío público...")
    
    mensajes_enviados = 0
    for i, evento in enumerate(eventos[:3]): # Limitamos a los 3 primeros
        mensaje_markdown = formatear_mensaje_telegram(evento)
        
        print(f"Enviando Evento {i+1}...")
        if enviar_mensaje_telegram(BOT_TOKEN, CHAT_ID, mensaje_markdown):
            mensajes_enviados += 1
        else:
            # Fallo en el envío público. Enviamos una alerta específica.
            error_msg = f"ERROR: Fallo al enviar Evento {i+1} ({evento.get('evento_principal', 'Desconocido')}). Revisa el log de GitHub."
            print(error_msg)
            enviar_alerta_telegram(BOT_TOKEN, error_msg)
            
    print(f"--- PROCESO FINALIZADO. Mensajes enviados: {mensajes_enviados} ---")


if __name__ == "__main__":
    main()
