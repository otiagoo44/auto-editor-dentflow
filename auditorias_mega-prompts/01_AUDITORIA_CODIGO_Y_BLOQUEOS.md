# Auditoría técnica actual — DentFlow AutoEditor y preparación de Studio Web

**Fecha de consulta:** 29/09/2026, sesión nocturna.  
**Repositorio inspeccionado:** `otiagoo44/auto-editor-dentflow`.  
**Rama que contiene el trabajo nuevo:** `v2.1-remotion` a `55e16295ae4d94dfc686b96c1ae846868629202b`.  
**`main`:** `35e139138e8686c5551bcd1698e706697f5703b3`; **cinco commits por detrás** de `v2.1-remotion`. No se encontró PR ni merge.  
**Inventario real:** 83 entradas de Git, **62 archivos** y 21 carpetas en `v2.1-remotion`; no hay carpeta web ni API web ni worker remoto.

## Cómo interpretar esta auditoría

Inspeccioné por la conexión de GitHub los árboles de ambas ramas, diferencias/commits, README, motor Python, contratos de Remotion, todos los componentes TSX, scripts Windows, archivos de configuración, planes editoriales y tests relevantes. Inspeccioné también el resultado publicado de GitHub Actions. **No cloné ni ejecuté este commit en mi entorno:** la red del contenedor no permite acceder directamente a GitHub. Las ejecuciones locales descritas en el README son registros del autor y se distinguen de la prueba de CI verificada. `package-lock.json` y PNG se inventariaron, pero no hice auditoría línea a línea de dependencias transitivas ni comprobación visual directa de los seis PNG en esta sesión. Los dos JPG históricos son capturas de un informe anterior, no pruebas de la nueva versión.

**Lectura práctica, actualizada tras un commit nuevo durante la auditoría:** el checkpoint `3956e3a` dejó dos fallos de render Remotion, pero el posterior `55e1629` documenta su corrección y una ejecución **local Windows de 44 pruebas aprobadas, 0 fallos y 0 skips**, junto a tres demos sintéticas. Esa ejecución es evidencia declarada en el propio repositorio, no una prueba que yo haya repetido. **Comprobé externamente GitHub Actions de `55e1629`: dos jobs verdes, con tests V1 y contratos Remotion no opt-in y typecheck TS.** El motor local está significativamente más avanzado; aún faltan dos grabaciones iPhone reales, verificación audiovisual humana y TODA la plataforma web. No afirmar calidad editorial de producción solo por tests sintéticos.

## Lo más importante: estado real de Git y CI

1. **P0 — rama equivocada:** el último trabajo no está en `main`; está en `v2.1-remotion`. Si mañana clonás el repositorio sin elegir esa rama obtendrás una versión anterior sin `src/motion.py` ni `remotion/`. Crear rama de trabajo desde `v2.1-remotion`, probar y abrir PR cuando termine, sin forzar `main`.
2. **P1 — verificar el cierre V2.1 reciente, no reimplementarlo:** el checkpoint anterior `3956e3a` sí declaraba dos errores Remotion de FPS/píxel. El nuevo `55e1629` dice que fueron corregidos, añade `--color-space bt709`, el límite AAC y pruebas locales Windows: 44/44, incluidas Remotion/ASR opcionales. Comprobar el entorno propio y repetir un smoke corto, luego dos grabaciones reales. **No tratar los errores históricos como fallos aún presentes sin reproducirlos.**
3. **P1 — CI ampliada, pero cobertura incompleta:** verifiqué GitHub Actions `success` para `55e1629` con dos jobs: `timing-and-editorial` (`test_editor.py` y `test_motion.py`, con renders opt-in omitidos) y `remotion-types` (`npm ci` + `npm run typecheck`). **Todavía NO ejecuta `tests/test_v2.py` ni renders Remotion opt-in, ASR offline o rutas Windows**. Ampliar gradualmente sin confundir el CI verde con validación en móvil.
4. **P0 — faltan dos tomas reales:** no hay grabaciones iPhone en Git (correctamente ignoradas). Los resultados sintetizados en README no sustituyen inspección integral de cortes, audio, color, rostro, subtítulos ni legibilidad en teléfono.
5. **P0 — todavía no existe frontend web:** todo se maneja por BAT, PowerShell y `edicion.json`; no hay Next.js, subida privada, estado de trabajos, cuentas, base de datos, procesamiento remoto ni despliegue Vercel.

