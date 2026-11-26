/* =====================================================================
   Manejo de impresión automática de tickets para tiquetera (Fase 3.6)
   - Funciona con --kiosk-printing (Nivel 2).
   - Recuerda los pedidos ya impresos en sessionStorage para evitar duplicados.
   - Recuerda la casilla activa en localStorage.
   ===================================================================== */

function configurarImpresionAutomatica(casillaId, storageKeyCasilla, storageKeyImpresos) {
    const casilla = document.getElementById(casillaId);
    if (!casilla) return null;

    // Recuperar estado guardado de la casilla (apagada por defecto)
    casilla.checked = localStorage.getItem(storageKeyCasilla) === 'si';
    casilla.addEventListener('change', () => {
        localStorage.setItem(storageKeyCasilla, casilla.checked ? 'si' : 'no');
    });

    return {
        estaActivo: function () {
            return casilla.checked;
        },
        imprimirNuevos: function (ids) {
            if (!casilla.checked || !ids || !ids.length) return;

            let impresos = [];
            try {
                impresos = JSON.parse(sessionStorage.getItem(storageKeyImpresos) || '[]');
            } catch (e) {
                impresos = [];
            }

            const porImprimir = ids.filter(id => !impresos.includes(id));
            if (porImprimir.length > 0) {
                porImprimir.forEach(id => {
                    window.open('/staff/pedido/' + id + '/ticket?auto=1', '_blank');
                    impresos.push(id);
                });
                sessionStorage.setItem(storageKeyImpresos, JSON.stringify(impresos));
            }
        }
    };
}
