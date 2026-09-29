# Investigación real con Watch para DentFlow

## Estado actualizado 29-09-2026

El texto histórico de abajo describe la preparación anterior, no el estado actual.
El estudio posterior ya existe en [evidencia.csv](../Flow/Herramientas/DentFlow_AutoEditor/research/evidencia.csv)
y [guía](../Flow/Herramientas/DentFlow_AutoEditor/research/dentflow_educativo_v1.md).
Los estados PENDING/NOT_WATCHED del JSON original se conservan como procedencia de
la selección, no como inventario vigente. CSV canónico: 7 referentes y 8 tutoriales
con muestras visuales; T04/T10 sólo transcript; R07/R08/R10 NO_ACCESIBLE.

En esta nueva PC Watch está disponible y operativo, local, sin backend de nube.
Se reobservaron R01 4/4.5/5/5.5 s y R05 69/70/71 s. R07/R08 dieron empty media
response en un intento cada uno; R10 no tiene MP4 verificable. No hay MP4 en esta
carpeta: contiene enlaces y documentos. La instrucción histórica de no programar
en 02_PROMPT queda superada por la petición actual de implementar V2.

**Alcance verificado ahora:** lista de 10 tutoriales con URLs identificadas; 8 nuevos Reels específicos de cuatro creadores desde los metadatos previamente extraídos con Apify; un video largo de Tomi y una VSL anunciada en página propia (video no descargado ni validado). Documentación técnica de Watch examinada. **No se realizó inspección visual en esta sesión:** instalar la skill en Codex no la instala en este chat; aquí no hay acceso de red para ejecutar la versión local sobre las URLs remotas.

Pasos: 1) Abrí proyecto Flow en Codex. 2) Verificá skill `watch`; 3) copiá carpeta a `Flow/Herramientas/DentFlow_AutoEditor/research_input` o indicá la ruta en el prompt; 4) pegá el archivo `02_PROMPT...`; 5) ejecutá investigación; 6) inspeccioná los resultados antes del megaprompt definitivo para programar.

IMPORTANTE: Para Tomi no se pudo verificar el segundo MP4 exacto. R09 es un YouTube identificado públicamente, R10 es página VSL. No afirmar que ambos fueron observados hasta tener frames.
