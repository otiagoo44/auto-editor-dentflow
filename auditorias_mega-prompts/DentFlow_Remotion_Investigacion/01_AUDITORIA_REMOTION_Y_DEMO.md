# Auditoría técnica de Remotion para DentFlow AutoEditor
**Fecha:** 29-09-2026. **Naturaleza:** auditoría de arquitectura del árbol completo y lectura selectiva de código, manifiestos, documentación y skills relevantes; **no** análisis individual de 16.041 rutas ni prueba de ejecución del monorepo. No modificar el repositorio de Remotion; integrarlo como dependencia en proyecto propio.

## Fuentes y revisiones observadas
- Repositorio oficial: https://github.com/remotion-dev/remotion ; árbol de `main` inspeccionado: `2599f02ecaba7f6a4bd84aa494ddf854bf91ddb9` (16.041 entradas, 0 truncamiento).
- `packages/core/package.json`, `packages/renderer/package.json`, `packages/bundler/package.json`, `packages/media/package.json`, `packages/captions/package.json`, `packages/transitions/package.json`, `packages/sfx/package.json`, `packages/player/package.json`: versión observada `4.0.530`. Esta es una fotografía del monorepo, no una garantía de versión npm mañana.
- Documentación consultada: https://www.remotion.dev/docs/ssr-node ; https://www.remotion.dev/docs/cli/render ; https://www.remotion.dev/docs/video-tags ; https://www.remotion.dev/docs/ai/skills ; https://www.remotion.dev/docs/license/faq ; https://www.remotion.dev/docs/transitioning
- Código y guías examinadas: `AGENTS.md`, `LICENSE.md`, `packages/core/src/Composition.tsx`, `packages/transitions/src/TransitionSeries.tsx`, `packages/captions/src/create-tiktok-style-captions.ts`, `packages/template-overlay/src/Overlay.tsx` y `Root.tsx`, `packages/codex-plugin/skills/remotion-{markup,render,captions,saas}/SKILL.md`, `packages/template-prompt-to-motion-graphics/README.md`, archivos de skills `messaging.md`, `sequencing.md` y documentos oficiales `render-media.mdx`, `staticfile.mdx`, `audio/volume.mdx`, `ai/codex-plugin.mdx`.
- AutoEditor comparado: https://github.com/otiagoo44/auto-editor-dentflow, `main` en `35e139138e8686c5551bcd1698e706697f5703b3`, y auditoría previa proporcionada por el usuario. Releer HEAD antes de implementar porque puede cambiar.

