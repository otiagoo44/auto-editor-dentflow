# DentFlow Studio — arquitectura del editor visual, automatización y despliegue

**Objetivo del producto:** abrir una página, seleccionar un contenido del sistema V3, subir la toma grabada, comprobar opciones mínimas, iniciar edición, previsualizar, corregir cuando haga falta y descargar el MP4 1080×1920. Conservar editor FFmpeg y Remotion. La web coordina el trabajo; no reemplaza ni duplica los motores actuales.

## Decisión técnica que evita una aplicación imposible

**Vercel hospeda la interfaz y una API ligera; NO el proceso principal de edición.** El render contiene Whisper local, FFmpeg, Node, navegador Chromium, múltiples temporales y puede durar bastante más que una petición web. Para un primer producto personal de coste contenido:

```
TELÉFONO / LAPTOP (navegador)
  → WEB Next.js en Vercel, protegida
  → navegador sube raw directamente a Blob PRIVADO
  → API guarda proyecto/job y estado en base de datos
  → agente Python de tu PC Windows pide trabajos pendientes por HTTPS saliente
  → agente descarga raw y assets autorizados, genera plan, ejecuta V2.1
  → agente sube preview/MP4 + QA/reportes autorizados a Blob privado
  → API/DB registra estado y emite URL firmada para ver/descargar
```

**No** abrir puertos hacia la computadora de casa ni incrustar `WORKER_TOKEN` en JavaScript. El agente debe estar encendido e internet disponible mientras procesa. Si no lo está, `queued / esperando equipo` sin fingir progreso. Cuando se valide el flujo, el mismo contrato permite sustituir el agente de Windows por un worker con FFmpeg/Node/Chromium en un servidor de render permanente (Docker; comprobar recursos/CPU, tonemapping y licencia). No activar más de un render pesado en una PC básica; empezar concurrencia 1.

**Alternativa inmediata sin nube:** desarrollar el mismo Next.js usando API y worker en la PC `localhost`, con entrada directa en `http://localhost:3000`, sin login. Muy útil para comenzar a producir antes de configurar almacenamiento/pagos; no da acceso remoto por sí solo. La migración a Vercel conserva los modelos/contratos.

La documentación de Vercel exige subidas directas para archivos >4,5 MB y permite Blob privado con transferencias de cliente: https://vercel.com/docs/vercel-blob/client-upload ; https://vercel.com/docs/vercel-blob/private-storage . Límites de Functions dependen del plan, no asumir proceso de render persistente: https://vercel.com/docs/functions/limitations . El plan Hobby es no comercial según condiciones oficiales: https://vercel.com/docs/plans/hobby . Para producción comercial considerar Pro o alojamiento alternativo apropiado.

## Navegación propuesta y comportamiento REAL

Pantalla inicial «Contenido»: 6 semanas desplegables, **18 contenidos V3 R01–R18** y **3 alternativas A1–A3**, importados desde el JSON entregado `SEED_CONTENIDO_V3_18_REELS_3_ALTERNATIVAS.json`. Cada tarjeta muestra semana, título, hook sugerido, estado y fecha (desplazable). *El documento V3 original propone tres Reels por semana; no forzar cinco ni reescribir guiones a escondidas.* Botón «Nuevo Reel» para añadir contenido extra cuando decidas producir más. No asumir que `contenido-dentflow/semana-1/Reel 1` equivale a V3 R01: es otro guion. Conservarlo como ejemplo técnico independiente.

Detalle de un contenido: pestañas `Guion`, `Plan visual`, `Assets`, `Grabaciones`, `Versiones`, `Publicación`. Mostrar del V3 el texto literal, tres posibles hooks, caption, CTA, propósito comercial y la marca **demo pendiente** cuando aplique. El texto fuente nunca se altera silenciosamente; permitir variantes con historial. Gate D1–D4 para R03, R08, R11 y R15: no convertir ilustraciones en claims de producto.

