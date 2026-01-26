import requests
import os
import json
from datetime import datetime, date
from zoneinfo import ZoneInfo
import re
import random 

# --- Mapeo de meses ---
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

PLANTILLAS_POR_DEPORTE = {
    "⚽": [
        {"titulo": "⚽ *¡PARTIDAZO DE FÚTBOL!* ⚽", "cuerpo": "🏆 Encuentro: *{competidores}*\n\n🏟️ Estadio: {detalle_partido}\n\n⏰ Horario: *{horarios}*\n\n📺 Transmisión: _{canales}_", "cierre": "⚡ *Consulta horarios y canales aquí* 👇\n\n", "ESPECIAL_FIN_SEMANA": True},
        {"titulo": "⚽🚨 *ALERTA DE GOLAZOS* 🚨⚽", "cuerpo": "*{organizador}*\n\n🆚 Partido: *{competidores}*\n\n🕓 Hora: *{horarios}*\n\n📡 Ver en: _{canales}_", "cierre": "📲 No te quedes fuera:\n\n", "ESPECIAL_FIN_SEMANA": False},
        {"titulo": "⚽🔥 *FIEBRE DE FÚTBOL* 🔥⚽", "cuerpo": "🏟️ Sede: {detalle_partido}\n\n🏅 Duelo: *{competidores}*\n\n🕒 Inicio: *{horarios}*\n\n📺 Canales: _{canales}_", "cierre": "👇 *Guía completa aquí*:\n\n", "ESPECIAL_FIN_SEMANA": False}
    ],
    "🏈": [
        {"titulo": "🏈 *¡TOUCHDOWN!* 🏈", "cuerpo": "🏆 Juego: *{competidores}*\n\n🏟️ Estadio: {detalle_partido}\n\n🕒 Kickoff: *{horarios}*\n\n📺 Ver en: _{canales}_", "cierre": "💪 *Consulta detalles aquí*:\n\n", "ESPECIAL_FIN_SEMANA": True},
        {"titulo": "🏈🚨 *ALERTA NFL / NCAA* 🚨🏈", "cuerpo": "*{organizador}*\n\n⚔️ Enfrentamiento: *{competidores}*\n\n🕓 Hora: *{horarios}*\n\n📡 Transmisión: _{canales}_", "cierre": "📲 Guía completa:\n\n", "ESPECIAL_FIN_SEMANA": False}
    ],
    "⚾": [
        {"titulo": "⚾ *¡PLAY BALL!* ⚾", "cuerpo": "🏆 Duelo: *{competidores}*\n\n🏟️ Estadio: {detalle_partido}\n\n🕓 Hora: *{horarios}*\n\n📺 Transmisión: _{canales}_", "cierre": "🤩 *Consulta aquí*:\n\n", "ESPECIAL_FIN_SEMANA": False},
        {"titulo": "⚾🔥 *BÉISBOL EN VIVO* 🔥⚾", "cuerpo": "🏅 Evento: *{competidores}*\n\n🕒 Inicio: *{horarios}*\n\n🎥 Canales: _{canales}_", "cierre": "🔗 Sigue el juego:\n\n", "ESPECIAL_FIN_SEMANA": False}
    ],
    "🏀": [
        {"titulo": "🏀 *¡ACCIÓN EN LA DUELA!* 🏀", "cuerpo": "🏆 Juego: *{competidores}*\n\n🏟️ Sede: {detalle_partido}\n\n🕓 Hora: *{horarios}*\n\n📺 Ver en: _{canales}_", "cierre": "⚡ *Detalles aquí*:\n\n", "ESPECIAL_FIN_SEMANA": False},
        {"titulo": "🏀🚨 *ALERTA BASKET* 🚨🏀", "cuerpo": "*{organizador}*\n\n⚔️ Duelo: *{competidores}*\n\n⏰ Horario: *{horarios}*\n\n📡 Cobertura: _{canales}_", "cierre": "📲 Guía completa:\n\n", "ESPECIAL_FIN_SEMANA": False}
    ],
    "🥊": [
        {"titulo": "🥊 *¡NOCHE DE PELEA!* 🥊", "cuerpo": "*{organizador}*\n\n👊 Combate: *{competidores}*\n\n🏟️ Sede: {detalle_partido}\n\n⏱️ Hora: *{horarios}*\n\n📺 Ver en: _{canales}_", "cierre": "🔥 *Cartelera completa aquí*:\n\n", "ESPECIAL_FIN_SEMANA": True},
        {"titulo": "🥊🚨 *ALERTA UFC / BOX* 🚨🥊", "cuerpo": "🏅 Evento: *{competidores}*\n\n🕓 Hora: *{horarios}*\n\n📡 Transmisión: _{canales}_", "cierre": "📲 Sigue el evento:\n\n", "ESPECIAL_FIN_SEMANA": False}
    ],
    "🏎️": [
        {"titulo": "🏁 *¡MOTOR EN MARCHA!* 🏎️", "cuerpo": "*{organizador}*\n\n🛣️ Carrera/Sesión: *{competidores}*\n\n📍 Circuito: {detalle_partido}\n\n⏱️ Hora: *{horarios}*\n\n📺 Ver en: _{canales}_", "cierre": "💨 *Consulta horarios aquí*:\n\n", "ESPECIAL_FIN_SEMANA": True},
        {"titulo": "🏎️🚨 *ALERTA F1 / NASCAR* 🚨🏎️", "cuerpo": "🏅 Evento: *{competidores}*\n\n⏰ Horario: *{horarios}*\n\n🎥 Canales: _{canales}_", "cierre": "🔗 Acceso directo:\n\n", "ESPECIAL_FIN_SEMANA": False}
    ],
    "🎾": [
        {"titulo": "🎾 *TENIS EN VIVO* 🎾", "cuerpo": "*{organizador}*\n\n⚔️ Partido/Ronda: *{competidores}*\n\n📍 Torneo: {detalle_partido}\n\n⏱️ Hora: *{horarios}*\n\n📺 Transmisión: _{canales}_", "cierre": "👉 Sigue el marcador:\n\n", "ESPECIAL_FIN_SEMANA": False},
        {"titulo": "🎾🔔 *ALERTA GRAND SLAM / ATP* 🔔🎾", "cuerpo": "🏆 Evento: *{competidores}*\n\n⏰ Horario: *{horarios}*\n\n🎥 Dónde Verlo: _{canales}_", "cierre": "🌐 Resultados:\n\n", "ESPECIAL_FIN_SEMANA": False}
    ],
    "⭐": [
        {"titulo": "⭐ *DESTACADO DEL DÍA* ⭐", "cuerpo": "🏆 Evento: *{competidores}*\n\n🏟️ Detalle: {detalle_partido}\n\n⏰ Horario: *{horarios}*\n\n📺 Canales: _{canales}_", "cierre": "➡️ ¡Consulta más aquí!:\n\n", "ESPECIAL_FIN_SEMANA": False},
        {"titulo": "🔥 *EVENTO EN VIVO* 🔥", "cuerpo": "🏆 Competencia: *{competidores}*\n\n⌚ Hora: *{horarios}*\n\n📡 Transmisión: _{canales}_", "cierre": "📲 ¡Sintoniza ya!:\n\n", "ESPECIAL_FIN_SEMANA": False}
    ]
}

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

