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
URL_JSON_LEGACY_CHECK = "https://24hometv.xyz/eventos-relevantes.json"

# Nombres de Archivos
ARCHIVO_LEGACY = "eventos-relevantes.json"        # Top 5 | Emojis | 1 vez al día (Telegram)
ARCHIVO_ROKU = "eventos-destacados-roku.json"     # Top 20 | Limpio | Recurrente
ARCHIVO_FIRE = "eventos-destacados-fire.json"     # Top 20 | Emojis | Recurrente (NUEVO)
ARCHIVO_WEB = "eventos-importantes-web.json"      # Top Dinámico (3 o 5) | Emojis | Recurrente

FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MEXICO_TZ = pytz.timezone('America/Mexico_City')

# Configuración de Variedad
MAX_EVENTOS_POR_LIGA = 2  
META_CANDIDATOS_IA = 50   # Pedimos muchos para poder filtrar bien

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
    """Elimina emojis y caracteres especiales para Roku."""
    if not texto:
        return ""
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

def verificar_necesidad_legacy(hoy_str):
    """
    Verifica si el archivo legacy en el servidor ya tiene la fecha de hoy.
    """
    print(f"Verificando estado de '{ARCHIVO_LEGACY}' en servidor...")
    try:
        # USAMOS LOS HEADERS COMPLETOS AQUÍ
        resp = requests.get(URL_JSON_LEGACY_CHECK, headers=HEADERS_SEGURIDAD, params={'v': datetime.now().timestamp()}, timeout=15)
        
        if resp.status_code == 200:
            datos = resp.json()
            fecha_remota = datos.get("fecha_guia")
            if fecha_remota == hoy_str:
                print(f" -> El archivo Legacy ya está actualizado ({fecha_remota}). NO se generará de nuevo.")
                return False
            else:
                print(f" -> El archivo Legacy es antiguo ({fecha_remota}). Se generará uno nuevo para {hoy_str}.")
                return True
        elif resp.status_code == 404:
            print(" -> El archivo Legacy no existe aún. Se generará.")
            return True
        else:
            print(f" -> Advertencia: Respuesta {resp.status_code}. Se forzará generación.")
            return True
    except Exception as e:
        print(f" -> Error verificando Legacy: {e}. Se generará por seguridad.")
        return True

