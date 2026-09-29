# Arquitectura propuesta: DentFlow AutoEditor V2 estable → V2.1 con Remotion

## Objetivo del producto
Entrada mínima en modo educativo: grabación iPhone `raw.mp4`, guion opcional en texto, carpeta de assets **propios/autorizados** con manifiesto y —cuando se quiera edición avanzada— Codex prepara una sola configuración editorial `edicion.json`. Salida: preview independiente, MP4 final vertical, subtítulos correctos, cortes naturales y gráficos justificables. El creador revisa antes de publicar. El proceso técnico de render no requiere API pagas ni subir material clínico a la nube. Reducir trabajo repetitivo **no** significa atribuir a código determinista criterio humano no disponible.

## Cierre V2 antes de integrar Remotion: contrato obligatorio
Releer código HEAD actual; el estado inspeccionado era `35e1391`.
1. Separar `OUTPUT/VIDEO_PREVIEW.mp4` (360×640) de `OUTPUT/VIDEO_BORRADOR.mp4` (1080×1920); el preview jamás sustituye el final. Mantener historial y estado SHA/resolución por ejecución.
2. `transcript.json` corregido debe estar vinculado a `source_sha256`, `source_duration` y versión o pedir aceptación explícita si cambia `raw.mp4`.
3. Endurecer `install.ps1` y diagnóstico real H.264/AAC/libass/filtros y calentamiento local; ensayar segunda PC Windows.
4. Aislar fixtures de tests del contenido auténtico; impedir que `DENTFLOW_VALIDATION` apunte a carpetas reales.
5. Comprobar iPhone SDR/HDR/HEVC/rotación/VFR con muestras auténticas, tonemapping a Rec.709 solo si el HDR se detecta y resulta necesario.
6. Dos Reels propios: escucha de uniones, revisión de captions, reencuadre, lectura de C/E, rango de móvil. Repetir lote 5 con fallo controlado. No declarar «completado» antes de esos criterios.

## Dos rutas, un solo contrato editorial
```text
REEL/
  raw.mp4                  (entrada, NO versionar)
  guion.txt                (opcional, contexto editorial)
  edicion.json             (única configuración de usuario, esquema V2 compatible)
  transcript.json          (opcional, correcciones con hash de fuente)
SEMANA/Assets/             (propios/autorizados; manifest.json + imágenes o demos)

                   ┌──────────────────────────────────────────────────┐
                   │ Python: ffprobe + iPhone/SDR + faster-whisper     │
                   │ audio_analysis + planificación validada          │
                   │ resolve_beats + keep_segments + time_map         │
                   └───────────────────────┬──────────────────────────┘
                                           │
                               edicion.json + plan_edicion
                          ┌────────────────┴─────────────────┐
                          │                                  │
                    engine=ffmpeg                     engine=remotion
                    (V2 estable)                      (V2.1 opcional)
                          │                                  │
              render_final + ASS               FFmpeg render_cut_video
              + overlay actual                [SIN ASS NI OVERLAYS]
                          │                                  │
                          │                     mezzanine.mp4 H264/AAC
                          │                      + props derivadas JSON
                          │                      + assets autorizados
                          │                                  │
                          │                     Remotion React TS local
                          │                     2 composiciones parametrizadas:
                          │                        DentFlowEducativo
                          │                        DentFlowComercial
                          │                                  │
                          │                         MP4 completo local
                          └────────────────┬─────────────────┘
                                           │
                                    QA + alias atómicos:
                     VIDEO_PREVIEW.mp4  /  VIDEO_BORRADOR.mp4
                     plan_edicion.json + warnings + log detallado
```

**Decisión preferida:** Remotion renderiza **el video completo** en modo nuevo a partir del video A-roll previamente recortado. Evita vídeo transparente/alpha en Windows, problemas de codecs VP9, varios pipelines de subtítulos y una capa final de overlays que ya habría quedado quemada. El modo FFmpeg anterior sigue siendo fallback. Si más adelante la CPU/RAM obligan a optimizar, considerar renders parciales de gráficos, siempre midiendo transparencia y coste de complejidad primero.

