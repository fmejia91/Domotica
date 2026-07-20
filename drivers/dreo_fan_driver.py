import yaml
import json
import requests
import logging
import paho.mqtt.client as mqtt
import time

# --- CONFIGURACIÓN DE LOGS (Crucial para ver qué sucede) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("DreoDriver")

# --- CONSTANTES Y RUTAS ---
# URL específica para la región de Europa [5]
DREO_API_URL = "https://app-api-eu.dreo-cloud.com/"
CONFIG_PATH = "config/settings.yaml"

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"No se pudo cargar el archivo de configuración: {e}")
        return None

class DreoFanDriver:
    def __init__(self, config):
        self.config = config
        self.token = None
        self.user_id = None
        
        # Datos del dispositivo (Extraídos del YAML)
        self.device_config = config['zonas']['sala']['dispositivos']['ventilador_dreo']
        self.mqtt_topic = self.device_config['topico_comando']
        
        # Cliente MQTT (Sintaxis para paho-mqtt 2.x [6])
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message

    def login(self):
        """Fase 1: Autenticación REST con Dreo Europa [3]"""
        logger.info("[DREO] Intentando autenticación en la nube de Europa...")
        # Nota: Aquí deberías usar las credenciales de tu cuenta de la app móvil [7, 8]
        payload = {
            "email": "fabian.mejia91@gmail.com", # Reemplazar con datos reales o del YAML
            "password": "Fabuloso91"
        }
        
        try:
            # Endpoint simulado según el comportamiento de la API
            response = requests.post(f"{DREO_API_URL}/api/v1/login", json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("accessToken")
                logger.info("[DREO] Login exitoso. Token obtenido.")
                return True
            else:
                logger.error(f"[DREO] Error de autenticación {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"[DREO] Error crítico de red al conectar con Dreo: {e}")
            return False

    def on_mqtt_connect(self, client, userdata, flags, rc, properties):
        if rc == 0:
            logger.info(f"[MQTT] Conectado al broker local. Suscribiendo a {self.mqtt_topic}...")
            client.subscribe(self.mqtt_topic)
        else:
            logger.error(f"[MQTT] Error de conexión al broker. Código: {rc}")

    def on_mqtt_message(self, client, userdata, msg):
        """Procesa comandos recibidos desde el Backend (Flask) [9]"""
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"[COMMAND] Recibido de MQTT: {payload}")
            
            # Aquí se enviaría la petición HTTP/WebSocket a Dreo para ejecutar la acción [9]
            # Ejemplo: self.send_dreo_command(payload)
            logger.info(f"[DREO] Enviando comando a la nube: {payload}")
            
        except Exception as e:
            logger.error(f"Error procesando mensaje MQTT: {e}")

    def run(self):
        if self.login():
            try:
                self.mqtt_client.connect("localhost", 1883, 60)
                logger.info("[SYSTEM] Driver en ejecución y escuchando eventos...")
                self.mqtt_client.loop_forever()
            except Exception as e:
                logger.error(f"[SYSTEM] No se pudo conectar al broker MQTT: {e}")
        else:
            logger.critical("[SYSTEM] Abortando inicio por falta de autenticación.")

if __name__ == "__main__":
    conf = load_config()
    if conf:
        driver = DreoFanDriver(conf)
        driver.run()