import yaml
import json
import logging
from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt

# --- CONFIGURACIÓN DE LOGGING SENIOR ---
# Configuramos el nivel a INFO y el formato para incluir timestamp y nivel de error
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- CONFIGURACIÓN DE RUTAS ---
CONFIG_PATH = "../../config/settings.yaml"
MQTT_BROKER = "localhost"  # Broker Mosquitto en Docker [2, 3]
MQTT_PORT = 1883

def load_config():
    """Carga la configuración y loguea posibles errores de archivo [4, 5]."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            logger.info(f"[CONFIG] Cargando configuración desde {CONFIG_PATH}")
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"[CONFIG] Error crítico: No se encontró el archivo en {CONFIG_PATH}")
        return {"zonas": {}}
    except Exception as e:
        logger.error(f"[CONFIG] Error inesperado al leer YAML: {str(e)}")
        return {"zonas": {}}

# --- LÓGICA MQTT CON CALLBACKS DE ESTADO ---
# Usamos CallbackAPIVersion.VERSION2 para evitar DeprecationWarnings [6].
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, rc, properties):
    """Callback para verificar la conexión con el broker [7, 8]."""
    if rc == 0:
        logger.info(f"[MQTT] Conexión establecida exitosamente con el broker en {MQTT_BROKER}:{MQTT_PORT}")
    else:
        logger.error(f"[MQTT] Fallo en la conexión. Código de error: {rc}")

def on_publish(client, userdata, mid, reason_code, properties):
    """Log de confirmación de publicación de mensaje."""
    logger.debug(f"[MQTT] Mensaje publicado exitosamente (ID: {mid})")

mqtt_client.on_connect = on_connect
mqtt_client.on_publish = on_publish

try:
    logger.info(f"[MQTT] Intentando conectar al broker...")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start() # Mantiene la comunicación asíncrona [9]
except Exception as e:
    logger.error(f"[MQTT] No se pudo iniciar el cliente: {str(e)}")

# --- RUTAS DE LA API ---

@app.route('/')
def index():
    """Renderiza la UI y loguea el acceso."""
    data = load_config()
    logger.info("[HTTP] Acceso a la interfaz principal detectado.")
    return render_template('index.html', zonas=data.get('zonas', {}))

@app.route('/toggle/<zona>/<dispositivo>', methods=['POST'])
def toggle_device(zona, dispositivo):
    """Despachador de comandos individuales con logs de acción [10]."""
    data = load_config()
    try:
        device = data['zonas'][zona]['dispositivos'][dispositivo]
        nuevo_estado = not device['estado']
        device['estado'] = nuevo_estado
        
        # Persistencia simple en YAML
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(data, f)
        
        # Publicación del comando real
        topic = device['topico_comando']
        payload = json.dumps({"power": "on" if nuevo_estado else "off"})
        
        mqtt_client.publish(topic, payload)
        logger.info(f"[ACTION] {dispositivo} ({zona}) -> Nuevo estado: {'ENCENDIDO' if nuevo_estado else 'APAGADO'}")
        logger.info(f"[MQTT] Publicado en tópico: {topic} | Payload: {payload}")
        
        return jsonify({"success": True, "estado": nuevo_estado})
    except KeyError:
        logger.warning(f"[API] Intento de acceso a dispositivo inexistente: {zona}/{dispositivo}")
        return jsonify({"success": False, "error": "Dispositivo no encontrado"}), 404
    except Exception as e:
        logger.error(f"[API] Error al procesar toggle: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    logger.info("[SYSTEM] Iniciando servidor Flask en modo desarrollo...")
    # Escuchamos en 0.0.0.0 para permitir acceso desde el móvil en la misma red [11].
    app.run(host='0.0.0.0', port=5000, debug=True)