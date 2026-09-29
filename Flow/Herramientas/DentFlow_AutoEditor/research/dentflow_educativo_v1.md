# DentFlow educativo v1 — guía audiovisual original

Esta guía convierte evidencia parcial en decisiones configurables. Es una propuesta editorial para un fundador que explica sistemas a dueños de clínicas; no es un estilo de ningún referente ni una fórmula de retención. Las referencias respaldan funciones concretas del montaje, no los valores numéricos iniciales de abajo.

## Unidad narrativa

Una pieza responde una pregunta operativa: qué problema existe, cómo se reconoce, qué paso del sistema lo resuelve y qué decisión sigue perteneciendo a la clínica. Abrir con la situación específica y una promesa demostrable en esa pieza. Mostrar un caso ficticio claramente marcado o material propio autorizado. Terminar con una conclusión utilizable y, si corresponde, una única acción siguiente.

Ejemplo ORIGINAL: una consulta entra, queda pendiente, alguien revisa disponibilidad y confirma un turno. La pantalla debe probar el cambio de estado que se menciona. Un contador de mensajes o una captura de agenda no prueba aumento de ventas. No convertir una demostración de producto en garantía comercial.

## Cuándo intervenir

| Recurso | Disparador y finalidad | Aplicación inicial | Prueba de calidad / cuándo omitir |
|---|---|---|---|
| Corte de voz | Repetición, error de toma o tiempo muerto confirmado; recuperar continuidad de la idea | Primero señalar candidato; conservar respiración y remate. Referencia: T01 04:18–04:54 frente a T02 01:22–01:36 | Escuchar palabra anterior y posterior. No cortar negación, cifra, gesto ni pausa durante la lectura de una pantalla |
| Cambio fundador→demo | Se nombra una acción o dato que puede verse | Entrar cuando se identifica el objeto y mantener hasta observar su estado final. R01 00:32–00:34; R09 11:12–11:14; T05 08:42–08:51 | Un espectador puede señalar qué cambió. Si el apoyo sólo repite una palabra, omitirlo |
| Regreso a cámara | Termina la prueba y comienza interpretación, límite o acción siguiente | Volver después de permitir leer el resultado; no imponer vuelta entre todas las imágenes | La voz no menciona todavía detalles de una pantalla ya retirada. R02 00:32–00:34 muestra una vuelta vinculada a síntesis, con movimiento de cámara |
| Reencuadre/punch-in | Hay un énfasis concreto y sobra resolución | Cambio estático discreto, solicitado con reason; probar inicialmente 1.05–1.10. No afirmar segunda cámara | Ojos/manos permanecen dentro; no amplificar compresión. R03 00:44.5–00:45 es otro ángulo, no evidencia de zoom digital. No hay cadencia automática |
| Zoom animado | Ayuda a localizar un control pequeño en una demo | Pendiente de V2: conservar contexto, centro de interés estable, detenerse antes de leer; candidato ease-in-out suave | Si no mejora localizar/leer frente a corte directo, quitar. T07 06:20–06:30 enseña control de velocidad; no determina una curva para todas las interfaces |
| Overlay de esquema | Una relación es más fácil de comprender espacialmente | Una sola idea o etapa, creada con texto/datos propios. Distinguir diagnóstico, acción y resultado | El esquema añade relación causal o secuencia; no es decoración. R02 00:15–00:17 y T08 01:00–01:59 |
| Prueba / captura | Una afirmación depende de un estado visible | Mostrar contexto suficiente, fecha/periodo cuando aplique, anonimizar datos de pacientes; no inventar cifras | Captura legible y congruente con la voz. R05 01:10 y R09 11:14 muestran evidencia presentada por autores, sin validación independiente |
| Subtítulo | La voz aporta información indispensable | Frases comprensibles, máximo dos líneas, puntuación natural, texto estable; no copiar palabra-a-palabra por obligación | Entender sin audio; revisar nombres, cantidades y negaciones. No tapar control/resultado. T05 17:29–17:36; R06 00:16 y R03 00:45 |
| Transición gráfica | Cambia una relación espacial o etapa que necesita continuidad | Corte directo por defecto; fade breve para una tarjeta estática. Transición compleja sólo con función explícita | No usar destello para ocultar que una demostración no existe. R05 00:16 y R09 00:05 son flashes observados, no una cuota a imitar |
| Cambio de energía | Pasar de problema a explicación, de prueba a conclusión | Variar densidad de información y dejar respirar el resultado; conservar expresividad del fundador | No confundir velocidad, volumen y cantidad de efectos. Contraste R05 00:00–00:16 con R06 00:00–00:16; T03 04:26–04:43 |

