import requests
import json
import os
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import pytz
import re
import google.generativeai as genai
import cohere

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA = "eventos-relevantes.json"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
COHERE_API_KEY = os.getenv('COHERE_API_KEY')

# --- 2. FUNCIONES DE RANKING ---

def obtener_ranking_gemini(lista_texto_plano, hora_formateada_cst):
    """Opción 1: Intenta obtener el ranking de Google Gemini."""
    if not GEMINI_API_KEY:
        print("  > INFO: Clave de Gemini no disponible.")
        return None
    print("Intentando con Opción 1: Google Gemini...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"La hora actual es {hora_formateada_cst}. De la siguiente lista, escoge los 3 eventos más relevantes para México/USA que no hayan finalizado. Excluye ligas femeninas (WNBA, Liga MX Femenil). Prioriza Liga MX, NFL, MLB, NBA, Boxeo/UFC y equipos populares. Responde solo con los 3 nombres de eventos, cada uno en una línea nueva, sin texto extra.\nLISTA:\n{lista_texto_plano}"
        response = model.generate_content(prompt, request_options={'timeout': 120})
        ranking = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
        if ranking:
            print(f"  > ÉXITO con Gemini. Ranking: {ranking}")
            return ranking
        return None
    except Exception as e:
        print(f"  > FALLO Gemini: {e}")
        return None

def obtener_ranking_cohere(lista_texto_plano, hora_formateada_cst):
    """Opción 2: Si Gemini falla, intenta con Cohere."""
    if not COHERE_API_KEY:
        print("  > INFO: Clave de Cohere no disponible.")
        return None
    print("Intentando con Opción 2: Cohere...")
    try:
        co = cohere.Client(COHERE_API_KEY)
        prompt = f"La hora actual es {hora_formateada_cst}. De la siguiente lista de eventos, escoge los 3 más relevantes para una audiencia de México y USA que aún no hayan finalizado. Tienes que excluir ligas femeninas como WNBA o Liga MX Femenil. Debes priorizar eventos de alto interés como Liga MX, NFL, MLB, NBA, Boxeo/UFC y partidos de equipos muy populares como América, Chivas, Real Madrid, Barcelona, Cowboys, Lakers, Yankees. Responde únicamente con los 3 nombres de los eventos, cada uno en una línea nueva, sin texto introductorio ni explicaciones.\n\nLISTA DE EVENTOS:\n{lista_texto_plano}"
        
        response = co.chat(message=prompt, model="command-r-plus-08-2024", temperature=0.2)
        
        ranking = [linea.strip().replace('*','').replace('- ','') for linea in response.text.strip().split('\n') if linea.strip()]
        if ranking:
            print(f"  > ÉXITO con Cohere. Ranking: {ranking}")
            return ranking
        return None
    except Exception as e:
        print(f"  > FALLO Cohere: {e}")
        return None

def obtener_ranking_fallback_simple(lista_eventos):
    """Opción 3: Si todo falla, una selección simple y segura."""
    print("Usando Opción 3: Fallback Simple...")
    palabras_prohibidas = ["Femenil", "WNBA", "NWSL"]
    ranking = []
    for evento in lista_eventos:
        if not any(keyword in evento.get("evento_principal", "") for keyword in palabras_prohibidas):
            for partido in evento.get("partidos", []):
                descripcion = partido.get("descripcion")
                if descripcion:
                    ranking.append(descripcion)
                    if len(ranking) >= 3:
                        print(f"  > ÉXITO con Fallback. Ranking: {ranking}")
                        return ranking
    return ranking

# --- 3. FUNCIÓN PRINCIPAL ---
def main():
    print(f"Iniciando proceso de ranking de eventos...")
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        respuesta = requests.get(URL_JSON_FUENTE, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        lista_eventos_original = datos.get("eventos", [])
        if not lista_eventos_original: raise ValueError("El archivo events.json está vacío.")
        print("Archivo events.json leído correctamente.")
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    cst_offset = timezone(timedelta(hours=-6))
    hora_actual_cst = datetime.now(cst_offset)
    hora_formateada_cst = hora_actual_cst.strftime('%A, %d de %B de %Y - %I:%M %p CST')
    eventos_para_analizar_texto = []
    for evento in lista_eventos_original:
        for partido in evento.get("partidos", []):
            eventos_para_analizar_texto.append(f"{partido.get('descripcion', '')} {partido.get('horarios', '')}".strip())
    lista_texto_plano = "\n".join(filter(None, set(eventos_para_analizar_texto)))

    ranking_final = obtener_ranking_gemini(lista_texto_plano, hora_formateada_cst)
    if ranking_final is None:
        ranking_final = obtener_ranking_cohere(lista_texto_plano, hora_formateada_cst)
    if ranking_final is None:
        ranking_final = obtener_ranking_fallback_simple(lista_eventos_original)

    if not ranking_final:
        print("No se pudo obtener ranking por ningún método. El archivo de relevantes se creará vacío.")
        eventos_relevantes = []
    else:
        print("Construyendo el JSON de eventos relevantes...")
        eventos_relevantes = []
        descripciones_ya_anadidas = set()
        for desc_relevante in ranking_final:
            if len(eventos_relevantes) >= 3: break
            encontrado = False
            for evento in lista_eventos_original:
                for partido in evento.get("partidos", []):
                    descripcion_corta = partido.get("descripcion", "")
                    if descripcion_corta and desc_relevante in descripcion_corta and descripcion_corta not in descripciones_ya_anadidas:
                        evento_relevante = {"evento_principal": evento["evento_principal"], "detalle_evento": evento.get("detalle_evento", ""), "partidos": [partido]}
                        eventos_relevantes.append(evento_relevante)
                        descripciones_ya_anadidas.add(descripcion_corta)
                        encontrado = True
                        break
                if encontrado: break
    
    json_salida = {"eventos_relevantes": eventos_relevantes}

    print(f"Guardando archivo local '{NOMBRE_ARCHIVO_SALIDA}'...")
    with open(NOMBRE_ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(json_salida, f, indent=4, ensure_ascii=False)
    print("Archivo local guardado.")
    
    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]): return
    
    print(f"Subiendo '{NOMBRE_ARCHIVO_SALIDA}' al servidor FTP...")
    try:
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.set_pasv(True)
            ftp.cwd(RUTA_REMOTA_FTP)
            with open(NOMBRE_ARCHIVO_SALIDA, 'rb') as file:
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_SALIDA}', file)
            print("¡Archivo de eventos relevantes subido exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso de ranking finalizado ---")