Asistente «Editar este Reel», con **máximo cuatro decisiones** antes de procesar: (1) subir raw (arrastrar, reemplazar antes de iniciar); (2) guion/idea y hook sugerido (por defecto el contenido seleccionado); (3) elegir `Educativo Remotion`, `Básico FFmpeg` o `Comercial animado`, y seleccionar música propia autorizada o silencio; (4) pulsar **Generar borrador**. El software usa tags y assets preaprobados, no busca imágenes de terceros ni convierte solo palabras en afirmaciones nuevas. Si falta un recurso, conserva cámara o presenta alerta editable antes de la ejecución.

Página de trabajo durante procesamiento: pipeline `Subido → Cola → Descargando → Transcripción → Plan editorial → Cortes → Composición → QA → Preview disponible → Render final → Revisión pendiente`. Distinguir progreso real (frames/cambios de fase) de progreso estimado. Tiempo aproximado solo cuando haya medidas locales; nunca barra ficticia al 96%. Mostrar cancelación segura solo cuando el worker lo confirme. Dar aviso útil si PC/worker está offline.

Visor de resultados: reproductor 9:16, controles play/pausa, scrub, sonido, y **comparación fuente vs. preview** opcional. Lista de eventos/escenas sincronizadas con tiempos fuente y salida; badges por asset resuelto/omitido, edición manual de subtítulos/números, selector música y nivel, botón «Regenerar con correcciones» (nuevo job/versionado, no pisa el original). Información export: FPS, resolución, duración, advertencias técnicas y estado revisión humana. Botón Descargar video solo cuando existe MP4 final *verificado*; jamás «publicar automático» sin revisión y autorización explícita.

Biblioteca de assets: cada archivo tiene nombre, miniatura, tipo, semántica que explica, `source/provenance`, `usage_rights`, `approved_by_owner`, `safe_regions` opcional y bandera `demo`. El worker solo consume IDs autorizados resueltos a archivos que recibió; nunca rutas arbitrarias del navegador. Categorías: pantallas CRM, comparaciones, diagramas, fondos, música. Remotion utiliza componentes parametrizados sin guardar HTML/JS arbitrarios suministrados por el usuario.

Calendario: vista por semana/lote, estados `planned / needs_recording / uploaded / processing / review / approved / scheduled / published`; fecha de V3 tratada como propuesta editable. Lista de captions/CTA exportables a Instagram/TikTok; publicación en redes **manual** en MVP. Métricas de desempeño separadas (campos editables) sin prometer ingresos ni atribuir causalidad automática al editor.

## Modelo de datos mínimo

- `content_items`: id estable (R01...R18 o UUID), edición V3, título, semana, guion fuente, variantes de hook/caption/CTA, visual_plan, demo_gate, estado, fecha sugerida.
- `projects`: id UUID, content_id nullable, título, idioma, dueño, `source_mode=recording|graphics`, motor, estilo, contenido aprobado/versión.
- `assets`: UUID, owner_id, blob_key, sha256, mime, dimensions, semántica, licencia/declaración, aprobados, etiquetas, regiones, expiración.
- `jobs`: UUID, project_id, input_sha256, settings_hash, `status`, prioridad, motor, intent_idempotency_key, progreso estructurado, retries, lease_token_hash, lease_until, worker_id, salida/latest_version, logs resumidos saneados.
- `job_events`: id, job_id, timestamp, phase, percent_or_null, status, category, message público; logs técnicos secretos quedan fuera de la UI.
- `outputs`: id, job_id, kind `preview|final|thumbnail|qa`, blob_key, mime, codec, resolution, duration, output_sha256, source_sha256, human_review_state, created_at.
- `editorial_plans`: project_id, JSON v2 vigente validado, `source_sha256`, versión de estructura, `resolved/omitted`, procedencia de cada escena (guion/asset dueño/regla), tiempo fuente/salida.