## Auditoría detallada del motor Python

### `src/editor.py` (968 líneas; revisado)

**Fortalezas presentes:** selección conservadora de fuente; SHA256 y transcripción ligada a la fuente; validación de palabras y timecodes; worker separado para faster-whisper offline; autocortes sujetos a fin de frase, intervalo y silencio medido; `time_map` y comprobación de fronteras; subtítulos ASS saneados; allowlist por Reel; render H.264/AAC y descodificación completa; opción de tonemapping HDR HLG/PQ con control de metadatos; comprobación de intervalos negros, SHA y alias distintos para preview/final. La CLI ofrece `--plan-only`, `--auto`, `--engine`, `--week`, `--diagnose`, migración explícita de transcript y reportes por lote.

**Observaciones que obligan a intervenir antes de la web:**

- En `run()` se usa `subprocess.run(...,capture_output=True)` **sin timeout ni eventos de avance**. Es válido para CLI local, pero no permite mostrar progreso, cancelar jobs ni distinguir bloqueo real de un render lento en la web. Añadir capa de orquestación con etapas y callbacks, preservando las funciones existentes.
- `--auto` **no deduce un storyboard original** ni crea una animación a partir de una idea libre. Transcribe, aplica cortes conservadores y ejecuta solo los `beats`/`events` explícitos. Para edición casi automática hace falta un planificador que combine el reel seleccionado, guion V3, audio transcrito, biblioteca de plantillas y revisión de dudas. No vender el modo básico como editor audiovisual autónomo.
- `resolve_beats()` tiene degradación a cámara por errores; el proceso puede **terminar exitosamente en un MP4 sin algunos gráficos esperados**. El futuro panel debe mostrar `planned/resolved/omitted`, causas y botón de replanificación; un archivo exportado no significa que completó todas las intenciones creativas.
- `graphic_only` se infiere cuando `render.template='comercial'` y `spec.source` no existe. Una selección equivocada de plantilla podría ignorar un `raw.mp4` presente. Para web exigir `source_mode: recording|graphics`, explícito y validado, conservando compatibilidad de CLI.
- El ajuste geométrico del texto es estimativo y el reencuadre solo usa coordenadas manuales. No hay detección real de cara/controles de plataforma. Ante incertidumbre, mantener cámara y revisión humana; no introducir zoom automático periódico.
- Se calculan varios SHA de archivos grandes y se renderiza cada segmento temporal de forma separada; medir tiempos y espacio de trabajo con raw de iPhone antes de subir videos grandes desde la web. No refactorizar prematuramente sin mediciones.
- La comprobación final de `avg_frame_rate` y `pix_fmt` detiene la salida Remotion: en el checkpoint anterior causó dos fallos. En `55e1629` se incorporan color Rec.709, control del audio AAC y registros de pruebas que declaran resuelto el problema. Repetir un smoke en tu PC y conservar comprobaciones; NO eliminar validaciones.
- El modo final puede crear plan, metadatos e historial. La futura API deberá exponer **solo rutas e IDs autorizados** y no devolver rutas absolutas del sistema ni logs con datos privados a un visitante no autenticado.

### `src/planning.py` (180 líneas; revisado)

**Adecuado:** normaliza tokens con tildes, necesita frase única de al menos tres tokens, mantiene orden y conflictos, valida `focus_region`, rutas locales y raíces; prohíbe URL y carpetas de investigación. Permite eventos `motion` y valida referencias a las seis plantillas. Controla rangos de cortes de configuración.

**Limitaciones relevantes:** depende de `match_text` literal reconocido por el modelo base; la grabación espontánea puede omitir un disparador. El futuro planificador debe mostrar la coincidencia con su confianza, no inventar tiempos. `DIAGRAM_REVEAL` divide regiones estáticas con tiempos fijos; no equivale a una animación de UI por capas. La importación de guiones V3 exige separar *plan de contenido* de *plan de edición*; un PDF nunca se ejecuta directamente como `edicion.json`.

### `src/motion.py` (245 líneas en `55e1629`; revisado)

Es un puente correcto en concepto: reutiliza el montaje validado, convierte un A-roll a AAC, copia solamente recursos permitidos a un directorio temporal, genera props con tiempos **de salida**, ejecuta Remotion local sin `shell`, limita tiempo a 60 minutos y normaliza la mezcla final una vez. Restringe seis tipos de escena y exige declaración de derechos para música.

