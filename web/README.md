# DentFlow Studio Web

Web privada para subir una grabación, generar un borrador, corregir subtítulos y descargar el final 1080×1920. Usa el motor Python/FFmpeg/Remotion del repositorio y Whisper local. Las 18 fichas V3 y 3 alternativas se importan automáticamente sin reemplazar versiones editadas. El guion legado sigue separado.

## Publicar desde el panel de Vercel

La interfaz se publica desde GitHub. La edición necesita además **Postgres, Blob privado y esta PC encendida**. No alcanza con desplegar la página para ejecutar FFmpeg.

1. En esta PC, ejecutá `preparar_vercel.bat`. Genera `%LOCALAPPDATA%\DentFlow\studio\vercel.env` y la configuración del worker. No muestra contraseñas ni las guarda en Git. Si lo repetís, conserva las existentes.
2. En Vercel, **Add New → Project → Import** `otiagoo44/auto-editor-dentflow`, rama **main**. Elegí **Root Directory = web**, framework **Next.js**, Node.js **24.x**. Instalación y build ya están en `web/vercel.json`.
3. En **Environment Variables**, importá el archivo privado `vercel.env` para Production. Para Preview, configurá también las variables y recursos de ese entorno. Nunca uses prefijos `NEXT_PUBLIC_` para secretos.
4. En **Storage / Marketplace**, conectá una base **Neon/Postgres** dedicada a Studio. Tiene que quedar disponible `DATABASE_URL` (cadena de conexión del proveedor, con SSL cuando corresponda). Las tablas y los índices se crean de forma idempotente al primer acceso; no necesitás pegar SQL.
5. Creá un almacén **Vercel Blob de acceso Private**, conectalo a este proyecto y comprobá que exista `BLOB_READ_WRITE_TOKEN`. Esta versión usa el token del almacén para autorizar cargas directas temporales; no funciona con un bucket público ni solo con `BLOB_STORE_ID`.
6. Publicá/redeployá cuando estén todas las variables. Abrí la URL estable de producción: usuario **owner** y la contraseña `OWNER_PASSWORD` del archivo privado. El navegador pide esas credenciales; también están protegidas API, descargas y medios.
7. Ejecutá `conectar_worker_vercel.bat`, pegá la URL de producción y esperá el diagnóstico. Luego abrí `worker\start-remote-worker.bat`. Studio debe mostrar **Equipo conectado** y las capacidades disponibles en Ajustes.
8. Elegí un contenido o **Nuevo Reel**, subí tu raw, generá borrador, revisá/corregí subtítulos y generá final. Descargá el MP4 y reproducilo completo antes de marcarlo revisado.

Si tenés que crear el proyecto antes de conectar Storage, el primer despliegue puede compilar y negar el acceso hasta completar las variables: es intencional. Después de conectar los recursos, hacé **Redeploy**. No hay que volver a cargar los guiones.

### Protección adicional de Vercel

La aplicación tiene autenticación de propietario propia. Si además habilitaste Vercel Deployment Protection para la URL que usa el agente, creá un **Automation Bypass Secret** en la configuración de protección de Vercel y guardalo en el campo `bypass` de `%LOCALAPPDATA%\DentFlow\studio\worker.remote.json`. Ese valor queda solo en la PC; nunca en el navegador o Git. No desactives protecciones para solucionar un 401. Usá la URL estable de producción, no una preview temporal.

### Variables requeridas

| Variable | Procedencia |
| --- | --- |
| `STUDIO_MODE=REMOTE_STUDIO` | Archivo generado |
| `OWNER_USER`, `OWNER_PASSWORD` | Archivo generado; contraseña de al menos 32 caracteres |
| `WORKER_TOKEN` | Archivo generado; debe coincidir con `worker.remote.json` |
| `MEDIA_SIGNING_SECRET` | Archivo generado; firma descargas por 15 minutos |
| `DATABASE_URL` | Integración Postgres/Neon |
| `BLOB_READ_WRITE_TOKEN` | Almacén Blob privado |
| `APP_DISPLAY_NAME` | Opcional; DentFlow Studio por defecto |
| `MAX_UPLOAD_MB`, `MAX_DURATION_SECONDS`, `MAX_RENDERS_PER_DAY` | Opcionales; 1024 MB, 600 s y 50 renders diarios |

El worker remoto no necesita credenciales de Postgres ni el token completo de Blob. Obtiene un token de subida por archivo, con tamaño y caducidad limitados. Las cargas de video van directamente a Blob y no al body de una Function. Descargas y reproducción pasan por una ruta autenticada con streaming y soporte de rangos.

Verificá los planes y costes de los proveedores antes de contratarlos: Vercel reserva Hobby al uso personal/no comercial. Esta preparación no contrató servicios. Referencias: [subidas directas](https://vercel.com/docs/vercel-blob/client-upload), [Blob privado](https://vercel.com/docs/vercel-blob/private-storage), [límites de Functions](https://vercel.com/docs/functions/limitations), [plan Hobby](https://vercel.com/docs/plans/hobby).

## Uso y desarrollo local

`instalar_studio.bat` prepara la web; `iniciar_studio.bat` abre `http://127.0.0.1:3000` con worker local. No hay login local. Servidor y worker se detienen con Ctrl+C en la ventana del lanzador. Los datos viven en `%LOCALAPPDATA%\DentFlow\studio`, fuera de Git. No uses `STUDIO_MODE=LOCAL_STUDIO` en una web pública.

```powershell
cd web
npm ci
npm test
npm run typecheck
npm run build
npm run dev
```

Para migración explícita, cargá el entorno remoto de forma segura y ejecutá `npm run migrate`. El comando no carga `.env.local` por sí mismo; Next.js sí lo hace. La CI prueba una base Postgres 17 descartable mediante `npm run test:postgres`.

## Persistencia, borrado y recuperación

- Cada render tiene un ID y una versión inmutables. El preview no sobrescribe el final. Las correcciones se vinculan al SHA de la grabación.
- Mis Reels permite borrar un proyecto detenido y sus resultados; conserva guion y grabación. Biblioteca permite borrar un recurso cuando ya no lo usa ningún proyecto. Un fallo de red conserva metadata para reintentar el borrado.
- `POST /api/maintenance`, autenticado como propietario, elimina subidas abandonadas hace más de 24 horas. Los originales completos no caducan silenciosamente.
- El worker reintenta errores transitorios, renueva su lease, recupera un resultado verificado tras reiniciarse y rechaza leases vencidos. Los temporales de trabajos completados caducan a los siete días en la PC. Los fallidos se conservan para diagnóstico.
- Si la PC está apagada, se conserva la cola. Un render no se ejecuta dentro de Vercel.
- Los gráficos son propuestas explícitas: deben aprobarse y coincidir con una frase o un tiempo fuente. Los controles D1–D4 bloquean demos no verificadas. Una idea libre produce cámara y subtítulos; no inventa un storyboard.

## Comprobar el despliegue

Sin sesión, `/`, `/api/content`, `/api/assets` y `/api/outputs/...` deben negar acceso. Con propietario: ver 21 contenidos, subir un video sintético, observar fases reales, descargar un preview 360×640 y un final 1080×1920 distintos y reproducibles. Apagá el worker y verificá que el siguiente trabajo quede en cola; al reiniciarlo debe continuar. Hasta pasar este recorrido, el despliegue remoto **no está validado como editor**.

El estado y la evidencia de esta sesión están en [IMPLEMENTACION_STUDIO](../docs/IMPLEMENTACION_STUDIO.md). La aceptación audiovisual con dos tomas iPhone reales sigue siendo una revisión del propietario.
