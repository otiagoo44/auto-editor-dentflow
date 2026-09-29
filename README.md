# DentFlow AutoEditor V2 local

Coloca `raw.mp4` en una carpeta Reel y ejecuta un BAT. Produce un borrador vertical
con voz, subtítulos y un plan auditable. El modo editorial añade sólo imágenes
propias declaradas y enlazadas a frases. Sin API, música automática, publicación,
Watch en runtime ni suscripciones por render. **No validado para producción con
dos grabaciones reales**: todavía no existen R1/R2 del iPhone en este checkout.

## Empezar en esta PC

El HEAD recibido `e03cafbfd1cc403c124f1bf8ea9e2ef172064098` movió el proyecto de
`dentflow/` a **esta raíz**. No ejecutes comandos desde otro árbol Flow.
PowerShell, desde `C:\xampp\htdocs\tiago3roBTI2026\auto-editor-dentflow`:

```powershell
.\install.bat
.\editar_reel.bat --diagnose
& "$env:LOCALAPPDATA\DentFlow\venv\Scripts\python.exe" -m unittest discover -s tests -v
.\editar_reel.bat ".\contenido-dentflow\semana-1\Reel 1" --auto --preview
.\editar_reel.bat ".\contenido-dentflow\semana-1\Reel 1" --auto
.\editar_semana.bat ".\contenido-dentflow\semana-1" --auto
```

Los tres últimos comandos necesitan que hayas copiado `raw.mp4`. La carpeta
`contenido-dentflow/semana-1/Reel 1` ya tiene un plan basado en C/E y el guion de
abajo. El borrador aparece exactamente en
`contenido-dentflow/semana-1/Reel 1/OUTPUT/VIDEO_BORRADOR.mp4`.

También puedes arrastrar **la carpeta** Reel sobre `editar_reel.bat` o pasar una
ruta absoluta externa con espacios, sin mover tus archivos. `--preview` genera
360×640 y también actualiza VIDEO_BORRADOR; ejecuta sin esa opción para obtener
1080×1920. Se conserva cada versión en `OUTPUT/fecha_hora/FINAL.mp4` o PREVIEW.mp4.
El alias se reemplaza atómicamente sólo después de validar el render.

`install.bat` instala uv/Python 3.12 y dependencias fuera del repo en
`%LOCALAPPDATA%\DentFlow\venv`; instala FFmpeg mediante winget si falta y descarga
explícitamente el modelo base. Necesita red sólo en instalación/precalentamiento.
Probado aquí: Ryzen 5 5600G, ~7.4 GiB RAM utilizable, Python 3.12.14,
FFmpeg/ffprobe 9.0.2 con libass, faster-whisper 1.1.1 CPU/int8. No WhisperX.
`--diagnose` verifica herramientas; no demuestra precisión de ASR.

## Flujo y contrato único

```text
semana-1/
  Assets/                 imágenes/clips propios compartidos
  Reel 1/
    raw.mp4
    edicion.json           opcional, única entrada editorial
    transcript.json        opcional, palabras corregidas en tiempo fuente
    OUTPUT/
      VIDEO_BORRADOR.mp4
      fecha_hora/          plan_edicion.json, transcript.json, warnings.json,
                           subtitulos.ass, render_log.txt, FINAL o PREVIEW.mp4
```

**Sólo raw + --auto:** ASR local, subtítulos y cortes conservadores. Cada corte
requiere final de frase, pausa entre 1.8 y 6 s y silencio medido por debajo de
-42 dBFS; conserva al menos .35 s después y .25 s antes. Si eliminaría más del
25%, conserva todo. Son umbrales ajustables, no garantías de naturalidad; ASR
puede omitir voz tenue y no ve gestos. Sin palabras fiables, sin audio audible
o con error ASR, conserva cámara, no inventa texto y escribe avisos.
No inventa título, diagramas ni narrativa. `--no-auto-cuts` desactiva autocortes.
Para restaurar fuente íntegra quita `keep_segments` y usa esa opción.

