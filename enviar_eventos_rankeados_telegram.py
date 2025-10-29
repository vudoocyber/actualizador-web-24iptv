import requests
import os
import json
from datetime import datetime
import pytz # Usamos pytz para consistencia
import re
import random 

# --- CONFIGURACIÓN Y SECRETS ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# URL_VALIDACION ya no es necesaria, se elimina.
URL_RANKING = os.environ.get("URL_RANKING_JSON")     
MEXICO_TZ = pytz.timezone(os.environ.get("TZ", "America/Mexico_City")) 
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; Script/1.0)'}

# --- DICCIONARIO DE PLANTILLAS POR DEPORTE (AMPLIADO) ---
PLANTILLAS_POR_DEPORTE = {
    "⚽": [
        {"titulo": "⚽ *¡PARTIDAZO DEL DÍA!* ⚽", "cuerpo": "🏆 Duelo: *{competidores}*\n🏟️ Sede: {detalle_partido}\n⏰ Horario: *{horarios}*\n📺 Transmisión: _{canales}_", "cierre": "⚡ ¡Que ruede el balón! Sigue la acción aquí:\n"},
        {"titulo": "🚨 *ALERTA DE GOL* 🚨", "cuerpo": "*{organizador}*\n🆚 Encuentro: *{competidores}*\n📍 Estadio: {detalle_partido}\n🕓 Hora CDMX: *{horarios}*\n📡 Cobertura: _{canales}_", "cierre": "📲 ¡No te quedes fuera! Sintoniza ya:\n"},
        {"titulo": "🔥 *FIEBRE DE FÚTBOL EN VIVO* 🔥", "cuerpo": "🏅 Duelo Clave: *{competidores}*\n🕒 Inicio: *{horarios}*\n📺 Míralo en: _{canales}_", "cierre": "👇 Todos los detalles y links:\n"},
        {"titulo": "🏆 *JORNADA DE ALTO VOLTAJE* 🏆", "cuerpo": "⚔️ ¡Batalla! *{competidores}*\n⏰ Hora de inicio: *{horarios}*\n📺 Transmisión: _{canales}_", "cierre": "👉 No te pierdas este partido decisivo:\n"},
        {"titulo": "🎯 *GUÍA RÁPIDA: FÚTBOL HOY* 🎯", "cuerpo": "⚽ *{competidores}* — Hoy\n⏱️ Horarios: *{horarios}*\n🎥 Dónde Verlo: _{canales}_", "cierre": "🔗 Consulta toda la jornada aquí:\n"},
        {"titulo": "📣 *PARTIDO ESTELAR DE LA NOCHE* 📣", "cuerpo": "*{organizador}*\n💥 Enfrentamiento: *{competidores}*\n⏰ Horario Principal: *{horarios}*\n📺 Cobertura: _{canales}_", "cierre": "🌐 Guía completa y noticias:\n"},
        {"titulo": "⚔️ *UN CLÁSICO IMPERDIBLE* ⚔️", "cuerpo": "Una rivalidad histórica se reaviva hoy.\n🆚 Partido: *{competidores}*\n⏰ Horario: *{horarios}*\n📺 Canales: _{canales}_", "cierre": "¡Prepárate para un duelo épico! Míralo aquí:\n"},
        {"titulo": "🌍 *FÚTBOL INTERNACIONAL DE LUJO* 🌍", "cuerpo": "Los mejores equipos del mundo en acción.\n🏆 Duelo: *{competidores}*\n🕒 Inicio: *{horarios}*\n📺 Cobertura Exclusiva: _{canales}_", "cierre": "Sigue cada jugada en vivo:\n"},
        {"titulo": "⏳ *¡A POCOS MINUTOS DEL SILBATAZO INICIAL!* ⏳", "cuerpo": "El partido está por comenzar.\n⚽ *{competidores}*\n⏰ Horario: *{horarios}*\n📺 Transmisión: _{canales}_", "cierre": "¡No te lo pierdas! Link directo:\n"},
        {"titulo": "📈 *DUELO CLAVE EN LA TABLA* 📈", "cuerpo": "Puntos vitales en juego para ambos equipos.\n🆚 Partido: *{competidores}*\n🏟️ Estadio: {detalle_partido}\n🕓 Hora: *{horarios}*\n📡 Canales: _{canales}_", "cierre": "Sigue el minuto a minuto aquí:\n"}
    ],
    "🏈": [
        {"titulo": "🏈 *¡DOMINGO DE TOUCHDOWN!* 🏈", "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Estadio: {detalle_partido}\n🕒 Kickoff: *{horarios}*\n📺 Cobertura Nacional: _{canales}_", "cierre": "💪 ¡A romper las tacleadas! Mira la acción aquí:\n", "ESPECIAL_FIN_SEMANA": True},
        {"titulo": "🚨 *ALERTA NFL / NCAA EN VIVO* 🚨", "cuerpo": "*{organizador}*\n⚔️ Enfrentamiento: *{competidores}*\n🕓 Hora CDMX: *{horarios}*\n📡 Transmisión: _{canales}_", "cierre": "📲 No te pierdas este épico duelo de emparrillado:\n"},
        {"titulo": "🔥 *MÁXIMA TENSIÓN EN EL CAMPO* 🔥", "cuerpo": "🏅 Duelo: *{competidores}*\n📍 Ubicación: {detalle_partido}\n⏰ Inicio: *{horarios}*\n🎥 Canales: _{canales}_", "cierre": "🔗 Todos los pases y jugadas en vivo:\n"},
        {"titulo": "📰 *HOY: JUEGO CLAVE DE LA SEMANA* 📰", "cuerpo": "*{organizador}* - *{competidores}*\n⏱️ Horario Principal: *{horarios}*\n📺 Múltiples Canales: _{canales}_", "cierre": "🌐 Guía completa y noticias de la liga:\n"},
        {"titulo": "🏟️ *RIVALIDAD EN EL EMPARRILLADO* 🏟️", "cuerpo": "💥 Duelo divisional: *{competidores}*\n🕒 Comienza: *{horarios}*\n📡 Cobertura: _{canales}_", "cierre": "👉 Pases, yardas y más, síguelo en vivo:\n"}
    ],
    "🏀": [
        {"titulo": "🏀 *¡ACCIÓN EN LA CANCHA!* 🏀", "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Sede: {detalle_partido}\n🕓 Hora de Salto: *{horarios}*\n📺 Canales: _{canales}_", "cierre": "⚡ ¡Máxima velocidad! Mira el partido aquí:\n"},
        {"titulo": "🔥 *SHOWTIME EN EL TABLERO* 🔥", "cuerpo": "🏅 Evento: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕒 Inicio: *{horarios}*\n🎥 Canales: _{canales}_", "cierre": "🔗 Sigue los mejores highlights:\n"},
        {"titulo": "⭐ *PARTIDO DESTACADO DE LA NBA* ⭐", "cuerpo": "*{organizador}* - *{competidores}*\n⏱️ Horario Principal: *{horarios}*\n📺 Transmisión: _{canales}_", "cierre": "🌐 Guía completa de la jornada de baloncesto:\n"},
        {"titulo": "🎯 *DUELO DE GIGANTES EN LA PINTURA* 🎯", "cuerpo": "🏆 Partido: *{competidores}*\n🕓 Salto Inicial: *{horarios}*\n📺 Dónde Verlo: _{canales}_", "cierre": "🚀 Accede al link de transmisión:\n"},
        {"titulo": "🚨 *NOCHE DE TRIPLES Y CLAVADAS* 🚨", "cuerpo": "🏀 Enfrentamiento: *{competidores}*\n⏰ Hora de inicio: *{horarios}*\n📡 Cobertura: _{canales}_", "cierre": "👉 Toda la acción de la liga, aquí:\n"}
    ],
    "⚾": [
        {"titulo": "⚾ *¡HOME RUN! EL JUEGO DE HOY* ⚾", "cuerpo": "🏆 Duelo: *{competidores}*\n🏟️ Estadio: {detalle_partido}\n🕓 Primera Bola: *{horarios}*\n📺 Transmisión: _{canales}_", "cierre": "🤩 ¡Play ball! Mira el juego completo aquí:\n"},
        {"titulo": "🔔 *RECORDATORIO MLB / LMB* 🔔", "cuerpo": "*{organizador}*\n⚔️ Encuentro: *{competidores}*\n⏰ Hora CDMX: *{horarios}*\n📡 Cobertura: _{canales}_", "cierre": "📲 Conéctate al juego y las estadísticas:\n"},
        {"titulo": "🔥 *NOCHE DE BATAZOS EN EL DIAMANTE* 🔥", "cuerpo": "🏅 Evento: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕒 Inicio: *{horarios}*\n🎥 Canales: _{canales}_", "cierre": "🔗 Sigue todas las entradas en vivo:\n"},
        {"titulo": "⭐ *SERIE CLAVE DEL DÍA* ⭐", "cuerpo": "*{organizador}* - *{competidores}*\n⏱️ Horario Principal: *{horarios}*\n📺 Múltiples Canales: _{canales}_", "cierre": "🌐 Guía y resultados actualizados al instante:\n"},
        {"titulo": "🏟️ *BÉISBOL BAJO LAS LUCES* 🏟️", "cuerpo": "💥 Duelo: *{competidores}*\n⚾ Primera Bola: *{horarios}*\n📺 Transmisión: _{canales}_", "cierre": "👉 Todos los partidos de la jornada aquí:\n"}
    ],
    "🥊": [
        {"titulo": "🥊 *¡NOCHE DE NOQUEOS!* 🥊", "cuerpo": "*{organizador}*\n👊 Duelo: *{competidores}*\n🏟️ Sede: {detalle_partido}\n⏱️ Comienza: *{horarios}*\n📺 PPV/Canal: _{canales}_", "cierre": "🔥 ¡Máxima adrenalina! Mira el combate aquí:\n", "ESPECIAL_FIN_SEMANA": True},
        {"titulo": "💥 *DUELO ESTELAR DE COMBATE* 💥", "cuerpo": "*{organizador}*\n⚔️ Enfrentamiento: *{competidores}*\n📍 Lugar: {detalle_partido}\n⏰ Horario Principal: *{horarios}*\n🎥 Dónde Verlo: _{canales}_", "cierre": "🔗 Acceso directo y previa del combate:\n"},
        {"titulo": "🚨 *ALERTA UFC / BOX* 🚨", "cuerpo": "🏅 Pelea: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕓 Hora de la cartelera: *{horarios}*\n📡 Transmisión: _{canales}_", "cierre": "📲 Sigue el evento completo, round por round:\n"},
    ],
    "🏎️": [
        {"titulo": "🏁 *¡ARRANCAN LOS MOTORES!* 🏎️", "cuerpo": "*{organizador}*\n🛣️ Evento: *{competidores}*\n📍 Circuito: {detalle_partido}\n⏱️ Hora de Salida: *{horarios}*\n📺 Transmisión: _{canales}_", "cierre": "💨 ¡Velocidad pura! Mira la carrera aquí:\n", "ESPECIAL_FIN_SEMANA": True},
        {"titulo": "🚦 *LUZ VERDE PARA LA ACCIÓN* 🚦", "cuerpo": "*{organizador}*\n🏆 Competencia: *{competidores}*\n🌎 Zona Horaria: *{horarios}*\n📡 Cobertura total: _{canales}_", "cierre": "➡️ Guía completa y horarios locales:\n"},
    ],
    "🎾": [
        {"titulo": "🎾 *DUELO EN LA CANCHA CENTRAL* 🎾", "cuerpo": "*{organizador}*\n⚔️ Partido: *{competidores}*\n📍 Torneo: {detalle_partido}\n⏱️ Comienza: *{horarios}*\n📺 Transmisión: _{canales}_", "cierre": "👉 Sigue el marcador en vivo, punto a punto:\n"},
        {"titulo": "🔔 *ALERTA: TENIS PROFESIONAL* 🔔", "cuerpo": "🏆 Evento: *{competidores}*\n⏰ Horario: *{horarios}*\n🎥 Dónde Verlo: _{canales}_", "cierre": "🌐 Guía y resultados actualizados del torneo:\n"},
    ],
    "⭐": [
        {"titulo": "⭐ *DESTACADO DEL DÍA* ⭐", "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Sede: {detalle_partido}\n⏰ Horario: *{horarios}*\n📺 Canales: _{canales}_", "cierre": "➡️ ¡No te lo pierdas! Mira la acción aquí:\n"},
        {"titulo": "📰 *HOY EN EL MUNDO DEL ENTRETENIMIENTO* 📰", "cuerpo": "*{organizador}*\n🏅 Evento: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕒 Inicio: *{horarios}*\n📺 Cobertura: _{canales}_", "cierre": "🌐 Toda la programación del día:\n"},
        {"titulo": "🔔 *RECORDATORIO DE EVENTO IMPERDIBLE* 🔔", "cuerpo": "*{organizador}*\n⏱️ Horarios: *{horarios}*\n🎥 Dónde Verlo: _{canales}_", "cierre": "🔗 Todos los detalles en nuestra web:\n"},
        {"titulo": "🔥 *EVENTO EN VIVO AHORA* 🔥", "cuerpo": "🏆 Competencia: *{competidores}*\n⌚ ¡Prepara el reloj! *{horarios}*\n📡 Transmisión: _{canales}_", "cierre": "📲 ¡Sintoniza ya y no te quedes fuera!:\n"},
        {"titulo": "📺 *GUÍA RÁPIDA DE TRANSMISIÓN* 📺", "cuerpo": "*{organizador}* - *{competidores}*\n🕐 Horario: *{horarios}*\n🥇 Canales destacados: _{canales}_", "cierre": "👇 Haz click para ver la guía completa:\n"},
        {"titulo": "🎯 *PROGRAMACIÓN ESPECIAL DE HOY* 🎯", "cuerpo": "🏅 Duelo: *{competidores}*\n⏰ Horario Principal: *{horarios}*\n📺 Múltiples Canales: _{canales}_", "cierre": "🔗 Acceso directo y horarios locales:\n"},
        {"titulo": "✨ *LA NOCHE SE ILUMINA CON ESTE EVENTO* ✨", "cuerpo": "Prepárate para un espectáculo inolvidable.\n🌟 Evento: *{competidores}*\n⏰ Comienza: *{horarios}*\n📺 Transmisión: _{canales}_", "cierre": "Disfruta de la transmisión en vivo:\n"},
        {"titulo": "🚀 *¡ESTÁ POR COMENZAR!* 🚀", "cuerpo": "Faltan pocos minutos para el inicio.\n💥 Evento: *{competidores}*\n🕒 Hora: *{horarios}*\n📡 Cobertura: _{canales}_", "cierre": "Conéctate ahora mismo:\n"},
        {"titulo": "🗓️ *AGÉNDALO: EL EVENTO MÁS ESPERADO* 🗓️", "cuerpo": "*{organizador}*\n🆚 Duelo: *{competidores}*\n⏰ Horario: *{horarios}*\n📺 Canales: _{canales}_", "cierre": "Toda la información que necesitas está aquí:\n"},
        {"titulo": "💡 *RECOMENDACIÓN DEL DÍA* 💡", "cuerpo": "No te puedes perder este gran evento.\n🏆 *{competidores}*\n📍 Sede: {detalle_partido}\n🕓 Hora: *{horarios}*\n📺 Míralo en: _{canales}_", "cierre": "Sigue nuestra guía completa para más:\n"}
    ]
}