## Ruta A: Educativo / cámara y demostración
El editor debe mostrar tu grabación como fondo la mayor parte del tiempo; cada efecto necesita una razón editorial en `edicion.json`. React dibuja los apoyos SOLO cuando el `beat` fue resuelto/permitido en el plan de Python.
- `QuestionHook`: primera frase breve con resaltado animado si no tapa cara.
- `SplitExplanation`: fundador en región segura y esquema al lado o sección superior; puede omitir presentación de rostro cuando demo necesita pantalla principal.
- `CRMHighlight`: representación limpia y original del estado/responsable/fecha/próxima acción; entrada progresiva al mencionar cada concepto.
- `ScreenshotFocus`: sobre captura autorizada y marcada demo; máscara o resaltado de control específico; el resto del panel puede permanecer visible como contexto.
- `StepDiagram`: pipeline Entrada→Responsable→Próxima acción→Revisión; etapas guiadas por frases, no animadas mecánicamente cada 2 segundos.
- `SummaryCTA`: retoma cámara; muestra una única conclusión y acción verificable, nunca pacientes/ROI prometidos.

El AutoEditor **no genera una segunda toma** desde una sola cámara, ni decide que un fallo ASR representa un corte. Para perspectiva diferente se necesita grabación adicional; el pequeño punch digital de la V2 no debe confundirse con multicámara.

## Ruta B: Comercial / video gráfico de alto acabado
Reconstruir con COMPONENTES EDITABLES las seis fases observadas en el video de 28 segundos adjunto:
1. Hook «Llegan consultas. ¿Y después?» con 1–3 canales que llegan uno tras otro; usar nombres de fuentes disponibles reales.
2. Problema de gestión con tres tarjetas (entrada, responsable, seguimiento); cada tarjeta entra al referirla la narración o a tiempo preconfigurado **solo si es comercial sin voz variable**.
3. Proceso visual con tarjeta CRM ilustrativa (`Lead 07` SOLO como ficticio), estados originales de DentFlow; no fingir interacción real.
4. Vista detallada de una consulta con siguiente paso y responsable, una cosa a la vez.
5. Lista de prioridades y próximas acciones. Evitar porcentajes inventados y nombres de pacientes.
6. CTA y marca, usando destino de demo real confirmable.
Esta ruta puede utilizar música licenciada, SFX mínimos y transiciones de escenas motivadas. No convertir por defecto todos los videos educativos en presentaciones comerciales.

## `edicion.json` sigue siendo la ÚNICA entrada manual
Agregar claves opcionales, sin romper V1/V2:
```json
{
  "schema_version": 2,
  "source": "raw.mp4",
  "mode": "editorial",
  "render": {
    "engine": "remotion",
    "template": "educativo",
    "music": {"enabled": false, "file": null, "rights_declared": false},
    "captions": "remotion"
  },
  "allowed_assets": ["../Assets/Asset C.png", "../Assets/Asset E.png"],
  "beats": [
    {
      "id": "definicion_estado", "purpose": "Explicar estado de una consulta",
      "match_text": "estado en qué etapa", "until_text": "responsable quién sigue",
      "asset": "../Assets/Asset E.png", "animation": "fade",
      "template": "CRMHighlight", "focus_region": [0.035,0.39,0.225,0.37],
      "approved": true, "fallback": "camera",
      "reason": "La tarjeta añade una definición visible al enunciado"
    }
  ]
}
```
No introducir `instrucciones.json` como segundo contrato. Solo el planner Python genera internamente `remotion_props.json` a partir de `plan_edicion.json` y la ruta elegida. La propiedad `template` adicional necesita validación estricta, nunca permite ejecutar TS/JS arbitrario inyectado por el usuario. Entradas `rights_declared` son manifestaciones del autor, no prueba de licencia.