**Problemas/riesgos concretos:**

- `render_options()` **acepta `render.captions`** como `ass|remotion`, pero **no lo devuelve** en su diccionario ni lo utiliza. La composición React siempre dibuja subtítulos. Corregir contrato: una sola fuente de captions; o eliminar el ajuste no soportado.
- Comprueba Chromium exclusivamente en un patrón de directorio bajo `remotion/node_modules/.remotion`. La instalación llama a `remotion browser ensure`, pero la ruta efectiva debe comprobarse en Windows. Si está en otro caché, el chequeo podría fallar con navegador instalado. Probar con `node`, CLI real y la ruta del instalador, no suponer compatibilidad.
- No hay protocolo estructurado de progreso por fase ni cancelación cooperativa para web. El `stdout` se captura en log y Remotion ya tiene un proceso supervisado con `timeout` y limpieza de árbol en Windows, pero la UI futura necesita eventos JSON, estados y reintento idempotente.
- `speech_windows` llega a la música por palabra; la composición cambia inmediatamente de volumen cuando detecta voz. Agrupar ventanas de habla y aplicar rampas de ducking para evitar bombeo audible entre palabras.
- La música requiere `rights_declared:true`, acertado, pero una declaración no acredita realmente licencias. Crear biblioteca administrada con licencia, fuente y alcance de uso guardados; no buscar ni incorporar pistas automáticamente desde terceros.
- `build_props()` redondea a cuadros y compara duración dentro de tolerancia; los cambios de `55e1629` registran prueba específica de AAC/frames y demos válidas. Asegurar extensiones de test de 30/60 FPS y captions al límite del plano cuando la UI permita más formatos; mantener FPS 30 del proyecto actual.

## Código Remotion, revisado archivo por archivo

| Archivo | Qué hace hoy | Hallazgo y próxima acción |
|---|---|---|
| `remotion/package.json` | Dependencias clavadas en Remotion **4.0.530**, React, Zod y TypeScript; scripts Studio/typecheck/browser. | Mantener versiones coordinadas y lockfile; agregar prueba de build/render a CI y un comando fiable para generar still/frame. |
| `remotion/package-lock.json` | Fija dependencias npm; se comprobó presencia, no auditoría de cada transitiva. | Ejecutar `npm ci`, `npm audit` informado y `npm run typecheck`; no cambiar versiones indiscriminadamente. |
| `remotion/tsconfig.json` | Compilación TS de la subaplicación. | Comprobar Windows y CI; no mezclar con Next.js web. |
| `remotion/src/index.ts` | Registra Root. | Correcto en lectura. |
| `remotion/src/Root.tsx` | Dos composiciones (`DentFlowEducativo` y `DentFlowComercial`), props validables y demo Studio. | La UI deberá permitir elegir una de las dos y previsualizarla sin render completo. No confiar solo en demo por defecto para declarar exportación real. |
| `remotion/src/schema.ts` | Zod valida props, timelines, duración vertical y paths por job. | Muy útil como frontera de seguridad; al crear API pública no aceptar props arbitrarias sin autorización, ni `asset_roots` del cliente como ruta de sistema. |
| `remotion/src/Composition.tsx` | Monta A-roll, escenas, una pista de subtítulos y música. | La composición no «piensa» el storyboard; consume eventos de Python. Reducir saltos de volumen musicales y revisar safe zones de teléfono. |
| `remotion/src/components/Design.tsx` | Paleta DentFlow, animación de entrada, frames y cards. | **Problema de acabado:** posiciones/tamaños fijos en 1080×1920, tarjetas parecidas para varios conceptos y riesgo de texto largo. Prueba visual de un título corto/largo y 1/4 cards en preview y teléfono. |
| `remotion/src/components/AnimatedMessages.tsx` | Actualmente envuelve el mismo `Cards` genérico. | No simula realmente el flujo de mensajes con burbujas de chat y estados. Desarrollar componente distintivo y reutilizable, sin copiar apariencia de WhatsApp ni crear capturas falsas. |
| `remotion/src/components/CRMHighlight.tsx` | También es un wrapper de `Cards`. | Aún no dibuja un CRM detallado, foco de fila ni cursor/timeline. Crear componentes de ficha con datos ficticios y animación de selección/estado. |
| `remotion/src/components/StepDiagram.tsx` | Cards numeradas con entrances escalonados. | Primera versión útil; añadir conectores y progresión condicional según sentido, sin exagerar efectos. |
| `remotion/src/components/QuestionHook.tsx` | Frame/título con animación genérica de entrada. | Verificar que el hook no requiera inventar palabras no dichas; cámara visible o full según el tipo de Reel. |
| `remotion/src/components/ScreenshotFocus.tsx` | Muestra imagen o video autorizado con fade en caja. | No aplica recorrido animado ni magnificación posterior: el recorte lo precalcula Python. Añadir zoom/pan suave únicamente en región ya autorizada y donde se conserve contexto legible. |
| `remotion/src/components/SummaryCTA.tsx` | Bloque visual de CTA y título. | Comprobar texto, márgenes y que el CTA tenga un destino real cuando lo requiera; no simular demostraciones de funcionalidades. |
| `remotion/src/components/Captions.tsx` | Dibuja una frase precomputada por vez. | No hay resaltado de palabras ni medición de tipografía real. Priorizar contraste, una o dos líneas y no disputar espacio con demostraciones; resaltado opcional después. |

