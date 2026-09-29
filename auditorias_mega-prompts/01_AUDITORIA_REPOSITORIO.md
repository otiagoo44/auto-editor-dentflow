# Auditoría técnica del repositorio DentFlow AutoEditor — corte del 28-09-2026

**Repositorio:** `otiagoo44/auto-editor-dentflow`  
**Commit examinado:** `7082841b932ffaec2579f0920e5ca2991795f089` (`main`; "Auto Editor, aun no completado V1.1").  
**Método:** lectura estática por el conector GitHub de árbol, README, configuración, scripts BAT, pruebas, archivo `src/editor.py` completo (492 líneas), muestras y distribución del CSV de evidencia visual (128 registros aproximadamente), referencias audiovisuales y guía audiovisual. **No ejecuté el repositorio ni pude visualizar sus MP4 de prueba o fotogramas Watch** en este entorno. La existencia de tests y resultados declarados en README NO equivale a una validación independiente de sus renders en tu PC. Esta auditoría debe actualizarse después del `git pull` de mañana si el commit es diferente.

## 1. Diagnóstico ejecutivo

El proyecto **ya es sustancialmente mejor que el prototipo inicial**. V1.1 propone cortes sin aplicarlos automáticamente, separa la ASR local en otro proceso, remapea transcripciones/cortes/eventos, permite `edicion.json`, renderiza overlays limitados con `trim`+`setpts`+`eof_action=pass`, conserva una traza de plan y trae pruebas sintéticas de FFmpeg. **No rehacerlo desde cero**. El principal problema ya no es únicamente la sincronización de overlays: ahora la distancia más importante es entre un motor manual/semiautomático y el flujo de un clic que buscas para publicar cada semana.

Una sesión futura de Codex con Watch **no convierte a Codex en editor permanentemente entrenado**. Las técnicas vistas deben convertirse en presets, reglas explicables, eventos del plan, pruebas, ejemplos y documentación que sobrevivan a nuevas sesiones.

## 2. Inventario real y discrepancias de rutas

Todo lo ejecutable está bajo `dentflow/` dentro del repositorio; los BAT, el `README.md`, `config.yaml`, `edicion.example.json`, `requirements.txt`, `src/editor.py` y `tests/test_editor.py` NO están bajo `dentflow/Flow/Herramientas/DentFlow_AutoEditor/`. Esta última ruta **solo contiene `research/dentflow_educativo_v1.md` y `research/evidencia.csv`** en el commit inspeccionado. Los seis assets actuales están en `dentflow/contenido-dentflow/semana-1/Assets/Asset A.png` a `Asset F.png` (nombres sin semántica autoexplicativa). No hay `raw.mp4` propio ni `edicion.json` real para Reel 1 en el árbol. El README describe carpetas genéricas que no coinciden con la disposición exacta del repositorio. Para mañana, Codex deberá adoptar **una única raíz ejecutable**, resolver rutas en configuración y evitar duplicar el motor.

El directorio `dentflow/videos_estudiar/` conserva el JSON inicial de investigación y un prompt en el que todos los videos figuran pendientes. En cambio `research/evidencia.csv` y `research/dentflow_educativo_v1.md` ya recogen resultados posteriores de Watch. No debe volver a estudiar todo ni usar el JSON antiguo como descripción del estado actual. El README vincula `research/hallazgos.md` y `research/propuesta_autoeditor.md`, pero esos archivos **no existen en este commit**: reparar enlaces o consolidar la información en la guía ya existente.

Se han incluido archivos compilados `dentflow/src/__pycache__/editor.cpython-312.pyc` y `dentflow/tests/__pycache__/test_editor.cpython-312.pyc`. No existe `.gitignore` en el árbol enumerado. Es necesario ignorar pycache, OUTPUT, videos originales, temporales, `.venv` y caches ASR; **no borrar assets, evidencia ni archivos de trabajo sin revisar**. `asset_map.example.json` es explícitamente legado no consumido por el código actual; `requests>=2.32,<3` no figura importado en el único editor ni en los tests presentes. Revisar usos antes de retirar ambos.

## 3. Lo implementado (según código; ejecución pendiente)

