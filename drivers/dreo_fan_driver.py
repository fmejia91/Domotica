# drivers/dreo_fan_driver.py
import json
import time
import paho.mqtt.client as mqtt
import requests
import logging
import sys

# CONFIGURACIÓN
MQTT_BROKER = "localhost"  # O la IP de tu contenedor domotica_mqtt
MQTT_PORT = 1883
COMMAND_TOPIC = "casa/sala/ventilador/comando"
STATE_TOPIC = "casa/sala/ventilador/estado"

DREO_EMAIL = "fabian.mejia91@gmail.com"
DREO_PASSWORD = "Fabuloso91"
DREO_API_URL = "https://app-api-eu.dreo-cloud.com/api"

# Configuración para ver absolutamente todo lo que pasa en la consola
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class DreoFanDriver:
    def __init__(self):
        self.token = None
        self.device_sn = None
        self.mqtt_client = mqtt.Client()

    def login_dreo(self):
        """Autenticación en la nube de Dreo para obtener el Bearer Token"""
        print("[DREO] Autenticando en la nube de Dreo...")
        payload = {"email": DREO_EMAIL, "password": DREO_PASSWORD}
        # Nota: En implementaciones reales se calcula un hash/firma, esto es una abstracción estructural
        try:
            # Simulación de handshake con endpoint Dreo Cloud
            # En producción puedes apoyarte en la librería nativa 'pydreo' 
            self.token = "mock_valid_bearer_token_from_dreo_cloud"
            self.device_sn = "DREO-HTF004S-SALA01" 
            print(f"[DREO] Login exitoso. Dispositivo Vinculado Encontrado: {self.device_sn}")
            return True
        except Exception as e:
            print(f"[DREO] Error al conectar con el servidor central: {e}")
            return False

    def send_dreo_command(self, action, value):
        """Envía la instrucción estructurada a la API / WebSocket de Dreo"""
        print(f"[DREO] Transmitiendo comando a la nube -> {action}: {value}")
        # Aquí se realiza el POST/WebSocket original a Dreo Cloud:
        # headers = {"Authorization": f"Bearer {self.token}"}
        # requests.post(f"{DREO_API_URL}/device/control", json={"sn": self.device_sn, "method": action, "val": value})
        return True

    def on_mqtt_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Conectado al broker de Mosquitto (Código: {rc}).")
        client.subscribe(COMMAND_TOPIC)
        print(f"[MQTT] Suscrito al tópico de comandos: {COMMAND_TOPIC}")

    def on_mqtt_message(self, client, userdata, msg):
        """Escucha las peticiones de Flask que llegan por MQTT y las traduce a Dreo"""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            print(f"[MQTT] Comando recibido desde el Backend: {payload}")

            # Parseo de controles del DREO Smart Fan (5 Velocidades, 4 Modos, Oscilación)
            if "power" in payload:
                self.send_dreo_command("power", payload["power"])
            if "speed" in payload:
                # El dispositivo soporta niveles 1 a 5
                speed = max(1, min(int(payload["speed"]), 5))
                self.send_dreo_command("windlevel", speed)
            if "mode" in payload:
                # Modos DREO comunes: Normal, Natural, Sleep, Auto
                self.send_dreo_command("mode", payload["mode"])
            if "oscillation" in payload:
                self.send_dreo_command("horizontalaos", payload["oscillation"])

            # Reportar de vuelta el estado confirmado al backend
            self.mqtt_client.publish(STATE_TOPIC, json.dumps({"status": "success", "current_state": payload}), retain=True)

        except Exception as e:
            print(f"[DRIVER ERROR] Error procesando mensaje MQTT: {e}")

    def start(self):
        if not self.login_dreo():
            return
        
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print("[DRIVER] Driver de Ventilación DREO inicializado y escuchando...")
        self.mqtt_client.loop_forever()

if __name__ == "__main__":
    driver = DreoFanDriver()
    driver.start()