# --- 3. FUNCIÓN PRINCIPAL GEMINI ---
def obtener_ranking_eventos(lista_eventos):
    if not GEMINI_API_KEY:
        print("ERROR: No API Key.")
        return None

    print("Contactando a Gemini con Prompt MEJORADO (Premium/Vip)...")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        cst_offset = timezone(timedelta(hours=-6))
        hora_actual = datetime.now(cst_offset).strftime('%A, %d de %B - %I:%M %p (CDMX)')
        
        # Construcción de la lista para análisis
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
        if not lista_texto:
            return []

        # --- PROMPT REFINADO PARA CLASE MEDIA/ALTA Y EVENTOS VIP ---
        prompt = f"""
       Rol: Eres un curador experto en deportes para TV y plataformas digitales, especializado en audiencias de México, USA, LATAM y España, con enfoque en contenido premium y de alto interés (clase media-alta y alta).

Contexto temporal: {hora_actual}.

OBJETIVO:
Analizar una lista de eventos y seleccionar los 40 eventos más importantes del día completo, ordenados estrictamente por relevancia real, no por horario.

REGLA CRÍTICA:
La importancia del evento siempre supera la hora. Eventos nocturnos importantes deben incluirse aunque falten horas.

METODOLOGÍA OBLIGATORIA:

Analizar todos los eventos de la lista.
Asignar un score de relevancia de 0 a 100 a cada evento.
Ordenarlos por score.
Aplicar filtros de calidad.
Seleccionar los mejores 40.

SISTEMA DE SCORING:

Nivel del evento (0–40 pts):

Final / Campeonato / PPV: +40
Playoffs / Eliminación directa: +30
Torneo internacional importante: +25
Temporada regular: +10
Partido irrelevante: +0

Popularidad del deporte (0–25 pts):

Fútbol internacional top: +25
NBA / NFL: +25
Boxeo / UFC / F1: +25
MLB / Tenis / Golf: +20
Otros: +10

Protagonistas (0–20 pts):

Equipos o figuras élite (América, Real Madrid, Lakers, Canelo, etc.): +20
Equipos conocidos: +10
Sin relevancia: +0

Interés regional (0–15 pts):

Alto interés en México/USA: +15
Interés medio: +8
Bajo: +0

REGLAS DE EXCLUSIÓN:

No incluir partidos sin impacto competitivo.
No incluir ligas menores sin relevancia mediática.
No incluir equipos desconocidos sin contexto.
Evitar eventos repetitivos o de bajo nivel.

CONTROL DE DISTRIBUCIÓN:

Máximo 12 eventos de fútbol.
Mínimo 5 deportes diferentes en la lista.
Incluir variedad entre fútbol, NBA/NFL/MLB, tenis, combate y motor.

PRIORIDAD ABSOLUTA:

Grand Slams (Tenis)
F1 (cualquier sesión)
Peleas PPV (Box/UFC)
NBA (especialmente juegos clave o playoffs)
NFL (especialmente Prime Time / Playoffs)
Liga MX (equipos grandes)
Champions League (fases finales)

REGLA DE TIEMPO:

Solo excluir eventos que ya terminaron.
Incluir eventos de todo el día (mañana, tarde, noche).

FORMATO DE SALIDA:

Exactamente 40 líneas.
Sin numeración.
Sin explicaciones.
Formato por línea:
"Equipo A vs Equipo B"
o
"Evento - Protagonista"

IMPORTANTE:

No inventar eventos.
No repetir eventos.
No agregar texto adicional.
No explicar el razonamiento.
Entregar solo la lista final.

        LISTA A ANALIZAR:
        {lista_texto}
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        
        if response.text:
            return [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
        return []

    except Exception as e:
        print(f"Error Gemini: {e}")
        return None

# --- 4. FUNCIÓN PRINCIPAL ---
def main():
    print(f"--- Iniciando Ranker Multi-Archivo ---")
    
    fecha_actual_dt = datetime.now(MEXICO_TZ)
    fecha_iso = fecha_actual_dt.isoformat()
    hoy_str = fecha_actual_dt.strftime('%Y-%m-%d')
    
    # --- LOGICA DE FIN DE SEMANA ---
    dia_semana = fecha_actual_dt.weekday()
    if dia_semana >= 5:
        limit_web = 5
        print("📅 Es Fin de Semana: El archivo WEB tendrá 5 eventos.")
    else:
        limit_web = 3
        print("📅 Es Día de Semana: El archivo WEB tendrá 3 eventos.")

    # 1. Determinar si generamos el Legacy
    generar_legacy = verificar_necesidad_legacy(hoy_str)
    
    try:
        print(f"Descargando {URL_JSON_FUENTE}...")
        # USAMOS LOS HEADERS COMPLETOS AQUÍ TAMBIÉN
        resp = requests.get(URL_JSON_FUENTE, headers=HEADERS_SEGURIDAD, params={'v': datetime.now().timestamp()}, timeout=20)
        resp.raise_for_status()
        datos = resp.json()
        
        if datos.get("fecha_guia") != hoy_str:
            print(f"ERROR: La fecha de la guía ({datos.get('fecha_guia')}) no es de hoy ({hoy_str}). Abortando.")
            return
        
        lista_original = datos.get("eventos", [])
        if not lista_original: raise ValueError("JSON vacío.")
        
    except Exception as e:
        print(f"Error fatal leyendo fuente: {e}")
        return

    # 2. Obtener Ranking Maestro de IA
    ranking_ia = obtener_ranking_eventos(lista_original)
    
    if not ranking_ia:
        print("Fallo en IA. No se generan archivos.")
        return

    # 3. Procesamiento y Filtrado (Variedad)
    eventos_seleccionados = []
    eventos_reserva = []
    conteo_liga = {}
    
    candidatos_obj = []
    vistos = set()
    
    # Mapeo IA -> Objetos
    for desc_ia in ranking_ia:
        encontrado = False
        for evento in lista_original:
            for partido in evento.get("partidos", []):
                d_orig = partido.get("descripcion", "")
                if d_orig and (d_orig in desc_ia or desc_ia in d_orig):
                    if d_orig not in vistos:
                        candidatos_obj.append((evento, partido))
                        vistos.add(d_orig)
                        encontrado = True
                    break
            if encontrado: break
            
    # Filtro de Variedad
    palabras_off = ["Femenil", "WNBA", "NWSL", "Femenino", "Womens"]
    
    for evento, partido in candidatos_obj:
        if len(eventos_seleccionados) >= 40: 
            break
        
        nombre_liga = evento.get("evento_principal", "Otros")
        if any(w in nombre_liga for w in palabras_off): continue

        key = nombre_liga.split()[0] if nombre_liga else "Otros"
        count = conteo_liga.get(key, 0)
        
        # Regla: Para las primeras posiciones (Legacy/Web), diversidad máxima
        if len(eventos_seleccionados) < 3 and count >= 1:
            eventos_reserva.append((evento, partido, nombre_liga))
            continue
            
        if count < MAX_EVENTOS_POR_LIGA:
            eventos_seleccionados.append((evento, partido, nombre_liga))
            conteo_liga[key] = count + 1
        else:
            eventos_reserva.append((evento, partido, nombre_liga))

    # Relleno para llegar a 20 (Meta Roku mínima)
    if len(eventos_seleccionados) < 20 and eventos_reserva:
        faltan = 20 - len(eventos_seleccionados)
        eventos_seleccionados.extend(eventos_reserva[:faltan])

    print(f"Total eventos procesados: {len(eventos_seleccionados)}")

    # --- 4. GENERACIÓN DE ARCHIVOS JSON ---
    archivos_a_subir = []

    # A. EVENTOS-RELEVANTES (Legacy - Top 5 - Solo 1 vez al día)
    if generar_legacy:
        top_5 = []
        for ev, pt, nom in eventos_seleccionados[:5]:
            top_5.append({
                "evento_principal": nom,
                "detalle_evento": ev.get("detalle_evento", ""),
                "partidos": [pt]
            })
        
        json_legacy = {
            "fecha_actualizacion": fecha_iso,
            "fecha_guia": hoy_str,
            "eventos_relevantes": top_5
        }
        print(f"Generando {ARCHIVO_LEGACY} (Top 5)...")
        with open(ARCHIVO_LEGACY, 'w', encoding='utf-8') as f:
            json.dump(json_legacy, f, indent=4, ensure_ascii=False)
        archivos_a_subir.append(ARCHIVO_LEGACY)
    else:
        print(f"Saltando {ARCHIVO_LEGACY} (Ya existe para hoy).")

    # B. EVENTOS-DESTACADOS-ROKU (Top 20 - Limpio)
    top_20_roku = []
    limit_roku = min(len(eventos_seleccionados), 20)
    
    for ev, pt, nom in eventos_seleccionados[:limit_roku]:
        pt_clean = copy.deepcopy(pt)
        pt_clean["detalle_partido"] = limpiar_texto_roku(pt.get("detalle_partido", ""))
        pt_clean["descripcion"] = limpiar_texto_roku(pt.get("descripcion", ""))
        pt_clean["horarios"] = limpiar_texto_roku(pt.get("horarios", ""))
        pt_clean["canales"] = [limpiar_texto_roku(c) for c in pt.get("canales", [])]
        pt_clean["competidores"] = [limpiar_texto_roku(c) for c in pt.get("competidores", [])]
        pt_clean["organizador"] = limpiar_texto_roku(pt.get("organizador", ""))

        top_20_roku.append({
            "evento_principal": limpiar_texto_roku(nom),
            "detalle_evento": limpiar_texto_roku(ev.get("detalle_evento", "")),
            "partidos": [pt_clean]
        })

    json_roku = {
        "fecha_actualizacion": fecha_iso,
        "fecha_guia": hoy_str,
        "eventos_relevantes": top_20_roku
    }
    print(f"Generando {ARCHIVO_ROKU} (Top 20 Limpio)...")
    with open(ARCHIVO_ROKU, 'w', encoding='utf-8') as f:
        json.dump(json_roku, f, indent=4, ensure_ascii=False)
    archivos_a_subir.append(ARCHIVO_ROKU)

    # C. EVENTOS-DESTACADOS-FIRE (Top 20 - Emojis - NUEVO)
    # Usamos los mismos eventos que Roku (Top 20) pero SIN limpiar texto (con Emojis)
    top_20_fire = []
    limit_fire = min(len(eventos_seleccionados), 20)
    
    for ev, pt, nom in eventos_seleccionados[:limit_fire]:
        # No usamos limpiar_texto_roku, agregamos directo
        top_20_fire.append({
            "evento_principal": nom,
            "detalle_evento": ev.get("detalle_evento", ""),
            "partidos": [pt]
        })

    json_fire = {
        "fecha_actualizacion": fecha_iso,
        "fecha_guia": hoy_str,
        "eventos_relevantes": top_20_fire
    }
    print(f"Generando {ARCHIVO_FIRE} (Top 20 Fire TV - Con Emojis)...")
    with open(ARCHIVO_FIRE, 'w', encoding='utf-8') as f:
        json.dump(json_fire, f, indent=4, ensure_ascii=False)
    archivos_a_subir.append(ARCHIVO_FIRE)

    # D. EVENTOS-IMPORTANTES-WEB (Top Dinámico)
    top_web = []
    limit_real_web = min(len(eventos_seleccionados), limit_web)

    for ev, pt, nom in eventos_seleccionados[:limit_real_web]:
        top_web.append({
            "evento_principal": nom,
            "detalle_evento": ev.get("detalle_evento", ""),
            "partidos": [pt]
        })

    json_web = {
        "fecha_actualizacion": fecha_iso,
        "fecha_guia": hoy_str,
        "eventos_relevantes": top_web
    }
    print(f"Generando {ARCHIVO_WEB} (Top {limit_web} Web)...")
    with open(ARCHIVO_WEB, 'w', encoding='utf-8') as f:
        json.dump(json_web, f, indent=4, ensure_ascii=False)
    archivos_a_subir.append(ARCHIVO_WEB)

    # --- 5. SUBIDA FTP ---
    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("No FTP config. Bye.")
        return

    print("Subiendo archivos a FTP...")
    try:
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.set_pasv(True)
            ftp.cwd(RUTA_REMOTA_FTP)
            for archivo in archivos_a_subir:
                with open(archivo, 'rb') as file:
                    print(f" -> Subiendo {archivo}...")
                    ftp.storbinary(f'STOR {archivo}', file)
            print("¡Subida Completada!")
    except Exception as e:
        print(f"Error FTP: {e}")

if __name__ == "__main__":
    main()