## Contrato **interno** Python→Remotion (validado con esquema TypeScript/Zod)
- `job_id`, `format_version`, `template=educativo|comercial`, `fps=30`, `width=1080`, `height=1920`, `duration_frames`.
- `base_video`: ruta local *staged* `public/jobs/<jobid>/aroll.mp4`; video H.264/AAC con voz y TODOS los cortes ya hechos. En modo comercial sin cámara se omite.
- `scenes`: `id`, `template`, `start_frame`, `duration_frames`, `params` delimitados (texto limpio, elementos ficticios/de datos autorizados, colores y focus_region).
- `captions`: palabra/agrupación con tiempos **del video montado**; mismos datos Python, NO segundo ASR. Compatibilidad `Caption` de Remotion `startMs/endMs`, `timestampMs=null`, `confidence=null`; el plan original preserva tiempos fuente.
- `music`: ruta stage validada y estado de autorización, curva de volumen consensuada y cue points si hay audio; no inventar derechos ni descarga de canciones.
- `asset_paths`: lista generada ÚNICAMENTE a partir de `allowed_assets` + política de directorios, copiada con nombres seguros al stage; ningún acceso arbitrario a rutas de disco/red.
- `metadata`: origen SHA fuente, plantilla/versión, status de beats usados, duración real, no información clínica.

**Tiempo:** `render_cut_video()` se ocupa de `keep_segments` y produce un único A-roll con voz en duración output. Remotion trabaja EXCLUSIVAMENTE en output time; segundos a frame `round(t*fps)` de forma coherente y test de diferencia ≤ 1 frame en entradas/salidas. Ningún React component vuelve a restar cortes ni aplica offsets del original. `duration_frames` se deriva del video cortado medido por ffprobe y se comprueba contra time_map. Considerar final de último frame/decimales evitando eventos con cero frames.

## Staging, compatibilidad y QA
1. `render_cut_video()` genera MKV H.264/PCM temporal; convertir por remux cuando sea posible a **MP4 H.264/AAC CFR 30fps SDR Rec.709** antes de `staticFile()`. PCM en `.mp4` no es una opción portátil. Si fuente iPhone es HDR aplicar tonemapping condicionado antes de la fase de mezcla y controlar tonos de piel.
2. `remotion/public/jobs/<jobid>/` ignorado por Git, con `aroll.mp4`, imágenes/demos aprobados, `music.*` aprobada y `props.json`; nombres y tamaños limitados. Copiar rutas absolutas externas solo tras autorización validada y resolver `..`/symlinks. No copiar research ni usar MP4 terceros por defecto.
3. Node independiente en `remotion/` con `package-lock.json` y todas las versiones Remotion **fijadas exactamente iguales**. Proyecto empaquetado mínimo: `react`, `react-dom`, `remotion`, `@remotion/cli`, `@remotion/media`, `@remotion/captions`, `@remotion/transitions`, quizá `@remotion/sfx`, `typescript`, `zod`; añadir otras únicamente si la plantilla funcional las usa. Elegir versión tras comprobar release/docs, no mezclar 4.x con 5.x.
4. `src/index.ts` registra root; `Root.tsx` expone `DentFlowEducativo` y `DentFlowComercial`, ambas con `calculateMetadata` o duración validada. `components/` incluye cinco o seis elementos ORIGINALES con estilos/animaciones predecibles; paleta de marca calibrada desde assets.
5. Primer prototipo con `npx remotion render ... --props <ruta-archivo-json> --concurrency 1` invocado con `subprocess.run([...], cwd=..., shell=False, timeout=...)`. EN WINDOWS: JSON `--props` por archivo, NO inline por quoting. Usar `<Video/>`/`<Audio/>` de `@remotion/media` recomendado por versión comprobada; fallback documentado a `<OffthreadVideo/>` ante codec/versión que falle.
6. Sin doble subtítulo: si `engine=remotion`, FFmpeg no llama a `write_ass` sobre el A-roll; Remotion dibuja subtítulos desde plan. Si `engine=ffmpeg`, sigue el ASS actual.
7. Mezcla: voz audible siempre. Música OFF por defecto; cuando esté autorizada, `Audio` y volumen bajo respecto a voz con entrada/salida/ducking parametrizado. SFX solo en acciones que explican un paso. Medir LUFS/pico del resultado final, escuchar con auriculares y en teléfono; la lectura de `volumedetect` no demuestra calidad.
8. Preview independiente: se puede renderizar 360×640 pero verificar que las plantillas usan escalas/márgenes relativos y texto legible; no promover preview a final. Para 8 GB RAM comenzar `--concurrency 1`, batch secuencial; no ejecutar Whisper/FFmpeg largo y Chromium simultáneamente.
9. Límite 2–5 min de render de PRUEBA es objetivo de UX, no promesa. Registrar tiempo y memoria antes de fijar SLA; fallback a V2 FFmpeg para hardware limitado. Contenido e inputs pueden cambiar la velocidad.
10. Revisión: capturas en inicio, cada entrada/salida de apoyo ±1 fotograma, cambio de escena, mitad y cierre; buscar negro, overlays tardíos, saltos, títulos fuera de safe zones, errores de ASR; mirar los dos MP4 completos en móvil antes de autorizar publicación.