def es_fin_de_semana():
    hoy = datetime.now(MEXICO_TZ).weekday()
    return hoy >= 5

def es_evento_femenino(evento):
    organizador = evento.get('evento_principal', '').upper()
    descripcion = ''
    if evento.get('partidos') and evento['partidos']:
        descripcion = evento['partidos'][0].get('descripcion', '').upper()
    if 'FEMENIL' in organizador or 'WNBA' in organizador or 'NWSL' in organizador:
        return True
    return False

def obtener_y_validar_eventos(url_ranking):
    try:
        respuesta = requests.get(url_ranking, headers=HEADERS, timeout=10, params={'v': datetime.now().timestamp()})
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        fecha_guia_str = datos.get("fecha_guia")
        if not fecha_guia_str:
            print("Validación fallida: El campo 'fecha_guia' no se encontró en eventos-relevantes.json.")
            return []

        hoy_mx_str = datetime.now(MEXICO_TZ).strftime('%Y-%m-%d')
        
        if fecha_guia_str != hoy_mx_str:
            print(f"Validación fallida: Guía de relevantes desactualizada. Guía: {fecha_guia_str} | Hoy: {hoy_mx_str}.")
            return []

        print(f"Validación de fecha exitosa: {fecha_guia_str} coincide con hoy.")
        
        eventos = datos.get("eventos_relevantes", []) 
        eventos_filtrados = [e for e in eventos if not es_evento_femenino(e)]
        
        if len(eventos) != len(eventos_filtrados):
            print(f"Advertencia: {len(eventos) - len(eventos_filtrados)} eventos femeninos fueron filtrados.")
        
        print(f"Obtenidos {len(eventos_filtrados)} eventos rankeados.")
        return eventos_filtrados
    except Exception as e:
        print(f"Error al obtener o procesar el JSON de ranking: {e}")
        return []

