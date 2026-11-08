# WhatsApp: ¿hay que invertir dinero? (consultado el 03/11/2026)

**Respuesta corta:** no por ahora. Lo que usa hoy el proyecto (enlaces `wa.me` con el mensaje ya escrito) cuesta **cero** y no necesita aprobación de Meta. La API oficial cobra por mensaje y exige trámites; solo conviene si el volumen y el tiempo del staff lo justifican.

## Qué opciones existen
| Opción | Costo | Qué exige | Comentario |
|---|---|---|---|
| **Enlaces `wa.me` (lo que usamos)** | $0 | Que el staff toque el botón y envíe | Es manual: un toque por aviso. Es la opción de las Fases 3.4 y 3.8. |
| **Cliente escribe primero** ("Enviar por WhatsApp al local") | $0 con la app de WhatsApp Business del local | Nada | El cliente abre la conversación; el local le responde gratis desde su celular. |
| **API oficial de WhatsApp Business (Meta Cloud API)** | Por mensaje entregado | Cuenta Meta Business verificada, plantillas aprobadas, consentimiento del cliente, y un servidor público con HTTPS (hosting) | Automatiza los avisos. Es la Fase 5A y es opcional. |

## Tarifas de la API (Meta, USD por mensaje entregado; verifica siempre la tarifa oficial vigente)
- Desde el 1 de julio de 2025 Meta cobra por mensaje y por categoría (marketing, utilidad, autenticación).
- Perú tenía fila propia hasta el 30/09/2026: **marketing ≈ $0.081**, **utilidad ≈ $0.023** (según la tabla pública de un proveedor).
- Desde el 01/10/2026 las tablas públicas que revisé listan "Resto de Latinoamérica": **marketing ≈ $0.074**, **utilidad ≈ $0.0113**. **No pude confirmar si Perú conserva fila propia desde esa fecha.** Consulta la tarifa oficial de Meta o a tu proveedor antes de presupuestar.
- Desde el 01/10/2026 las respuestas de servicio dentro de la ventana de 24 h dejan de ser gratis después de 1.000 al mes por número. Los proveedores no coinciden en si las plantillas de utilidad dentro de la ventana también se cobran: confírmalo.
- Si usas un proveedor intermediario (BSP), suele sumar su propia mensualidad o recargo.

## Ejemplo ilustrativo (no es una cotización)
- 20 pedidos por día, 2 avisos de utilidad por pedido: 20 × 30 × 2 = 1.200 mensajes al mes → **$13.6 a $27.6** al mes con las tarifas de utilidad de arriba.
- Si además enviaras un mensaje de "pide más" (marketing) por pedido: 600 mensajes → **$44 a $49** al mes más. Es el que más cuesta y el que más riesgo de queja tiene.

## Recomendación
1. **Ahora:** `wa.me` con mensajes bien redactados (Fase 3.8). Costo $0.
2. **La publicidad ("pide más")** va dentro de la web (bloque "Complementa tu pedido" del carrito) y en un único mensaje amable al entregar, no en envíos masivos.
3. **Evalúa la API** solo si el staff pierde tiempo real enviando avisos a mano (por ejemplo, decenas al día) **y** el local ya paga hosting con HTTPS. Antes hay que tener: número dedicado o compatible, plantillas aprobadas y un campo de consentimiento específico para WhatsApp.
4. Usar el mismo número que la dueña tiene en su celular con la API tiene restricciones de compatibilidad con la app: verifícalo antes de decidir.

## Fuentes consultadas
- Documentación de precios de Meta (developers.facebook.com/documentation/business-messaging/whatsapp/pricing).
- Tabla de tarifas por país de SleekFlow (help.sleekflow.io/en_US/pricing), con vigencia hasta el 30/09/2026.
- Tablas del 01/10/2026 publicadas por Zernio y SleekFlow; avisos de cambio de Wati sobre mensajes de servicio y de utilidad.
