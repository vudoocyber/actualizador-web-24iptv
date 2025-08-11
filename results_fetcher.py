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

# --- 2. FUNCIONES DE MANEJO DE TIEMPO Y CONSULTA A IA ---

def convertir_hora_a_24h(hora_str):
    """Convierte una hora como '7 pm' o '10:30 p.m.' a formato de 24 horas (ej. 19, 22.5)."""
    hora_str = hora_str.lower().replace('.', '')
    match = re.search(r'(\d+)(?::(\d+))?\s*(am|pm)', hora_str)
    if not match:
        return None
    
    hora, minuto, periodo = match.groups()
    hora = int(hora)
    minuto = int(minuto) if minuto else 0
    
    if periodo == 'pm' and hora != 12:
        hora += 12
    if periodo == 'am' and hora == 12:
        hora = 0
        
    return hora + (minuto / 60.0)

def obtener_resultado_gemini(descripcion_partido):
    """Consulta a Gemini por el resultado de un partido específico."""
    if not GEMINI_API_KEY:
        print("ADVERTENCIA: API Key de Gemini no encontrada. Omitiendo búsqueda de resultado.")
        return "Resultado no disponible"
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Actúa como un asistente de resultados deportivos EN TIEMPO REAL.
        Quiero saber el resultado final del siguiente partido que se jugó hoy.
        
        PARTIDO: "{descripcion_partido}"

        Responde ÚNICAMENTE con el marcador final en el formato más común (ej. "2-1", "27-14", "3-0").
        Si el partido fue un empate, usa ese formato (ej. "1-1").
        Si no puedes encontrar el resultado, responde exactamente con la frase "Resultado no encontrado".
        No añadas explicaciones, contexto ni ninguna otra palabra.
        """
        
        response = model.generate_content(prompt, request_options={'timeout': 90})
        resultado = response.text.strip()
        print(f"  > Resultado de Gemini para '{descripcion_partido}': {resultado}")
        return resultado if "no encontrado" not in resultado.lower() else None

    except Exception as e:
        print(f"  > ERROR al contactar con Gemini para '{descripcion_partido}': {e}")
        return None

# --- 3. FUNCIÓN PRINCIPAL ---
def main():
    print(f"Iniciando proceso de búsqueda de resultados...")
    
    # --- PASO A: LEER EL JSON DESDE LA WEB ---
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        respuesta = requests.get(URL_JSON_FUENTE, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        lista_eventos_original = datos.get("eventos", [])
        if not lista_eventos_original:
            raise ValueError("El archivo events.json está vacío o no tiene la clave 'eventos'.")
        print("Archivo events.json leído correctamente.")
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    # --- PASO B: IDENTIFICAR PARTIDOS FINALIZADOS Y OBTENER RESULTADOS ---
    print("2. Identificando partidos finalizados y buscando resultados...")
    resultados_finales = []
    
    # Definimos la zona horaria del Centro de México (CST es UTC-6)
    cst_offset = timezone(timedelta(hours=-6))
    hora_actual_cst = datetime.now(cst_offset)
    print(f"Hora actual (Centro de México): {hora_actual_cst.strftime('%I:%M %p CST')}")

    for evento in lista_eventos_original:
        # Ignoramos los eventos relevantes ya que son un subconjunto de la lista principal
        if "partido_relevante" in evento:
            continue
            
        for partido in evento.get("partidos", []):
            horario_str = partido.get("horarios", "")
            if "Este" not in horario_str:
                continue

            # Extraemos la primera hora que aparezca en el string
            hora_et_24 = convertir_hora_a_24h(horario_str)
            if hora_et_24 is None:
                continue
            
            # Convertimos la hora del Este (ET) a Centro (CT). ET es 1 hora adelante de CT.
            hora_ct_24 = hora_et_24 - 1
            
            # Comparamos si el partido ya debería haber terminado
            # (si la hora actual es 3.5 horas después del inicio)
            if hora_actual_cst.hour + (hora_actual_cst.minute / 60.0) > hora_ct_24 + 3.5:
                print(f"- Partido finalizado detectado: {partido['descripcion']}")
                resultado = obtener_resultado_gemini(partido['descripcion'])
                if resultado:
                    resultados_finales.append({
                        "evento_principal": evento["evento_principal"],
                        "descripcion": partido["descripcion"],
                        "resultado": resultado,
                        "estado": "Finalizado"
                    })

    # --- PASO C: CREAR EL JSON DE RESULTADOS ---
    json_salida = {
        "fecha_actualizacion": datetime.now().isoformat(),
        "resultados": resultados_finales
    }

    # --- PASO D: GUARDAR Y SUBIR EL NUEVO ARCHIVO ---
    print(f"3. Guardando archivo local '{NOMBRE_ARCHIVO_SALIDA}'...")
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