**edicion.json:** compatible con `source`, `keep_segments` y `events` de V1.
En V2 agrega `schema_version:2`, `mode:editorial|auto`, `script_summary`,
`allowed_assets` (lista de rutas exactas), `beats`, `camera_policy`,
`subtitle_policy`, `cut_policy`. El archivo [ejemplo](edicion.example.json)
conserva eventos con tiempos explícitos; el [plan R1](contenido-dentflow/semana-1/Reel%201/edicion.json)
usa frases de la locución. Los planes antiguos avisan que falta allowlist V2.

- Cada beat necesita `id`, `purpose`, `reason`, `approved:true` para intervenir,
  `fallback:camera` y **sólo uno** entre `source_time:[inicio,fin]` o `match_text`.
  Se exige una coincidencia textual única de al menos tres palabras, ignorando
  tildes, mayúsculas y puntuación. No hay selección por keywords ni fuzzy matching.
- `duration` fija la ventana o `until_text` la termina al empezar otra frase única.
  Si faltan frases, se repiten o no alcanza `min_read_seconds`, omite el beat y avisa.
  `source_time` no se combina con `until_text`. Revisa triggers contra tu voz.
- `asset` sólo puede estar en allowed_assets y en el Reel, Assets de su semana o
  `asset_roots` expresamente declarados. Research y videos_estudiar se rechazan.
  El manifiesto de Assets describe contenidos; no selecciona recursos en runtime.
  `approved` declara tu decisión editorial; no verifica derechos de terceros.
- Conflictos: primero events explícitos, después beats por `priority` descendente
  (empates respetan orden). Los inferiores se omiten. Un evento que cruce un corte
  explícito se rechaza con mensaje: divide el beat/evento en dos intervalos fuente
  o conserva ese tramo. El autocorte protege las ventanas visuales ya resueltas.
- Events de entrada usan `start/end` fuente y `time_basis:source` opcional.
  El plan de salida usa `source_start/source_end` más `start/end` de montaje y
  `time_basis:output`; incluye `time_map`. Nunca copies events de salida como entrada.
  `plan_edicion.json` es evidencia generada, no una segunda fuente de configuración.

`--plan-only` deja transcripción/plan sin render. Para corregir nombres, cifras,
negaciones y puntuación, copia `OUTPUT/fecha_hora/transcript.json` junto a raw.mp4
y cambia `words[].text`, conservando tiempos **del original**. Vuelve a ejecutar.
Ese archivo tiene prioridad; la caché automática depende de SHA-256/configuración.
Tras cambiar raw.mp4, retira o revalida cualquier transcript manual antiguo.

## Imagen, composición y audio

`camera_policy` admite `fit:contain|cover` y punto de interés `x/y` entre 0 y 1.
Contain conserva el encuadre; cover recorta y exige comprobar cara/manos.
FFmpeg aplica metadatos de orientación, convierte a 30 fps y normaliza timestamps;
VFR/rotación de un iPhone real todavía requieren comprobación.

`layout:card` comparte cuadro; `full` sustituye visualmente la cámara durante la
prueba. Con subtítulos, el gráfico ocupa como máximo hasta 69% del alto; la banda
inferior queda libre. `focus_region:[x,y,ancho,alto]` recorta una región normalizada
del asset **antes** de escalar. No detecta cara ni decide automáticamente qué leer.
Una card puede tapar al presentador: el reporte pide revisión.

Recursos permitidos: `fade`/`none` para gráficos; `HOOK_TEXT`/`CALLOUT` de hasta dos
líneas con aparición discreta; `CAMERA_PUNCH_IN_OUT` animado con easing seno al
cuadrado y escala máxima 1.10 (vuelve al encuadre inicial); `DIAGRAM_REVEAL` recorre
`steps:[{focus_region,duration}]` de elementos ya preparados. Los steps suman la
duración del beat. Para locución variable conviene un beat por frase, como R1.
No crea UI a partir de voz. El antiguo `reframe` sin `animated:true` sigue estático.
`demo:true` añade EJEMPLO FICTICIO. Los textos se escapan en ASS; no son filtros FFmpeg.

