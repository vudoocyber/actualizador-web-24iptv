import requests
import os
import json
from datetime import datetime
import pytz # Usamos pytz para consistencia con los otros scripts
import re
import random 

# --- CONFIGURACIÓN Y SECRETS ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
URL_VALIDACION = os.environ.get("URL_EVENTOS_JSON") 
URL_RANKING = os.environ.get("URL_RANKING_JSON")     
MEXICO_TZ = pytz.timezone(os.environ.get("TZ", "America/Mexico_City")) 
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; Script/1.0)'}

# --- DICCIONARIO DE PLANTILLAS POR DEPORTE ---
PLANTILLAS_POR_DEPORTE = {
    # ... (Tu diccionario de plantillas completo y sin cambios)
    "⚽": [
        {"titulo": "⚽ ¡EL CLÁSICO DEL FIN DE SEMANA! ⚽", "cuerpo": "...", "ESPECIAL_FIN_SEMANA": True},
        {"titulo": "🚨 ALERTA DE GOLAZOS EN VIVO 🚨", "cuerpo": "...", "ESPECIAL_FIN_SEMANA": False},
        # ... más plantillas
    ],
    "🏈": [
        {"titulo": "🏈 ¡DÍA DE TOUCHDOWN! 🏈", "cuerpo": "...", "ESPECIAL_FIN_SEMANA": True},
        {"titulo": "🚨 ALERTA NFL / NCAA EN VIVO 🚨", "cuerpo": "...", "ESPECIAL_FIN_SEMANA": False},
        # ... más plantillas
    ],
    # ... resto de deportes
    "⭐": [
        {"titulo": "⭐ DESTACADO DEL DÍA ⭐", "cuerpo": "...", "ESPECIAL_FIN_SEMANA": False},
        {"titulo": "📰 HOY EN EL DEPORTE 📰", "cuerpo": "...", "ESPECIAL_FIN_SEMANA": False},
        # ... más plantillas
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
    if 'FEMENIL' in organizador or 'WNBA' in organizador or 'NWSL' in organizador or \
       'FEMENIL' in descripcion or 'WNBA' in descripcion or 'NWSL' in descripcion:
        return True
    return False

# --- FUNCIÓN DE VALIDACIÓN DE FECHA (ACTUALIZADA) ---
def validar_fecha_guia(url_json):
    """
    Descarga el JSON principal y verifica que la `fecha_guia` 
    corresponda al día de hoy en la Ciudad de México.
    """
    try:
        respuesta = requests.get(url_json, headers=HEADERS, timeout=10, params={'v': datetime.now().timestamp()})
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        # Leemos la nueva etiqueta 'fecha_guia'
        fecha_guia_str = datos.get("fecha_guia")
        
        if not fecha_guia_str:
            print("Validación fallida: El campo 'fecha_guia' no se encontró en el JSON.")
            return False

        # Comparamos la fecha en formato YYYY-MM-DD
        hoy_mx_str = datetime.now(MEXICO_TZ).strftime('%Y-%m-%d')
        
        if fecha_guia_str == hoy_mx_str:
            print(f"Validación de fecha exitosa: {fecha_guia_str} coincide con hoy ({hoy_mx_str}).")
            return True
        else:
            print(f"Validación de fecha fallida: Guía desactualizada. Guía: {fecha_guia_str} | Hoy: {hoy_mx_str}.")
            return False

    except Exception as e:
        print(f"Error durante la validación de fecha: {e}")
        return False

def obtener_eventos_rankeados(url_ranking):
    try:
        respuesta = requests.get(url_ranking, headers=HEADERS, timeout=10, params={'v': datetime.now().timestamp()})
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        eventos = datos.get("eventos_relevantes", []) 
        
        eventos_filtrados = [e for e in eventos if not es_evento_femenino(e)]
        
        if len(eventos) != len(eventos_filtrados):
            print(f"Advertencia: {len(eventos) - len(eventos_filtrados)} eventos femeninos fueron filtrados.")
        
        print(f"Obtenidos {len(eventos_filtrados)} eventos rankeados.")
        return eventos_filtrados

    except Exception as e:
        print(f"Error al obtener o parsear el JSON de ranking: {e}")
        return []

def formatear_mensaje_telegram(evento):
    # ... (código sin cambios)
    return ""

def enviar_mensaje_telegram(token, chat_id, mensaje):
    # ... (código sin cambios)
    return False

def main():
    if not (BOT_TOKEN and CHAT_ID and URL_VALIDACION and URL_RANKING):
        print("ERROR CRÍTICO: Faltan secretos de configuración. Proceso detenido.")
        return

    print("--- INICIANDO PROCESO DE ENVÍO DE EVENTOS RANKADOS ---")
    
    # 1. VALIDACIÓN DE FECHA (Ahora usa la nueva función)
    if not validar_fecha_guia(URL_VALIDACION):
        print("La fecha de la guía no es la de hoy. Deteniendo el envío.")
        return
    
    # 2. OBTENCIÓN Y FILTRADO DE EVENTOS
    eventos = obtener_eventos_rankeados(URL_RANKING)
    
    if not eventos:
        print("No se encontraron eventos rankeados para enviar. Proceso finalizado.")
        return
        
    # 3. ENVÍO DE MENSAJES INDIVIDUALES
    print(f"Encontrados {len(eventos)} eventos. Iniciando envío...")
    
    mensajes_enviados = 0
    for i, evento in enumerate(eventos[:3]):
        mensaje_markdown = formatear_mensaje_telegram(evento)
        
        print(f"Enviando Evento {i+1}...")
        if enviar_mensaje_telegram(BOT_TOKEN, CHAT_ID, mensaje_markdown):
            mensajes_enviados += 1
        else:
            print(f"Fallo en el envío del evento {i+1}.")
            
    print(f"--- PROCESO FINALIZADO. Mensajes enviados: {mensajes_enviados} ---")

if __name__ == "__main__":
    main()
