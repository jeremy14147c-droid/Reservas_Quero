# Tipografías del cliente (Quero Gastrobar)

> Decisión actual: **Opción B · Clásica elegante** (`Playfair Display` + `Source Sans 3`).
> Las opciones A y C quedan documentadas aquí para poder cambiarlas en minutos si la
> dueña cambia de opinión.

## Vista previa

Abre **`docs/preview_tipografias.html`** en el navegador (doble clic o, desde el agente,
con la herramienta de vista previa). Muestra las tres combinaciones con el nombre, el
eslogan, un texto de ejemplo, el botón y la paleta de colores del local.

## Las tres opciones

| Opción | Títulos | Texto | Sensación |
|---|---|---|---|
| **A · Cálida moderna** | `Fraunces` | `Inter` | Cercana y actual; títulos con carácter sin dejar de ser legible. |
| **B · Clásica elegante (ACTIVA)** | `Playfair Display` | `Source Sans 3` | Formal, tipo carta de restaurante; transmite tradición y buen servicio. |
| **C · Pollería casual** | `Bebas Neue` | `Lato` | Títulos enormes e informales, estilo aviso de pollería. |

## Cómo cambiar de opción (3 pasos)

1. **`app/templates/base_cliente.html`**: reemplaza el `<link>` de Google Fonts por el de la opción.
2. **`app/static/css/cliente.css`**: en `:root`, cambia `--fuente-titulos` y `--fuente-texto`
   (el bloque de comentarios de arriba tiene los tres pares listos para copiar).
3. Recarga la página. No hay que tocar nada más.

### Enlaces de Google Fonts

```text
A: https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900&family=Inter:wght@400;500;600;700&display=swap
B: https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap
C: https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Lato:wght@400;700&display=swap
```

## Detalles técnicos

- Se cargan con `font-display: swap`: el texto se ve de inmediato con la fuente de respaldo
  (`Georgia` para títulos, `system-ui` para el texto) y se cambia al terminar de descargar.
- La política de seguridad (CSP) de `app/__init__.py` ya permite `fonts.googleapis.com` y
  `fonts.gstatic.com`; no hay que modificarla.
- No se descargan archivos de fuente al repositorio: siguen viniendo del CDN de Google.
- El wordmark de respaldo (cuando todavía no existe `app/static/img/logo.png`) usa la fuente
  de títulos con un degradado rojo → naranja → amarillo, los colores del logo.
