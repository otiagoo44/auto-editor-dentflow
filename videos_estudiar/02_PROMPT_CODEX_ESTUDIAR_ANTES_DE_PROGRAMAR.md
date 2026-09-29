# MISIÓN ÚNICA PARA CODEX: auditoría audiovisual real con Watch — NO IMPLEMENTAR AÚN EL EDITOR

Estás en el proyecto local `Flow` de DentFlow. El usuario ya instaló la skill **watch** desde `bradautomates/claude-video`. Comprueba que está disponible en esta sesión e inspecciona su `SKILL.md`. Usa el archivo `01_REFERENCIAS_10_TUTORIALES_Y_10_REFERENTES.json` adjunto: contiene 10 tutoriales seleccionados y diez materiales nuevos de cinco referentes (8 Instagram, un YouTube de Tomi y una VSL propia que puede requerir reemplazo).

## Límites y alcance
1. **No programes ni refactorices AutoEditor todavía**. Esta tarea concluye entregando observaciones verificables y una especificación audiovisual, no inventando edición.
2. Nunca afirmes que viste un video al que no accediste. Distingue `VIDEO_VISUALIZADO`, `SOLO_TRANSCRIPT`, `SOLO_METADATA`, `NO_ACCESIBLE`. La misma distinción aplica a cada afirmación (p. ej., un caption no demuestra cuántos zooms hubo).
3. Usa Watch `--engine local`, sin Gemini ni claves pagas, con `balanced` para piezas cortas. Primero ejecuta setup diagnóstico y verifica ffmpeg/ffprobe/yt-dlp. No instales WhisperX pesado sin evaluar si existen captions y recursos disponibles. Puedes usar el faster-whisper local que ya forma parte del proyecto para los videos sin captions si es compatible. Documenta dependencias y consumo.
4. En tutoriales muy largos, analiza capítulos directamente relacionados con el proyecto (selección de material, ritmo, subtítulos, animación de interfaces, easing). Registra las partes que no viste. No dediques tiempo a herramientas específicas que no vamos a programar.
5. Si Instagram/YouTube bloquea yt-dlp (403/429 o login), usa evidencia accesible o identifica el MP4 que el usuario debe suministrar. No evadas controles, no uses páginas dudosas y no te atribuyas observaciones inexistentes.
6. No uses material de terceros dentro del producto DentFlow, ni copies branding distintivo, música o guiones. Los videos sólo son evidencia de investigación.

## Método de observación visual por Reel
- Pasada A, `--detail balanced` y transcripción/captions. Carga y EXAMINA cada fotograma informado; no te limites a leer el reporte de Watch.
- Pasada B para los 0–5 segundos: marcos de referencia en 0, 0.5, 1, 2, 3, 4 y 5 s, en la medida permitida por la skill. Indica texto y encuadre del hook y cuándo aparece la primera imagen auxiliar.
- Pasada C, intervalos clave: puntos donde el creador menciona un ejemplo, introduce una conclusión, cambia de idea, muestra pantalla o invita a comentar. Usa `--timestamps` y observa cuadros antes/después para comprobar qué transición ocurrió; Watch local muestrea y PUEDE OMITIR microcortes.
- Por Reel registrar: duración, primer enunciado y promesa, primer plano (cámara/gráfico/pantalla), número de cambios de plano **observados**, tipo de cortes, posibles zooms (diferenciar zoom real en edición de cambios de toma), aparición/duración de gráficos, palabras por pantalla y ubicación de subtítulos, cambios de energía, estructura de argumentos, CTA, calidad de prueba y timecodes. Cualquier valor medido a partir de muestras parciales debe marcarse aproximado.
- Compara DOS REELS POR CREADOR, no mezcles estilos diferentes sin explicar si un video es largo, entrevista, serie o venta. Para Tomi, `R09` es un video largo y `R10` es una VSL cuya reproducción no fue comprobada; si no puede observarse, sustituye por Reel verificado de @tomiibuschiazzo o devuelve evidencia parcial; nunca inventes URL.
- Comparar métricas previas de Apify dentro de cada creador sólo como contexto; 2 videos no determinan reglas de retención ni causalidad.

## Método de aprendizaje por tutorial
Para cada tutorial T01–T10 extrae 3–5 principios APRENDIDOS CON EVIDENCIA en formato: (a) principio y timecode, (b) ejemplo mostrado si hay prueba visual, (c) por qué sirve para un fundador mostrando sistemas B2B, (d) implementación viable con Python+FFmpeg y opcional Remotion, (e) qué NO automatizar, (f) una prueba concreta de calidad. Distingue lo enseñado por el autor de tu propia interpretación. Evita copiar fórmulas sin considerar claridad para dueños de clínicas.

## Entregables de investigación en una SOLA carpeta
Crea sólo `Flow/Herramientas/DentFlow_AutoEditor/research/` con:
- `evidencia.csv`: un registro por video y por evento visual observado (video_id, creator, video_url, source_time_s, scene, cut_type, camera_scale, subtitle_style, asset, visible_text, observed_or_inferred, evidence_source, note).
- `hallazgos.md`: conclusiones separadas por creador, y transferencias generales a DentFlow. Toda afirmación específica debe citar `video_id` y timecode. Incluir faltantes y errores de acceso.
- `dentflow_educativo_v1.md`: guía audiovisual ÚNICA y original. Fijar reglas iniciales configurables, evitar intervalos mecánicos, no imponer cuotas de efectos sin evidencia.
- `propuesta_autoeditor.md`: arquitectura MÍNIMA y priorización técnica a partir de las capacidades demostradas; no implementar en esta misión.
No guardar descargas pesadas dentro del repo. Usa directorio temporal fuera del repositorio, registra procedencia y elimina sólo temporales creados por esta tarea.

## Criterios de calidad
Los resultados tienen que enseñarnos específicamente CUÁNDO y POR QUÉ hacer cortes, zooms, overlays, subtítulos y cambios de cámara; no acepto únicamente adjetivos tipo "dinámico". Si los fotogramas muestreados no permiten saber si hubo un zoom, dilo. Prefiere evidencia incompleta pero verdadera a cifras inventadas. La V2 editará cinco Reels por semana sin API paga; no incluyas dependencias que requieran servicios externos para el render.

## Finalización
Entrega tabla de cobertura con estado de cada uno de los 20 materiales (10 tutoriales + 10 referentes), fallos concretos y enlaces/archivos faltantes. Si no se pudieron observar suficientes materiales, entrega igualmente hallazgos útiles y propuesta condicionada, sin considerar completa la investigación.
