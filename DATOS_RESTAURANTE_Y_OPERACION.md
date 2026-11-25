# Datos de la Empresa y Parámetros Operativos — Quero Gastrobar

Este documento consolida la ficha técnica comercial del restaurante y los parámetros operativos oficiales proporcionados por la dueña (**Jhoana**), utilizados para alimentar la tabla `config_local` y las reglas del sistema web.

---

## 1. Identidad Comercial y Contacto del Restaurante

* **Razón / Nombre Comercial:** Quero Gastrobar
* **Descripción de la Empresa:**  
  *Somos una empresa dedicada a la venta de comida marina, criolla, alitas variedad de sabores, piqueos, platos a la carta, frappé, jugos, cócteles variados y más. El mejor ambiente y los mejores precios lo encuentras aquí en QUERO GASTROBAR.*
* **Eslogan:** *"El sabor del mar y lo criollo, en un solo lugar."*
* **Dirección Física:** Av. Inca Garcilaso de la Vega 54, Villa María del Triunfo 15816, Lima, Perú.
* **Número de Teléfono / Celular:** `996908138`
* **Enlace Directo de WhatsApp:** `https://wa.me/51996908138` (o enlace corto `https://wa.me/message/7W4XRBX3KVZFB1`)
* **Ubicación Google Maps:** `https://maps.app.goo.gl/rATMHp75PEziVzCQ8`
* **Página de Facebook:** `https://www.facebook.com/GastrobarPiqueosTragos/`
* **Perfil de Instagram:** `https://www.instagram.com/quero_gastrobar`
* **Datos de Cobro Digital (Yape / Plin):**
  * **Número:** `996908138`
  * **Titular de la cuenta:** Jhoana / Quero Gastrobar

---

## 2. Parámetros Operativos Oficiales del Local (`config_local`)

Estos valores fueron definidos directamente por la dueña del restaurante (sección 6 de `PASOS_PREVIOS.md`) y son totalmente editables desde el panel en **Administración > Configuración**:

| Parámetro | Valor Oficial | Campo en Base de Datos | Justificación Operativa |
|---|:---:|---|---|
| **Aforo Máximo** | **60 personas** | `aforo_personas` | Capacidad máxima de clientes sentados en el salón a la vez. |
| **Total de Mesas** | **15 mesas** | `total_mesas` | Número físico de mesas disponibles en el salón. |
| **Personas por Mesa** | **4 personas** | `personas_por_mesa` | Capacidad estándar por mesa para el cálculo de mesas ocupadas (redondeado hacia arriba). |
| **Duración en Mesa: 1 a 3 personas** | **30 minutos** | `duracion_1_3_min` | Grupos pequeños consumen rápido y desocupan la mesa en ~30 min. |
| **Duración en Mesa: 4 a 7 personas** | **60 minutos** | `duracion_4_7_min` | Grupos familiares o amigos ocupan mesa durante 1 hora. |
| **Duración en Mesa: 8 a más personas** | **90 minutos** | `duracion_8_mas_min` | Grupos grandes o celebraciones requieren 1 hora y media. |
| **Franja Horaria** | **30 minutos** | `franja_min` | Intervalo de tiempo para cada columna de la pizarra y horarios de reserva. |
| **Horario de Atención** | **12:00 a 22:00** | `hora_apertura`, `hora_cierre` | Rango de atención para reservas del público y pedidos remotos. |
| **Tolerancia de Espera** | **20 minutos** | `tolerancia_min` | Tiempo de espera tras la hora pactada antes de alertar en rojo al staff (no cancela sola). |
| **Umbral de Alerta de Ocupación** | **80 %** | `umbral_alerta_pct` | Porcentaje a partir del cual una franja horaria se colorea en amarillo ("a punto de llenarse"). |
| **Tope de Reservas Web por Teléfono** | **2 reservas en 24h** | `max_reservas_web_por_telefono` | Evita saturación o abusos de reservas no atendidas con el mismo celular. |
| **Tiempo Máximo de Preparación** | **20 minutos** | `umbral_preparacion_min` | Tiempo estimado en cocina; superado este lapso, el pedido se alerta en rojo en la pantalla de pedidos. |
| **Días Máximos de Anticipación** | **2 días** | `dias_max_anticipacion` | Margen de días futuros hacia adelante para que un cliente pueda agendar su mesa. |
| **Anticipación Mínima Web** | **30 minutos** | `anticipacion_min_min` | Tiempo mínimo requerido antes de una franja para poder reservarla por la web hoy. |

---

## 3. Dinámica Operativa del Restaurante

### A. Ciclo de Vida de las Reservas
1. **Solicitud Web:** Nace como `pendiente`. **No descuenta cupo del aforo**.
2. **Revisión del Staff:** El recepcionista o administrador verifica la solicitud en la pizarra y confirma con un clic. Al pasar a `confirmada`, entra al cálculo de capacidad.
3. **Llegada:** Cuando el grupo llega al local, el personal marca `llego`. Si pasan más de 20 min de tolerancia, la tarjeta se alerta en rojo pero el staff decide si reprograma o marca `no_llego`.
4. **Vencimiento Automático:** Si una solicitud pendiente no fue atendida y su hora ya pasó, se rechaza automáticamente. Si una reserva confirmada terminó su tiempo de mesa sin registrar llegada, se cierra como `no_llego` para no ensuciar la pizarra.

### B. Ciclo de Vida de los Pedidos
1. **Pedidos de Recojo (Web):** Nace `pendiente`. El cliente indica sus platos. El personal revisa stock y acepta el pedido (`aceptado`).
2. **Confirmación del Pago:** El cliente envía su comprobante por Yape/Plin al número `996908138`. El staff valida en su aplicativo bancario y marca como cobrado.
3. **Cocina:** Al estar cobrado, el pedido pasa a `en_preparacion`. Cocina lo atiende (priorizando pedidos de recojo sobre locales) y lo pasa a `listo`.
4. **Entrega:** El cliente retira su pedido y se marca como `entregado`.