## Dictamen por subsistema (diseñado específicamente para DentFlow)
| Componente | Qué permite | Uso en DentFlow | Riesgo o restricción |
|---|---|---|---|
| `remotion` / core | `<Composition>`, `<Sequence>`, `useCurrentFrame`, `interpolate`, `spring`, `calculateMetadata` | Composiciones verticales parametrizadas en React para escenas CRM, hooks, tarjetas, CTA | Animaciones reproducibles por fotograma; no usar CSS transitions asíncronas |
| `@remotion/renderer` + `@remotion/bundler` | Render programático Node con `selectComposition()` y `renderMedia()`; bundling | Fase posterior para integración de proceso Python↔Node, sin servicios remotos | Requiere Node, navegador/render local, almacenamiento y RAM; al principio preferir CLI `--props` por menor superficie |
| `@remotion/cli` | Render desde proyecto y JSON props | `--engine remotion` invoca CLI en subprocess con argumentos, ruta de props JSON y código de salida | No interpolar cadenas en shell; en Windows `--props` con ruta de archivo, no JSON inline |
| `@remotion/media` | Video/audio sobre composición; recomendado en docs actuales para nuevo código | Incorporar A-roll cortado con voz y banda sonora opcional | Probar codec H.264/AAC de mezzanine; usar `OffthreadVideo` como alternativa documentada si hay incompatibilidad |
| `@remotion/captions` | Transformación de palabras a captions y páginas | Usar palabras YA reconocidas por faster-whisper y remapeadas por Python | NO duplicar ASR en Node ni quemar ASS y subtítulos React simultáneamente |
| `@remotion/transitions` | `TransitionSeries`, fade, slide, overlay y timings | Cambios de escenas del **modo comercial**; fade discreto para overlays del modo educativo | Cada transición debe tener finalidad, no un efecto cada X segundos; algunas transiciones alteran duración total |
| `@remotion/sfx` | Biblioteca de efectos de sonido | Uno o dos acentos opcionales autorizados en apariciones de UI | No obligatorios ni sonoros en cada corte; música de terceros requiere licencia propia |
| `@remotion/shapes`, motion-blur, Lottie, Three | Gráficos y efectos | Etapas, flechas, resaltados, máscaras, animación de UI propia | Motion blur/3D solo si mejora una escena y rinde bien en la PC; evitar sobreingeniería |
| `@remotion/player` y Studio | Preview navegable/editable | Futuro visor si el lote justifica una interfaz | V2.1 puede funcionar sin GUI; `remotion studio` es suficiente para desarrollo de plantillas |
| `packages/template-overlay` | Ejemplo básico de tarjeta que entra con spring y sale | Referencia conceptual de un overlay parametrizable | Es demostración, no biblioteca final; adaptar marca, safe zones y timings |
| `packages/template-prompt-to-motion-graphics` | Pipeline prompt→skill→generación→sanitización→preview | Inspiración para separar **planificación editorial** de **render determinista** | Tiene SDK/API de OpenAI y Next.js/Lambda; no copiar a runtime sin querer cargos ni complejidad |
| `packages/template-prompt-to-video` | Ejemplo de historia generada con IA | Solo estudiar representación de timeline con texto y audio | Depende de API OpenAI/ElevenLabs: no adecuado para el objetivo de producción local barata |
| Remotion Codex plugin/skills | Guías de composición, render y edición | Que Codex construya una vez las plantillas, revise e itere sobre renders con Watch | Instalar plugin en Codex no añade Remotion automáticamente a `editor.py` ni comparte instalación con este chat |
| Lambda, Cloudrun, Vercel, render-server/Starter | Rendering distribuido y herramientas para terceros | No necesario para 5 Reels/semana en PC personal | Coste, licencias y complejidad si luego se ofrece el editor a clínicas |

**Paquetes:** fijar versiones iguales de `remotion` y todos `@remotion/*`, inicialmente las que Codex verifique en npm y plugin; `4.0.530` es versión OBSERVADA en el checkout inspeccionado. No clonar el monorepo de ~16k entradas dentro de AutoEditor ni ejecutar su `bun install`/test global; iniciar paquete pequeño `remotion/` con dependencias npm propias.

**Licencia:** Remotion es **source-available, NO open source OSI**. La FAQ oficial permite gratis a individuos y organizaciones de hasta tres personas, incluso uso comercial y automatizado, bajo sus condiciones. Si el equipo crece, si otros clientes operan el código o si el autoeditor se comercializa como software, revisar licencia y recuento aplicable. Ver https://www.remotion.dev/docs/license/faq y https://github.com/remotion-dev/remotion/blob/main/LICENSE.md. La licencia de Remotion no concede automáticamente derechos sobre música, logos, fotos o vídeos de terceros.

## Auditoría del MP4 que adjuntaste y que produjo el plugin
Archivo: `DentFlow_Comercial_Reel_1080x1920(1).mp4`; he extraído 28 fotogramas, uno por segundo; adjunto dos hojas de contacto visual. Es un **video comercial gráfico**, no una prueba del flujo de montaje con fundador a cámara. Los cuadros observados son evidencia visual; no he revisado auditivamente la pista completa.
- Metadatos medidos: duración 28.000 s, 1080 × 1920, 30 fps, H.264/yuv420p, audio AAC mono a 44.1 kHz, ~6.6 MB. Pista de audio existe. FFmpeg `volumedetect`: media -23.2 dBFS y máximo -4.4 dBFS; esas cifras no son LUFS ni prueban la licencia/mezcla de música.
- 00–04 s: pregunta «Llegan consultas. ¿Y después?»; tarjetas de entradas WhatsApp, Instagram y web aparecen progresivamente. Hook directo y animación secuencial.
- 04–08 s: problema «Una consulta no se gestiona sola» con lista de tres pasos que aparece por etapas; fondo claro alterna con oscuro y conserva tipografía/colores.
- 08–12 s: «De mensajes sueltos a un proceso claro» y pantalla demostrativa ficticia de pendientes con filas `Lead 07`/`Lead 08`. Conservar rótulo de demo; nunca mostrarla como captura demostrada del producto si no coincide.
- 12–16 s: siguiente paso con ficha `Lead 07`, estado pendiente y responsable/acción; mensaje visual vinculado con el beneficio concreto.
- 16–20 s: «Todo claro. En un solo lugar» con tres tarjetas de consultas, prioridades y próximas acciones.
- 20–24 s: «Tu recepción sabe qué sigue hoy» y lista breve de tareas.
- 24–28 s: logo, lema «Cada consulta. Una próxima acción» y botón «SOLICITÁ UNA DEMO»; bloque de texto final pequeño que requiere test móvil.
- Identidad visual observada (aproximada, extraída de cuadros comprimidos; NO manual oficial de marca): azul marino muy oscuro ~`#071629`, azules secundarios, blanco y celeste grisáceo. Predomina presentación limpia con jerarquía visual, márgenes consistentes y entradas escalonadas, no 3D complejo.