Utilizar un Postgres externo conectado a Vercel (p. ej., proveedor compatible del Marketplace); Vercel Postgres clásico ya no está disponible: https://vercel.com/docs/postgres . Para prototipo local se acepta SQLite si se define migración clara; no ejecutar escrituras SQLite como persistencia en Function serverless.

Transiciones válidas del job: `created → awaiting_upload → queued → leased → downloading → transcribing → planning → rendering → qa → preview_ready → final_ready → human_review_pending → approved`. Ramas recuperables `failed`, `cancel_requested`, `canceled`, `worker_unavailable`. **Una fase puede reintentarse idempotentemente**; upload, transcripción y render se distinguen para no duplicar trabajo. El estado visible en DB se confirma solo cuando Blob final y SHA son accesibles. No guardar rutas absolutas de Windows en la base.

## API sugerida (Next.js App Router)

- `GET /api/content` lista contenido importado/personalizado, con filtrado por semana/estado.
- `GET /api/content/:id`, `PATCH /api/content/:id` para decisiones editoriales/versiones.
- `POST /api/assets/upload-token` emite autorización temporal de Blob privado para MIME/extensión/tamaño, con identidad propietaria.
- `POST /api/jobs` crea idempotentemente un trabajo a partir de un `project_id`, blob ya subido, `source_sha256` y opciones permitidas.
- `GET /api/jobs/:id` devuelve fases, warnings saneados y preview/final firmados si corresponden.
- `PATCH /api/jobs/:id/plan` aplica una modificación validada contra schema y marca resultado anterior como versión antigua.
- `POST /api/jobs/:id/retry` y `POST /api/jobs/:id/cancel` bajo autorización.
- `POST /api/worker/lease` (o `GET` autenticado) entrega hasta 1 job para agente registrado, con lease e idempotency; usar timeout razonable.
- `POST /api/worker/:jobId/heartbeat|progress|finish|fail` exige secreto de servidor-agente + lease actual, no acepta logs arbitrarios ni rutas públicas.
- `POST /api/jobs/:id/approve` marca revisión humana sin pretender medir calidad comercial.

**Auth:** Studio local de propietario puede no tener login. En internet, Vercel Deployment Protection o una autenticación de propietario ligera (passkey/magic link) protege tanto UI como todas las rutas que puedan crear jobs, emitir tokens o descargar resultados. Sin autorización jamás generar URLs firmadas; sesión no editable desde HTML inyectado. `WORKER_TOKEN` solamente variables privadas del servidor y de la PC, rotables; usar HTTPS y rate limiting/cupos. Si Vercel Deployment Protection también cubre endpoints que consume el agente, configurá un bypass exclusivamente de servidor/agente conforme a la documentación o empleá autenticación propia de API: **la protección del navegador no debe cortar el polling del worker, ni el bypass debe enviarse al JS público**. No usar un «PIN» solo validado por frontend.

**Blob:** vídeo crudo, preview y final en bucket **privado**; uploads directos desde el navegador con token corto. La API solo recibe metadata y nunca el cuerpo completo del MP4. TTL de temporales, botón borrar proyecto que borra entrada, assets derivados y job en almacenamiento (con cuidado de borrado idempotente), logs sin nombres, teléfonos ni datos de pacientes. Extensiones/MIME compatibles más verificación `ffprobe` real en worker (la extensión del usuario no demuestra codec). Límites configurables de MB y duración.

## Agente local persistente (Windows) — implementación más reutilizable

