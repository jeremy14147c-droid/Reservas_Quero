# ESTADO ACTUAL – léelo primero (actualizado el 19/11/2026)

Archivo para el equipo y el agente. Si algo contradice a otro documento del repo, manda este archivo y luego `AGENTS.md`.

## 1. Dónde estamos
- Hechas: Fases 0, 1, 1.1, 2, 3, **3.1** (buscador y mesa), **3.2** (tiempo en mesa por grupo), **3.0** (higiene Git), **Despliegue D** (Neon y Render en vivo), **Fases S1 + S2 de Seguridad (Semana 14)** (sesión revocable, fuerza bruta, redirect seguro, cabeceras, UUID), y **Fase 3.R (Capa DAO y desacoplamiento)**: 100% del SQL movido a `app/dao/` (`ConfigDAO`, `ClienteDAO`, `PersonalDAO`, `CartaDAO`, `ReservaDAO`, `PedidoDAO`), servicios desacoplados con inyección de DAO, y pruebas unitarias aisladas sin base de datos en `tests/unidad/`. **65 pruebas en verde**.
- Siguiente paso: **Fase 3.3** (Horas pasadas no reservables y vencimiento automático). El detalle y los prompts están en `PROMPTS_POR_FASE.md`.

## 2. Problemas detectados (verificados)
1. [RESUELTO en 3.0] `.venv/` ya no está versionado en Git (se eliminó del índice con `git rm -r --cached .venv`). `.env` no está en el historial (revisado).
2. [RESUELTO en 3.R] `DEFENSA_RUBRICA.md` y `GUION_EXPOSICION.md` actualizados: ahora sí existe la capa DAO por entidad en `app/dao/` y pruebas unitarias con fakes en `tests/unidad/` (sin BD).
3. [RESUELTO] `ahora_local()` y `hoy()` usan `ZoneInfo("America/Lima")` con el paquete `tzdata`. Funciona idéntico en Windows local y servidores en la nube.
4. No se valida que la hora reservada ya haya pasado hoy (se puede reservar a las 12:00 pm a las 4:00 pm). Se corrige en la 3.3.
5. [RESUELTO en 3.R] Cero SQL dentro de rutas: `app/auth/routes.py` y `app/publico/routes.py` usan servicios y DAOs. Cero SQL dentro de servicios.
6. El principio 2.1 de `AGENTS.md` decía que nada se libera solo. Se pidió el vencimiento automático de reservas, así que ahora hay **una excepción explícita** (sección 7). Conviene confirmarla con la dueña.

## 3. Decisiones ya tomadas
- Franja de 30 min. Tiempo en mesa: 1 a 3 personas 30 min, 4 a 7 personas 60 min, 8 o más 90 min (editables en Configuración).
- Imágenes (comprobantes y fotos de platos) se guardan en la base de datos, no en disco. Los comprobantes se borran a los 30 días.
- El comprobante de pago es solo apoyo: el staff verifica en su Yape real y confirma con un botón.
- El atajo "local directo a entregado" quedó descartado por ahora.
- WhatsApp: se usan enlaces `wa.me` (costo cero). La API oficial cuesta por mensaje (ver `WHATSAPP_COSTOS.md`) y queda para el proyecto final.
- El cliente ve una interfaz de restaurante; el staff, una sobria. Las páginas públicas nunca muestran el menú de staff.

## 4. Orden de trabajo
| Fase | Qué | Depende de | Estado |
|---|---|---|---|
| 3.0 | Higiene de Git e integración a `main` | – | Completado en `main` |
| D | Despliegue en Neon y Render | 3.0 | Desplegado y verificado |
| S1-S2 | Seguridad OWASP (login, sesión revocable, cabeceras, UUID) | D | Completado (62 tests en verde) |
| 3.R | Capa DAO real y arranque del TDD | 3.0 | Completado (65 tests en verde) |
| 3.3 | Horas pasadas no reservables y vencimiento automático | 3.R | Siguiente |
| 3.4 | Identidad visual del cliente | 3.3 | Pendiente |
| 3.5 | Carta y pedido en celular (categorías, desplegables, carrito) | 3.4 | Pendiente |
| 3.6 | Cocina: imprimir y recojo primero | 3.5 | Pendiente |
| 3.7 | Pago con comprobante | 3.6 | Pendiente |
| 3.8 | WhatsApp sin costo (mensajes y botones) | 3.7 | Pendiente |
| 3.9 | Imágenes de platos (opcional) | 3.7 | Pendiente |

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