def formatear_mensaje_telegram(evento):
    def escape_markdown(text):
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

    partido_principal = evento.get('partidos', [{}])[0]

    horarios = escape_markdown(partido_principal.get('horarios', 'Sin hora'))
    canales = escape_markdown(", ".join(partido_principal.get('canales', ['Desconocido'])))
    competidores = escape_markdown(" vs ".join(partido_principal.get('competidores', ['Competidores'])))
    organizador = escape_markdown(evento.get('evento_principal', 'Evento'))
    detalle_partido = escape_markdown(partido_principal.get('detalle_partido', 'Sede Desconocida'))
    
    tipo_deporte = "⭐"
    evento_principal_texto = evento.get('evento_principal', '')
    
    emoji_map = {"⚽": "⚽", "🏈": "🏈", "⚾": "⚾", "🏀": "🏀", "🎾": "🎾", "🥊": "🥊", "🏎️": "🏎️"}
    for emoji, key in emoji_map.items():
        if emoji in evento_principal_texto:
            tipo_deporte = key
            break
            
    plantillas_disponibles = PLANTILLAS_POR_DEPORTE.get(tipo_deporte, PLANTILLAS_POR_DEPORTE["⭐"])
    
    if not es_fin_de_semana():
        plantillas_filtradas = [p for p in plantillas_disponibles if not p.get("ESPECIAL_FIN_SEMANA")]
        if plantillas_filtradas:
            plantillas_disponibles = plantillas_filtradas

    plantilla = random.choice(plantillas_disponibles)
    
    cuerpo_dinamico = plantilla["cuerpo"].format(
        organizador=organizador,
        competidores=competidores,
        detalle_partido=detalle_partido,
        horarios=horarios,
        canales=canales
    )
    
    mensaje = (f"{plantilla['titulo']}\n\n"
               f"{cuerpo_dinamico}\n\n"
               f"{plantilla['cierre']}"
               f"https://24hometv.xyz/")
    return mensaje