**No confundas la presencia de seis nombres de plantilla con seis animaciones sofisticadas ya implementadas:** varias comparten exactamente la misma composición de tarjetas.

## Windows, pruebas, documentación y recursos

| Archivo(s) | Verificación / asunto |
|---|---|
| `.github/workflows/tests.yml` | CI verificada **actual `55e1629`**: `success` para `test_editor.py` + `test_motion.py` (renders opt-in omitidos) y otro job `npm ci`/`typecheck`. Falta `test_v2.py` en CI y una estrategia de smoke Remotion; Windows e iPhone siguen en pruebas locales. |
| `.gitignore` | Excluye videos/audio reales, `node_modules`, directorios temporales de Remotion, transcripciones y claves; mantenerlo. Agregar `.next`, artefactos web, cache Next.js y secretos del worker cuando se cree web. |
| `config.yaml` | Preset conservador CPU/int8, 1080×1920, cortes cautos. Mantener como una única fuente de parámetros nativos; UI guarda preferencias válidas pero no permite pasar flags FFmpeg libres. |
| `requirements.txt` | Incluye faster-whisper y PyYAML clavados; no hay FastAPI ni worker remoto. Incorporar dependencias del worker de forma separada, no cargar Next.js con ASR. |
| `install.bat`, `scripts/install.ps1` | Versión actual mejorada: winget uv/FFmpeg, caché de modelo y diagnóstico. Aún requiere prueba en una instalación Windows verdaderamente limpia. |
| `instalar_remotion.bat`, `scripts/install-remotion.ps1` | Instalan Node/npm y Chromium para Remotion, verifican TypeScript. Revisar ruta real del navegador y que no haya descargas durante el render. |
| `editar_reel.bat`, `editar_semana.bat` | CLI por pieza y lote; adecuadas como fallback para cuando web o worker fallen. |
| `autoeditor.bat`, `scripts/launcher.ps1` | Menú visual limitado a consola/carpeta Windows. **No es web**, ni soporta el navegador desde otra computadora por sí solo. Conservar como modo local de emergencia. |
| `edicion.example.json` | Contrato de ejemplo; verificar siempre respecto al schema presente y actualizar cuando la web añada propiedades no rompedoras. |
| `contenido-dentflow/semana-1/Reel 1/edicion.json` | Plan demo existente centrado en 4 campos, C/E, `preserve` y triggers vinculados a guion específico. **No representa automáticamente el R01 del sistema V3** (el documento V3 tiene otro guion y título). Importarlos como proyectos distintos para no perder la correspondencia. |
| `ejemplos/Comercial/edicion.json` | Demo gráfica de 28 segundos, siete escenas y música apagada. No sustituye prueba real de `test_commercial_no_camera_and_silence`. |
| `tests/test_editor.py` | **7 tests** V1; ahora también corre `test_motion.py` en CI. Mantener regresión. |
| `tests/test_v2.py` | **25 tests definidos**; incluyen HDR/HLG, migración de transcripción, ruta Windows, ASR opt-in, cortes, overlays y lote. Ejecutar todos en Windows; Linux CI puede omitir condicionalmente tests de Windows. |
| `tests/test_motion.py` | **12 tests definidos** en `55e1629`: ocho pruebas de contrato y cuatro renders opt-in (uno específico de Windows). El README/documento de cierre declaran una suite local de **44 pruebas aprobadas** y corrección de los dos fallos anteriores. GitHub CI no ejecuta los renders opt-in. |
| `tests/render_acceptance.py` | Pruebas sintéticas de editor, no la validación de voz propia. Mantener fuera de carpetas de producción. |
| `tests/render_motion_acceptance.py` | Aceptación sintética comercial y educativa: en `55e1629` el informe de cierre documenta tres demos completas, metadatos y muestreo con Watch. Sigue sin reemplazar dos clips propios + escucha y reproducción humana en móvil. |
| `contenido-dentflow/semana-1/Assets/manifest.json` | Descripciones/limitaciones de seis imágenes; no tiene selección inteligente en runtime. Extender metadatos semánticos opcionales para planificador, sin inventar derechos. |
| `Asset A.png` | Tabla con estado/próxima acción; no tiene responsable según manifiesto. Revisión visual anterior, no reanalizada ahora. |
| `Asset B.png` | Contraste conversación vs. control; separar regiones para vertical. |
| `Asset C.png` | Ficha ficticia; excluir nombres/contactos ilustrativos al recortar. |
| `Asset D.png` | Manifiesto señala discrepancia título «10» frente a seis filas; no usar sin corregir. |
| `Asset E.png` | Cuatro campos de seguimiento; apto para explicar uno por vez. |
| `Asset F.png` | Conversaciones dispersas; puede ser redundante con voz. |
| `Flow/.../research/dentflow_educativo_v1.md` y `evidencia.csv` | Investigación histórica: usar como guía atribuida de edición; muestras parciales, no reproducción integral de todos los referentes. |
| `videos_estudiar/01_REFERENCIAS...json`, `02_PROMPT...md`, `03_FICHA_VISUAL.csv`, `LEER_PRIMERO.md` | Inventario histórico y plantilla: los estados `NOT_WATCHED` pueden ser anteriores al CSV más reciente. `02_PROMPT` es una orden antigua «no programar aún»; archivar/rotular para que Codex no frene el desarrollo. |
| `auditorias_mega-prompts/*.md`, `DentFlow_Remotion_Investigacion/*.md`, `04_EJEMPLO_PLAN...json`, `LEER_PRIMERO.md`, `CIERRE_V21.md` y 2 JPG | Archivos de consulta y registro. `CIERRE_V21.md` añadido en el nuevo HEAD declara validación local, demos y límites; leerlo como reporte del ejecutor, no como prueba independiente en esta sesión. Proteger medios y evitar usar docs como assets publicables. |

