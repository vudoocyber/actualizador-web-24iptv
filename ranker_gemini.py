import requests
import json
import os
import time
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import pytz
import re
from google import genai
from google.genai import types
import copy

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
URL_JSON_LEGACY_CHECK = "https://24hometv.xyz/eventos-relevantes.json"

# Nombres de Archivos
ARCHIVO_LEGACY = "eventos-relevantes.json"        # Top 5 | Emojis | 1 vez al día (Telegram)
ARCHIVO_ROKU = "eventos-destacados-roku.json"     # Top 20 | Limpio | Recurrente
ARCHIVO_FIRE = "eventos-destacados-fire.json"     # Top 20 | Emojis | Recurrente
ARCHIVO_WEB = "eventos-importantes-web.json"      # Top Dinámico (3 o 5) | Emojis | Recurrente

FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY') # NUEVA LLAVE DE RESPALDO
MEXICO_TZ = pytz.timezone('America/Mexico_City')

# Configuración de Variedad
MAX_EVENTOS_POR_LIGA = 2  
META_CANDIDATOS_IA = 50   

# --- HEADERS DE NAVEGADOR (ANTI-BLOQUEO 403) ---
HEADERS_SEGURIDAD = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/json,xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Referer': 'https://24hometv.xyz/',
    'Connection': 'keep-alive'
}

# --- 2. FUNCIONES AUXILIARES ---

def limpiar_texto_roku(texto):
    """Elimina emojis, selectores de variación, tags y caracteres especiales para Roku."""
    if not texto:
        return ""
    
    # Patrón extendido: ahora atrapa también los "Tags" de banderas compuestas (Inglaterra, Escocia, etc.)
    emoji_pattern = re.compile(
        r'[\U0001F000-\U0001FAFF]'  # Emojis misceláneos y extendidos
        r'|[\U00002600-\U000027BF]' # Símbolos y pictogramas
        r'|[\U0001F300-\U0001F5FF]' # Símbolos varios
        r'|[\U0001F680-\U0001F6FF]' # Transporte y mapas
        r'|[\U0001F1E0-\U0001F1FF]' # Banderas Nacionales
        r'|[\U000E0000-\U000E007F]' # Tags invisibles (El causante de la bandera de Inglaterra)
        r'|[\u2700-\u27BF]'         # Dingbats
        r'|[\uFE00-\uFE0F]'         # Selectores de variación
        r'|[\u200B-\u200D]',        # Zero-width spaces y joiners
        flags=re.UNICODE
    )
    texto_limpio = emoji_pattern.sub('', texto)
    
    # Elimina espacios dobles que puedan quedar tras borrar los caracteres
    return re.sub(r'\s+', ' ', texto_limpio).strip()

def verificar_necesidad_legacy(hoy_str):
    """Verifica si el archivo legacy en el servidor ya tiene la fecha de hoy."""
    print(f" -> 🔍 Verificando estado de '{ARCHIVO_LEGACY}' en servidor...")
    try:
        resp = requests.get(URL_JSON_LEGACY_CHECK, headers=HEADERS_SEGURIDAD, params={'v': datetime.now().timestamp()}, timeout=15)
        if resp.status_code == 200:
            datos = resp.json()
            fecha_remota = datos.get("fecha_guia")
            if fecha_remota == hoy_str:
                print(f" -> ✅ El archivo Legacy ya está actualizado ({fecha_remota}). NO se generará de nuevo.")
                return False
            else:
                print(f" -> ⚠️ El archivo Legacy es antiguo ({fecha_remota}). Se generará uno nuevo para {hoy_str}.")
                return True
        elif resp.status_code == 404:
            print(" -> ℹ️ El archivo Legacy no existe aún. Se generará.")
            return True
        else:
            print(f" -> ⚠️ Advertencia: Respuesta HTTP {resp.status_code}. Se forzará generación.")
            return True
    except Exception as e:
        print(f" -> ❌ Error verificando Legacy: {e}. Se generará por seguridad.")
        return True


# --- 3. FUNCIONES DE IA (PRINCIPAL Y RESPALDO) ---

def obtener_ranking_groq(prompt):
    """Función de Respaldo que consulta a Groq (Llama 3.3) si Gemini falla."""
    print(" -> 🛟 [PLAN B] Activando IA de respaldo: Groq (Llama 3.3)...")
    if not GROQ_API_KEY:
        print(" -> ❌ ERROR: No se encontró GROQ_API_KEY en los Secrets.")
        return []
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile", # <-- MODELO ACTUALIZADO Y VALIDADO
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        respuesta_texto = resp.json()['choices'][0]['message']['content']
        lineas = [linea.strip() for linea in respuesta_texto.strip().split('\n') if linea.strip()]
        print(f" -> ✅ Groq procesó {len(lineas)} candidatos exitosamente.")
        return lineas
    except Exception as e:
        print(f" -> ❌ Error fatal en Groq: {e}")
        return []


