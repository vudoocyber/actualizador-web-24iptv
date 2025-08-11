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

def obtener_resultado_gemini(descripcion_partido):
    if not GEMINI_API_KEY:
        print("  [ERROR] API Key de Gemini no encontrada.")
        return None
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Actúa como un motor de búsqueda y asistente de resultados deportivos. Tu única tarea es encontrar el resultado final del siguiente partido que se jugó hoy.
        
        PARTIDO: "{descripcion_partido}"

        Busca el resultado y devuelve la respuesta en el siguiente formato exacto: "MARCADOR, ESTADO".
        Ejemplos de respuestas válidas:
        - "2-1, Finalizado"
        - "27-14, Finalizado"

        Si no puedes encontrar el resultado de manera definitiva, responde exactamente con la frase "Resultado no disponible".
        No añadas explicaciones ni ninguna otra palabra.
        """
        
        response = model.generate_content(prompt, request_options={'timeout': 90})
        respuesta_cruda = response.text.strip()
        print(f"  [DIAGNÓSTICO] Respuesta de Gemini para '{descripcion_partido}': {respuesta_cruda}")

        if "no disponible" in respuesta_cruda.lower():
            return None

        partes = respuesta_cruda.split(',')
        resultado = partes[0].strip()
        estado = partes[1].strip() if len(partes) > 1 else "Finalizado"

        return {"resultado": resultado, "estado": estado}

    except Exception as e:
        print(f"  [ERROR] Excepción al contactar con Gemini para '{descripcion_partido}': {e}")
        return None

# --- 3. FUNCIÓN PRINCIPAL CON REGISTRO DE DIAGNÓSTICO MEJORADO ---
def main():
    print(f"Iniciando proceso de búsqueda de resultados...")
    
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        respuesta = requests.get(URL_JSON_FUENTE, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        lista_eventos_original = datos.get("eventos", [])
        if not lista_eventos_original:
            raise ValueError("El archivo events.json está vacío o no tiene la clave 'eventos'.")
        print(f"Archivo events.json leído correctamente con {len(lista_eventos_original)} ligas/eventos.")
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    print("\n--- INICIO DEL DIAGNÓSTICO DE PARTIDOS ---")
    resultados_finales = []
    
    cst_offset = timezone(timedelta(hours=-6))
    hora_actual_cst = datetime.now(cst_offset)
    hora_actual_float = hora_actual_cst.hour + (hora_actual_cst.minute / 60.0)
    print(f"Hora actual de referencia (Centro de México): {hora_actual_cst.strftime('%I:%M %p CST')} ({hora_actual_float:.2f})")

    for evento in lista_eventos_original:
        if "partido_relevante" in evento: continue
            
        for partido in evento.get("partidos", []):
            horario_str = partido.get("horarios", "")
            
            hora_centro_str = extraer_hora_centro(horario_str)
            if not hora_centro_str:
                continue

            hora_ct_24 = convertir_hora_a_24h(hora_centro_str)
            if hora_ct_24 is None:
                continue
            
            # Hora a la que consideramos que un partido ya terminó (inicio + 1.5 horas)
            hora_fin_estimada = hora_ct_24 + 1.5
            
            print(f"\n- Verificando: '{partido['descripcion']}'")
            print(f"  Hora de inicio (CT): {hora_ct_24:.2f}h. Hora de fin estimada: {hora_fin_estimada:.2f}h.")
            
            if hora_actual_float > hora_fin_estimada:
                print(f"  [ACCIÓN] Partido considerado FINALIZADO. Consultando a Gemini...")
                info_resultado = obtener_resultado_gemini(partido['descripcion'])
                if info_resultado:
                    resultados_finales.append({
                        "evento_principal": evento["evento_principal"],
                        "descripcion": partido["descripcion"],
                        "resultado": info_resultado["resultado"],
                        "estado": info_resultado["estado"]
                    })
                    print(f"  [ÉXITO] Resultado añadido: {info_resultado['resultado']}")
                else:
                    print(f"  [INFO] Gemini no devolvió un resultado válido.")
            else:
                print(f"  [INFO] Omitiendo partido (aún no ha finalizado).")

    print("\n--- FIN DEL DIAGNÓSTICO DE PARTIDOS ---")
    json_salida = {"fecha_actualizacion": datetime.now().isoformat(), "resultados": resultados_finales}

    print(f"\n3. Guardando archivo local '{NOMBRE_ARCHIVO_SALIDA}'...")
    with open(NOMBRE_ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(json_salida, f, indent=4, ensure_ascii=False)
    print("Archivo local guardado.")
    
    # ... (El resto del código de subida por FTP no cambia)
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