| Subsistema | Implementación comprobada estáticamente | Límite importante |
|---|---|---|
| Fuente | `choose_source_video()` y `source` explícito | Más de un candidato exige resolver origen. Correcto como protección. |
| Voz | `faster-whisper` CPU int8 en proceso aislado, cache SHA-256+config, `transcript.json` manual prevalece | No hay prueba integrada con una grabación real de tu iPhone en este commit; la nueva computadora puede no tener descargado el modelo. |
| Cortes | `build_keep_segments()` sugiere, `validate_cut_boundaries()` impide atravesar palabras | **No aplica sugerencias automáticamente**; sin `keep_segments` la duración y pausas son las originales. |
| Tiempo | `remap_time()`, `make_captions()`, `prepare_events()` trabajan sobre `keep_segments` | Eventos no pueden cruzar unión de cortes. Faltan pruebas específicas para varias combinaciones y FPS variable de iPhone. |
| Imágenes/video | `render_final()` usa duración acotada, `setpts`, alpha fades y `overlay` con `eof_action=pass:repeatlast=0` | Verificado solo mediante lectura + test sintético declarado; animaciones UI aún no existen. |
| Cámara | Evento `reframe` de crop/scale fijo, con motivo obligatorio | No es un zoom animado ni un segundo ángulo; no hay detector de cara. |
| Subtítulos | ASS blanco/contorno, dos líneas, 26 caracteres/línea, agrupación por puntuación/pausas | Sin karaoke discreto, énfasis puntual, autoubicación al aparecer gráficos ni comprobación perceptual móvil. |
| Sonido | AAC, resample 48 kHz, `loudnorm` aproximado -16 LUFS, detección de silencio previo | Una pasada no equivale a loudness final certificado; revisar voz real, clipping, respiraciones y iPhone. |
| Entrega | `--plan-only`, `--preview` 360×640, render 1080×1920, carpetas OUTPUT por ejecución, `--week` secuencial | No hay prueba real de cinco Reels semanales en Git; la salida está anidada bajo timestamp, no un borrador cómodo de acceso directo. |

## 4. Hallazgos por prioridad y funciones concretas

**P0 — Bloqueadores de flujo productivo:**

1. `process_reel()` (aprox. líneas 390–446) toma `{}` cuando no existe `edicion.json`; por defecto `keep_segments=[[0,duration]]` y `events=[]`. Por eso arrastrar solo `raw.mp4` produce como mucho un talking head subtitulado, pero no elimina silencios ni incorpora diagramas correctamente. Crear `--auto` **conservador**: detectar y aplicar únicamente cortes seguros con umbrales editables, permitir guion/beat plan preaprobado, fallback de cámara si no hay correspondencia fiable y avisos claros. Evitar auto-inserción de `Asset A-F` por palabras genéricas.
2. `edicion.example.json` es un plan por segundos **de video fuente**. Falta una capa que ate escenas y assets a expresiones transcritas/intención editorial, genere tiempos del video fuente, resuelva conflictos y preserve compatibilidad del `edicion.json` actual. El JSON editorial puede crearlo ChatGPT al preparar el guion o Codex tras mirar el Reel. El render local no debe llamar a Codex ni a una API.
3. `render_final()` (~331–389) soporta solo overlays `card/full` o reencuadre fijo; `prepare_events()` (~248–290) prohíbe eventos visuales solapados. No hay representación de `HOOK_TEXT`, `CALLOUT`, resaltado localizado, zoom animado a región de un dashboard o subtítulos movidos fuera del overlay. Añadir **dos o tres** efectos configurables de alto valor, no una nueva plataforma completa.
4. La documentación presupone caché ASR ya creada (`transcription.offline: true`). En otra PC limpia se instalarán paquetes, pero `install.bat` diagnostica sin garantizar descargar/precalentar `base`. Se necesita `doctor`/`setup` explícito que garantice operación antes del primer Reel sin pedir claves comerciales.

**P1 — Riesgos verificables en el código y pruebas:**

