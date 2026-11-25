# ESTADO ACTUAL – léelo primero (actualizado el 24/11/2026)

Archivo para el equipo y el agente. Si algo contradice a otro documento del repo, manda este archivo y luego `AGENTS.md`.

## 1. Dónde estamos
- Hechas: Fases 0, 1, 1.1, 2, 3, **3.1** (buscador y mesa), **3.2** (tiempo en mesa por grupo), **3.0** (higiene Git), **Despliegue D** (Neon y Render en vivo), **Fases S1 + S2 de Seguridad (Semana 14)** (sesión revocable, fuerza bruta, redirect seguro, cabeceras, UUID), **Fase 3.R (Capa DAO y desacoplamiento)** (100% del SQL en `app/dao/`), **Fase 3.3 (Horas pasadas y vencimiento automático)**, **Fase 3.4 (Identidad visual del cliente)** y **Fase 3.5 (Carta y pedido en celular)**: chips de categorías con scroll lateral, acordeón por categoría, buscador por nombre o número, tarjetas con +/− y espacio reservado para imagen, barra inferior "Ver pedido", panel (offcanvas) con el carrito guardado en `sessionStorage`, bloque "Complementa tu pedido" (`categoria.es_complemento`, migración `005`), carta pública en acordeón y casilla en Carta Staff. **110 pruebas en verde**.
- Siguiente paso: **Fase 3.6** (Cocina: imprimir y recojo primero). El detalle y los prompts están en `PROMPTS_POR_FASE.md`.

## 2. Problemas detectados (verificados)
1. [RESUELTO en 3.0] `.venv/` ya no está versionado en Git (se eliminó del índice con `git rm -r --cached .venv`). `.env` no está en el historial (revisado).
2. [RESUELTO en 3.R] `DEFENSA_RUBRICA.md` y `GUION_EXPOSICION.md` actualizados: ahora sí existe la capa DAO por entidad en `app/dao/` y pruebas unitarias con fakes en `tests/unidad/` (sin BD).
3. [RESUELTO] `ahora_local()` y `hoy()` usan `ZoneInfo("America/Lima")` con el paquete `tzdata`. Funciona idéntico en Windows local y servidores en la nube.
4. [RESUELTO en 3.3] Se valida que la hora reservada no haya pasado hoy (horas pasadas deshabilitadas y validadas con `anticipacion_min_min` en web y staff).
5. [RESUELTO en 3.R] Cero SQL dentro de rutas: `app/auth/routes.py` y `app/publico/routes.py` usan servicios y DAOs. Cero SQL dentro de servicios.
6. [RESUELTO en 3.3] El vencimiento automático de reservas (`liberar_reservas_vencidas`) cierra pendientes vencidas como rechazadas y confirmadas como no_llego de forma perezosa e idempotente.

## 3. Decisiones ya tomadas
- Franja de 30 min. Tiempo en mesa: 1 a 3 personas 30 min, 4 a 7 personas 60 min, 8 o más 90 min (editables en Configuración).
- Anticipación mínima por defecto: 30 min (editable en Configuración).
- Imágenes (comprobantes y fotos de platos) se guardan en la base de datos, no en disco. Los comprobantes se borran a los 30 días.
- El comprobante de pago es solo apoyo: el staff verifica en su Yape real y confirma con un botón.
- El atajo "local directo a entregado" quedó descartado por ahora.
- WhatsApp: se usan enlaces `wa.me` (costo cero). La API oficial cuesta por mensaje (ver `WHATSAPP_COSTOS.md`) y queda para el proyecto final.
- El cliente ve una interfaz de restaurante; el staff, una sobria. Las páginas públicas nunca muestran el menú de staff.
- Datos reales del local (Fase 3.4): WhatsApp 996908138, Av. Inca Garcilaso de la Vega 54 (Villa María del Triunfo), Google Maps `https://maps.app.goo.gl/rATMHp75PEziVzCQ8`, Facebook `GastrobarPiqueosTragos` e Instagram `quero_gastrobar`. Paleta tomada del logo: rojo `#c8382b`, naranja `#e08a2e`, amarillo `#f2b233`, crema `#faf7f2`, tinta `#1e1b18`.
- Eslogan provisional (hasta que la dueña defina el definitivo): "El sabor del mar y lo criollo, en un solo lugar." Es editable en Administración > Configuración.

## 4. Orden de trabajo
| Fase | Qué | Depende de | Estado |
|---|---|---|---|
| 3.0 | Higiene de Git e integración a `main` | – | Completado en `main` |
| D | Despliegue en Neon y Render | 3.0 | Desplegado y verificado |
| S1-S2 | Seguridad OWASP (login, sesión revocable, cabeceras, UUID) | D | Completado (62 tests en verde) |
| 3.R | Capa DAO real y arranque del TDD | 3.0 | Completado (65 tests en verde) |
| 3.3 | Horas pasadas no reservables y vencimiento automático | 3.R | Completado (75 tests en verde) |
| 3.4 | Identidad visual del cliente | 3.3 | Completado (101 tests en verde) |
| 3.5 | Carta y pedido en celular (categorías, desplegables, carrito) | 3.4 | Completado (110 tests en verde) |
| 3.6 | Cocina: imprimir y recojo primero | 3.5 | Siguiente |
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
- [RESUELTO] Logo real guardado como `app/static/img/logo.png` (el original también quedó en `app/static/img/Quero_Gastrobar_logo.jpg`). Optimizarlo (pesa ~299 KB y tiene fondo blanco) queda como mejora opcional.
- [RESUELTO] Tipografía: **Opción B · Clásica elegante** (`Playfair Display` + `Source Sans 3`). Las opciones A y C están documentadas en `GUIA_TIPOGRAFIA_CLIENTE.md` con la vista previa `docs/preview_tipografias.html`.
- Confirmar con la dueña si el acceso a la **carta pública** (`/carta`) debe seguir existiendo: en la Fase 3.5 se quitó de los accesos del inicio y del menú (hoy solo se llega por URL directa) porque todo se elige dentro de `/pedir`.
- Si el margen mínimo de anticipación para reservar por la web es 30 min (valor por defecto editable) o 0.
- Confirmar con la dueña el vencimiento automático (pendientes vencidas → rechazadas; confirmadas sin "Llegó" → no llegó automático): puede inflar las estadísticas de "no llegó" si el staff olvida marcar la llegada.
- Dónde se publica definitivamente (hoy: Render + Neon) y si se usa un dominio propio.
- Si hay fotos reales de los platos (decide si se hace la 3.9).
- [RESUELTO] El prototipo Node/Express antiguo se movió a `_prototipo_antiguo/` (con su README) y se conserva en el historial de Git.

## 7. No hacer
Usar la API de WhatsApp, agregar ORM o frameworks de JavaScript, volver a escribir SQL dentro de servicios o rutas, tocar fases cerradas sin pedirlo, ni inventar datos del local.
