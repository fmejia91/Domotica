/**
 * Proyecto: Domótica - Control de Dispositivos (Frontend)
 * Arquitectura: Fetch API asíncrona hacia servidor Flask
 */

document.addEventListener('DOMContentLoaded', () => {
    // Inicializar los escuchas de eventos de la interfaz
    initIndividualSwitches();
    initMasterSwitches();
});

/**
 * Controla los switches individuales (.smart-card)
 */
function initIndividualSwitches() {
    const cards = document.querySelectorAll('.smart-card');

    cards.forEach(card => {
        card.addEventListener('click', async (e) => {
            // Prevenir comportamientos extraños en móviles
            e.preventDefault();

            const deviceId = card.getAttribute('data-device-id');
            const isCurrentlyOn = card.classList.contains('active');
            
            // 1. UI Optimista: Cambiar visualmente antes de la respuesta del servidor
            toggleCardVisualState(card, !isCurrentlyOn);

            try {
                // 2. Llamada asíncrona al endpoint de Flask
                const response = await fetch(`/toggle/${deviceId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error('Error en la respuesta del servidor');
                }

                const data = await response.json();
                
                // 3. Sincronizar con el estado real devuelto por el backend
                toggleCardVisualState(card, data.status === 'on' || data.status === true);

            } catch (error) {
                console.error(`Error al controlar el dispositivo ${deviceId}:`, error);
                // Revertir el estado visual si la petición falla
                toggleCardVisualState(card, isCurrentlyOn);
                alert('No se pudo conectar con el servidor domótico.');
            }
        });
    });
}

/**
 * Controla los 'Switches Maestros' por zona
 */
function initMasterSwitches() {
    const masterSwitches = document.querySelectorAll('.master-switch');

    masterSwitches.forEach(switchInput => {
        switchInput.addEventListener('change', async (e) => {
            const zoneName = switchInput.getAttribute('data-zone');
            const shouldTurnOn = switchInput.checked;

            // 1. UI Optimista: Apagar/Encender visualmente todos los focos de esta zona
            const zoneCards = document.querySelectorAll(`.smart-card[data-zone="${zoneName}"]`);
            zoneCards.forEach(card => toggleCardVisualState(card, shouldTurnOn));

            try {
                // 2. Llamada asíncrona al endpoint maestro de Flask
                const action = shouldTurnOn ? 'on' : 'off';
                const response = await fetch(`/zona/maestro/${zoneName}?action=${action}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error('Error en el control maestro de zona');
                }

                const data = await response.json();
                
                // 3. Confirmación del backend: Forzar el estado final según la respuesta
                // (Asumiendo que el backend devuelve una lista o estado de éxito)
                if (data.status !== 'success') {
                     throw new Error('El backend no procesó correctamente el comando maestro');
                }

            } catch (error) {
                console.error(`Error en el switch maestro de la zona ${zoneName}:`, error);
                // Revertir el switch maestro y las tarjetas de la zona
                switchInput.checked = !shouldTurnOn;
                zoneCards.forEach(card => toggleCardVisualState(card, !shouldTurnOn));
                alert('Error al procesar el comando por zona.');
            }
        });
    });
}

/**
 * Función auxiliar para alterar el estado visual estilo HomeKit
 */
function toggleCardVisualState(cardElement, turnOn) {
    const icon = cardElement.querySelector('.lucide');

    if (turnOn) {
        cardElement.classList.add('active');
        // Si usas clases de Tailwind dinámicas mediante JS para iluminar el icono:
        if (icon) icon.classList.add('text-yellow-500');
    } else {
        cardElement.classList.remove('active');
        if (icon) icon.classList.remove('text-yellow-500');
    }
}