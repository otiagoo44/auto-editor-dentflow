# Worker de DentFlow Studio

El agente usa una conexión **saliente** hacia Studio y procesa un video a la vez con Python, Whisper offline, FFmpeg y Remotion. No abre puertos de tu casa. La PC debe permanecer encendida, conectada y sin suspensión mientras edita.

## En esta PC

- `worker\install-worker.bat`: instala/verifica los motores y la web con los instaladores existentes.
- `iniciar_studio.bat`: abre web y worker locales juntos.
- `worker\start-worker.bat`: solo worker local, si la web ya está abierta.
- `preparar_vercel.bat`: prepara secretos privados para tu despliegue, sin contratar ni publicar nada.
- `conectar_worker_vercel.bat`: vincula la URL de producción y verifica autenticación/capacidades.
- `worker\start-remote-worker.bat`: conecta el agente con Vercel. Dejá su ventana abierta; Ctrl+C lo detiene y el trabajo se podrá retomar cuando venza el lease.

Las instrucciones del panel de Vercel están en [web/README.md](../web/README.md).

## Archivos privados

En `%LOCALAPPDATA%\DentFlow\studio`:

- `worker.local.json`: URL loopback y token local.
- `worker.remote.json`: URL HTTPS, token remoto, ID del equipo y carpeta aislada. Opcionalmente `bypass` si Vercel exige Deployment Protection.
- `vercel.env`: variables para importar en el panel y contraseña del propietario. Nunca compartir ni commitear.

El worker remoto conserva intentos en `%LOCALAPPDATA%\DentFlow\studio-worker-remote`. Cada carpeta de job guarda diagnóstico y datos descargados; los secretos de lease no se escriben ahí. No confundas el token del agente con `OWNER_PASSWORD`: tienen permisos diferentes.

## Diagnóstico

```powershell
& "$env:LOCALAPPDATA/DentFlow/venv/Scripts/python.exe" worker/agent.py --config "$env:LOCALAPPDATA/DentFlow/studio/worker.remote.json" --check
```

Tiene que informar servidor listo, FFmpeg, Whisper offline y Remotion disponibles. Para un render fallido, revisar `engine.log` dentro de su carpeta local; la web solo muestra un error saneado. `engine_unavailable` requiere instalar el motor o seleccionar Básico FFmpeg. `invalid_media` indica formato, duración, integridad o ausencia de video válidos. Un timeout no se presenta como éxito.

El lease dura 120 segundos y se renueva cada 10. Un agente que pierde contacto durante más de 60 segundos detiene el proceso; otro intento puede recuperar la fuente y la salida verificada del mismo job. Las descargas incompletas nunca se reutilizan como originales válidos. La finalización es transaccional e idempotente.

Valores opcionales en `worker.remote.json`: `timeout` (3600 segundos por intento), `max_duration` (600 segundos de fuente), `state_dir`, `worker_id`. Mantené `max_duration` alineado con `MAX_DURATION_SECONDS` del servidor. Se requieren espacio libre y los modelos/navegador ya instalados; el render no instala herramientas ni usa una API de IA de pago.