Subtítulos: blanco/contorno, máximo dos líneas, 26 caracteres por línea de inicio,
fuente/tamaño/márgenes configurables. Reporta caracteres/s y caja geométrica estimada;
rechaza configuraciones que invadan gráficos. No es medición tipográfica perfecta
ni detección automática de boca/controles IG. Valida en tu teléfono.

Audio AAC 48 kHz, loudnorm inicial -16 LUFS/-1.5 dBTP de una pasada; silencio no se
normaliza. `audio.normalize:false` lo desactiva. Se miden pico/volumen medio/silencios
fuente y salida; se avisa de fuente tenue o posible clipping. No repara micrófono
saturado ni elimina automáticamente ruido. Cortes sin solapar sílabas.
Export H.264 yuv420p, +faststart; valida duración, codecs, dimensiones y decode completo.

## Primer Reel: guion original para grabar

Lee con tus pausas naturales. No fuerces una duración; deja terminar cada idea.
Los triggers se adaptan a los tiempos reconocidos, pero no a cambios arbitrarios
de palabras. No necesitas preparar nuevos assets ni afirmar funciones no demostradas.

> ¿Cuántas consultas siguen abiertas y quién las debe contactar? Si la respuesta
> está repartida en conversaciones, cuesta saber qué sigue.
>
> Mirá estos cuatro datos. Estado: en qué etapa está. Responsable: quién sigue
> esto. Fecha: cuándo revisar. Próxima acción: qué hacer ahora.
>
> En este ejemplo ficticio, el seguimiento está pendiente y lo tiene Recepción.
> La próxima acción es llamar hoy a las dieciséis. Esto es una ilustración del seguimiento.
>
> La idea es simple. Que cada consulta abierta tenga alguien a cargo y un siguiente
> paso. Revisá una consulta de tu clínica: ¿están claros esos datos?

E aparece por campo durante su definición; C enseña estado/responsable y luego
la acción, excluyendo nombre/contacto. La interpretación vuelve a cámara. El zoom
de conclusión queda **sin aprobar** hasta ver tu toma. CTA utilizable hoy, sin
prometer una descarga inexistente, pacientes, ventas ni ingresos.

Inspección visual de A–F realizada en esta sesión; [manifiesto](contenido-dentflow/semana-1/Assets/manifest.json):

| Asset | Qué explica | Límite editorial |
|---|---|---|
| A | Tratamiento, estado y próxima acción en tres filas | No muestra responsable; ejemplo ficticio |
| B | Conversación frente a control | Aislar paneles para móvil; no prueba funcionalidad |
| C | Seguimiento pendiente, Recepción, llamar hoy 16:00 | Demo ilustrada; recortar nombre/contacto |
| D | Responsables/acciones faltantes en auditoría | Título dice 10 pero hay seis filas; no usar como conteo validado |
| E | Estado, responsable, fecha, próxima acción | Un bloque por frase para leer en vertical |
| F | Conversaciones dispersas sin siguiente paso claro | Omitir si sólo repite la voz |

## Evidencia, checkpoints y límites

**A — `83db49b`**: git limpio, fetch/pull ff-only y comparación con `7082841`.
7/7 tests V1 antes de modificar el motor (3.89 s, cuatro renders). Primer intento
bloqueado por PyYAML ausente, segundo por PATH sin refrescar. Instalación desde PC
sin entorno; smoke de 8 s de voz real R01 con modelo base offline. Pycache retirado
sólo del índice, archivos locales conservados; requests directo/mapa sin consumidores retirados.

**B — `3a2d2e2`**: --auto, degradación ASR, medición de audio, borrador atómico y
reportes. 11/11 tests (6.25 s). Patrón sintético de 12 s revisado con Watch en .1/6/11.8 s:
`%LOCALAPPDATA%\DentFlow\validacion_v2\Reel 1\OUTPUT\VIDEO_BORRADOR.mp4`.

