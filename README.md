# DentFlow AutoEditor y Studio Web

Subí una grabación, generá un borrador, corregí subtítulos y descargá el Reel vertical. El montaje usa Python, FFmpeg, Whisper offline y Remotion en tu PC. La web administra contenidos, archivos, cola, versiones y revisión.

## Usar ahora en esta PC

1. Ejecutá `instalar_studio.bat` si todavía no preparaste la web.
2. Abrí `iniciar_studio.bat` y mantené su ventana abierta.
3. En `http://127.0.0.1:3000`, elegí R01–R18, una alternativa o **Nuevo Reel**.
4. Subí el video, generá borrador, revisá/corregí los subtítulos y generá el final.
5. Descargá y reproducí el MP4 completo antes de aprobarlo.

Las 21 fichas V3 se importan automáticamente desde el seed original. Los gráficos propuestos necesitan aprobación; las demos de producto conservan los controles D1–D4. Sin un plan aprobado, el editor mantiene cámara y subtítulos. El Reel 1 legado no se mezcla con R01 V3.

## Publicar en Vercel

[Guía completa del panel y variables](web/README.md) · [Worker de Windows](worker/README.md)

1. Ejecutá `preparar_vercel.bat`: genera un archivo privado de variables y el acceso del propietario fuera de Git.
2. Importá este repositorio en Vercel desde **main**, con **Root Directory: web** y Node.js **24.x**.
3. Importá las variables generadas y conectá **Postgres/Neon** (`DATABASE_URL`) y **Blob privado** (`BLOB_READ_WRITE_TOKEN`). Publicá o hacé Redeploy.
4. Ejecutá `conectar_worker_vercel.bat`, pegá tu URL y abrí `worker\start-remote-worker.bat`.

**Vercel hospeda la web; la PC hace la edición y debe estar encendida.** Importar solamente el repositorio no instala una base de datos ni un almacén privado. No se contrató ningún servicio ni se certificó el E2E remoto. Los pasos restantes del panel están descritos en la guía.

## Instalación nueva y modo CLI

`install.bat` prepara Python, FFmpeg y el modelo offline. `instalar_remotion.bat` añade Node/Remotion/Chromium. `autoeditor.bat`, `editar_reel.bat` y `editar_semana.bat` conservan el flujo por carpetas. La documentación histórica y sus pruebas están en [Historial del motor V2.1](docs/HISTORIAL_MOTOR_V21.md); sus rutas se interpretan desde la raíz del repositorio.

## Validación y límites

[Checkpoint y evidencia de pruebas](docs/IMPLEMENTACION_STUDIO.md). La CI valida el motor, TypeScript, API, Postgres y build web. Los videos, transcripciones, resultados y secretos se guardan fuera de Git.

El final es H.264/AAC, 1080×1920; el preview es 360×640. Cada versión tiene su propio SHA y nunca pisa un final anterior. La calidad editorial con tus dos primeras tomas reales de iPhone requiere revisar voz, piel/HDR, encuadre, cifras, negaciones y subtítulos en teléfono. La publicación en redes es manual.
