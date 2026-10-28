/**
 * Quero Gastrobar - JavaScript principal
 * Manejo de eventos de red y comportamiento sin conexión (AGENTS.md sección 11).
 */

document.addEventListener('DOMContentLoaded', () => {
    const bannerSinConexion = document.getElementById('banner-sin-conexion');
    const elementosConexion = document.querySelectorAll('[data-requiere-conexion]');

    function actualizarEstadoRed(estaOnline) {
        if (!estaOnline) {
            // Mostrar banner de alerta fija
            if (bannerSinConexion) {
                bannerSinConexion.classList.remove('d-none');
            }
            // Deshabilitar todos los botones y acciones operativas
            elementosConexion.forEach(el => {
                el.disabled = true;
                el.setAttribute('aria-disabled', 'true');
                el.classList.add('disabled');
            });
        } else {
            // Ocultar banner
            if (bannerSinConexion) {
                bannerSinConexion.classList.add('d-none');
            }
            // Habilitar elementos nuevamente
            elementosConexion.forEach(el => {
                el.disabled = false;
                el.removeAttribute('aria-disabled');
                el.classList.remove('disabled');
            });
        }
    }

    // Escuchar eventos de navegador sobre conectividad
    window.addEventListener('online', () => {
        actualizarEstadoRed(true);
        // Al volver la red, refrescar datos operativos
        console.info('Conexión reestablecida.');
    });

    window.addEventListener('offline', () => {
        actualizarEstadoRed(false);
        console.warn('Conexión perdida. Operaciones bloqueadas.');
    });

    // Interceptar errores de fetch para detectar caídas de conexión con el servidor
    const fetchOriginal = window.fetch;
    window.fetch = async function(...args) {
        try {
            const respuesta = await fetchOriginal.apply(this, args);
            return respuesta;
        } catch (error) {
            // Si la llamada fetch falla por red, activar banner
            actualizarEstadoRed(false);
            throw error;
        }
    };

    // Verificar estado inicial al cargar la página
    if (!navigator.onLine) {
        actualizarEstadoRed(false);
    }

    // Inicializar tooltips de Bootstrap (etiquetas flotadas de botones desactivados, etc.)
    if (window.bootstrap) {
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
            .forEach(el => new bootstrap.Tooltip(el));
    }
});