def obtener_ranking_eventos(lista_eventos):
    print(" -> 🧠 [3/5] Contactando a Gemini 2.0 Flash...")
    
    cst_offset = timezone(timedelta(hours=-6))
    hora_actual = datetime.now(cst_offset).strftime('%A, %d de %B - %I:%M %p (CDMX)')
    
    eventos_para_analizar = []
    for evento in lista_eventos:
        for partido in evento.get("partidos", []):
            canales_str = ", ".join(partido.get('canales', []))
            info = (f"LIGA: {evento.get('evento_principal', '')} | "
                    f"PARTIDO: {partido.get('descripcion', '')} | "
                    f"HORA: {partido.get('horarios', '')} | "
                    f"CANALES: {canales_str}")
            eventos_para_analizar.append(info.strip())
    
    lista_texto = "\n".join(eventos_para_analizar)
    if not lista_texto: return []

    prompt = f"""
Rol: Eres un curador experto en deportes para TV y plataformas digitales, especializado EXCLUSIVAMENTE en audiencias de México, con enfoque en contenido premium y de alto interés (clase media-alta y alta).

Contexto temporal: {hora_actual}.

OBJETIVO:
Analizar una lista de eventos y seleccionar los 40 eventos más importantes del día completo, optimizados específicamente para el público de México, ordenados estrictamente por relevancia real, no por horario.

REGLA CRÍTICA:
La importancia del evento siempre supera la hora. Eventos nocturnos importantes deben incluirse aunque falten horas.

ENFOQUE GEOGRÁFICO OBLIGATORIO (MÉXICO):
Priorizar eventos con alto interés en México.
Ligas sudamericanas (Argentina, Brasil, etc.) SOLO se incluyen si es final, semifinal o clásico internacional relevante.
Partidos regulares de ligas sudamericanas deben ser descartados.

SISTEMA DE SCORING:
- Nivel del evento (0–40 pts)
- Popularidad del deporte en México (0–25 pts)
- Protagonistas (América, Chivas, Real Madrid, Lakers, etc.) (0–20 pts)
- Interés específico en México (0–15 pts)

FORMATO DE SALIDA:
Exactamente 40 líneas. Sin numeración ni explicaciones. 
Formato: "Equipo A vs Equipo B" o "Evento - Protagonista".

LISTA A ANALIZAR:
{lista_texto}
    """

    if not GEMINI_API_KEY:
        print(" -> ⚠️ No Gemini API Key. Saltando directo a Plan B...")
        return obtener_ranking_groq(prompt)

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        
        if response.text:
            lineas = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
            print(f" -> ✅ Gemini procesó {len(lineas)} candidatos exitosamente.")
            return lineas
        return []

    except Exception as e:
        # AQUÍ OCURRE LA MAGIA DEL RESPALDO
        print(f" -> ⚠️ Error en Gemini ({e}). Activando Plan B...")
        return obtener_ranking_groq(prompt)

