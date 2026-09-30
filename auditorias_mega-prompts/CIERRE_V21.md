# Cierre técnico AutoEditor V2.1 — 29/09/2026

## Estado y uso

Implementación local terminada y probada. La aceptación audiovisual con dos
tomas reales de iPhone sigue pendiente: no se encontraron esas grabaciones.
Las demos con voz son sintéticas y no prueban naturalidad, piel ni gestos.

Abrir `C:\auto-editor-dentflow\autoeditor.bat`, elegir carpeta Reel o semana,
Vista previa y motor. Revisar `OUTPUT\VIDEO_PREVIEW.mp4`; repetir con Exportar
borrador para `VIDEO_BORRADOR.mp4`. Se puede arrastrar la carpeta sobre el BAT.
Los gráficos se preparan en el único `edicion.json`; no requieren editar React
o Python por Reel. Remotion es opcional y FFmpeg sigue siendo el predeterminado.

## Recuperación e implementación

- Rama `v2.1-remotion`, conservando `b8ab8a5` y `3a9c802`; recuperación en `4f33bac`.
- Checkpoint `3956e3a` subido a origin por autorización expresa del usuario.
  El cierre posterior queda local por su última indicación; no se fusionó main.
- Leídos los dos megaprompts, auditorías, arquitectura y ejemplo de props de
  esta carpeta, además de las evidencias previas de investigación audiovisual.
- Dos composiciones y seis plantillas originales; tiempos de salida remapeados,
  props generadas, catálogo/parametrización estrictos y staging temporal autorizado.
- Subtítulos Remotion o ASS según motor, sin duplicación; recursos C/E recortados,
  regreso a cámara y protección de alias, hashes e historial ante errores.
- Música local opcional apagada por defecto; derechos declarados, ducking,
  normalización de mezcla y medición de LUFS/pico real exportado.
- Menú, instalador separado, diagnóstico, demo comercial sin cámara y guía de uso.
  No se introdujeron APIs de contenido ni render cloud.
- Corregidos color Rec.709/yuv420p, sobrante AAC, mensajes de fallo, recursos
  faltantes no seleccionados y reporte de salidas anteriores en lotes fallidos.

## Verificación ejecutada

| Comprobación | Resultado |
| --- | --- |
| Suite completa Windows con ASR y renders activados | 44 aprobadas, 0 fallos, 0 omitidas; 273,155 s |
| Regresión específica del ajuste final de duración | Aprobada; tolerancia de un fotograma a 30 fps |
| TypeScript | `npm run typecheck` aprobado |
| Instalación Remotion desde BAT | npm ci, typecheck y navegador: código 0 |
| Diagnóstico final desde BAT | passed; ASR base offline, H.264/AAC/ASS, zscale/tonemap y Remotion presentes |
| Semana de cinco Reels distintos con Remotion | Primera corrida 5/0; segunda 4/1, archivo previo del fallido conservado y hash comprobado |
| FFmpeg con runtime Node no disponible | Exportación correcta; fallo Remotion explícito conserva salida previa |
| Preview después de final | Alias final conservado, incluyendo demo comercial persistente |
| Contratos y medios | Rutas Windows con espacios/ñ/apóstrofe, allowlist, PNG/MP4, música autorizada, silencio, HDR sintético, captions y cortes |
| Render con guardia de red Node | Aprobado bloqueando DNS/conexiones externas de Node; loopback permitido |

La guardia de red no es un firewall del sistema ni una auditoría de todos los
procesos Chromium. El proyecto usa medios/fuentes locales y no necesita claves.
La suite completa precedió al último límite de duración AAC; después se volvió
a ejecutar la prueba temporal afectada y se exportaron la demo R2 y la preview
comercial con ese límite. La prueba temporal incluye PNG, MP4 y dos escenas
animadas, retorno de overlay y ausencia de ASS bajo Remotion.

## Demos y mediciones en esta PC

Raíz de evidencia persistente, fuera del contenido real:

