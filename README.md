# DentFlow AutoEditor V2 local

## Checkpoint V2.1 — integración en curso (29/09/2026)

Rama `v2.1-remotion`. Se recuperaron los cambios locales de la sesión anterior
en `4f33bac`, conservando los commits `b8ab8a5` y `3a9c802`.
Este checkpoint se sube por pedido del usuario; **V2.1 todavía no está validada**.

- Añadidos motor Remotion opcional (`--engine remotion`), puente de tiempos/recursos,
  composiciones educativa/comercial, seis plantillas, instalador y menú `autoeditor.bat`.
- Ejemplo comercial: `ejemplos/Comercial/edicion.json`. No requiere cámara; música apagada.
- Base antes de integrar: 31 pruebas descubiertas, 30 aprobadas, 1 ASR opt-in omitida.
  Prueba adicional de política de cortes aprobada; diagnóstico offline aprobado.
- TypeScript compila con Remotion 4.0.530 y Zod 4.5.4 fijados.
- Primera ejecución de `test_motion.py`: 6 pruebas de contrato aprobadas y
  **2 errores de render** en la comprobación final de FPS/formato de píxel.
  Investigar metadata del MP4 Remotion y su conversión antes de dar la versión por lista.
- Pendientes: corregir esos errores, ejecutar regresión completa, revisar demos
  completas y probar dos grabaciones reales de iPhone, aún no disponibles.
- El texto posterior documenta V2 y sus verificaciones anteriores; no demuestra
  aceptación de la nueva integración. No se versionan videos, caches ni node_modules.

Una grabación → montaje local → revisión, sin APIs de pago por render.
**Faltan tus grabaciones iPhone R1/R2 para validar calidad editorial real.**
La raíz ejecutable es `C:\auto-editor-dentflow`.

## Empezar en esta PC

PowerShell desde esta raíz:

1. **Instalar:** `.\install.bat`.
2. **Diagnosticar:** `.\editar_reel.bat --diagnose`. Debe indicar `status: passed` y código 0.
3. **Colocar raw:** copia tu toma a `contenido-dentflow\semana-1\Reel 1\raw.mp4`.
4. **Generar --plan-only:** `.\editar_reel.bat ".\contenido-dentflow\semana-1\Reel 1" --auto --plan-only`.
5. **Preparar edicion.json con Codex:** entrega la carpeta Reel y su `Assets/manifest.json`.
   Codex contrasta los triggers con la transcripción real y revisa el video con Watch local;
   escribe el único `edicion.json`. R1 ya tiene plan C/E para el guion de abajo.
6. **Preview:** `.\editar_reel.bat ".\contenido-dentflow\semana-1\Reel 1" --auto --preview`.
7. **Final:** `.\editar_reel.bat ".\contenido-dentflow\semana-1\Reel 1" --auto`.
8. **Encontrar output:** `Reel 1\OUTPUT\VIDEO_PREVIEW.mp4` (360×640) y
   `VIDEO_BORRADOR.mp4` (1080×1920), con metadata `.json` e historial por fecha.
9. **Corregir subtítulos:** copia `OUTPUT\fecha_hora\transcript.json` junto a raw;
   cambia `words[].text`, conserva identidad/tiempos fuente y repite preview/final.
10. **Procesar semana:** `.\editar_semana.bat ".\contenido-dentflow\semana-1" --auto`.
    Reporte por pieza, SHA, resolución y errores en `semana-1\OUTPUT\lote_fecha.json`.
11. **Recuperar errores:** revisa `OUTPUT\fecha_hora\render_log.txt` y `warnings.json`,
    corrige y repite. Un fallo conserva ambos alias válidos. Si cambias raw, retira
    el transcript anterior y genera uno nuevo con `--plan-only`.

**Siguiente paso único para R1: copiar raw.mp4.** Preview nunca pisa final.
No publiques antes de revisar voz, ortografía, rostro, gráficos y lectura en teléfono.

