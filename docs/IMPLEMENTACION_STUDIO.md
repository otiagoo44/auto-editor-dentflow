# DentFlow Studio V3 — checkpoint de implementación

## Base y alcance

- 2026-09-30: rama `feat/dentflow-studio-web`, desde `55e1629` (`origin/v2.1-remotion`). Fetch realizado; main conservada. Los únicos cambios iniciales eran los tres informes nuevos sin seguimiento.
- Windows, Python del entorno `%LOCALAPPDATA%/DentFlow/venv`, Node 24.15.0, motores existentes.
- Leídos auditoría 01, arquitectura 02 y mega-prompt 03. Este último gobierna el trabajo. No se publican servicios ni se contratan recursos.
- No encontrado `SEED_CONTENIDO_V3_18_REELS_3_ALTERNATIVAS.json`. Solicitado al usuario. El Reel 1 legado permanece independiente; ninguna demo equivale a R01.
- Faltan dos tomas iPhone reales y credenciales/configuración de staging remoto. No se declara aceptación editorial ni E2E remoto.

## Fases

- [ ] Fase 0: suite completa Windows, diagnóstico, renders sintéticos y QA visual.
- [ ] Fase 1: upload → worker → preview → corrección → final en Studio local.
- [ ] Fase 2: propuestas editoriales deterministas, biblioteca, versiones, publicación manual.
- [ ] Fase 3: adaptadores remotos, protección, pruebas de acceso; despliegue requiere configuración autorizada.

## Cambios iniciales

Contrato captions exclusivo por motor, unión de pausas cortas para música y rampas suaves; Chromium admite ruta explícita y comprueba ejecución sin descargar. CI incorpora V2.

## Evidencia

Regresión en ejecución: `%LOCALAPPDATA%/DentFlow/validacion_v3/baseline.log`.
Actualizar con resultados observados antes de cerrar cada fase.