5. `prepare_events()` acepta paths resueltos respecto a la carpeta del Reel sin whitelist de assets autorizados ni comprobación de que queden dentro de `semana/Assets`/`Reel/Assets`. Bloquea segmentos llamados `research` y `videos_estudiar`, pero no valida todas las rutas de material ajeno ni asigna A-F a escenas. Añadir manifiesto por semana y allowlist por Reel; `approved:true` expresa aprobación humana, no prueba derechos.
6. `transcribe_worker()` asume que hay audio utilizable; el test sintético de «fuente sin audio» desactiva la transcripción. Testear falta de pista *con* ASR activada y salir con mensaje o silencio seguro (sin transcripción inventada), no bloquear el render.
7. Las pruebas actuales validan render de color PNG/MP4 finito, cortes, parte de ASS y ausencia de audio, **pero no prueban end-to-end** en Windows/iPhone VFR con ASR real, cinco Reels, overlay con subtítulos que eviten colisiones, audio percibido, fallos de rutas complejas, calidad visual de una demo 16:9 en móvil, ni instalación nueva sin caché. Ampliar `tests/test_editor.py` sólo donde sea útil y conservar tests que ya pasan.
8. `fit_filter()` usa `contain` o `cover` centrado para TODO el A-roll; un iPhone puede tener proporciones/giro distintos. El cuerpo, manos y UI pueden quedar cortados. Agregar orientación/metadata y encuadre manual normalizado; detección facial local es diferible salvo evidencia de necesidad.
9. `render_cut_video()` reencoda cada intervalo H.264+PCM y concatena, y `render_final()` vuelve a encodar. Es razonable para una V1 segura pero el tiempo/carga real de 1080×1920 en la PC futura se desconoce. PERFILAR antes de adoptar paralelismo, GPU o migrar el motor.
10. Faltan validación explícita/versionada del esquema `edicion.json` y límites robustos de memoria/duración/recuentos de eventos. Hoy hay validaciones ad hoc que deben mantenerse; preferir un módulo de schema ligero solo cuando aporte claridad.
11. `write_ass()` sitúa todos los subtítulos en zona inferior fija; con `layout=full` un gráfico de texto puede ser tapado. Incorporar política de zonas seguras y eventos de subtítulos dinámicos, probados en teléfono.
12. `run()` muestra los últimos 5000 bytes de error FFmpeg; `process_reel()` imprime error en stderr, pero falta `render_log` persistente por Reel/fallo y aviso resumen legible. Los temporales desaparecen incluso en fallos: conservar plan, código de salida y diagnósticos no sensibles fuera de temporales.
13. Hay posibles pequeñas divergencias de documentación y BAT: `editar_semana.bat` dice «arrastra una carpeta Reel» aunque espera una semana; scripts detectan uv en ruta rígida de Windows y dependen de ffmpeg/ffprobe en PATH. Probar literalmente desde nueva PC.

**P2 — Evolución condicionada a experiencia real:**

14. Un módulo Remotion opcional para composiciones UI complejas (proceso, dashboard, checklist), conectado por el JSON del plan: NO migrar de inmediato audio, cortes, ASR, batch ni caption básico, ni construir un frontend/editor completo. Solo comenzar si dos Reels ya salen bien con FFmpeg y una necesidad demostrada supera sus efectos simples.
15. Antes de limpiar `videos_estudiar` o notas, consolidar hallazgos nuevos y falta de cobertura. Añadir sistema de niveles de evidencia y evitar presentar hipótesis como cortes/zooms «comprobados».

## 5. Qué aprendió realmente el proyecto de Watch y qué no

`research/evidencia.csv` contiene registros de una investigación Watch **realizada previamente por tu Codex**, no por este chat. Su fila inicial declara para cada material lo que se pudo observar. **8/10 tutoriales tienen al menos fotogramas visualizados; T04 y T10 solo transcripción. Entre los diez materiales de referentes, R01–R06 y R09 tienen muestras visuales; R07, R08 y R10 no fueron accesibles.** El número de fotogramas difiere y hay sesgos de muestreo. La misma investigación advierte que no se puede contar todos los microcortes, inferir retención ni confundir cámara física con zoom digital.

Ejemplos concretos respaldados por el CSV, que Codex debe transformar en decisiones de producto sin clonarlos:

