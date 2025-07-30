// 🚀 HISPE PULSE - JavaScript App Optimizado
class MarcacionApp {
    constructor() {
        this.currentMarcationType = null;
        this.qrScanner = null;
        this.isProcessing = false;
        this.connectionStatus = true;
        
        // Configuración
        this.config = {
            qrScanConfig: {
                fps: 10,
                qrbox: { width: 280, height: 280 },
                aspectRatio: 1.0,
                disableFlip: false,
                rememberLastUsedCamera: false,
                showTorchButtonIfSupported: true,
                showZoomSliderIfSupported: false,
                defaultZoomValueIfSupported: 1,
                supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA]
            },
            autoRefreshInterval: 30000, // 30 segundos
            messageTimeout: 5000 // 5 segundos
        };
        
        this.init();
    }

    async init() {
        console.log('🚀 Iniciando HISPE PULSE...');
        
        try {
            // Mostrar loading inicial
            this.showLoading(true);
            
            // Verificar conexión
            await this.checkConnection();
            
            // Cargar datos del usuario
            await this.loadUserData();
            
            // Cargar marcaciones del día
            await this.loadTodayAttendance();
            
            // Configurar event listeners
            this.setupEventListeners();
            
            // Configurar auto-refresh
            this.startAutoRefresh();
            
            console.log('✅ App inicializada correctamente');
            
        } catch (error) {
            console.error('❌ Error inicializando app:', error);
            this.showMessage('Error al inicializar la aplicación', 'error');
            this.updateConnectionStatus(false);
        } finally {
            this.showLoading(false);
        }
    }

    async checkConnection() {
        try {
            const response = await fetch('/api/health', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });
            
            this.connectionStatus = response.ok;
            this.updateConnectionStatus(this.connectionStatus);
            
            if (!this.connectionStatus) {
                throw new Error('Servidor no disponible');
            }
            
        } catch (error) {
            this.connectionStatus = false;
            this.updateConnectionStatus(false);
            throw error;
        }
    }

    updateConnectionStatus(isConnected) {
        const statusElement = document.getElementById('connectionStatus');
        const dot = statusElement.querySelector('.status-dot');
        const text = statusElement.querySelector('.status-text');
        
        if (isConnected) {
            dot.style.background = 'var(--color-success)';
            text.textContent = 'Conectado';
            statusElement.style.color = 'var(--color-success)';
        } else {
            dot.style.background = 'var(--color-error)';
            text.textContent = 'Sin conexión';
            statusElement.style.color = 'var(--color-error)';
        }
    }

    async loadUserData() {
        try {
            const response = await fetch('/api/user');
            if (!response.ok) throw new Error('Error cargando usuario');
            
            const user = await response.json();
            
            // Actualizar UI con datos del usuario
            document.getElementById('userName').textContent = user.userName;
            document.getElementById('userEmail').textContent = user.userEmail;
            document.getElementById('userDni').textContent = `DNI: ${user.userDni}`;
            
            // Actualizar iniciales del avatar
            const initials = user.userName
                .split(' ')
                .map(n => n[0])
                .join('')
                .substring(0, 2)
                .toUpperCase();
            document.getElementById('userInitials').textContent = initials;
            
        } catch (error) {
            console.error('❌ Error cargando usuario:', error);
            this.showMessage('Error cargando datos del usuario', 'error');
        }
    }

    async loadTodayAttendance() {
        try {
            const response = await fetch('/api/attendance/today');
            if (!response.ok) throw new Error('Error cargando marcaciones');
            
            const attendance = await response.json();
            this.updateMarcationCards(attendance);
            
        } catch (error) {
            console.error('❌ Error cargando marcaciones:', error);
            this.showMessage('Error cargando marcaciones del día', 'error');
        }
    }

    updateMarcationCards(attendance) {
        const cards = document.querySelectorAll('.marcation-card');
        
        cards.forEach(card => {
            const type = card.dataset.type;
            const timeElement = card.querySelector('.card-time');
            const statusElement = card.querySelector('.card-status');
            
            // Reset classes
            card.classList.remove('available', 'completed', 'disabled');
            
            switch(type) {
                case 'Ingreso':
                    if (attendance.horaentrada) {
                        card.classList.add('completed');
                        timeElement.textContent = attendance.horaentrada;
                        statusElement.textContent = '✅ Completado';
                        statusElement.style.color = 'var(--color-success)';
                    } else {
                        card.classList.add('available');
                        timeElement.textContent = '';
                        statusElement.textContent = 'Toca para marcar';
                        statusElement.style.color = 'var(--text-muted)';
                    }
                    break;
                    
                case 'Inicio de Refrigerio':
                    if (attendance.horaRefrigerioInicio) {
                        // Ya marcó inicio de refrigerio
                        card.classList.add('completed');
                        timeElement.textContent = attendance.horaRefrigerioInicio;
                        statusElement.textContent = '✅ Completado';
                        statusElement.style.color = 'var(--color-success)';
                    } else if (attendance.horaentrada && !attendance.horasalida) {
                        // Puede marcar inicio de refrigerio (tiene ingreso, no tiene salida)
                        card.classList.add('available');
                        timeElement.textContent = '';
                        statusElement.textContent = 'Toca para marcar';
                        statusElement.style.color = 'var(--text-muted)';
                    } else {
                        // Bloqueado
                        card.classList.add('disabled');
                        timeElement.textContent = '';
                        statusElement.textContent = attendance.horaentrada ? 'No disponible' : 'Requiere ingreso';
                        statusElement.style.color = 'var(--text-muted)';
                    }
                    break;
                    
                case 'Salida de Refrigerio':
                    if (attendance.horaRefrigerioFin) {
                        // Ya marcó fin de refrigerio
                        card.classList.add('completed');
                        timeElement.textContent = attendance.horaRefrigerioFin;
                        statusElement.textContent = '✅ Completado';
                        statusElement.style.color = 'var(--color-success)';
                    } else if (attendance.horaRefrigerioInicio && !attendance.horasalida) {
                        // Puede marcar fin de refrigerio (tiene inicio, no tiene salida)
                        card.classList.add('available');
                        timeElement.textContent = '';
                        statusElement.textContent = 'Toca para marcar';
                        statusElement.style.color = 'var(--text-muted)';
                    } else {
                        // Bloqueado
                        card.classList.add('disabled');
                        timeElement.textContent = '';
                        if (!attendance.horaentrada) {
                            statusElement.textContent = 'Requiere ingreso';
                        } else if (!attendance.horaRefrigerioInicio) {
                            statusElement.textContent = 'Requiere inicio refrigerio';
                        } else {
                            statusElement.textContent = 'No disponible';
                        }
                        statusElement.style.color = 'var(--text-muted)';
                    }
                    break;
                    
                case 'Salida':
                    if (attendance.horasalida) {
                        // Ya marcó salida
                        card.classList.add('completed');
                        timeElement.textContent = attendance.horasalida;
                        statusElement.textContent = '✅ Completado';
                        statusElement.style.color = 'var(--color-success)';
                    } else if (attendance.horaentrada && 
                              (!attendance.horaRefrigerioInicio || attendance.horaRefrigerioFin)) {
                        // Puede marcar salida: tiene ingreso Y (no inició refrigerio O terminó refrigerio)
                        card.classList.add('available');
                        timeElement.textContent = '';
                        statusElement.textContent = 'Toca para marcar';
                        statusElement.style.color = 'var(--text-muted)';
                    } else {
                        // Bloqueado
                        card.classList.add('disabled');
                        timeElement.textContent = '';
                        if (!attendance.horaentrada) {
                            statusElement.textContent = 'Requiere ingreso';
                        } else if (attendance.horaRefrigerioInicio && !attendance.horaRefrigerioFin) {
                            statusElement.textContent = 'Termine refrigerio primero';
                        } else {
                            statusElement.textContent = 'No disponible';
                        }
                        statusElement.style.color = 'var(--text-muted)';
                    }
                    break;
            }
        });
        
        // Re-asignar eventos después de actualizar
        this.reassignCardEvents();
    }

    reassignCardEvents() {
        // Limpiar eventos anteriores y asignar nuevos
        document.querySelectorAll('.marcation-card').forEach(card => {
            // Crear nueva función para evitar duplicados
            const newCard = card.cloneNode(true);
            card.parentNode.replaceChild(newCard, card);
            
            // Asignar evento al nuevo elemento si está disponible
            if (newCard.classList.contains('available')) {
                newCard.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    if (!this.isProcessing) {
                        this.currentMarcationType = newCard.dataset.type;
                        console.log('🎯 Card clickeada - Activando cámara para:', this.currentMarcationType);
                        
                        // Activar cámara DIRECTAMENTE
                        this.startQRScan();
                    }
                });
                
                // Añadir efectos visuales
                newCard.style.cursor = 'pointer';
                
                newCard.addEventListener('mouseenter', () => {
                    if (!this.isProcessing) {
                        newCard.style.transform = 'translateY(-4px)';
                    }
                });
                
                newCard.addEventListener('mouseleave', () => {
                    newCard.style.transform = '';
                });
                
            } else {
                // Card deshabilitada o completada
                newCard.style.cursor = newCard.classList.contains('completed') ? 'default' : 'not-allowed';
            }
        });
        
        console.log('🔄 Eventos de cards actualizados');
    }

    setupEventListeners() {
        // Botón para cancelar escaneo
        const cancelButton = document.getElementById('cancelScanButton');
        cancelButton.addEventListener('click', () => {
            this.stopQRScan();
            this.showMessage('Escaneo cancelado', 'info');
        });

        // Prevenir submit de forms
        document.addEventListener('submit', (e) => {
            e.preventDefault();
        });

        // Manejar visibility change para auto-refresh
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.loadTodayAttendance();
            }
        });
        
        // Los eventos de las cards se asignan en reassignCardEvents()
    }

    startQRScan() {
        if (this.isProcessing) return;
        
        console.log('🎯 INICIANDO CÁMARA FULLSCREEN...');
        
        const qrReaderElement = document.getElementById('qrReader');
        const cancelButton = document.getElementById('cancelScanButton');
        
        // Activar modo fullscreen
        qrReaderElement.classList.remove('hidden');
        qrReaderElement.classList.add('fullscreen');
        cancelButton.classList.add('hidden'); // Ocultar botón original
        
        // Crear controles de cámara overlay
        const cameraControls = document.createElement('div');
        cameraControls.className = 'camera-controls';
        cameraControls.innerHTML = `
            <h3>📱 Escanear QR</h3>
            <button class="camera-close-btn" id="cameraCloseBtn">✕ Cerrar</button>
        `;
        
        // Crear overlay de QR box
        const qrOverlay = document.createElement('div');
        qrOverlay.className = 'qr-overlay';
        
        // Crear instrucciones
        const instructions = document.createElement('div');
        instructions.className = 'camera-instructions';
        instructions.innerHTML = '<p>Coloca el código QR dentro del marco</p>';
        
        // Limpiar y agregar elementos
        qrReaderElement.innerHTML = '';
        qrReaderElement.appendChild(cameraControls);
        qrReaderElement.appendChild(qrOverlay);
        qrReaderElement.appendChild(instructions);
        
        // Event listener para cerrar
        document.getElementById('cameraCloseBtn').addEventListener('click', () => {
            this.stopQRScan();
        });
        
        // CREAR INSTANCIA Y ACTIVAR CÁMARA
        this.qrScanner = new Html5Qrcode("qrReader");
        
        this.qrScanner.start(
            { facingMode: "environment" },
            {
                fps: 10,
                qrbox: { width: 280, height: 280 },
                aspectRatio: 1.0
            },
            (decodedText) => {
                console.log('✅ QR ESCANEADO:', decodedText);
                
                // Feedback visual de éxito
                this.showScanSuccess();
                
                // Procesar QR y cerrar después de delay
                setTimeout(() => {
                    this.processQRCode(decodedText);
                    this.stopQRScan();
                }, 800);
            },
            (errorMessage) => {
                // Ignorar errores normales de escaneo
            }
        ).then(() => {
            console.log('✅ CÁMARA FULLSCREEN ACTIVADA');
            
            // Ocultar elementos de fondo (opcional)
            document.body.style.overflow = 'hidden';
            
        }).catch(err => {
            console.error('❌ ERROR CÁMARA:', err);
            this.showMessage('Error de cámara: ' + err, 'error');
            this.stopQRScan();
        });
        
        // Timeout de seguridad
        this.scanTimeout = setTimeout(() => {
            this.stopQRScan();
            this.showMessage('Tiempo de escaneo agotado', 'info');
        }, 120000);
    }

    showScanSuccess() {
        // Feedback visual cuando se escanea exitosamente
        const qrReaderElement = document.getElementById('qrReader');
        const successOverlay = document.createElement('div');
        successOverlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(39, 174, 96, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2002;
            animation: fadeIn 0.3s ease;
        `;
        successOverlay.innerHTML = `
            <div style="text-align: center; color: white;">
                <div style="font-size: 60px; margin-bottom: 10px;">✅</div>
                <div style="font-size: 18px; font-weight: bold;">¡QR Escaneado!</div>
            </div>
        `;
        
        qrReaderElement.appendChild(successOverlay);
    }

    stopQRScan() {
        console.log('🛑 CERRANDO CÁMARA FULLSCREEN...');
        
        // Restaurar scroll del body
        document.body.style.overflow = '';
        
        // Limpiar timeout
        if (this.scanTimeout) {
            clearTimeout(this.scanTimeout);
            this.scanTimeout = null;
        }
        
        // Parar cámara
        if (this.qrScanner) {
            this.qrScanner.stop().then(() => {
                console.log('✅ CÁMARA CERRADA');
            }).catch(() => {
                console.log('Error cerrando cámara');
            });
            this.qrScanner = null;
        }
        
        // Restaurar elementos
        const qrReaderElement = document.getElementById('qrReader');
        qrReaderElement.classList.add('hidden');
        qrReaderElement.classList.remove('fullscreen');
        qrReaderElement.innerHTML = '';
        
        document.getElementById('cancelScanButton').classList.add('hidden');
        
        console.log('🏠 REGRESANDO A PANTALLA PRINCIPAL...');
    }

    async processQRCode(qrCode) {
        if (this.isProcessing || !this.currentMarcationType) {
            this.showMessage('Selecciona un tipo de marcación primero', 'error');
            return;
        }

        this.isProcessing = true;
        this.showLoading(true);
        this.showMessage('Procesando marcación...', 'info');

        try {
            const response = await fetch('/api/attendance/mark', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    qrCode: qrCode,
                    marcationType: this.currentMarcationType
                })
            });

            const result = await response.json();

            if (response.ok) {
                // Éxito
                this.showMessage(result.message, 'success');
                
                // Recargar marcaciones del día
                await this.loadTodayAttendance();
                
                // Limpiar input
                const qrInput = document.getElementById('qrInput');
                qrInput.value = '';
                
                // Feedback visual adicional
                this.celebrateSuccess();
                
            } else {
                // Error del servidor
                this.showMessage(result.error || 'Error procesando marcación', 'error');
            }

        } catch (error) {
            console.error('❌ Error procesando QR:', error);
            
            if (!this.connectionStatus) {
                this.showMessage('Sin conexión al servidor', 'error');
            } else {
                this.showMessage('Error de comunicación con el servidor', 'error');
            }
            
        } finally {
            this.isProcessing = false;
            this.showLoading(false);
            this.currentMarcationType = null;
        }
    }

    celebrateSuccess() {
        // Pequeña animación de éxito
        const cards = document.querySelectorAll('.marcation-card.completed');
        cards.forEach(card => {
            card.style.transform = 'scale(1.05)';
            setTimeout(() => {
                card.style.transform = '';
            }, 300);
        });
    }

    showMessage(message, type = 'info') {
        const messageElement = document.getElementById('statusMessage');
        
        messageElement.textContent = message;
        messageElement.className = `status-message ${type} fade-in`;
        messageElement.classList.remove('hidden');

        // Auto-hide después del timeout configurado
        clearTimeout(this.messageTimeout);
        this.messageTimeout = setTimeout(() => {
            messageElement.classList.add('hidden');
        }, this.config.messageTimeout);
    }

    showLoading(show) {
        const loadingElement = document.getElementById('loadingOverlay');
        if (show) {
            loadingElement.classList.remove('hidden');
        } else {
            loadingElement.classList.add('hidden');
        }
    }

    startAutoRefresh() {
        // Auto-refresh cada 30 segundos
        this.autoRefreshInterval = setInterval(() => {
            if (!this.isProcessing && !document.hidden) {
                this.loadTodayAttendance();
            }
        }, this.config.autoRefreshInterval);
    }

    // Métodos públicos para uso externo
    refresh() {
        this.loadTodayAttendance();
    }

    // Limpiar recursos cuando se cierre la página
    destroy() {
        // Limpiar scanner QR
        if (this.qrScanner) {
            this.qrScanner.clear();
        }
        
        // Limpiar timeouts
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        if (this.messageTimeout) {
            clearTimeout(this.messageTimeout);
        }
        
        if (this.scanTimeout) {
            clearTimeout(this.scanTimeout);
        }
        
        console.log('🧹 App destroyed');
    }
}

// 🚀 Inicializar app cuando el DOM esté listo
let app;

document.addEventListener('DOMContentLoaded', () => {
    try {
        app = new MarcacionApp();
        
        // Exponer app globalmente para debugging
        window.hispeApp = app;
        
    } catch (error) {
        console.error('❌ Error fatal inicializando app:', error);
        
        // Mostrar error fallback
        document.body.innerHTML = `
            <div style="padding: 20px; text-align: center; color: white;">
                <h2>❌ Error de inicialización</h2>
                <p>No se pudo cargar la aplicación.</p>
                <button onclick="location.reload()" style="padding: 10px 20px; margin-top: 10px;">
                    🔄 Recargar página
                </button>
            </div>
        `;
    }
});

// Limpiar recursos cuando se cierre la página
window.addEventListener('beforeunload', () => {
    if (app) {
        app.destroy();
    }
});