def crear_json_eventos(texto_crudo):
    datos_json = { "fecha_actualizacion": datetime.now().isoformat(), "titulo_guia": "", "eventos": [] }
    lineas = texto_crudo.strip().split('\n')
    evento_actual = None
    buffer_descripcion = [] 
    
    REGEX_EMOJI = re.compile(r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE_HORARIOS = ["Este", "Centro", "Pacífico", "partir de las"]

    for linea in lineas:
        linea = linea.strip()
        if not linea or "Kaelus Soporte" in linea or "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳" in linea: continue
        
        if "Eventos Deportivos" in linea:
            datos_json["titulo_guia"] = linea
            continue

        es_titulo_evento = REGEX_EMOJI.search(linea) or "Evento BOX" in linea
        es_linea_horario = any(keyword in linea for keyword in PALABRAS_CLAVE_HORARIOS)

        if es_titulo_evento:
            if evento_actual: datos_json["eventos"].append(evento_actual)
            evento_actual = { "evento_principal": linea, "detalle_evento": "", "partidos": [] }
            buffer_descripcion.clear()
        
        elif es_linea_horario:
            if evento_actual:
                partido = {}
                descripcion, horarios, canales_raw = "", "", ""
                canales = []

                # --- INICIO DE LA LÓGICA CORREGIDA ---
                frases_a_limpiar = ["a partir de las", "apartir de las", "a las"]
                
                # Primero, separamos la descripción del horario
                base_descripcion = linea
                base_horarios = ""
                
                for frase in frases_a_limpiar:
                    pattern = r'\s+' + re.escape(frase) + r'\s+'
                    if re.search(pattern, linea, re.IGNORECASE):
                        partes = re.split(pattern, linea, 1, re.IGNORECASE)
                        base_descripcion = partes[0]
                        base_horarios = partes[1]
                        break
                
                # Si no se partió, usamos la lógica anterior como respaldo
                if not base_horarios:
                    match_horario = re.search(r'\d.*(?:am|pm|AM|PM)', linea)
                    if match_horario:
                        pos_inicio = match_horario.start()
                        base_descripcion = linea[:pos_inicio].strip()
                        base_horarios = linea[pos_inicio:]
                    else: # Si sigue sin encontrar horario, toda la línea es la descripción
                        base_descripcion = linea
                        base_horarios = ""

                # --- FIN DE LA LÓGICA CORREGIDA ---
                
                # Separar horarios y canales
                if " por " in base_horarios:
                    horarios, canales_raw = base_horarios.split(" por ", 1)
                    canales_raw = canales_raw.replace(" y ", ", ")
                    canales = [c.strip() for c in canales_raw.split(',')]
                else:
                    horarios = base_horarios

                descripcion_final = " ".join(buffer_descripcion + [base_descripcion]).strip()
                
                partido["descripcion"] = descripcion_final
                partido["horarios"] = horarios.strip()
                partido["canales"] = canales
                
                evento_actual["partidos"].append(partido)
                buffer_descripcion.clear()

        else: # Si no tiene emoji ni horario, es un detalle que precede a un horario
            buffer_descripcion.append(linea)

    if evento_actual: datos_json["eventos"].append(evento_actual)
    datos_json["eventos"] = [e for e in datos_json["eventos"] if e.get("partidos")]
    
    return json.dumps(datos_json, indent=4, ensure_ascii=False)