## Flujo futuro en tres acciones humanas
1. Grabar el Reel y copiar `raw.mp4` a carpeta de la semana, opcional `guion.txt`.
2. Codex (asistente editorial local, NO API de runtime) examina transcript, audita assets permitidos/manifiesto, prepara/ajusta `edicion.json` y señala solo dudas. En producción habitual, plantillas y manifest permanecen entre videos, por lo que solo cambian pocas frases y capturas autorizadas.
3. Ejecutar `editar_reel.bat ".../Reel 1" --auto --engine remotion --preview`, revisar previsualización; exportar sin `--preview` a `VIDEO_BORRADOR.mp4` y hacer QA final. En batch, preparar planes editorialmente antes y luego `editar_semana.bat ... --auto --engine remotion` secuencial. Este comando es **objetivo de implementación**, NO existe aún en el código inspeccionado.

## Pruebas que liberan V2.1
- Los 24 tests históricos del AutoEditor deben seguir verdes (con skips documentados) y sus reparaciones V2 P0/P1 aprobadas; su número aumentará al crear tests V2.1.
- Prueba de tiempo: clips con tres `keep_segments`, tres gráficos en tiempos fuente, evento detrás de segundo corte; sincronía output en ±1 fotograma, ningún gráfico fuera del segmento.
- Prueba de simple/híbrido/comercial; video con audio y sin audio, assets 16:9, Unicode/español, PNG/MP4, captions de nombres/cifras/negaciones, 9:16 vertical, HEVC/VFR/HDR real.
- `FFmpeg only` corre aunque no haya Node; engine Remotion falla con mensaje claro y no modifica salida previa si Node o navegador faltan.
- Render 28 s de comercial original con **datos ficticios**, seis plantillas y audio de biblioteca autorizado: comparar storyboard, no pixel a pixel con el MP4 ejemplo.
- Render de DOS Reels propios de iPhone con overlays y voz sin retocar código; visualización completa humana.
- Batch de cinco con un error inducido y estados por Reel; suma de errores correcta; sin salida de preview confundible.
- Seguridad: sin importar research como recursos, sin sobrescribir crudos de usuario con fixtures, sin transmitir datos clínicos y sin ejecutar código arbitrario generado desde prompts.

## Qué NO incorporar todavía
- No clonar/forkear Remotion completo: 16k entradas no son necesarias para usar un paquete npm.
- No generar interfaces React nuevas con IA en **cada Reel**: las plantillas reusable/props proporcionan coherencia y bajo coste; solo crear una plantilla nueva cuando una explicación lo amerita.
- No agregar Next.js, Lambda, Player embebido ni aplicación SaaS: cinco videos semanales justifican un CLI local primero.
- No fijar 3D, blur, efectos de destello ni música por cuota temporal. La evidencia audiovisual de referentes no sustenta fórmulas garantizadas de retención.