def enviar_mensaje_telegram(token, chat_id, mensaje):
    if not token or not chat_id:
        print("Error: El token del bot o el ID del chat no están configurados.")
        return False
    
    url_api = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': mensaje, 'parse_mode': 'MarkdownV2'}
    
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
        print(f"Respuesta del servidor: {e.response.text if e.response else 'No response'}")
        return False

def main():
    if not (BOT_TOKEN and CHAT_ID and URL_RANKING):
        print("ERROR CRÍTICO: Faltan secretos de configuración. Proceso detenido.")
        return

    print("--- INICIANDO PROCESO DE ENVÍO DE EVENTOS RANKADOS ---")
    
    eventos = obtener_y_validar_eventos(URL_RANKING)
    
    if not eventos:
        print("No se encontraron eventos válidos o la guía está desactualizada. Proceso finalizado.")
        return
        
    print(f"Encontrados {len(eventos)} eventos. Iniciando envío...")
    
    mensajes_enviados = 0
    for i, evento in enumerate(eventos[:3]):
        mensaje_markdown = formatear_mensaje_telegram(evento)
        print(f"--- Enviando Mensaje {i+1} ---\n{mensaje_markdown}\n--------------------")
        if enviar_mensaje_telegram(BOT_TOKEN, CHAT_ID, mensaje_markdown):
            mensajes_enviados += 1
        else:
            print(f"Fallo en el envío del evento {i+1}.")
            
    print(f"--- PROCESO FINALIZADO. Mensajes enviados: {mensajes_enviados} ---")

if __name__ == "__main__":
    main()
