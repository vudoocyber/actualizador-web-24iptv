import requests
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import random # Importamos la librería random para elegir un formato aleatorio

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


# --- NUEVAS VARIABLES DE MENSAJE DINÁMICO (10 Plantillas) ---
# Usaremos {organizador}, {competidores}, {detalle_partido}, {horarios}, {canales}
# como placeholders dentro de cada plantilla.
MENSAJE_PLANTILLAS = [
    # 1. Énfasis en lo imperdible
    {
        "titulo": "🔥 *¡EVENTO IMPERDIBLE DEL DÍA!* 🔥",
        "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Sede: {detalle_partido}\n⏰ Horario: *{horarios}*\n📺 Canales: _{canales}_",
        "cierre": "⚡ *¡Máxima adrenalina!* Mira la acción aquí:\n"
    },
    # 2. Énfasis en la competencia
    {
        "titulo": "🚨 *ALERTA DE COMPETENCIA ÉPICA* 🚨",
        "cuerpo": "*{organizador}*\n🆚 Partido: *{competidores}*\n📍 Ubicación: {detalle_partido}\n🕓 Hora CDMX/MEX: *{horarios}*\n📡 Transmisión: _{canales}_",
        "cierre": "📲 No te quedes fuera. ¡Sintoniza ya!:\n"
    },
    # 3. Formato de recordatorio rápido
    {
        "titulo": "🔔 *RECORDATORIO: ¡A JUGAR!* 🔔",
        "cuerpo": "⚽ *{competidores}* — Hoy\n⏱️ Horarios: *{horarios}*\n🎥 Dónde Verlo: _{canales}_",
        "cierre": "🔗 Todos los detalles en nuestra web:\n"
    },
    # 4. Formato de Noticia de Última Hora
    {
        "titulo": "📰 *HOY EN EL DEPORTE: ¡EVENTAZO!* 📰",
        "cuerpo": "*{organizador}*\n💥 Enfrentamiento: *{competidores}*\n🌎 Zona Horaria: *{horarios}*\n¡En vivo por! _{canales}_",
        "cierre": "➡️ Acceso directo y horarios locales:\n"
    },
    # 5. Estilo "Vibrante"
    {
        "titulo": "🤩 *¡VIBRA CON EL PARTIDO ESTELAR!* 🤩",
        "cuerpo": "⚽ Evento: *{competidores}*\n🗓️ Fecha: {detalle_partido}\n⌚ ¡Prepara el reloj! *{horarios}*\n📺 Velo en HD: _{canales}_",
        "cierre": "🔥 ¡La emoción está asegurada! Míralo aquí:\n"
    },
    # 6. Estilo "Faltan Pocas Horas"
    {
        "titulo": "⏳ *FALTAN POCAS HORAS PARA...* ⏳",
        "cuerpo": "*{organizador}*\n👊 Duelo: *{competidores}*\n🏟️ Sede: {detalle_partido}\n⏱️ Comienza: *{horarios}*\n📺 Canales: _{canales}_",
        "cierre": "🚀 ¡Despegamos! Link rápido:\n"
    },
    # 7. Formato con ubicación
    {
        "titulo": "📍 *¿DÓNDE ESTÁ LA ACCIÓN HOY?* 📍",
        "cuerpo": "*{organizador}*\n🏟️ Desde el {detalle_partido}\n⚔️ Batalla: *{competidores}*\n⏰ Horario Principal: *{horarios}*\n📺 Múltiples Canales: _{canales}_",
        "cierre": "🌐 Toda la programación:\n"
    },
    # 8. Énfasis en el canal
    {
        "titulo": "📺 *GUÍA RÁPIDA DE TRANSMISIÓN* 📺",
        "cuerpo": "*{organizador}* - *{competidores}*\n🕐 Horario: *{horarios}*\n🥇 Canales destacados: _{canales}_",
        "cierre": "👇 Haz click para ver la lista completa de canales:\n"
    },
    # 9. Estilo "Clásico"
    {
        "titulo": "⭐ *DESTACADO DEL DÍA* ⭐",
        "cuerpo": "🏆 Encuentro: *{competidores}*\n🏟️ Sede: {detalle_partido}\n⏰ Horario: *{horarios}*\n📺 Canales: _{canales}_",
        "cierre": "➡️ ¡No te lo pierdas! Mira la acción aquí:\n"
    },
    # 10. Estilo "Deportivo"
    {
        "titulo": "⚽ *EL PARTIDO MÁS ESPERADO* 🏀",
        "cuerpo": "*{organizador}*\n🏆 Competencia: *{competidores}*\n⏱️ Horario de inicio: *{horarios}*\n📡 Cobertura total: _{canales}_",
        "cierre": "¡Prepárate! Enlace a la guía completa:\n"
    }
]

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
    plantilla de mensaje aleatoria.
    """
    # Escapamos caracteres especiales de Markdown
    def escape_markdown(text):
        # Escapamos los caracteres que Telegram podría interpretar como formato
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
    
    # 1. SELECCIONAR PLANTILLA ALEATORIA
    plantilla = random.choice(MENSAJE_PLANTILLAS)
    
    # 2. CONSTRUIR CUERPO DEL MENSAJE (Sustitución de placeholders)
    # Rellenamos los placeholders con los datos de escape_markdown ya aplicados
    cuerpo_dinamico = plantilla["cuerpo"].format(
        organizador=organizador,
        competidores=competidores,
        detalle_partido=detalle_partido,
        horarios=horarios,
        canales=canales
    )
    
    # 3. CONSTRUCCIÓN FINAL
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
