import requests
import json
import os
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import pytz
import re
from google import genai
from google.genai import types
import copy

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA_LEGACY = "eventos-relevantes.json"    # Top 3 con emojis
NOMBRE_ARCHIVO_SALIDA_ROKU = "eventos-destacados-roku.json" # Top 10 limpio y variado
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MEXICO_TZ = pytz.timezone('America/Mexico_City')

# --- CONFIGURACIÓN DE VARIEDAD ---
# Máximo de eventos permitidos por misma liga/deporte en la lista final
MAX_EVENTOS_POR_LIGA = 3 

# --- FUNCIÓN DE LIMPIEZA PARA ROKU ---
def limpiar_texto_roku(texto):
    if not texto:
        return ""
    # 1. Regex para eliminar emojis
    emoji_pattern = re.compile(
        r'[\U0001F000-\U0001F9FF]'
        r'|[\U00002600-\U000027BF]'
        r'|[\U0001F300-\U0001F5FF]'
        r'|[\U0001F680-\U0001F6FF]'
        r'|[\U0001F1E0-\U0001F1FF]'
        r'|[\u2700-\u27BF]',
        flags=re.UNICODE
    )
    texto_limpio = emoji_pattern.sub('', texto)
    return re.sub(r'\s+', ' ', texto_limpio).strip()

