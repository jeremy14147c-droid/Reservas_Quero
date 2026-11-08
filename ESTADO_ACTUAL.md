# ESTADO ACTUAL – léelo primero (actualizado el 03/11/2026)

Archivo para el agente y para el equipo. Si algo contradice a otro documento del repo, manda este archivo y luego `AGENTS.md`.

## 1. Dónde estamos
- Hechas: Fases 0, 1, 1.1, 2, 3, **3.1** (buscador y mesa) y **3.2** (tiempo en mesa por tamaño de grupo y pizarra clara). 52 pruebas en verde.
- La rama `fase-3-1` (con 3.1 y 3.2) **aún no está integrada a `main`**.
- Siguiente paso: **Fase 3.0** (higiene de Git) y luego **3.R** (capa DAO). El detalle y los prompts están en `PROMPTS_POR_FASE.md`, sección "Fases 3.x".

## 2. Problemas detectados (verificados)
1. `.venv/` está versionado en Git (más de 3.500 archivos) aunque `.gitignore` lo lista. `.env` no está en el historial (revisado).
2. `DEFENSA_RUBRICA.md` y `GUION_EXPOSICION.md` afirman que hay una capa DAO propia y que se trabaja con TDD ("primero el test"). Hoy **no es cierto**: el SQL está dentro de los servicios (`db.py` solo son helpers) y `git log` muestra que las pruebas se escribieron al final de cada fase. La Fase 3.R lo corrige; hasta entonces no se exponen esas frases.
3. `ahora_local()` y `hoy()` usan `datetime.now()` (hora del equipo, no la de Lima). En un servidor en la nube serían 5 horas de diferencia. Se corrige en la 3.3.
4. No se valida que la hora reservada ya haya pasado hoy (se puede reservar a las 12:00 pm a las 4:00 pm). Se corrige en la 3.3.
5. Hay SQL dentro de rutas: `app/auth/routes.py` (3) y `app/publico/routes.py` (3). Se corrige en la 3.R.
6. El principio 2.1 de `AGENTS.md` decía que nada se libera solo. Se pidió el vencimiento automático de reservas, así que ahora hay **una excepción explícita** (sección 7). Conviene confirmarla con la dueña.

## 3. Decisiones ya tomadas
- Franja de 30 min. Tiempo en mesa: 1 a 3 personas 30 min, 4 a 7 personas 60 min, 8 o más 90 min (editables en Configuración).
- Imágenes (comprobantes y fotos de platos) se guardan en la base de datos, no en disco. Los comprobantes se borran a los 30 días.
- El comprobante de pago es solo apoyo: el staff verifica en su Yape real y confirma con un botón.
- El atajo "local directo a entregado" quedó descartado por ahora.
- WhatsApp: se usan enlaces `wa.me` (costo cero). La API oficial cuesta por mensaje (ver `WHATSAPP_COSTOS.md`) y queda para el proyecto final.
- El cliente ve una interfaz de restaurante; el staff, una sobria. Las páginas públicas nunca muestran el menú de staff.

## 4. Orden de trabajo
| Fase | Qué | Depende de |
|---|---|---|
| 3.0 | Higiene de Git e integración a `main` | – |
| 3.R | Capa DAO real y arranque del TDD | 3.0 |
| 3.3 | Horas pasadas no reservables y vencimiento automático | 3.R |
| 3.4 | Identidad visual del cliente | 3.3 |
| 3.5 | Carta y pedido en celular (categorías, desplegables, carrito) | 3.4 |
| 3.6 | Cocina: imprimir y recojo primero | 3.5 |
| 3.7 | Pago con comprobante | 3.6 |
| 3.8 | WhatsApp sin costo (mensajes y botones) | 3.7 |
| 3.9 | Imágenes de platos (opcional) | 3.7 |

La numeración de `FASE_3_1_CAMBIOS.md` queda **reemplazada** por esta.

## 5. Cómo se trabaja (resumen de `AGENTS.md` sección 14)
1. Plan primero, aprobación después.
2. TDD: prueba en rojo (commit `test:`) → código mínimo en verde (`feat:` o `fix:`) → refactor. Mostrar la salida roja y la verde.
3. Una rama por fase; al terminar, integrar a `main`. Nunca versionar `.venv/`, `.env`, `__pycache__/` ni `.vscode/`.
4. Cambios de base de datos: scripts repetibles y numerados en `migraciones/` (la 001 ya existe; las fases 3.3 a 3.9 usan de la 002 a la 006) y el mismo resultado en `schema.sql` cuando el prompt lo autorice.
5. Probar en el navegador y reportar. Los documentos de defensa solo afirman lo que el código y `git log` demuestran.

## 6. Pendiente de decidir (Jeremy)
- Datos del local: WhatsApp, enlace de Google Maps, dirección, redes, logo y colores (la 3.4 no los inventa).
- Si el margen mínimo de anticipación para reservar por la web es 30 min (valor por defecto editable) o 0.
- Confirmar con la dueña el vencimiento automático (pendientes vencidas → rechazadas; confirmadas sin "Llegó" → no llegó automático): puede inflar las estadísticas de "no llegó" si el staff olvida marcar la llegada.
- Dónde se publica (hosting gratuito o de pago).
- Si hay fotos reales de los platos (decide si se hace la 3.9).

## 7. No hacer
Usar la API de WhatsApp, agregar ORM o frameworks de JavaScript, volver a escribir SQL dentro de servicios o rutas, tocar fases cerradas sin pedirlo, ni inventar datos del local.
