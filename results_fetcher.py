import requests
import json
import os
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import re
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA = "results.json"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- 2. FUNCIONES AUXILIARES ---
def extraer_hora_centro(horario_str):
    match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:a\.m\.|p\.m\.|am|pm))\s+Centro', horario_str, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def convertir_hora_a_24h(hora_str):
    if not hora_str: return None
    hora_str = hora_str.lower().replace('.', '')
    match = re.search(r'(\d+)(?::(\d+))?\s*(am|pm)', hora_str)
    if not match: return None
    
    hora, minuto, periodo = match.groups()
    hora = int(hora)
    minuto = int(minuto) if minuto else 0
    
    if periodo == 'pm' and hora != 12: hora += 12
    if periodo == 'am' and hora == 12: hora = 0
        
    return hora + (minuto / 60.0)

def obtener_url_resultado_gemini(descripcion_partido):
    if not GEMINI_API_KEY:
        print("ADVERTENCIA: API Key de Gemini no encontrada.")
        return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Actúa como un asistente de búsqueda. Tu única tarea es generar la URL de búsqueda de Google más probable para encontrar el resultado final del siguiente partido que se jugó hoy. PARTIDO: "{descripcion_partido}". Responde ÚNICAMENTE con la URL. Ejemplo de respuesta: https://www.google.com/search?q=resultado+final+{descripcion_partido.replace(" ", "+")}"""
        response = model.generate_content(prompt, request_options={'timeout': 90})
        url_resultado = response.text.strip()
        if url_resultado.startswith("http"):
            print(f"  > [DIAGNÓSTICO] URL de Gemini: {url_resultado}")
            return url_resultado
        else:
            print(f"  > [DIAGNÓSTICO] Respuesta inválida de Gemini (no es URL): {url_resultado}")
            return None
    except Exception as e:
        print(f"  > [DIAGNÓSTICO] ERROR al contactar con Gemini: {e}")
        return None

# --- 3. FUNCIÓN PRINCIPAL (CON REGISTRO DE DIAGNÓSTICO MEJORADO) ---
def main():
    print(f"Iniciando proceso de búsqueda de resultados...")
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        respuesta = requests.get(URL_JSON_FUENTE, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        lista_eventos_original = datos.get("eventos", [])
        if not lista_eventos_original: raise ValueError("El archivo events.json está vacío.")
        print(f"Archivo events.json leído con {len(lista_eventos_original)} ligas/eventos.")
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    print("\n--- INICIO DEL DIAGNÓSTICO DETALLADO DE PARTIDOS ---")
    resultados_finales = []
    cst_offset = timezone(timedelta(hours=-6))
    hora_actual_cst = datetime.now(cst_offset)
    hora_actual_float = hora_actual_cst.hour + (hora_actual_cst.minute / 60.0)
    print(f"Hora de referencia (Centro de México): {hora_actual_cst.strftime('%I:%M %p CST')} ({hora_actual_float:.2f})")

    for evento in lista_eventos_original:
        if "partido_relevante" in evento: continue
        for partido in evento.get("partidos", []):
            print(f"\n--- Analizando Partido: '{partido.get('descripcion', 'SIN DESCRIPCIÓN')}' ---")
            horario_str = partido.get("horarios", "")
            print(f"  1. Texto de Horario Original: '{horario_str}'")

            hora_centro_str = extraer_hora_centro(horario_str)
            if not hora_centro_str:
                print("  2. [FALLO] No se encontró 'Centro' en el texto. Omitiendo partido.")
                continue
            print(f"  2. [ÉXITO] Hora del Centro extraída: '{hora_centro_str}'")

            hora_ct_24 = convertir_hora_a_24h(hora_centro_str)
            if hora_ct_24 is None:
                print("  3. [FALLO] No se pudo convertir la hora a formato 24h. Omitiendo partido.")
                continue
            print(f"  3. [ÉXITO] Hora convertida a 24h: {hora_ct_24:.2f}")
            
            hora_fin_estimada = hora_ct_24 + 1.5
            print(f"  4. [CÁLCULO] Comparando: Hora Actual ({hora_actual_float:.2f}) > Hora Fin Estimada ({hora_fin_estimada:.2f})")
            
            if hora_actual_float > hora_fin_estimada:
                print("  5. [DECISIÓN] El partido ha finalizado. Consultando a Gemini...")
                url = obtener_url_resultado_gemini(partido['descripcion'])
                if url:
                    resultados_finales.append({
                        "descripcion": partido["descripcion"],
                        "estado": "Finalizado",
                        "url_resultado": url
                    })
                    print("  6. [ÉXITO] URL encontrada y añadida a la lista de resultados.")
                else:
                    print("  6. [INFO] Gemini no devolvió una URL válida para este partido.")
            else:
                print("  5. [DECISIÓN] El partido no ha finalizado. Omitiendo.")

    print("\n--- FIN DEL DIAGNÓSTICO DETALLADO DE PARTIDOS ---")
    json_salida = {"fecha_actualizacion": datetime.now().isoformat(), "resultados": resultados_finales}

    print(f"\n3. Guardando archivo local '{NOMBRE_ARCHIVO_SALIDA}' con {len(resultados_finales)} resultados...")
    with open(NOMBRE_ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(json_salida, f, indent=4, ensure_ascii=False)
    print("Archivo local guardado.")
    
    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return
    
    print(f"4. Subiendo '{NOMBRE_ARCHIVO_SALIDA}' al servidor FTP...")
    try:
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.set_pasv(True)
            ftp.cwd(RUTA_REMOTA_FTP)
            with open(NOMBRE_ARCHIVO_SALIDA, 'rb') as file:
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_SALIDA}', file)
            print("¡Archivo de resultados subido exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso de búsqueda de resultados finalizado ---")
