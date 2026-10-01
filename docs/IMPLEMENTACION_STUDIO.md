# DentFlow Studio V3 — estado para publicación manual

El editor web y el agente Windows están implementados. La publicación en Vercel queda a cargo del propietario, según su instrucción. La web requiere una base Postgres, Vercel Blob privado y el agente de esta PC conectado a la URL de producción. Los pasos exactos están en `web/README.md`.

## Alcance entregado

- Checkpoint inicial de los 55 cambios anteriores: `ea030e7`, conservado y publicado en la rama de trabajo antes de continuar.
- Seed V3 original incorporado: R01–R18 y A1–A3, con guiones, hooks, captions, CTA, planes visuales y compuertas D1–D4. La importación es idempotente, mantiene originales y versiones editadas. El Reel 1 legado sigue separado.
- Interfaz de contenido, creación libre, carga de medios, borradores, corrección de palabras, versiones, final, descarga, biblioteca, historial, borrado y publicación manual.
- API con autenticación de propietario y agente, enlaces de medios firmados, límites de subida/renders, almacenamiento local o Blob privado, cola persistente, leases, heartbeat y operaciones de finalización transaccionales.
- Agente saliente Windows que reutiliza fuente y render verificados tras reinicio, comprueba SHA, reintenta errores transitorios y mantiene diagnóstico local. Un trabajo por vez; la PC debe permanecer encendida.
- Archivos privados de preparación para Vercel generados en `%LOCALAPPDATA%\DentFlow\studio`, fuera de Git. No contienen credenciales de Postgres ni de Blob hasta que el propietario conecte esos recursos en Vercel.

## Validación realizada en esta PC

- Web: 13 pruebas unitarias/integración pasadas, TypeScript sin errores, build optimizado de Next.js aprobado, `npm audit` con 0 vulnerabilidades al instalar. La versión compilada respondió en `127.0.0.1:3000` y cargó los 21 contenidos originales.
- Motor: suite completa de 49 pruebas pasada (1 omisión por muestra ASR no provista); prueba ASR offline con muestra existente ejecutada aparte y pasada. La prueba de integridad de descarga y repetición de finalización del agente también pasó.
- E2E HTTP local: subida real, SHA, solicitud idempotente, transcripción sin red, borrador 360×640, dos correcciones, nueva versión, final 1080×1920, tres SHA distintos, descarga/decodificación íntegra y rango HTTP 206. Evidencia en `%LOCALAPPDATA%\DentFlow\validacion_v3\e2e_65f5775a-d2be-48b8-a5c8-b3a56a92dde4\evidence.json`.
- Revisión visual: biblioteca V3 y editor navegados en Chrome en escritorio y ancho estrecho; cuadro del final sintético revisado en 0, 3, 6 y 9 segundos. El material de prueba muestra una placa sintética, no una filmación de iPhone.
- Un render inicial falló porque Chromium de Remotion agotó sus 25 segundos de arranque mientras Windows tenía poca memoria libre. El reintento del mismo trabajo terminó bien; el E2E posterior completó tres renders seguidos. Se conserva el diagnóstico en la carpeta local del agente.

## Validación pendiente al publicar

- Conectar Postgres y Blob privado, importar las variables privadas, publicar desde GitHub y conectar el agente a la URL de producción. No hubo acceso a ese equipo de Vercel en esta sesión, por lo que el flujo remoto aún no está probado.
- Repetir en producción el recorrido de `web/README.md`, incluyendo acceso no autenticado, conexión del agente, subida, preview, corrección, final y descarga.
- Revisar con sonido y en teléfono dos tomas iPhone reales para aceptar voz, color, subtítulos, zonas seguras y calidad editorial. Esas tomas no están en el repositorio.

No declarar una demo D1–D4 ni una propuesta visual como aprobada sin la evidencia editorial correspondiente. El sistema permite un montaje básico de cámara y subtítulos cuando falta esa aprobación.