```text
C:\Users\User\AppData\Local\DentFlow\validacion_v21\20260929_172943_404970
```

| Demo | Archivo relativo a esa raíz | Duración contenedor | LUFS / pico real |
| --- | --- | --- | --- |
| Comercial: seis plantillas, siete escenas | `Comercial/OUTPUT/VIDEO_BORRADOR.mp4` | 28,053 s | Silencio intencional, sin música autorizada |
| Educativo R1: voz SAPI y apoyos C/E | `Reel 1/OUTPUT/VIDEO_BORRADOR.mp4` | 51,000 s | −15,95 / −1,50 dBTP |
| R2: voz SAPI y subtítulos corregidos | `Reel 2/OUTPUT/VIDEO_BORRADOR.mp4` | 10,167 s | −16,42 / −1,54 dBTP |
| R2 comparación FFmpeg | `Reel 2 FFmpeg/OUTPUT/VIDEO_BORRADOR.mp4` | 10,167 s | −16,41 / −1,53 dBTP |

Finales H.264/AAC 48 kHz, 1080×1920, 30 fps; decode completo aprobado y sin
intervalos negros detectados. Comercial/R1 se exportaron antes del último
ajuste de duración AAC; el comercial contiene 28 s de video más 53 ms de cola
de audio. Su preview posterior usa el ajuste final y está en
`Comercial/OUTPUT/VIDEO_PREVIEW.mp4` (360×640).

Inspección visual local con Watch: siete cuadros comerciales, nueve de R1 y tres
de R2. En R2 se corrigió el transcript sintético y se volvió a renderizar; el
cuadro `r2_corregido_8_5.jpg` confirma «Revisá… quién lo sigue». Las correcciones
son del fixture y nunca se aplican automáticamente a grabaciones propias.
Capturas E/C legibles, márgenes y separación respecto a subtítulos comprobados
en los cuadros revisados; sin nombres/contactos en los recortes mostrados.
No se declara escucha humana completa ni revisión en un teléfono.

Comparación secuencial del mismo raw/transcript R2, sin ASR durante el render:

| Motor | Tiempo de proceso medido | Pico muestreado del árbol de procesos |
| --- | ---: | ---: |
| FFmpeg | 13,18 s | 343 MiB |
| Remotion | 60,46 s | 1176 MiB |

Memoria: suma de WorkingSetSize de proceso y descendientes cada segundo
(10/49 muestras); puede contar páginas compartidas y perder picos breves.
No representa RAM total del equipo ni garantiza el mismo consumo en otros Reels.
Remotion no resulta más rápido en esta comparación; aporta gráficos editables.

Evidencias: `tests_finales.log`, `test_duracion_final.log`, `instalacion_remotion.log`,
`diagnostico_final.log`, `preview_comercial.log`, `comparacion_motores.json`,
`qa_final.json`, `resultados.json` y `watch/`. Los JSON de metadata conservan
SHA, tipo de salida, validación y ruta del historial. Los videos no se versionan.

## Reproducción y límite de aceptación

```powershell
$env:DENTFLOW_REMOTION_TESTS = '1'
$env:DENTFLOW_ASR_SAMPLE = "$env:LOCALAPPDATA\DentFlow\validacion_v21\20260929_172943_404970\Reel 1\raw.mp4"
& "$env:LOCALAPPDATA\DentFlow\venv\Scripts\python.exe" -m unittest discover -s tests -v
.\editar_reel.bat --diagnose --engine remotion
.\editar_reel.bat ".\ejemplos\Comercial" --preview
```

Entregar dos grabaciones iPhone distintas: R1 demostración con C/E y R2 idea a
cámara, sin apoyo forzado. Tras preparar sus planes/transcripts reales, revisar
voz completa, cortes, piel/rostro y lectura en teléfono. El software está listo
para ese flujo; la aceptación de videos publicables depende de esa evidencia.
El diálogo gráfico del menú se revisó en código; los BAT de render/instalación
sí se ejecutaron. CI se configuró, sin afirmar una corrida remota del cierre local.