`install.bat` descubre uv/FFmpeg en PATH de proceso, usuario y máquina e instala
faltantes con winget, sin ejecutar scripts remotos. Python/dependencias viven en
`%LOCALAPPDATA%\DentFlow\venv`. Precalienta explícitamente base y luego lo carga
offline. Diagnóstico prueba H.264/AAC/ASS, ffprobe, zscale, tonemap y decode;
una capacidad requerida ausente devuelve fallo. No instala Node ni WhisperX.

## Flujo y contrato único

```text
semana-1/
  Assets/                 imágenes/clips propios compartidos
  Reel 1/
    raw.mp4
    edicion.json           opcional, única entrada editorial
    transcript.json        opcional, palabras corregidas en tiempo fuente
    OUTPUT/
      VIDEO_PREVIEW.mp4    preview 360×640
      VIDEO_BORRADOR.mp4   final 1080×1920
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
muestra beats V2 sin aprobar hasta revisar el material; el [plan R1](contenido-dentflow/semana-1/Reel%201/edicion.json)
usa frases de la locución. Los eventos temporales V1 requieren también allowed_assets; si falta, se omite el asset con aviso.

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
El export incluye `schema_version:2`, `time_basis:source`, `source_sha256` y
`source_duration`. El transcript manual prevalece sólo si esa identidad coincide;
se rechaza después de cambiar raw. Solapamientos de hasta 20 ms se normalizan con
aviso; desorden/solapamientos mayores se rechazan. No altera texto de cifras,
negaciones, nombres ni CTA. Huecos sin palabras ni silencio medido generan aviso.

Un transcript antiguo sin identidad exige revisión explícita de voz y tiempos:

```powershell
Get-FileHash ".\contenido-dentflow\semana-1\Reel 1\raw.mp4" -Algorithm SHA256
.\editar_reel.bat ".\contenido-dentflow\semana-1\Reel 1" --migrate-transcript PEGAR_SHA256_REVISADO
```

Se conserva `transcript.legacy.json` sin sobrescribirlo. No se permite reasignar
un transcript ya identificado a otro video. La caché ASR sigue vinculada a SHA/config.

**Borrador editorial preparado con Codex:** interpretar la voz y decidir demos
requiere preparación editorial; no surge de un clic offline sin modelo que
comprenda el contenido. Codex puede preparar el JSON por ti. Después, renders
locales sin Codex/Watch/conexión. Preset **DENTFLOW_EDUCATIVO**: problema concreto
→ importancia → explicación → demostración propia → conclusión y próximo paso.
Reglas comunes en config.yaml; no se modifica Python por guion.

**R1 mantiene deliberadamente `cut_policy.mode:preserve`:** desactiva autocortes
incluso con `--auto`, para preservar pausas de la primera demo. Cada unión de otros
montajes se lista en `uniones_corte.json` con tiempo fuente/salida y ventana ±1 s.
Intervenciones inválidas (allowlist, aprobación, cruce de corte) avisan y conservan cámara.

## Imagen, composición y audio

`camera_policy` admite `fit:contain|cover` y punto de interés `x/y` entre 0 y 1.
Contain conserva el encuadre; cover recorta y exige comprobar cara/manos.
FFmpeg aplica metadatos de orientación, convierte a 30 fps y normaliza timestamps;
VFR/rotación se prueban con fixtures; iPhone real pendiente. Se registra ffprobe
completo (color, HEVC, profundidad, cadencia, rotación y audio). HLG/PQ con BT.2020
se convierte a luz lineal float, tonemapping Mobius y Rec.709. SDR no recibe tonemap.
HDR sin colorimetría fiable falla con instrucción de exportar SDR. Fixtures HEVC
10 bits HLG/PQ pasan; piel, blancos y saturación reales requieren revisión en teléfono.
Referencia: [tonemap de FFmpeg](https://ffmpeg.org/ffmpeg-filters.html#tonemap).

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
fuente/tamaño/márgenes configurables. No fragmenta nombres/cifras o palabras largas; avisa de ancho excesivo. Reporta caracteres/s y caja geométrica estimada;
rechaza configuraciones que invadan gráficos. No es medición tipográfica perfecta
ni detección automática de boca/controles IG. Valida en tu teléfono.

Audio AAC 48 kHz, loudnorm inicial -16 LUFS/-1.5 dBTP de una pasada; silencio no se
normaliza. `audio.normalize:false` lo desactiva. Se miden pico/volumen medio/silencios
fuente y salida; se avisa de fuente tenue o posible clipping. No repara micrófono
saturado ni elimina automáticamente ruido. Cortes sin solapar sílabas.
Export H.264 yuv420p, +faststart; valida duración, codecs, dimensiones, FPS y decode
completo; informa intervalos casi negros. Metadata por salida: tipo, resolución,
SHA fuente/salida, timestamp, historial y validación técnica; `human_review:pending`.
Alias reemplazados sólo después de validar y verificar que raw no cambió. Renders
pequeños de tests no reciben alias de final 1080p. MP4/metadata se reemplazan
individualmente de forma atómica: si hay interrupción entre ambos, comprobar
`output_sha256` y recuperar metadata del historial.

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

Inspección histórica A–F; en el cierre actual se reobservaron C/E y el render con B; [manifiesto](contenido-dentflow/semana-1/Assets/manifest.json):

| Asset | Qué explica | Límite editorial |
|---|---|---|
| A | Tratamiento, estado y próxima acción en tres filas | No muestra responsable; ejemplo ficticio |
| B | Conversación frente a control | Aislar paneles para móvil; no prueba funcionalidad |
| C | Seguimiento pendiente, Recepción, llamar hoy 16:00 | Demo ilustrada; recortar nombre/contacto |
| D | Responsables/acciones faltantes en auditoría | Título dice 10 pero hay seis filas; no usar como conteo validado |
| E | Estado, responsable, fecha, próxima acción | Un bloque por frase para leer en vertical |
| F | Conversaciones dispersas sin siguiente paso claro | Omitir si sólo repite la voz |

## Evidencia HISTÓRICA, checkpoints y límites

Los recuentos de esta sección provienen de commits anteriores. Ejecución actual al final.

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

**FFmpeg suficiente por ahora.** Remotion queda diferido hasta evaluar R1/R2 reales.
Sólo ante una composición que lo justifique: POC aislado de 10–15 s con el mismo
JSON/timeline, export consumible por FFmpeg y fallback. Antes de integrarlo,
verificar documentación/licencia vigente, RAM/rendimiento y aprobación de complejidad.
No se agregó React/Node a la instalación principal.

Runtime fuerza modelo offline, HF_HUB_OFFLINE y desactiva telemetría Hugging Face;
no importa Watch ni SDKs comerciales. Instalación y estudio sí descargan. Para
comprobar aislamiento completo puedes desconectar la red tras install.bat; para
inspección por proceso usa Monitor de recursos de Windows. No se afirma que el
resto del sistema operativo no haga conexiones.

Antes de publicar: ver completo, escuchar uniones/voz, corregir cifras y negaciones,
comprobar móvil y que cada demo explique algo. Si falla claridad, cambia el plan
o la grabación, no agregues efectos. Falta validación real R1/R2 y escucha humana;
el software y el procedimiento ya no dependen de otra investigación.


## Cierre ejecutado el 29/09/2026 en esta PC

- HEAD inicial actualizado por fetch/pull ff-only: `35e139138e8686c5551bcd1698e706697f5703b3`.
  Sin diferencias respecto a la referencia. Sin raw iPhone en el checkout.
- Base: 24 descubiertas, 23 ejecutadas/aprobadas, 1 ASR opt-in omitida, 0 fallos (85,435 s).
- Cierre: 30 descubiertas, 30 ejecutadas/aprobadas, 0 omitidas, 0 fallos (110,561 s).
  ASR opt-in usó voz SAPI local con `socket.connect` bloqueado. No demuestra precisión
  de la voz del fundador. CI añadida, todavía no ejecutada en GitHub (sin push).
- Windows real: Python 3.12.14, uv, FFmpeg/ffprobe 9.0.1, faster-whisper 1.1.1;
  precalentamiento y diagnóstico offline aprobados. No se simuló una reinstalación
  en una VM virgen. Incluye pruebas de rutas con espacios, ñ y apóstrofos.
- Regresiones: final 1080p → preview → fallos preservan ambos SHA; transcript/migración;
  HDR PQ/HLG; VFR/rotación; PNG finito, alpha, MP4 offset, cortes/remapeo, zoom/retorno,
  sin audio/ASR fallida; ASS/Unicode; allowlist/traversal/no aprobado/fallback.
- Lote de cinco probado por BAT: cinco correctos; después cuatro correctos y un fallo
  controlado, preservando el MP4 previo. Reporte JSON con estado/SHA/resolución.
- Fixtures sólo en TemporaryDirectory o nueva raíz marcada de aceptación.
  `DENTFLOW_VALIDATION` ya no elige carpeta de escritura. Colisión raw rechazada.

Artefactos sintéticos de esta sesión (no publicar como grabaciones reales):

```text
C:\Users\User\AppData\Local\DentFlow\validacion_v2\editorial_20260929_161332_274497\Reel 1\OUTPUT\VIDEO_PREVIEW.mp4
C:\Users\User\AppData\Local\DentFlow\validacion_v2\editorial_20260929_161332_274497\Reel 1\OUTPUT\VIDEO_BORRADOR.mp4
C:\Users\User\AppData\Local\DentFlow\validacion_v2\editorial_20260929_161332_274497\Reel 2\OUTPUT\VIDEO_BORRADOR.mp4
```

R1: 50,93 s, siete eventos C/E; R2: 22,60 s, asset B y otro tema, mismo motor.
Watch local/backend none: se leyeron las 39 imágenes de R1 y las 9 de R2 del informe
preview. R1: hook 0–3,5; E estado 12,90–15,98, responsable 15,98–19,20,
fecha 19,20–21,98, acción 21,98–25,06; C estado/responsable 25,06–31,10,
acción 31,10–35,04; retorno 35,09. R2: B 7,10–15,26, retorno 15,31.
Los recortes C ocultan nombre/contacto y muestran Seguimiento pendiente/Recepción/
Llamar hoy 16:00; E muestra un campo a la vez, separado de subtítulos. Primera revisión de fades
antes/durante/después; se ajustó R1 a corte directo entre campos consecutivos. No zoom aprobado en R1; el test comprueba retorno.
Informes y fotogramas están en `watch/` de esa misma raíz de validación.

No se afirma escucha humana íntegra, reproducción en teléfono, piel/gestos reales
ni aptitud profesional. Ambos fixtures conservan voz íntegra sin uniones; las
uniones sintéticas se verifican también por amplitud de audio en la suite. Falta
material real del fundador y su revisión humana para cerrar la aceptación audiovisual.

```powershell
& "$env:LOCALAPPDATA\DentFlow\venv\Scripts\python.exe" -m unittest discover -s tests -v
$env:DENTFLOW_ASR_SAMPLE = "$env:LOCALAPPDATA\DentFlow\validacion_v2\editorial_20260929_161332_274497\Reel 1\raw.mp4"
& "$env:LOCALAPPDATA\DentFlow\venv\Scripts\python.exe" -m unittest discover -s tests -v
```


Calibración editorial de cierre: blackdetect señaló 31,0667–31,1333 s (dos fotogramas)
en R1 al encadenar salida/entrada de fades. Se corrigió **edicion.json**, sin tocar
Python: campos consecutivos usan `animation:none`, regla reutilizable del preset;
las tarjetas independientes pueden conservar fade (R2). CTA R2 corregido sólo en
su transcript (`Revisar/comprobar` → `Revisá/comprobá`) contra el guion SAPI.
Además de previews se inspeccionaron tres cuadros de raw sintético, diez del final
R1 (incluyendo CTA 46/48,5 s), cuatro de R2 y dos del CTA corregido 18,5/20,6 s.

Semana persistente: `semana_cinco/` dentro de la raíz de validación anterior;
cinco raw sintéticos distintos, cinco previews, reportes de 5/0 y 4/1 en OUTPUT.
Las cinco carpetas quedaron válidas; `semana_cinco_evidence.json` registra los cinco
SHA preservados tras el fallo. `qa_outputs.json` y `evidence/` guardan diagnóstico,
pruebas y comprobaciones de outputs. No se agregan estos MP4 ni transcripts a Git.