# --- AQUÍ ESTÁ LA CORRECCIÓN CLAVE ---
def formatear_mensaje_telegram(evento):
    def escape_markdown(text):
        return re.sub(r'([\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

    if evento.get('partidos'):
        partido = evento['partidos'][0]
    else:
        partido = evento 

    # 1. INTELIGENCIA PARA EL CAMPO "COMPETIDORES"
    # Si la lista de competidores está vacía (como en el Tenis o F1),
    # usamos la "descripcion" (ej: Cuartos de Final) como el texto principal.
    lista_competidores = partido.get('competidores', [])
    descripcion_partido = partido.get('descripcion', '').strip()
    nombre_evento_principal = evento.get('evento_principal', 'Evento Deportivo')

    if lista_competidores:
        # Caso ideal: Hay equipos (Real Madrid vs Barcelona)
        texto_central = " vs ".join(lista_competidores)
    elif descripcion_partido:
        # Caso Tenis/Torneos: Usamos la descripción (Cuartos de Final)
        # Y le agregamos contexto si es necesario
        texto_central = descripcion_partido
    else:
        # Caso Extremo: Usamos el nombre del evento para no mandar vacío
        texto_central = nombre_evento_principal

    # Extracción de datos con escape para Markdown
    competidores = escape_markdown(texto_central)
    horarios = escape_markdown(partido.get('horarios', 'Sin hora'))
    canales = escape_markdown(", ".join(partido.get('canales', ['Canal Desconocido'])))
    organizador = escape_markdown(nombre_evento_principal)
    detalle_partido = escape_markdown(partido.get('detalle_partido', 'Sede por confirmar'))
    
    # Detección de deporte
    tipo_deporte = "⭐"
    texto_para_emoji = nombre_evento_principal
    
    if re.search(r'(⚽|\u26BD)', texto_para_emoji): tipo_deporte = "⚽"
    elif re.search(r'(🏈|\U0001F3C8)', texto_para_emoji): tipo_deporte = "🏈"
    elif re.search(r'(⚾|\u26BE)', texto_para_emoji): tipo_deporte = "⚾"
    elif re.search(r'(🏀|\U0001F3C0)', texto_para_emoji): tipo_deporte = "🏀"
    elif re.search(r'(🎾|\U0001F3BE)', texto_para_emoji): tipo_deporte = "🎾"
    elif re.search(r'(🥊|\U0001F94A|🤼)', texto_para_emoji): tipo_deporte = "🥊"
    elif re.search(r'(🏎️|\U0001F3CE)', texto_para_emoji): tipo_deporte = "🏎️"
             
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
        competidores=competidores, # ¡AHORA YA NO ESTARÁ VACÍO!
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