**Resultado del inventario actual:** 62 archivos totales (incluyendo 6 PNG, 2 JPG, un lockfile y documentación). El análisis exhaustivo se concentra en los archivos ejecutables y sus interacciones; no se auditaron las dependencias npm externas ni los píxeles de todos los recursos binarios como si fueran código.

## Auditoría temporal del commit de cierre `55e1629` (dato comprobado durante esta revisión)

Este commit llegó **después** de empezar la inspección del checkpoint `3956e3a`. Revisé su diff: ocho archivos modificados más el documento nuevo `auditorias_mega-prompts/CIERRE_V21.md`; incorpora `loudness_analysis`, ajustes explícitos `bt709`/duración AAC, pruebas adicionales de Motion, amplia CI y actualiza instalación y mensajes. El informe de cierre afirma **44 tests Windows aprobados, 0 fallos/omisiones**, exportaciones sintéticas comercial de ~28 s, R1 ~51 s y R2 ~10 s, comparación de RAM/tiempo y lote de cinco con fallo recuperable. **GitHub Actions realmente verde con dos jobs sobre ESTE SHA** confirma tests V1+contratos Motion y typecheck TS, pero no confirma por sí mismo renders Windows/iPhone. El manifiesto de cierre indica que la suite total precedió a un ajuste final AAC, seguido por regresión puntual y nuevos renders; sus notas de «cierre todavía local» han quedado obsoletas porque el propio cierre `55e1629` ya se publicó en `origin/v2.1-remotion`; por eso la reejecución integral del nuevo HEAD en tu PC sigue siendo útil para certificar ese último ajuste.

Defecto independiente de la corrección de FPS: `motion.render_options()` todavía valida `render.captions=ass|remotion` pero omite esta clave al devolver las opciones; el compositor Remotion siempre dibuja captions. Mantener un único motor de subtítulos y rechazar combinaciones no soportadas o implementar realmente la preferencia. La integración visual sigue sin automatizar decisiones semánticas y `AnimatedMessages`/`CRMHighlight` siguen siendo wrappers de tarjetas; V2.1 local funcional no equivale a editor creativo web autónomo.