# --- 4. FUNCIÓN PRINCIPAL ---
def main():
    print(f"--- 🚩 [1/5] Iniciando Ranker Multi-Archivo ---")
    
    fecha_actual_dt = datetime.now(MEXICO_TZ)
    fecha_iso = fecha_actual_dt.isoformat()
    hoy_str = fecha_actual_dt.strftime('%Y-%m-%d')
    
    dia_semana = fecha_actual_dt.weekday()
    if dia_semana >= 5:
        limit_web = 5
        print(" -> 📅 Configuración: Fin de Semana (WEB 5 eventos).")
    else:
        limit_web = 3
        print(" -> 📅 Configuración: Día de Semana (WEB 3 eventos).")

    print(f"--- 🚩 [2/5] Descarga de Datos Fuente ---")
    generar_legacy = verificar_necesidad_legacy(hoy_str)
    
    try:
        print(f" -> 🌐 Descargando {URL_JSON_FUENTE}...")
        resp = requests.get(URL_JSON_FUENTE, headers=HEADERS_SEGURIDAD, params={'v': datetime.now().timestamp()}, timeout=20)
        resp.raise_for_status()
        datos = resp.json()
        
        if datos.get("fecha_guia") != hoy_str:
            print(f" -> ❌ ERROR: Fecha de guía ({datos.get('fecha_guia')}) no es hoy. Abortando.")
            return
        
        lista_original = datos.get("eventos", [])
        if not lista_original: raise ValueError("JSON de eventos está vacío.")
        
    except Exception as e:
        print(f" -> ❌ Error fatal descargando fuente: {e}")
        return

    # Ranking IA
    ranking_ia = obtener_ranking_eventos(lista_original)
    if not ranking_ia:
        print(" -> ❌ Error: Ninguna IA pudo procesar los datos. Cancelando.")
        return

    print(f"--- 🚩 [4/5] Generación de Archivos JSON Locales ---")
    eventos_seleccionados = []
    eventos_reserva = []
    conteo_liga = {}
    vistos = set()
    
    # Mapeo IA -> Objetos JSON
    for desc_ia in ranking_ia:
        encontrado = False
        for evento in lista_original:
            for partido in evento.get("partidos", []):
                d_orig = partido.get("descripcion", "")
                if d_orig and (d_orig in desc_ia or desc_ia in d_orig):
                    if d_orig not in vistos:
                        eventos_seleccionados.append((evento, partido, evento.get("evento_principal", "Otros")))
                        vistos.add(d_orig)
                        encontrado = True
                    break
            if encontrado: break

    # A. EVENTOS-RELEVANTES (Legacy)
    archivos_a_subir = []
    if generar_legacy:
        top_5 = [{"evento_principal": nom, "detalle_evento": ev.get("detalle_evento", ""), "partidos": [pt]} for ev, pt, nom in eventos_seleccionados[:5]]
        with open(ARCHIVO_LEGACY, 'w', encoding='utf-8') as f:
            json.dump({"fecha_actualizacion": fecha_iso, "fecha_guia": hoy_str, "eventos_relevantes": top_5}, f, indent=4, ensure_ascii=False)
        archivos_a_subir.append(ARCHIVO_LEGACY)
        print(f" -> 💾 Generado: {ARCHIVO_LEGACY}")

    # B. ROKU (Top 20 Limpio)
    top_20_roku = []
    limit_roku = min(len(eventos_seleccionados), 20)
    for ev, pt, nom in eventos_seleccionados[:limit_roku]:
        pt_clean = copy.deepcopy(pt)
        pt_clean["detalle_partido"] = limpiar_texto_roku(pt.get("detalle_partido", ""))
        pt_clean["descripcion"] = limpiar_texto_roku(pt.get("descripcion", ""))
        pt_clean["horarios"] = limpiar_texto_roku(pt.get("horarios", ""))
        pt_clean["canales"] = [limpiar_texto_roku(c) for c in pt.get("canales", [])]
        pt_clean["organizador"] = limpiar_texto_roku(pt.get("organizador", ""))
        top_20_roku.append({"evento_principal": limpiar_texto_roku(nom), "detalle_evento": limpiar_texto_roku(ev.get("detalle_evento", "")), "partidos": [pt_clean]})
    
    with open(ARCHIVO_ROKU, 'w', encoding='utf-8') as f:
        json.dump({"fecha_actualizacion": fecha_iso, "fecha_guia": hoy_str, "eventos_relevantes": top_20_roku}, f, indent=4, ensure_ascii=False)
    archivos_a_subir.append(ARCHIVO_ROKU)
    print(f" -> 💾 Generado: {ARCHIVO_ROKU}")

    # C. FIRE TV (Top 20 Emojis)
    limit_fire = min(len(eventos_seleccionados), 20)
    top_20_fire = [{"evento_principal": nom, "detalle_evento": ev.get("detalle_evento", ""), "partidos": [pt]} for ev, pt, nom in eventos_seleccionados[:limit_fire]]
    with open(ARCHIVO_FIRE, 'w', encoding='utf-8') as f:
        json.dump({"fecha_actualizacion": fecha_iso, "fecha_guia": hoy_str, "eventos_relevantes": top_20_fire}, f, indent=4, ensure_ascii=False)
    archivos_a_subir.append(ARCHIVO_FIRE)
    print(f" -> 💾 Generado: {ARCHIVO_FIRE}")

    # D. WEB (Top Dinámico)
    limit_real_web = min(len(eventos_seleccionados), limit_web)
    top_web = [{"evento_principal": nom, "detalle_evento": ev.get("detalle_evento", ""), "partidos": [pt]} for ev, pt, nom in eventos_seleccionados[:limit_real_web]]
    with open(ARCHIVO_WEB, 'w', encoding='utf-8') as f:
        json.dump({"fecha_actualizacion": fecha_iso, "fecha_guia": hoy_str, "eventos_relevantes": top_web}, f, indent=4, ensure_ascii=False)
    archivos_a_subir.append(ARCHIVO_WEB)
    print(f" -> 💾 Generado: {ARCHIVO_WEB}")

    print(f"--- 🚩 [5/5] Subida FTP con Reintentos ---")
    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print(" -> ❌ Error: Faltan credenciales FTP.")
        return

    max_reintentos = 3

    for intento in range(1, max_reintentos + 1):
        try:
            print(f" -> 🚀 Conectando a FTP (Intento {intento}/{max_reintentos})...")
            with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA, timeout=30) as ftp:
                ftp.set_pasv(True)
                ftp.cwd(RUTA_REMOTA_FTP)
                print(f" -> ✅ Conexión establecida. Subiendo {len(archivos_a_subir)} archivos...")
                
                for archivo in archivos_a_subir:
                    with open(archivo, 'rb') as file:
                        ftp.storbinary(f'STOR {archivo}', file)
                        print(f"    -> OK: {archivo}")
                
                print("--- 🏁 PROCESO FINALIZADO CON ÉXITO ---")
                break 
        
        except Exception as e:
            print(f" -> ⚠️ Error FTP en intento {intento}: {e}")
            if intento < max_reintentos:
                print(" -> ⏳ Reintentando en 5 segundos...")
                time.sleep(5)
            else:
                print(" -> ❌ Se agotaron los reintentos FTP. El proceso falló.")

if __name__ == "__main__":
    main()