### Lo que sí conviene reutilizar
1. Las seis estructuras escénicas como plantilla **comercial parametrizable**: múltiples canales→problema→pipeline→acción→control→CTA.
2. Animaciones por elementos separados y **datos**, no movimiento de captura horizontal entera; el video ya muestra cuánto más claro puede ser un panel dibujado con React que un flyer 16:9 encogido.
3. Persistencia de colores, espacio negativo y títulos cortos, con fondos oscuros/claros para separar etapas.
4. Apoyos explicativos sobre **video educativo con fundador a cámara**: tarjetas puntuales sobre una frase, zoom de control UI y regreso a cámara. No convertir todos los Reels educativos en un comercial de pantalla completa.

### Limitaciones del ejemplo
- No hay rostro/grabación de fundador: no demuestra calidad de cortes de voz, errores de toma, encuadre de cara, ni sincronización de una grabación espontánea.
- No se puede recuperar React fuente, assets originales ni curvas exactas de easing de un MP4 renderizado. Para reutilización fiable, reconstruir seis componentes originales a partir de guiones y datos permitidos.
- Contiene interfaces **ilustrativas**, no capturas verificadas. Ajustar nombre, URL, formulario y estados a DentFlow real antes de publicar; **no** inventar funciones, ventas ni testimonios.
- No he auditado por escucha la banda sonora, ritmo percibido ni ducking. Que exista AAC no equivale a un master aprobado.
- En pantalla pequeña, subtextos y controles del mockup deben contrastarse a tamaño de teléfono. Las seis capturas en la hoja de contacto no reemplazan la prueba móvil.

## Referentes: transferencia que sí respalda el estudio previo
- **Nik Setting:** el CSV histórico observó una tablet como soporte del discurso, con acercamientos al diagrama durante la explicación y vuelta al expositor; no demostró que todos fueran zooms digitales. Transferencia: diagramas de DentFlow vinculados a frases y regreso a cámara para interpretación.
- **Alex Hormozi:** dos ejemplos muestran cambio entre ángulos/interlocutores en el desarrollo de argumentos; no es correcto inventar automáticamente una «segunda cámara» desde una sola toma. Transferencia: subtítulos legibles, cambios de encuadre sutiles y estructura de contraste cuando el guion lo pide.
- **Ramiro Cubría:** títulos iniciales legibles, apoyos gráficos introducidos con un ejemplo y cierre con acción. No imponer su cadencia de flashes a videos educativos B2B.
- **Tomi Buschiazzo:** se inspeccionó visualmente un video largo, que NO equivale a un Reel. Su progresión narrativa es inspiración editorial, no una tabla de intervalos de edición.
- **Marcos Razzetti:** R07/R08 no accesibles en el CSV: no atribuirle una fórmula visual sin MP4 y observación real.
- **Tutoriales:** ocho con muestras visuales y dos solo transcript. No reutilizar imágenes, música ni branding de terceros. Watch puede completar faltantes cuando existan clips, pero **no bloquear** los primeros Reels por ello.

## Decisión técnica
El AutoEditor actual ya hace transcripción, cortes prudentes, remapeo temporal, ASS, assets estáticos, zoom y renders FFmpeg. **Remotion no corrige por sí mismo selección semántica de assets, errores ASR ni cortes de sílabas.** Añade principalmente componentes React animados reutilizables, diagramas/UI legibles, diseños gráficos, composición multicapa y potencial mezcla audiovisual de proyectos completos. Su valor principal en DentFlow será un catálogo de plantillas **parametrizadas y repetibles**, no generar React arbitrario mediante un LLM en cada exportación.
