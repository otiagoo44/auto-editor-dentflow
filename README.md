# DentFlow AutoEditor V2 local

## Checkpoint B — borrador automático

`--auto` ya produce `Reel/OUTPUT/VIDEO_BORRADOR.mp4`. Sólo reemplaza esa copia
tras verificar duración, H.264/AAC 48 kHz, resolución y decodificación completa;
preserva los renders con timestamp. `--preview` genera 360×640 (también actualiza
el borrador); sin esa opción genera 1080×1920. El modo auto requiere final de
frase, pausa larga y silencio medido para cortar; protege eventos explícitos,
conserva inicio/final y no supera 25% eliminado. No garantiza conservar gestos.
`--no-auto-cuts` desactiva esos cortes; `keep_segments` explícito tiene prioridad.
Sin audio audible o ante fallo ASR conserva cámara limpia y avisa, sin inventar
texto. Cada corrida entrega plan, transcript, ASS, warnings y render_log.

Pruebas ejecutadas: 11/11 (6.25 s); ASR activada sin pista, baseline auto de 12 s,
fallo ASR, protección de demo y de la última salida ante fallo de render.
Borrador sintético persistido en `%LOCALAPPDATA%\DentFlow\validacion_v2\Reel 1\OUTPUT\VIDEO_BORRADOR.mp4`.
Es patrón de prueba sin voz, no una grabación tuya ni validación profesional.

## Estado de preparación — 29-09-2026, checkpoint A

HEAD recibido `e03cafbfd1cc403c124f1bf8ea9e2ef172064098`, posterior a `7082841`:
el proyecto fue movido de `dentflow/` a esta raíz; no hay segundo editor.
Repositorio limpio, fetch y pull fast-forward sin cambios. En esta PC se instalaron
uv 0.12.20, Python 3.12.14, FFmpeg/ffprobe 9.0.2 y faster-whisper 1.1.1.
Referencia antes de modificar el motor: 7/7 tests pasaron (3.89 s), cuatro renders.
Primer intento falló por falta de PyYAML; segundo por PATH de FFmpeg sin refrescar.
Modelo base descargado y smoke de 8 s de voz real R01 transcrito con
`local_files_only=True`; no es validación de voz iPhone ni español propio.
`install.bat` ahora instala/precalienta; `--diagnose` sólo diagnostica herramientas.

CONFIRMADO POR EJECUCIÓN / YA RESUELTO: imágenes finitas, retorno después de
PNG/MP4, límites de corte, escapes ASS, render sin audio con ASR apagada.
CONFIRMADO POR LECTURA: caché SHA/config, worker separado y transcript manual;
faltan modo auto, contrato semántico y allowlist en el HEAD recibido.
RIESGO PENDIENTE DE REPRODUCIR: iPhone/VFR real, español propio, ASR sin audio,
legibilidad móvil y lote. No existen R1/R2 propios en este checkout.

Watch 0.3.2 operativo con motor local y backend none; no WhisperX ni nube.
Inspección nueva R01 4/4.5/5/5.5 s: perspectiva cambia hacia tablet; no prueba
zoom digital. Se conserva la procedencia de la evidencia anterior.

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

La investigación está en la [guía audiovisual](Flow/Herramientas/DentFlow_AutoEditor/research/dentflow_educativo_v1.md) y [evidencia](Flow/Herramientas/DentFlow_AutoEditor/research/evidencia.csv). Los antiguos enlaces a hallazgos/propuesta no existían. Se retiró el mapa obsoleto sin consumidores y la dependencia directa requests sin uso.