# --- 2. FUNCIÓN PARA LLAMAR A GEMINI ---
def obtener_ranking_eventos(lista_eventos):
    if not GEMINI_API_KEY:
        print("ERROR: No se encontró la API Key de Gemini. No se puede continuar.")
        return None

    print("Contactando a la IA de Gemini para obtener candidatos...")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        cst_offset = timezone(timedelta(hours=-6))
        hora_actual_cst = datetime.now(cst_offset)
        hora_formateada_cst = hora_actual_cst.strftime('%A, %d de %B de %Y - %I:%M %p CST')
        
        eventos_para_analizar = []
        for evento in lista_eventos:
            for partido in evento.get("partidos", []):
                # Incluimos el evento principal en el texto para que la IA sepa la liga
                info_completa = f"{evento.get('evento_principal', '')}: {partido.get('descripcion', '')} {partido.get('horarios', '')}"
                eventos_para_analizar.append(info_completa.strip())
        
        lista_texto_plano = "\n".join(filter(None, set(eventos_para_analizar)))
        if not lista_texto_plano:
            print("No se encontraron eventos para analizar.")
            return []

        # --- PROMPT ACTUALIZADO (LIGA MX, LIBERTADORES Y PLAYOFFS/FINALES) ---
        prompt = f"""
        Actúa como un curador de deportes experto para una TV en México y USA.
        Fecha/Hora actual (CDMX): {hora_formateada_cst}.
        
        Analiza la lista y selecciona los 20 eventos más importantes para enviarlos a filtrado.
        
        CRITERIOS DE SELECCIÓN (JERARQUÍA ESTRICTA):
        
        1. **NIVEL VIP (PRIORIDAD ABSOLUTA - INCLUIR SÍ O SÍ):**
           - **FÚTBOL:** Liga MX (Cualquier partido), Copa Libertadores, UEFA Champions League, Premier League, MLS, Eliminatorias Mundialistas y Copas de Selecciones.
           - **INSTANCIAS DECISIVAS (Cualquier Deporte):** Si un evento es **FINAL, SEMIFINAL, PLAYOFFS, CLASIFICACIÓN, ELIMINACIÓN DIRECTA o CARRERA (GP)** de: NFL, NBA, MLB, NHL, F1 o Tenis, TIENE PRIORIDAD sobre cualquier partido de temporada regular.
           - **F1:** Carreras de Gran Premio (Especialmente Checo Pérez).
           - **TENIS:** Finales de torneos importantes.

        2. **NIVEL ALTO (TEMPORADA REGULAR):**
           - Partidos normales de NFL, NBA, MLB, NHL (Priorizando equipos populares: Cowboys, Lakers, Yankees, Red Sox, Warriors, etc.).
           - Boxeo / UFC (Carteleras estelares).
        
        3. **VARIEDAD:** Intenta mezclar competiciones. No pongas 10 partidos de la misma liga si hay opciones VIP de otros deportes disponibles.
        
        4. **TIEMPO:** Ignora eventos que ya hayan finalizado según la hora actual.

        SALIDA REQUERIDA:
        - Devuelve una lista de los 20 mejores candidatos, ordenados por relevancia.
        - Formato exacto por línea: "Equipo A vs Equipo B" (Solo la descripción del partido).
        - NO uses viñetas ni numeración.

        LISTA:
        {lista_texto_plano}
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3
            )
        )
        
        if response.text:
            ranking_limpio = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
            print(f"Candidatos recibidos de Gemini: {len(ranking_limpio)}")
            return ranking_limpio
        else:
            print("Gemini devolvió una respuesta vacía.")
            return []

    except Exception as e:
        print(f"ERROR al contactar con Gemini: {e}. Omitiendo el ranking.")
        return None

# --- 3. FUNCIÓN PRINCIPAL ---
def main():
    print(f"Iniciando proceso de ranking variado...")
    
    fecha_actualizacion_iso = datetime.now(MEXICO_TZ).isoformat()
    
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        respuesta = requests.get(URL_JSON_FUENTE, headers=headers, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        fecha_guia_str = datos.get("fecha_guia")
        if not fecha_guia_str:
            print("ERROR: No se encontró la etiqueta 'fecha_guia'.")
            return

        hoy_mexico_str = datetime.now(MEXICO_TZ).strftime('%Y-%m-%d')
        if fecha_guia_str != hoy_mexico_str:
            print(f"ADVERTENCIA: Fecha guía ({fecha_guia_str}) != Hoy ({hoy_mexico_str}). Cancelando.")
            return
        
        lista_eventos_original = datos.get("eventos", [])
        if not lista_eventos_original:
            raise ValueError("El JSON está vacío.")
        
    except Exception as e:
        print(f"ERROR FATAL descarga JSON: {e}")
        return

    ranking_crudo = obtener_ranking_eventos(lista_eventos_original)

    # Lista maestra final (Objetivo: 10 eventos variados)
    eventos_relevantes_maestra = []
    
    # Contador para controlar repeticiones (Ej: {"NBA": 3, "Liga MX": 2})
    conteo_por_liga = {}

    if ranking_crudo:
        print("2. Aplicando filtros de VARIEDAD y CÓDIGO...")
        palabras_prohibidas = ["Femenil", "WNBA", "NWSL", "Femenino", "Womens"]
        
        # Pre-procesamiento: Buscar los objetos completos
        candidatos_encontrados = []
        descripciones_vistas = set()

        for desc_gemini in ranking_crudo:
            for evento in lista_eventos_original:
                for partido in evento.get("partidos", []):
                    desc_partido = partido.get("descripcion", "")
                    # Coincidencia flexible
                    if desc_partido and (desc_partido in desc_gemini or desc_gemini in desc_partido):
                        if desc_partido not in descripciones_vistas:
                            candidatos_encontrados.append((evento, partido))
                            descripciones_vistas.add(desc_partido)
                        break 
                if desc_partido in descripciones_vistas: break

        # Selección final con control de variedad
        for evento, partido in candidatos_encontrados:
            # Meta: 10 eventos para Roku
            if len(eventos_relevantes_maestra) >= 10:
                break
            
            nombre_liga = evento.get("evento_principal", "Otros")
            
            # FILTRO 1: Palabras prohibidas
            if any(keyword in nombre_liga for keyword in palabras_prohibidas):
                continue

            # FILTRO 2: Control de Variedad (Tope por liga)
            # Normalizamos el nombre de la liga (ej: "NBA Basketball" -> "NBA")
            liga_key = nombre_liga.split()[0] if nombre_liga else "Otros" 
            
            conteo_actual = conteo_por_liga.get(liga_key, 0)
            
            if conteo_actual >= MAX_EVENTOS_POR_LIGA:
                # Si ya tenemos 3 de esta liga, saltamos (para dar espacio a Champions, Premier, etc.)
                # Excepción: Si nos faltan muchos eventos para llenar 6, somos permisivos
                if len(eventos_relevantes_maestra) > 5:
                    continue 
            
            # Agregar evento
            evento_relevante = {
                "evento_principal": nombre_liga,
                "detalle_evento": evento.get("detalle_evento", ""),
                "partidos": [partido]
            }
            eventos_relevantes_maestra.append(evento_relevante)
            
            # Actualizar contador
            conteo_por_liga[liga_key] = conteo_actual + 1
        
        print(f"Ranking Maestro Variado (Top {len(eventos_relevantes_maestra)}):")
        for ev in eventos_relevantes_maestra:
            print(f" - {ev['evento_principal']}: {ev['partidos'][0]['descripcion']}")

    # --- 3. GENERACIÓN DE ARCHIVOS ---

    # A. Archivo Legacy (Top 3 estricto tomado de la lista variada)
    eventos_legacy = eventos_relevantes_maestra[:3]
    json_legacy = {
        "fecha_actualizacion": fecha_actualizacion_iso,
        "fecha_guia": fecha_guia_str,
        "eventos_relevantes": eventos_legacy
    }

    # B. Archivo Roku (Top 10 Completo y Limpio)
    eventos_roku_limpios = []
    for evento in eventos_relevantes_maestra:
        partido_orig = evento["partidos"][0]
        
        # Limpieza profunda
        evento_nuevo = {
            "evento_principal": limpiar_texto_roku(evento["evento_principal"]),
            "detalle_evento": limpiar_texto_roku(evento["detalle_evento"]),
            "partidos": [{
                "detalle_partido": limpiar_texto_roku(partido_orig.get("detalle_partido", "")),
                "descripcion": limpiar_texto_roku(partido_orig.get("descripcion", "")),
                "horarios": limpiar_texto_roku(partido_orig.get("horarios", "")),
                "canales": [limpiar_texto_roku(c) for c in partido_orig.get("canales", [])],
                "competidores": [limpiar_texto_roku(c) for c in partido_orig.get("competidores", [])]
            }]
        }
        eventos_roku_limpios.append(evento_nuevo)

    json_roku = {
        "fecha_actualizacion": fecha_actualizacion_iso,
        "fecha_guia": fecha_guia_str,
        "eventos_relevantes": eventos_roku_limpios
    }

    # --- 4. GUARDADO Y SUBIDA ---
    
    print(f"Guardando {NOMBRE_ARCHIVO_SALIDA_LEGACY}...")
    with open(NOMBRE_ARCHIVO_SALIDA_LEGACY, 'w', encoding='utf-8') as f:
        json.dump(json_legacy, f, indent=4, ensure_ascii=False)

    print(f"Guardando {NOMBRE_ARCHIVO_SALIDA_ROKU}...")
    with open(NOMBRE_ARCHIVO_SALIDA_ROKU, 'w', encoding='utf-8') as f:
        json.dump(json_roku, f, indent=4, ensure_ascii=False)

    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables FTP.")
        return
    
    print("5. Subiendo archivos al servidor FTP...")
    archivos_a_subir = [NOMBRE_ARCHIVO_SALIDA_LEGACY, NOMBRE_ARCHIVO_SALIDA_ROKU]
    
    try:
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.set_pasv(True)
            ftp.cwd(RUTA_REMOTA_FTP)
            for archivo in archivos_a_subir:
                with open(archivo, 'rb') as file:
                    print(f"Subiendo '{archivo}'...")
                    ftp.storbinary(f'STOR {archivo}', file)
            print("¡Subida completada!")
    except Exception as e:
        print(f"ERROR FATAL FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")
