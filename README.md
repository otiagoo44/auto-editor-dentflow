# DentFlow AutoEditor V1

Editor local funcional para grabaciones propias. Genera transcripción, subtítulos por frases, plan auditable y MP4 vertical. Mantiene las pausas por defecto y propone intervalos para revisión. Los cortes, apoyos y reencuadres se indican con tiempos de la grabación original. No decide por sí solo qué argumento convence ni promete retención.

## Uso en este equipo

El entorno está instalado fuera del proyecto: `%LOCALAPPDATA%\DentFlow\venv`, Python 3.12, faster-whisper CPU/int8. FFmpeg y ffprobe deben estar en PATH. No necesita claves ni servicios externos para renderizar. El modelo base ya se descargó en la caché de Hugging Face; se puede fijar `transcription.offline: true` en config.yaml.

Desde PowerShell, en C:\dentflow:

```powershell
.\editar_reel.bat "C:\ruta\Semana 1\Reel 1" --plan-only
.\editar_reel.bat "C:\ruta\Semana 1\Reel 1" --preview
.\editar_reel.bat "C:\ruta\Semana 1\Reel 1"
.\editar_semana.bat "C:\ruta\Semana 1" --preview
```

También puedes arrastrar la carpeta Reel sobre editar_reel.bat. Cada ejecución crea una carpeta nueva dentro de OUTPUT; no sobrescribe renders anteriores. Un error de un Reel permite continuar el lote, pero el proceso termina con código 1. Un lote de cinco es secuencial; no se ha medido todavía una semana real.

Para reinstalar dependencias, ejecutar install.bat. Usa uv y Python 3.12 fuera del repo; informa si falta FFmpeg. No instala software mediante ventanas visibles ni requiere privilegios de administrador.

## Carpeta mínima

```text
Semana 1/
  Assets/                  # sólo material propio/autorizado
  Reel 1/
    raw.mp4
    edicion.json           # opcional
    transcript.json        # opcional, corrección manual
    OUTPUT/                # generado
```

Sin edicion.json: conserva la grabación completa, encaja la imagen sin recortarla, transcribe y subtitula. Si hay varios candidatos sin raw.mp4 inequívoco, pide indicar source mediante un error claro; no elige el archivo más grande.

1. Ejecuta --plan-only y lee plan_edicion.json / transcript.json en la carpeta de ejecución.
2. Para corregir nombres, cifras o negaciones, copia ese transcript.json al nivel de raw.mp4 y edita sólo el texto de las palabras. Usa tiempos en segundos del original; no uses tiempos del montaje. Si haces cambios de segmentación, revisa también los tiempos.
3. Para aceptar cortes, copia los intervalos deseados de suggested_keep_segments a keep_segments en edicion.json. No copies ciegamente todos: una pausa puede permitir leer o ver una demostración. Cada par es [inicio, fin] del original, ordenado y sin solapamientos. Los límites se amplían a fotogramas y se rechazan si atraviesan una palabra reconocida.
4. Añade eventos de apoyo únicamente cuando ayuden a explicar ese momento. edicion.example.json ilustra el esquema: debes ajustar nombres y tiempos a tu grabación.
5. Revisa --preview y después exporta completo. El preview es 360×640; el final 1080×1920. No constituye una aprobación automática de calidad.

Ejemplo mínimo de corte y apoyo:

```json
{
  "source": "raw.mp4",
  "keep_segments": [[0, 7.5], [9, 24]],
  "events": [{
    "type": "asset",
    "file": "../Assets/agenda-propia.mp4",
    "approved": true,
    "start": 12,
    "end": 17,
    "offset": 2,
    "layout": "full",
    "reason": "Mostrar el cambio de estado al confirmar el turno"
  }]
}
```

En este ejemplo start 12 del original cae en 10.5 del montaje. offset es el inicio dentro del clip auxiliar; su audio se omite y continúa la voz principal. layout admite card (zona superior, conserva contexto) o full (encaje completo). Las imágenes pueden ser PNG/JPG/JPEG/WebP; los videos MP4/MOV/M4V/WebM/MKV. No se repiten clips auxiliares que resulten cortos: se devuelve error. approved expresa tu autorización; no verifica licencias.

Un evento reframe usa start/end/reason, scale (1–1.3), x/y (0–1). Es un cambio de encuadre estático por recorte, **no** una segunda cámara ni un zoom animado. No hay zoom periódico. V1 admite un evento visual a la vez y exige que cada evento esté dentro de un tramo conservado; no puede cubrir una unión de cortes sin ajustar el plan. Esta limitación queda pendiente para V2.

## Reglas configurables y límites

- config.yaml controla tamaño, FPS, encaje, audio, modelo y subtítulos. contain conserva todo el cuadro; cover recorta al centro y requiere verificar ojos, manos y pantallas.
- Subtítulos blancos con contorno, dos líneas como máximo, 26 caracteres por línea, grupos por puntuación, pausas y duración. La velocidad alta de lectura genera avisos; no se ralentiza la voz automáticamente.
- Los cortes sugeridos sólo consideran huecos entre palabras de al menos 1.2 s. No eliminan automáticamente silencio inicial/final ni emisiones breves.
- La caché ASR depende del SHA-256 del original y configuración. Un transcript.json manual tiene prioridad; no tiene garantía de exactitud. El proceso de ASR libera su memoria antes de renderizar.
- FFmpeg utiliza dos hilos de codificación y un hilo por grafo de filtros. Los temporales se crean fuera del repo y se eliminan al terminar.
- Audio principal normalizado a objetivo configurable (-16 LUFS inicial), AAC 48 kHz; normalización de una pasada, no masterización certificada. Si no hay audio, se crea silencio.
- El plan conserva procedencia, tiempos fuente/salida, eventos, avisos, configuración y duración. No hay búsqueda automática de material, guiones generados, publicación ni assets de terceros.
- Las animaciones de interfaz/easing avanzadas y decisiones semánticas se posponen. No requiere Remotion, Adobe, WhisperX ni API.

## Verificación y evidencia

```powershell
& "$env:LOCALAPPDATA\DentFlow\venv\Scripts\python.exe" src/editor.py --diagnose
& "$env:LOCALAPPDATA\DentFlow\venv\Scripts\python.exe" -m unittest discover -s tests -v
```

Pruebas de tiempos, palabras breves, límites de corte, agrupación de subtítulos, escapes ASS y renders reales de PNG/MP4 con corte y eventos tardíos. Muestra de aceptación original y sintética en `%LOCALAPPDATA%\DentFlow\validacion_v1`; no sustituye validar una grabación tuya. No había grabaciones propias en las carpetas Reel del proyecto.

La investigación está en [hallazgos](Flow/Herramientas/DentFlow_AutoEditor/research/hallazgos.md), junto a [guía audiovisual](Flow/Herramientas/DentFlow_AutoEditor/research/dentflow_educativo_v1.md), evidencia.csv y propuesta_autoeditor.md. Está incompleta respecto de los cinco creadores. El archivo asset_map.example.json pertenece al prototipo anterior: V1 usa eventos explícitos de edicion.json y no consume ese mapa.