**C — edición educativa**: motor conservado en src/editor.py; planning.py aísla
validación pura y triggers. 17/17 tests (12.24 s, hubo render final concurrente).
Dos Reels con voz sintética SAPI española local, ASR real y assets distintos, vía
editar_semana.bat; 50.93 y 22.60 s. Inspección de preview con Watch detectó steps
demasiado rápidos: se corrigieron por frases de entrada/salida y se ampliaron
regiones C. El rótulo de prueba sintética se movió para no pisar el hook.
Artefactos finales en `%LOCALAPPDATA%\DentFlow\validacion_v2\editorial_20260929_090522\Reel 1\OUTPUT\VIDEO_BORRADOR.mp4`
y `Reel 2\OUTPUT\VIDEO_BORRADOR.mp4` del mismo directorio.

| Hallazgo de auditoría | Clasificación al checkpoint C |
|---|---|
| PNG infinito / video congelado tras overlay | YA RESUELTO en V1; CONFIRMADO POR EJECUCIÓN, ventanas por píxel |
| Caché SHA, manual preferente, worker que libera memoria | CONFIRMADO POR LECTURA y ASR/cache por ejecución |
| Auto y fallback sin audio/ASR | CONFIRMADO POR EJECUCIÓN |
| Allowlist, traversal, triggers únicos, múltiples cortes, escapes ASS | CONFIRMADO POR EJECUCIÓN |
| Movimiento, foco, subtítulos separados de demo | Renders ejecutados; muestreo visual, no evaluación humana completa |
| Dos grabaciones reales, saltos de cabeza/sílabas y escucha iPhone | RIESGO PENDIENTE DE REPRODUCIR |
| Calidad profesional / eficacia comercial | No demostrada por estos tests |

Reproducir la aceptación sintética (Windows con voz española SAPI; crea directorio
nuevo fuera del repo, nunca escribe en tu Reel):

```powershell
& "$env:LOCALAPPDATA\DentFlow\venv\Scripts\python.exe" tests/render_acceptance.py
& "$env:LOCALAPPDATA\DentFlow\venv\Scripts\python.exe" tests/render_acceptance.py --final
```

Watch 0.3.2 local/backend none listo. Evidencia anterior **leída del repo**, no
reobservada completa: [CSV](Flow/Herramientas/DentFlow_AutoEditor/research/evidencia.csv)
y [guía](Flow/Herramientas/DentFlow_AutoEditor/research/dentflow_educativo_v1.md).
T04/T10 sólo transcript; R07/R08/R10 inaccesibles. Nuevas pasadas: R01 4–5.5 s
(cuatro imágenes, cambio de perspectiva hacia tablet, no zoom digital demostrado);
R05 69/70/71 s (tarjeta ya a 69, retorno al expositor a 71). R07/R08 un intento
cada uno, empty media response. Sin Apify ni cookies. R10 sin MP4 reproducible.
Las muestras pueden omitir microcortes; no se afirma escucha completa de terceros.

Transferencias adoptadas: gráfico en la explicación y vuelta a cámara para
interpretar (R01 32–34, R02 32–34); ausencia de zoom periódico (R06 15–16/85);
montaje antes de adornos (T02 179); foco de UI y jerarquía (T08 105, T06 103).
No se copiaron frases, imágenes ni diseños de referentes a los assets DentFlow.

**FFmpeg suficiente por ahora.** Sin Node/Remotion incorporado. La [FAQ oficial de
licencia](https://www.remotion.dev/docs/license/faq) revisada 29-09-2026 permite uso
comercial/automatización gratuito a individuos y equipos de hasta tres personas,
sujeto a términos; vuelve a revisar si participan clientes que operan el código.
No se justifica una prueba React antes de validar dos tomas propias.

Runtime fuerza modelo offline, HF_HUB_OFFLINE y desactiva telemetría Hugging Face;
no importa Watch ni SDKs comerciales. Instalación y estudio sí descargan. Para
comprobar aislamiento completo puedes desconectar la red tras install.bat; para
inspección por proceso usa Monitor de recursos de Windows. No se afirma que el
resto del sistema operativo no haga conexiones.

Antes de publicar: ver completo, escuchar uniones/voz, corregir cifras y negaciones,
comprobar móvil y que cada demo explique algo. Si falla claridad, cambia el plan
o la grabación, no agregues efectos. Falta validación real R1/R2 y escucha humana;
el software y el procedimiento ya no dependen de otra investigación.
