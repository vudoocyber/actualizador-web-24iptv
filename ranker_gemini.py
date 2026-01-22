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
NOMBRE_ARCHIVO_SALIDA_ROKU = "eventos-destacados-roku.json" # Top 20 limpio y variado
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MEXICO_TZ = pytz.timezone('America/Mexico_City')

# --- CONFIGURACIÓN DE VARIEDAD ---
MAX_EVENTOS_POR_LIGA = 2  # Límite general para la lista
META_EVENTOS_ROKU = 40    # Pedimos 40 candidatos a la IA para tener de sobra al filtrar

# --- FUNCIÓN DE LIMPIEZA PARA ROKU ---
def limpiar_texto_roku(texto):
    if not texto:
        return ""
    # Regex para eliminar emojis
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
        # Formato claro con AM/PM para facilitar la comparación a la IA
        hora_formateada_cst = hora_actual_cst.strftime('%A, %d de %B de %Y - %I:%M %p (Hora Centro México)')
        
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

        # --- PROMPT REFORZADO (TIEMPO Y VARIEDAD) ---
        prompt = f"""
        Rol
        Actúa como un curador senior de eventos deportivos.
        
        CONTEXTO TEMPORAL CRÍTICO
        ⚠️ **FECHA Y HORA ACTUAL (CDMX/Centro): {hora_formateada_cst}** ⚠️
        
        OBJETIVO
        Analiza la lista y selecciona los 40 eventos más relevantes VIGENTES (que se estén jugando ahora o vayan a empezar pronto).
        
        ⛔ REGLA CERO: FILTRO DE TIEMPO (ESTRICTO)
        - TU PRIMERA TAREA ES DESCARTAR LO QUE YA TERMINÓ.
        - Ejemplo: Si la hora actual es 6:00 PM y el partido dice "2:00 PM Centro", **ESTÁ TERMINADO. NO LO INCLUYAS.**
        - Ignora partidos finalizados, por más importantes que hayan sido (ej. Champions League de la tarde si ya es de noche).
        - Prioriza eventos **EN VIVO** o **POR COMENZAR**.

        REGLAS DE SELECCIÓN
        1. **JERARQUÍA:**
           - NIVEL 1 (PREMIUM): Finales, Clásicos, Liguilla Liga MX, Champions (solo si es horario vigente), Selección Mexicana.
           - NIVEL 2 (TOP): NBA, NFL, MLB, Premier League.
        
        2. **VARIEDAD OBLIGATORIA:**
           - No quiero una lista monotemática. Mezcla deportes.
        
        FORMATO DE SALIDA
        - Devuelve exactamente 40 líneas.
        - Solo el texto: "Equipo A vs Equipo B"
        - Sin numeración, sin viñetas.

        LISTA A ANALIZAR:
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

    # Listas para el proceso de filtrado
    eventos_seleccionados = []
    eventos_reserva = [] 
    conteo_por_liga = {}

    if ranking_crudo:
        print("2. Procesando candidatos y aplicando FILTRO DE VARIEDAD TOP 3...")
        palabras_prohibidas = ["Femenil", "WNBA", "NWSL", "Femenino", "Womens"]
        
        candidatos_obj = []
        descripciones_vistas = set()

        # Mapeo de texto Gemini a objetos originales
        for desc_gemini in ranking_crudo:
            encontrado = False
            for evento in lista_eventos_original:
                for partido in evento.get("partidos", []):
                    desc_partido = partido.get("descripcion", "")
                    if desc_partido and (desc_partido in desc_gemini or desc_gemini in desc_partido):
                        if desc_partido not in descripciones_vistas:
                            candidatos_obj.append((evento, partido))
                            descripciones_vistas.add(desc_partido)
                            encontrado = True
                        break 
                if encontrado: break

        # SELECCIÓN CON REGLAS ESTRICTAS
        META_FINAL = 20 # Definido en la configuración o aquí localmente
        
        for evento, partido in candidatos_obj:
            if len(eventos_seleccionados) >= META_FINAL:
                break
            
            nombre_liga = evento.get("evento_principal", "Otros")
            if any(keyword in nombre_liga for keyword in palabras_prohibidas):
                continue

            liga_key = nombre_liga.split()[0] if nombre_liga else "Otros"
            conteo_actual = conteo_por_liga.get(liga_key, 0)
            
            # --- REGLA CRÍTICA PARA EL TOP 3 ---
            # Si estamos llenando los espacios 1, 2 o 3 (índices 0, 1, 2)
            # NO PERMITIMOS REPETIR LIGA. Límite = 1.
            if len(eventos_seleccionados) < 3 and conteo_actual >= 1:
                # Ya hay uno de esta liga en el Top 3. Lo mandamos a reserva para usarlo después (puesto 4+)
                eventos_reserva.append({
                    "evento_principal": nombre_liga,
                    "detalle_evento": evento.get("detalle_evento", ""),
                    "partidos": [partido]
                })
                continue 

            # --- REGLA GENERAL PARA EL RESTO ---
            if conteo_actual < MAX_EVENTOS_POR_LIGA:
                eventos_seleccionados.append({
                    "evento_principal": nombre_liga,
                    "detalle_evento": evento.get("detalle_evento", ""),
                    "partidos": [partido]
                })
                conteo_por_liga[liga_key] = conteo_actual + 1
            else:
                eventos_reserva.append({
                    "evento_principal": nombre_liga,
                    "detalle_evento": evento.get("detalle_evento", ""),
                    "partidos": [partido]
                })

        # RELLENO SI FALTAN
        faltantes = META_FINAL - len(eventos_seleccionados)
        if faltantes > 0 and eventos_reserva:
            print(f"   -> Rellenando {faltantes} espacios con reservas...")
            relleno = eventos_reserva[:faltantes]
            eventos_seleccionados.extend(relleno)
        
        print(f"Ranking Final Generado (Total: {len(eventos_seleccionados)}):")
        for i, ev in enumerate(eventos_seleccionados, 1):
            print(f" {i}. {ev['evento_principal']}: {ev['partidos'][0]['descripcion']}")

    # --- 3. GENERACIÓN DE ARCHIVOS ---

    # A. Archivo Legacy (Top 3 estricto y variado)
    eventos_legacy = eventos_seleccionados[:3]
    json_legacy = {
        "fecha_actualizacion": fecha_actualizacion_iso,
        "fecha_guia": fecha_guia_str,
        "eventos_relevantes": eventos_legacy
    }

    # B. Archivo Roku (Top 20)
    eventos_roku_limpios = []
    for evento in eventos_seleccionados:
        partido_orig = evento["partidos"][0]
        
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