Colocar en `worker/` un **adaptador pequeño**, no copiar todo `src/` a otro repositorio. Ejecuta como proceso controlado en tu PC. Al arrancar valida el entorno FFmpeg/Whisper/Node/Chromium según motor y anuncia capacidades. Sondea jobs de la API autenticada cada 10–30 s (no exponer puerto). Crea directorio aislado por job, descarga y verifica `sha256`, materializa su `edicion.json` validado, llama a `src/editor.py` con path sin shell y `--engine`, obtiene avance por un `--progress-json` nuevo o señalización estructurada, sube outputs *después* de QA y emite registro final. Siempre libera lease, borra temporales al terminar y preserva resultados si la red se corta; idempotencia por job+attempt. Empezar concurrencia 1, política de disco, timeouts y reinicios. Si la PC está apagada, trabajo permanece en cola. No almacenar archivos del cliente en Git ni en directorio estático Remotion persistente.

`src/motion.py` ya construye staging temporal `remotion/public/jobs/job_...`, lo cual es reutilizable. Para alta concurrencia en la nube, el staging tendrá que separarse por proceso/bundle y tener cuidado con directorio compartido; *no* resolverlo a costa de render simultáneo en la misma PC. Nunca permitir al cliente subir código React ni flags libres para ejecutar en Node.

## Planificador editorial para baja intervención

**Ruta determinista sin pago por Reel:** contenido V3 (guion, hook, storyboard, CTA) y biblioteca semántica curada → fuente transcrita por faster-whisper local → alineación textual por secuencias y desambiguación de frases → `edicion.json` v2 validado con `source_sha256` y referencias de assets realmente existentes → preflight de clips/captions/tiempos/regiones → render. Si pronunciaste frases distintas y falla el match, *no* inventar momentos: mantener cámara y pedir seleccionar uno o dos cues en un editor visual (señalar con playhead). Un modo `idea libre` sin guion aprobado solo entrega borrador técnico y ofrece «armar storyboard con Codex» como fase editorial separada; si en futuro se configura proveedor de IA, hacerlo opt-in con tope de coste y tratamiento de datos claro.

**Watch**: herramienta para estudiar referencias y revisar muestras reales cuando se trabaja con Codex; no prometer acceso remoto automático al plugin desde una Function. Los principios ya documentados orientan componentes propios: diagrama coincidente con frase, vuelta a cámara al interpretar, zoom solo para atención concreta, subtítulos legibles, no efectos periódicos. No descargar ni incorporar videos de terceros como assets.

**Música/SFX:** silencio por defecto; biblioteca de pistas propias/licenciadas. Opciones `none / soft / energetic`, presets de volumen y ducking suave; efectos únicamente asociados a un evento justificable y con limitador. No extraer música protegida de Reels de referentes. Registrar fuente de cada pista.

## QA y aceptación — sin confundir «render terminó» con «listo para publicar»

Pruebas de diseño: móvil 375px y desktop; 18 contenidos V3 más 3 alternativas importados una sola vez; primer Reel legado preservado sin asociarlo a R01; drag/drop con MIME inválido y archivo grande; motor Remotion no instalado; PC worker desconectada; 1 reintento; cancelación; transcripción equivoca nombre/negación; subtítulos en safe zones; modo sin música. Capturas del hook, 3 escenas, conclusión y último fotograma; inspeccionar por persona.

Integración: 2 videos sintéticos + 2 originales reales usando mismo código; 1 con HDR si lo grabaste así; `--preview` y `--final` diferenciados; 3 cortes, asset PNG+MP4 y música licenciada opcional; previsualización desde *otra computadora* en despliegue protegido; cierre final verificado H.264 AAC 48k 30fps y 1080×1920; descarga con firma expirada; no duplicar render por doble click. CI unit/integration con mocks y smoke controlado; E2E en staging sin activar gasto accidental.

**Criterio mínimo de aceptación desde Vercel:** abrir Studio protegido; ver R01–R18 importados; elegir R02, subir un MP4 sintético o propio (privado), observar cola/worker real y tiempos, obtener preview y final diferentes, reproducir/descargar `VIDEO_BORRADOR` 1080p, apagar worker y comprobar mensaje de espera de nuevo job. No afirmar publicación funcional si solo se ve el prototipo estático.