- **Nik R01:** aprox. 0–2 s, hook a cámara con tablet física; 5.5 s, se aproxima al diagrama; ~32–34 s, se muestra tablet al proponer una prueba; ~70 s, vuelve a rostro para la conclusión. **Nik R02:** 14–17 s, pasa de rostro a tablet; ~32–34 s, vuelve al expositor. Los acercamientos podrían ser movimiento físico, no zoom digital demostrado. Transferencia: mostrar diagrama real justo al explicar un mecanismo y recuperar la cara para interpretar.
- **Alex R03:** título desde el inicio; ~44.5–45 s y ~61–62 s, se constatan cambios entre ángulos a la altura de puntos argumentales. Son diferentes cámaras, no necesariamente punch-ins digitales. **R04:** es entrevista; cambios de interlocutor alrededor de 13–14 y 27–28 s. No pedir al AutoEditor recrear dos cámaras si solo grabas una con iPhone; permitir crop moderado como sustituto visual discreto.
- **Ramiro R05:** título en los primeros segundos, auxiliar breve alrededor de 1–3 s; ~70 s, inserta tarjeta de ejemplo, regresa a cámara ~71 s; CTA visible ~78 s. **R06:** respuesta a comentario desde 0, comentario desaparece entre 15–16 s; se conserva una toma frontal en muestras incluso 83–86 s. **No** establecer una cadencia de cambios cada N segundos: algunos videos son deliberadamente más estáticos.
- **Tomi R09:** video largo (no Reel): texto inicial, captura superpuesta sobre afirmación propia alrededor de 674 s, cierre a cámara; 1911 s aparente acercamiento físico al lente. No copiar afirmaciones comerciales sin verificar ni trasplantar su duración a Reels.
- **Tutoriales:** T02 enseña cortes motivados y construir montaje antes de efectos; T03 propone variar energía y usar pausas útiles; T05 muestra A-roll/B-roll y composición vertical; T06 enseña legibilidad y textos breves; T07 suavización/easing; T08/T09 máscaras UI, jerarquía y cursor para dirigir atención. T01 tiene solo 5 cuadros revisados; T04/T10 carecen de prueba visual. Estas técnicas son herramientas, no indicadores causales de crecimiento.

**Trabajo audiovisual pendiente real:** inspeccionar R07/R08 si hay MP4 accesibles, obtener segundo material reproducible de Tomi que represente Reels si existe, subsanar limitaciones de T04/T10 si justifica el tiempo. **No bloquear los primeros cinco Reels de DentFlow por material de terceros inaccesible**. Para decisiones de sincronía y estilo, el mayor valor nuevo será estudiar y calibrar tus propias grabaciones Reel 1/Reel 2.

## 6. Decisión FFmpeg versus Remotion

- **FFmpeg existente:** ya corta, genera overlays (imagen/video), subtítulos ASS, encuadres fijos, normaliza voz, exporta vertical, evita costes por render y funciona mediante Python/Windows. Puede incorporar fundidos, desplazamientos y zooms 2D simples. Hoy permite conseguir un Reel informativo limpio SIN Remotion. Riesgo de crecer demasiado el filter graph para máscaras y animaciones elaboradas.
- **Remotion:** React/JS/CSS/SVG permiten componer interfaces 2D, tarjetas, diagramas con reveal secuencial, cursor, curvas de movimiento/easing y subtítulos animados con más control de diseño; requiere Node, herramientas de composición, render Chromium y coordinación precisa de timestamps con Python. NO genera automáticamente diseño de calidad ni decide qué edición es buena. Preservar Python + FFmpeg para ASR y preparación de cortes. Se recomienda un **adaptador opcional, no dependencia obligatoria**, solo después de pruebas comparativas 10–15 s y dos Reels aceptables. La licencia oficial consultada el 28-09-2026 permite uso comercial y automatizaciones sin pago a individuos y organizaciones de hasta tres personas, sujeta a términos; volver a comprobar si crece el equipo. Documentación: https://www.remotion.dev/docs/license/faq y https://www.remotion.dev/docs/cli/render.

## 7. Criterios mínimos de terminación de V2

A. En máquina Windows limpia: `install.bat` o `doctor` valida Python 3.12, uv, ffprobe, ffmpeg/libass y modelo ASR descargado; no llama API comerciales al editar. B. `Reel 1/raw.mp4` + plan opcional produce borrador con subtítulos legibles, audio sin problemas y cortes seguros o avisos; si no hay plan, **no** aparece gráfico incorrecto. C. Con plan elaborado por Codex/ChatGPT, los assets correctos aparecen en frases y regiones correctas, pueden animarse discretamente y no tapan subtítulos. D. Un segundo Reel con guion/recursos diferentes requiere **0 cambios de código**. E. Validación de audio/video real en un teléfono; reportar defectos y re-renderizar. F. Batch sólo si A–E pasan. G. Tests sintéticos ejecutados localmente y resumen claro de lo probado; en investigación, nivel de evidencia por observación real.
