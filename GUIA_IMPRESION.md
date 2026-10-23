# Guía de impresión de tickets (tiquetera) – Quero APP

## 1. Primero, averigua esto con la dueña (decide todo lo demás)
| Dato | Por qué importa |
|---|---|
| **Marca y modelo** de la tiquetera | Para buscar su controlador (driver) |
| **Cómo se conecta**: USB, red (cable o Wi-Fi) o Bluetooth | Define cómo se imprime (ver sección 3) |
| **Ancho del papel**: 58 mm u 80 mm | Es la variable del ticket |
| **Qué equipo está conectado** y qué sistema tiene (Windows, Android...) | La impresión silenciosa solo se configura en Windows con Chrome o Edge |

## 2. Nivel 1: impresión manual (funciona desde el primer día)
1. Conecta la tiquetera al equipo e instala su controlador. Imprime una página de prueba de Windows para comprobar que funciona.
2. En la app, abre el ticket y toca "Imprimir". Aparece el cuadro de impresión del navegador: elige la tiquetera.
3. En ese cuadro, desactiva **Encabezados y pies de página** y pon los márgenes en **Ninguno**. Si no, saldrán la fecha y la dirección de la página impresas.
4. Usa la página `/staff/imprimir/prueba` de la app para ajustar el ancho (80 o 58 mm) hasta que el texto no se corte.

## 3. Nivel 2: imprimir sin el cuadro de confirmación (kiosk printing)
Esto es una configuración del **equipo de la tiquetera**, no del código. Las guías de varios sistemas de caja coinciden en estos pasos para Windows:
1. Deja la **tiquetera como impresora predeterminada** de Windows.
2. Crea un acceso directo de **Chrome** (o Edge) en el escritorio y ponle un nombre claro, por ejemplo "Quero – Impresión".
3. Clic derecho → **Propiedades**. En el campo **Destino**, al final y después de un espacio, agrega: `--kiosk-printing`.
4. **Cierra Chrome por completo** (también desde el Administrador de tareas) y ábrelo siempre con ese acceso directo.
5. Prueba imprimir un ticket: debe salir directo, sin preguntar.

**Si instalaron la web como app (PWA)**, se puede lanzar sin barra del navegador y con impresión silenciosa: en `chrome://apps` o `chrome://app-ids` se ve el identificador de la app, y el acceso directo usa `--app-id=EL_ID --kiosk-printing`. Probado por otros sistemas de caja; pruébalo en su equipo.

**Limitaciones que debes conocer:**
- Imprime siempre en la impresora **predeterminada**; no puedes elegir otra desde el cuadro.
- Funciona con Chrome o Edge en **Windows**. No sirve en un celular iPhone ni en una tablet con otro sistema.
- Puede que el cuadro de vista previa parpadee un instante antes de imprimir.
- Si cambia el puerto USB o se reinstala la impresora, puede dejar de imprimir: revisa que siga como predeterminada.
- Algunos usuarios reportan que en ciertos equipos igual sale el cuadro o tarda; si te pasa, prueba con Firefox (existe una opción interna para impresión silenciosa, `print.always_print_silent`) o pasa al nivel 3.

## 4. Nivel 3 (proyecto final): impresión automática desde el servidor
Hay un problema de fondo: si el sistema está en internet, el servidor **no puede mandar datos a la IP de la tiquetera** del local. Opciones reales:
- **Agente local** (lo que describe la Fase 5B): un programa pequeño en el equipo del local que pregunta al servidor por tickets pendientes y los imprime con comandos ESC/POS. Es lo que recomiendo.
- **QZ Tray**: una aplicación que se instala en el equipo y permite imprimir desde la web sin cuadro de confirmación y con impresoras específicas. Otras guías la mencionan como alternativa al parámetro de Chrome. Revisa su licencia y costo antes de adoptarla.

## 5. Qué hacer según cómo se conecte la tiquetera
| Conexión | Camino recomendado |
|---|---|
| **USB** a una PC con Windows | Nivel 1 y 2; luego el agente local |
| **Red (cable o Wi-Fi)** | Igual que USB, instalando la impresora de red en la PC. El agente local puede imprimir a su IP desde el equipo del local |
| **Bluetooth** a un celular o tablet | La impresión desde el navegador es muy limitada (en iPhone la web no accede a Bluetooth). Conviene conectarla a una PC o usar impresión de red |

## 6. Lista de comprobación antes de la demostración
- [ ] La tiquetera imprime una página de prueba de Windows
- [ ] El ticket de `/staff/imprimir/prueba` sale completo, sin cortes ni encabezados
- [ ] El acceso directo con `--kiosk-printing` imprime sin preguntar
- [ ] El QR del ticket se escanea con la cámara del celular y abre la reserva o el pedido
- [ ] Hay papel de repuesto
- [ ] Se probó imprimir con el hosting "dormido" (si usan un plan gratuito) abriendo la página antes