## Diagnóstico de producto: lo que todavía falta para «subo raw → video terminado»

Actualmente no hay un planificador que, partiendo de un guion arbitrario/idea libre y un MP4, genere automáticamente un JSON rico válido y aprobado. Las plantillas no generan gráficas aleatoriamente: presentan datos suministrados. Watch no forma parte del runtime, y la skill instalada en Codex tampoco es un servicio remoto que la web pueda invocar sin construir integración explícita. Para el flujo sin coste por video, **usar guiones V3 y una biblioteca de assets preaprobados**, emparejar el audio con el guion y caer a cámara en los tramos dudosos. Un modo libre con IA puede ser opcional, presupuestado y autorizado por el usuario; nunca afirmar que funciona sin credenciales/modelo.

La web requerirá separar un **frontend de control** de un **worker de media persistente**. No ejecutar faster-whisper + FFmpeg + Chromium como si la publicación Next.js de Vercel fuera una PC que queda permanentemente encendida. Una función HTTP puede finalizar por límite de tiempo, y una subida de video excede habitualmente el límite de petición directa. Vercel documenta subidas directas de navegador a Blob y límites de Functions: https://vercel.com/docs/vercel-blob/client-upload ; https://vercel.com/docs/functions/limitations ; changelog 15/06/2026 de duración Pro hasta 30 minutos en beta. La arquitectura elegida se describe en el documento 02.

**Seguridad:** «sin iniciar sesión» solo es razonable en un Studio `localhost` o red privada. Una aplicación pública sin control permitiría que cualquiera consuma CPU/almacenamiento o vea material de grabación. Para la versión en internet exigir acceso de propietario o protección de despliegue; no guardar credenciales en React ni ofrecer endpoints que admitan URLs arbitrarias.

**Restricción de plan comercial:** Vercel especifica que el plan Hobby es solo personal/no comercial. Para una herramienta operativa del negocio verificar Pro o alternativa de hosting que admita ese uso: https://vercel.com/docs/plans/hobby .

## Orden de corrección (puertas de aceptación)

**Puerta 0: revalidar el cierre V2.1 y congelar contrato.** Confirmar HEAD `55e1629` o posterior, trabajar en rama nueva, verificar el reporte `CIERRE_V21.md` y reproducir la suite **44 métodos definidos** (7 V1 + 25 V2 + 12 motion) con las variables opt-in pertinentes y `npm run typecheck`. GitHub Actions de este commit ya valida los contratos generales Motion y TS, pero falta V2 en CI. Resolver `render.captions` (aceptado e ignorado), verificar ruta Chromium y smoke de preview y final en TU máquina; **los dos fallos antiguos figuran corregidos**, no reabrirlos sin evidencia. La plataforma web no se presenta como motor listo hasta pasar al menos un E2E local y la aceptación iPhone.

**Puerta 1: video real.** Dos grabaciones del fundador, una con C/E y otra con recurso distinto. Inspectar audio, piel/HDR, subtítulos y safe zones en teléfono. Repetir sin tocar Python para el segundo. Evaluar Remotion vs. FFmpeg con la misma voz y guion.

**Puerta 2: Studio local.** Interfaz Next.js que importe de forma explícita V3, suba un raw al worker local y produzca preview/final. Sin sesión personalizada en `localhost`; nombres y rutas no deben permitir traversal. API versionada y logs de progreso. No necesitar Codex para cada render de contenidos ya estructurados.

**Puerta 3: Studio Vercel remoto.** Frontend protegido en Vercel, subida directa a Blob privado, base de datos de jobs y agente **saliente** en la PC o worker de media externo. Solo declarar «listo en Vercel» tras **un trabajo real, desde otra computadora, hasta descargar MP4 final**. Si la PC está apagada, mostrar «worker desconectado» y conservar trabajo en cola, no simular edición.

**Fuentes primarias:** árbol, código, README, `CIERRE_V21.md` y Action de `55e1629` de `otiagoo44/auto-editor-dentflow`; `remotion-dev/remotion` para capacidades de Remotion; documentación oficial de Vercel para despliegue. Este informe no certifica compatibilidad mediante ejecución propia.
