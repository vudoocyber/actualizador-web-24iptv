import requests
import json
import os
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import pytz
import re
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA = "eventos-relevantes.json"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY') # <-- Nueva Clave

# --- 2. FUNCIONES DE IA Y FALLBACKS ---

def obtener_ranking_gemini(lista_texto_plano, hora_formateada_cst):
    """Opción 1: Intenta obtener el ranking de Google Gemini."""
    if not GEMINI_API_KEY:
        print("  > INFO: Clave de Gemini no disponible.")
        return None
    print("Intentando con Opción 1: Google Gemini...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        prompt = f"""
        Actúa como un analista de tendencias de entretenimiento para México y USA.
        La hora actual en el Centro de México es: {hora_formateada_cst}.
        De la siguiente lista, determina los 3 eventos más relevantes que no hayan finalizado.
        Reglas:
        1.  Excluye inmediatamente ligas femeninas (WNBA, Liga MX Femenil, NWSL).
        2.  Prioriza alto interés regional (Liga MX, NFL, MLB, NBA, Boxeo/UFC, equipos populares).
        Responde ÚNICAMENTE con la descripción exacta de los 3 eventos, cada uno en una nueva línea, en orden de relevancia. No añadas texto extra.
        LISTA DE EVENTOS:
        {lista_texto_plano}
        """
        response = model.generate_content(prompt, request_options={'timeout': 120})
        ranking = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
        if ranking:
            print(f"  > ÉXITO con Gemini. Ranking: {ranking}")
            return ranking
        return None
    except Exception as e:
        print(f"  > FALLO Gemini: {e}")
        return None

def obtener_ranking_huggingface(lista_texto_plano, hora_formateada_cst):
    """Opción 2: Si Gemini falla, intenta con Hugging Face."""
    if not HUGGINGFACE_API_KEY:
        print("  > INFO: Clave de Hugging Face no disponible.")
        return None
    print("Intentando con Opción 2: Hugging Face (Mixtral)...")
    try:
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
        prompt = f"""
        [INST] Eres un analista de tendencias de entretenimiento para México y USA. La hora actual es {hora_formateada_cst}. De la siguiente lista, escoge los 3 eventos más relevantes que no hayan finalizado. Excluye ligas femeninas (WNBA, Liga MX Femenil). Prioriza Liga MX, NFL, MLB, NBA, Boxeo/UFC y equipos populares. Responde solo con los 3 nombres de eventos, cada uno en una línea nueva, sin texto extra. LISTA: {lista_texto_plano} [/INST]
        """
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt, "parameters": {"max_new_tokens": 100}}, timeout=45)
        response.raise_for_status()
        # El formato de respuesta es diferente, necesitamos procesarlo
        respuesta_texto = response.json()[0]['generated_text']
        # Limpiamos el texto para quedarnos solo con la lista
        lista_cruda = respuesta_texto.split("[/INST]")[-1]
        ranking = [linea.strip() for linea in lista_cruda.strip().split('\n') if linea.strip()]
        if ranking:
            print(f"  > ÉXITO con Hugging Face. Ranking: {ranking}")
            return ranking
        return None
    except Exception as e:
        print(f"  > FALLO Hugging Face: {e}")
        return None

def obtener_ranking_fallback_simple(lista_eventos):
    """Opción 3: Si todo falla, una selección simple y segura."""
    print("Intentando con Opción 3: Fallback Simple...")
    palabras_prohibidas = ["Femenil", "WNBA", "NWSL"]
    ranking = []
    for evento in lista_eventos:
        if not any(keyword in evento.get("evento_principal", "") for keyword in palabras_prohibidas):
            for partido in evento.get("partidos", []):
                ranking.append(partido.get("descripcion", ""))
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

    # Preparar datos para las IAs
    cst_offset = timezone(timedelta(hours=-6))
    hora_actual_cst = datetime.now(cst_offset)
    hora_formateada_cst = hora_actual_cst.strftime('%A, %d de %B de %Y - %I:%M %p CST')
    eventos_para_analizar_texto = []
    for evento in lista_eventos_original:
        for partido in evento.get("partidos", []):
            eventos_para_analizar_texto.append(f"{partido.get('descripcion', '')} {partido.get('horarios', '')}".strip())
    lista_texto_plano = "\n".join(filter(None, set(eventos_para_analizar_texto)))

    # --- NUEVO SISTEMA DE RANKING EN CASCADA ---
    ranking_final = obtener_ranking_gemini(lista_texto_plano, hora_formateada_cst)
    if not ranking_final:
        ranking_final = obtener_ranking_huggingface(lista_texto_plano, hora_formateada_cst)
    if not ranking_final:
        ranking_final = obtener_ranking_fallback_simple(lista_eventos_original)

    if not ranking_final:
        print("No se pudo obtener ranking por ningún método. El archivo de eventos relevantes se creará vacío.")
        json_salida = {"eventos_relevantes": []}
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
    
    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return
    
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
