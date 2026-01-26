import requests
import os
import json
from datetime import datetime, date
from zoneinfo import ZoneInfo
import re
import random 

# --- CONFIGURACIÓN Y SECRETS ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
URL_VALIDACION = os.environ.get("URL_EVENTOS_JSON") 
URL_RANKING = os.environ.get("URL_RANKING_JSON")      
TELEGRAM_ALERT_CHAT_ID = os.environ.get("TELEGRAM_ALERT_CHAT_ID") 
MEXICO_TZ = ZoneInfo(os.environ.get("TZ", "America/Mexico_City")) 

# --- HEADERS DE SEGURIDAD ---
HEADERS_SEGURIDAD = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/json,xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Referer': 'https://24hometv.xyz/',
    'Connection': 'keep-alive'
}

# --- DICCIONARIO DE PLANTILLAS EXPANDIDO ---
PLANTILLAS_POR_DEPORTE = {
    # ⚽ FÚTBOL (5 Variantes)
    "⚽": [
        {
            "titulo": "⚽ *¡PARTIDAZO DE FÚTBOL!* ⚽",
            "cuerpo": "🏆 Encuentro: *{competidores}*\n\n🏟️ Estadio: {detalle_partido}\n\n⏰ Horario: *{horarios}*\n\n📺 Transmisión: _{canales}_",
            "cierre": "⚡ *Consulta horarios y canales aquí* 👇\n\n",
            "ESPECIAL_FIN_SEMANA": True
        },
        {
            "titulo": "⚽🚨 *ALERTA DE GOLAZOS* 🚨⚽",
            "cuerpo": "*{organizador}*\n\n🆚 Partido: *{competidores}*\n\n🕓 Hora: *{horarios}*\n\n📡 Ver en: _{canales}_",
            "cierre": "📲 No te quedes fuera:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "⚽🔥 *FIEBRE DE FÚTBOL* 🔥⚽",
            "cuerpo": "🏟️ Sede: {detalle_partido}\n\n🏅 Duelo: *{competidores}*\n\n🕒 Inicio: *{horarios}*\n\n📺 Canales: _{canales}_",
            "cierre": "👇 *Guía completa aquí*:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "⚽🏆 *JORNADA DE CAMPEONES* 🏆⚽",
            "cuerpo": "*{organizador}*\n\n⚔️ Enfrentamiento: *{competidores}*\n\n⏰ Kickoff: *{horarios}*\n\n🎥 Dónde ver: _{canales}_",
            "cierre": "🌐 Toda la información:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "⚽📢 *FÚTBOL EN VIVO AHORA* 📢⚽",
            "cuerpo": "🏅 *{competidores}*\n\n📍 Desde: {detalle_partido}\n\n⏱️ Hora: *{horarios}*\n\n📺 Señal: _{canales}_",
            "cierre": "🔗 Sigue el partido:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],

    # 🏈 NFL / AMERICANO (5 Variantes)
    "🏈": [
        {
            "titulo": "🏈 *¡TOUCHDOWN!* 🏈",
            "cuerpo": "🏆 Juego: *{competidores}*\n\n🏟️ Estadio: {detalle_partido}\n\n🕒 Kickoff: *{horarios}*\n\n📺 Ver en: _{canales}_",
            "cierre": "💪 *Consulta detalles aquí*:\n\n",
            "ESPECIAL_FIN_SEMANA": True
        },
        {
            "titulo": "🏈🚨 *ALERTA NFL / NCAA* 🚨🏈",
            "cuerpo": "*{organizador}*\n\n⚔️ Enfrentamiento: *{competidores}*\n\n🕓 Hora: *{horarios}*\n\n📡 Transmisión: _{canales}_",
            "cierre": "📲 Guía completa:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏈🛡️ *BATALLA EN EL GRIDIRON* 🛡️🏈",
            "cuerpo": "🏅 Duelo: *{competidores}*\n\n📍 Sede: {detalle_partido}\n\n⏰ Hora: *{horarios}*\n\n📺 Canal: _{canales}_",
            "cierre": "🔗 Estadísticas y más:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏈🔥 *ZONA ROJA: PARTIDO CLAVE* 🔥🏈",
            "cuerpo": "*{organizador}*\n\n🏈 Juegan: *{competidores}*\n\n⏱️ Inicio: *{horarios}*\n\n🎥 Cobertura: _{canales}_",
            "cierre": "👉 No te pierdas nada:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏈📢 *FÚTBOL AMERICANO HOY* 📢🏈",
            "cuerpo": "🏆 *{competidores}*\n\n🏟️ Lugar: {detalle_partido}\n\n🕓 Kickoff: *{horarios}*\n\n📺 Dónde ver: _{canales}_",
            "cierre": "🌐 Link de transmisión:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],

    # ⚾ BÉISBOL (5 Variantes)
    "⚾": [
        {
            "titulo": "⚾ *¡PLAY BALL!* ⚾",
            "cuerpo": "🏆 Duelo: *{competidores}*\n\n🏟️ Estadio: {detalle_partido}\n\n🕓 Hora: *{horarios}*\n\n📺 Transmisión: _{canales}_",
            "cierre": "🤩 *Consulta aquí*:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "⚾🔥 *BÉISBOL EN VIVO* 🔥⚾",
            "cuerpo": "🏅 Evento: *{competidores}*\n\n🕒 Inicio: *{horarios}*\n\n🎥 Canales: _{canales}_",
            "cierre": "🔗 Sigue el juego:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "⚾🧢 *TARDE DE DIAMANTE* 🧢⚾",
            "cuerpo": "*{organizador}*\n\n⚔️ Partido: *{competidores}*\n\n⏰ Primera bola: *{horarios}*\n\n📺 Ver en: _{canales}_",
            "cierre": "📲 Resultados en vivo:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "⚾🚨 *ALERTA MLB / LMP* 🚨⚾",
            "cuerpo": "🏟️ Sede: {detalle_partido}\n\n🆚 Equipos: *{competidores}*\n\n⏱️ Hora: *{horarios}*\n\n📡 Señal: _{canales}_",
            "cierre": "👉 Guía de canales:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "⚾💥 *HOME RUN DEL DÍA* 💥⚾",
            "cuerpo": "*{organizador}*\n\n🏆 *{competidores}*\n\n🕓 Comienza: *{horarios}*\n\n📺 Transmisión: _{canales}_",
            "cierre": "🌐 Todos los detalles:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],

    # 🏀 BASKETBALL (5 Variantes)
    "🏀": [
        {
            "titulo": "🏀 *¡ACCIÓN EN LA DUELA!* 🏀",
            "cuerpo": "🏆 Juego: *{competidores}*\n\n🏟️ Sede: {detalle_partido}\n\n🕓 Hora: *{horarios}*\n\n📺 Ver en: _{canales}_",
            "cierre": "⚡ *Detalles aquí*:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏀🚨 *ALERTA BASKET* 🚨🏀",
            "cuerpo": "*{organizador}*\n\n⚔️ Duelo: *{competidores}*\n\n⏰ Horario: *{horarios}*\n\n📡 Cobertura: _{canales}_",
            "cierre": "📲 Guía completa:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏀🔥 *SHOWTIME: NBA & MÁS* 🔥🏀",
            "cuerpo": "🏅 Partido: *{competidores}*\n\n📍 Arena: {detalle_partido}\n\n⏱️ Salto inicial: *{horarios}*\n\n🎥 Canal: _{canales}_",
            "cierre": "🔗 Sigue el marcador:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏀⛹️‍♂️ *BASKETBALL EN VIVO* ⛹️‍♂️🏀",
            "cuerpo": "*{organizador}*\n\n🆚 Equipos: *{competidores}*\n\n🕒 Hora: *{horarios}*\n\n📺 Transmisión: _{canales}_",
            "cierre": "👉 Dónde ver:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏀⭐ *PARTIDAZO EN LA PINTURA* ⭐🏀",
            "cuerpo": "🏆 *{competidores}*\n\n🏟️ Lugar: {detalle_partido}\n\n⏰ Hora: *{horarios}*\n\n📡 Señal: _{canales}_",
            "cierre": "🌐 Toda la info:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],

    # ⛳ GOLF (2 Variantes)
    "⛳": [
        {
            "titulo": "⛳ *¡DÍA DE GOLF!* ⛳",
            "cuerpo": "🏆 Torneo: *{organizador}*\n\n🏌️‍♂️ Ronda/Evento: *{competidores}*\n\n⛳ Campo: {detalle_partido}\n\n⏰ Tee Time/Inicio: *{horarios}*\n\n📺 Transmisión: _{canales}_",
            "cierre": "⚡ *Sigue el leaderboard aquí* 👇\n\n",
            "ESPECIAL_FIN_SEMANA": True
        },
        {
            "titulo": "⛳🏌️‍♂️ *SWING PERFECTO EN VIVO* 🏌️‍♂️⛳",
            "cuerpo": "🏅 Evento: *{competidores}*\n\n📍 Sede: {detalle_partido}\n\n🕓 Horario TV: *{horarios}*\n\n📡 Ver en: _{canales}_",
            "cierre": "📲 Guía de transmisión:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],

    # 🏒 NHL / HOCKEY (3 Variantes)
    "🏒": [
        {
            "titulo": "🏒 *¡FACE-OFF! HOCKEY EN VIVO* 🏒",
            "cuerpo": "🏆 Partido: *{competidores}*\n\n🧊 Pista: {detalle_partido}\n\n⏰ Hora: *{horarios}*\n\n📺 Transmisión: _{canales}_",
            "cierre": "❄️ *Sigue la acción aquí* 👇\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏒🚨 *ALERTA NHL / HIELO* 🚨🏒",
            "cuerpo": "*{organizador}*\n\n⚔️ Duelo: *{competidores}*\n\n⏱️ Inicio: *{horarios}*\n\n📡 Canal: _{canales}_",
            "cierre": "👉 Consulta horarios:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🏒🥅 *POWER PLAY EN PROGRESO* 🥅🏒",
            "cuerpo": "🏅 Evento: *{competidores}*\n\n📍 Arena: {detalle_partido}\n\n🕓 Hora: *{horarios}*\n\n🎥 Cobertura: _{canales}_",
            "cierre": "🔗 Ver detalles:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ],

    # ⭐ GENÉRICO / VARIOS (5 Variantes)
    "⭐": [
        {
            "titulo": "⭐ *DESTACADO DEL DÍA* ⭐",
            "cuerpo": "🏆 Evento: *{competidores}*\n\n🏟️ Detalle: {detalle_partido}\n\n⏰ Horario: *{horarios}*\n\n📺 Canales: _{canales}_",
            "cierre": "➡️ ¡Consulta más aquí!:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🔥 *EVENTO EN VIVO* 🔥",
            "cuerpo": "🏆 Competencia: *{competidores}*\n\n⌚ Hora: *{horarios}*\n\n📡 Transmisión: _{canales}_",
            "cierre": "📲 ¡Sintoniza ya!:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "📺 *GUÍA DE TRANSMISIÓN* 📺",
            "cuerpo": "*{organizador}*\n\n🏅 *{competidores}*\n\n🕐 Hora: *{horarios}*\n\n🎥 Canales: _{canales}_",
            "cierre": "👇 Info completa:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "📰 *AGENDA DEPORTIVA* 📰",
            "cuerpo": "🏅 Evento: *{competidores}*\n\n📍 Ubicación: {detalle_partido}\n\n🕒 Inicio: *{horarios}*\n\n📺 Cobertura: _{canales}_",
            "cierre": "🌐 Programación completa:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        },
        {
            "titulo": "🔔 *NO TE LO PIERDAS* 🔔",
            "cuerpo": "*{organizador}*\n\n⚔️ *{competidores}*\n\n⏱️ Horarios: *{horarios}*\n\n📡 Dónde ver: _{canales}_",
            "cierre": "🔗 Acceso rápido:\n\n",
            "ESPECIAL_FIN_SEMANA": False
        }
    ]
}

# --- FUNCIONES AUXILIARES ---

def enviar_alerta_telegram(token, mensaje):
    if not token or not TELEGRAM_ALERT_CHAT_ID:
        return False
    url_api = f"https://api.telegram.org/bot{token}/sendMessage"
    def escape_for_alert(text):
        return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)
    payload = {'chat_id': TELEGRAM_ALERT_CHAT_ID, 'text': f"🚨 *ALERTA* 🚨\n\n{escape_for_alert(mensaje)}", 'parse_mode': 'Markdown'}
    try:
        requests.post(url_api, json=payload).raise_for_status()
        return True
    except:
        return False

def es_fin_de_semana():
    return datetime.now(MEXICO_TZ).weekday() >= 5 

def es_evento_femenino(evento):
    organizador = evento.get('evento_principal', '').upper()
    descripcion = evento.get('partidos', [{}])[0].get('descripcion', '').upper()
    palabras_clave = ['FEMENIL', 'WNBA', 'NWSL', 'WOMEN', 'FEMENINO', 'LIGA MX FEMENIL', 'QUEENS LEAGUE']
    return any(k in organizador or k in descripcion for k in palabras_clave)

def validar_fecha_actualizacion(url_json):
    try:
        respuesta = requests.get(url_json, headers=HEADERS_SEGURIDAD, timeout=10)
        respuesta.raise_for_status()
        datos = respuesta.json()
        fecha_act = datetime.fromisoformat(datos.get("fecha_actualizacion")).date()
        hoy = datetime.now(MEXICO_TZ).date()
        if fecha_act == hoy:
            print(f"Fecha válida: {fecha_act}")
            return True
        print(f"Fecha inválida: JSON {fecha_act} vs Hoy {hoy}")
        return False
    except Exception as e:
        raise Exception(f"Error validando fecha: {e}")

def obtener_eventos_rankeados(url_ranking):
    try:
        respuesta = requests.get(url_ranking, headers=HEADERS_SEGURIDAD, timeout=10)
        respuesta.raise_for_status()
        eventos = respuesta.json().get("eventos_relevantes", [])
        return [e for e in eventos if not es_evento_femenino(e)]
    except Exception as e:
        raise Exception(f"Error obteniendo ranking: {e}")

def formatear_mensaje_telegram(evento):
    def escape_markdown(text):
        return re.sub(r'([\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

    if evento.get('partidos'):
        partido = evento['partidos'][0]
    else:
        partido = evento 

    # Lógica de respaldo para competidores
    lista_competidores = partido.get('competidores', [])
    descripcion_partido = partido.get('descripcion', '').strip()
    nombre_evento_principal = evento.get('evento_principal', 'Evento Deportivo')

    if lista_competidores:
        texto_central = " vs ".join(lista_competidores)
    elif descripcion_partido:
        texto_central = descripcion_partido
    else:
        texto_central = nombre_evento_principal

    # Extracción de datos
    competidores = escape_markdown(texto_central)
    horarios = escape_markdown(partido.get('horarios', 'Sin hora'))
    canales = escape_markdown(", ".join(partido.get('canales', ['Canal Desconocido'])))
    organizador = escape_markdown(nombre_evento_principal)
    detalle_partido = escape_markdown(partido.get('detalle_partido', 'Sede por confirmar'))
    
    # Detección de deporte (ACTUALIZADO CON GOLF Y HOCKEY)
    tipo_deporte = "⭐"
    texto_para_emoji = nombre_evento_principal
    
    if re.search(r'(⚽|\u26BD)', texto_para_emoji): tipo_deporte = "⚽"
    elif re.search(r'(🏈|\U0001F3C8)', texto_para_emoji): tipo_deporte = "🏈"
    elif re.search(r'(⚾|\u26BE)', texto_para_emoji): tipo_deporte = "⚾"
    elif re.search(r'(🏀|\U0001F3C0)', texto_para_emoji): tipo_deporte = "🏀"
    elif re.search(r'(⛳|\u26F3)', texto_para_emoji): tipo_deporte = "⛳"  # GOLF
    elif re.search(r'(🏒|\U0001F3D2)', texto_para_emoji): tipo_deporte = "🏒"  # HOCKEY
    elif re.search(r'(🥊|\U0001F94A|🤼)', texto_para_emoji): tipo_deporte = "⭐" # Uso genérico para combate si no hay específico
             
    # Selección de plantilla
    es_weekend = es_fin_de_semana()
    plantillas_pool = PLANTILLAS_POR_DEPORTE.get(tipo_deporte, PLANTILLAS_POR_DEPORTE["⭐"])
    
    if es_weekend:
        candidatas = plantillas_pool
    else:
        candidatas = [p for p in plantillas_pool if not p.get("ESPECIAL_FIN_SEMANA")]
    
    if not candidatas: candidatas = PLANTILLAS_POR_DEPORTE["⭐"]

    plantilla = random.choice(candidatas)
    
    cuerpo = plantilla["cuerpo"].format(
        organizador=organizador,
        competidores=competidores,
        detalle_partido=detalle_partido,
        horarios=horarios,
        canales=canales
    )
    
    return f"{plantilla['titulo']}\n\n{cuerpo}\n\n{plantilla['cierre']}https://24hometv.xyz/"

def enviar_mensaje_telegram(token, chat_id, mensaje):
    if not token or not chat_id: return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': mensaje, 'parse_mode': 'Markdown'}
    try:
        r = requests.post(url, json=payload, timeout=20)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"Error enviando mensaje: {e}")
        return False

def main():
    if not (BOT_TOKEN and CHAT_ID and URL_VALIDACION and URL_RANKING and TELEGRAM_ALERT_CHAT_ID):
        print("Faltan secrets.")
        return

    print("--- INICIANDO ENVÍO ---")
    
    try:
        if not validar_fecha_actualizacion(URL_VALIDACION): return
    except Exception as e:
        print(e); enviar_alerta_telegram(BOT_TOKEN, str(e)); return

    try:
        eventos = obtener_eventos_rankeados(URL_RANKING)
    except Exception as e:
        print(e); enviar_alerta_telegram(BOT_TOKEN, str(e)); return
    
    if not eventos: print("Sin eventos."); return
        
    print(f"Enviando {len(eventos[:5])} eventos...")
    enviados = 0
    for i, evento in enumerate(eventos[:5]): 
        msg = formatear_mensaje_telegram(evento)
        if enviar_mensaje_telegram(BOT_TOKEN, CHAT_ID, msg):
            enviados += 1
            print(f"Evento {i+1} enviado.")
        else:
            enviar_alerta_telegram(BOT_TOKEN, f"Fallo envío Evento {i+1}")
            
    print(f"Finalizado. Enviados: {enviados}")

if __name__ == "__main__":
    main()