## Valores iniciales, todos revisables

- 1080×1920 a 30 FPS; preview 360×640. contain por defecto para conservar diagramas/pantallas; cover centrado sólo tras comprobar composición. Los Reels horizontales estudiados R01/R02/R05 no justifican recortarlos automáticamente a vertical.
- Subtítulos Arial 58 px a 1080 de ancho, blanco y contorno oscuro de 3 px; margen inferior 260 px, laterales 80 px. Máximo 26 caracteres por línea y dos líneas. Son hipótesis de legibilidad para probar en teléfono, no valores deducidos de retención.
- Agrupar por puntuación, pausa de 0.55 s y duración máxima orientativa de 4 s. Avisar si supera 22 caracteres/s; revisar la frase o grabación en lugar de acelerar lectura. Permitir que desaparezca texto durante pausas: la sugerencia del autor de T05 17:20–17:27 de rellenar huecos no se adopta como automatismo.
- Candidato de corte sólo si hueco entre palabras ≥1.2 s, dejando 0.30 s después y 0.20 s antes. La V1 no aplica la propuesta sin keep_segments explícitos. Conservar íntegros los ejemplos que necesiten tiempo de lectura.
- Tarjeta dentro del 88% del ancho y 52% del alto, desde 12% del alto; full para una demo que requiera más espacio. No fija su duración: se define según explicación/lectura. Entrada/salida por fade de hasta 0.12 s, acortada para eventos breves.
- Voz principal con objetivo inicial -16 LUFS, pico objetivo -1.5 dBTP en normalizador; verificar resultado. Sin música por defecto. Nada del audio o identidad visual de terceros se reutiliza.
- Sin frecuencia de cortes, cuota de overlays, zoom cada N segundos ni máximo arbitrario de segundos sin efecto. La razón de cada intervención debe quedar escrita.

## Revisión de una pieza

1. Ver el montaje sin overlays: se entiende la tesis y no se perdió información necesaria.
2. Escuchar uniones y revisar texto contra voz. ASR base cometió errores con TAM, nombres y CTA en R01/R05/R06; su transcripción no es aprobación editorial.
3. Ver sin sonido en pantalla de teléfono: promesa, procedimiento y conclusión comprensibles; subtítulos lejos de controles de la plataforma y del producto.
4. Pausar cada demo: identificar entrada, acción y cambio de estado. Aumentar duración o recortar una región sólo si hace falta; nunca acelerar el sistema para simular un resultado.
5. Quitar cada efecto en una comparación A/B interna. Conservarlo sólo si aclara dónde mirar, qué cambió o por qué importa.
6. Revisar la pieza completa a velocidad normal antes de publicar. El render técnico exitoso no valida el argumento, naturalidad de los cortes o rendimiento comercial.

## Operación para cinco Reels semanales

Definir cinco preguntas reales de clínicas, grabar por bloques y capturar las demostraciones propias. Crear un plan por pieza, revisar subtítulos y aprobar sólo las intervenciones útiles. Renderizar secuencialmente; acumular correcciones reutilizables en configuración, nunca convertirlas en reglas rígidas para cada frase.

Registrar tiempo de preparación, revisión, render, errores de texto y claridad percibida por dueños de clínicas. Después de varias semanas, comparar dentro de un formato/objetivo similar, incluyendo ausencia de efectos. Dos videos por creador no permiten inferir causalidad ni asegurar retención. La V2 podrá acelerar tareas repetidas una vez que esa revisión identifique dónde se pierde tiempo.

