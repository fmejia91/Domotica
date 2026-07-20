import os
import yaml
from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import json


base_dir = os.path.abspath(os.path.dirname(__file__)) # apunta a backend/app/
frontend_dir = os.path.join(base_dir, '../../frontend') # apunta a la raíz y luego a frontend/

app = Flask(__name__, template_folder=frontend_dir, static_folder=frontend_dir)
""" 
app = Flask(__name__, 
            template_folder='frontend',  # Apunta a tus carpetas reales
            static_folder='frontend') """

# -------------------------------------------------------------------------
# CONFIGURACIÓN DEL BROKER MQTT (Contenedor Docker en WSL2)
# -------------------------------------------------------------------------
MQTT_BROKER = "127.0.0.1"  # Al estar en WSL2 y mapear el puerto, localhost es directo
MQTT_PORT = 1883
MQTT_TOPIC_PUBLISH = "domotica/casa/cambio_estado"

mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

def init_mqtt():
    """Inicializa y conecta el cliente MQTT de forma no bloqueante"""
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        # Iniciamos el bucle de red en un hilo separado para no bloquear el servidor Flask
        mqtt_client.loop_start()
        print(f" [*] Puente MQTT conectado exitosamente a {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f" [!] Error crítico al conectar al Broker MQTT: {e}")

# -------------------------------------------------------------------------
# CARGA DE CONFIGURACIÓN DOMÓTICA (YAML)
# -------------------------------------------------------------------------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'settings.yaml')

def cargar_configuracion():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def guardar_configuracion(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
        yaml.safe_dump(config, file, default_flow_style=False, allow_unicode=True)

# -------------------------------------------------------------------------
# RUTAS DEL SERVIDOR WEB & API REST
# -------------------------------------------------------------------------

@app.route('/')
def index():
    """Renderiza la interfaz móvil enviando los estados de los dispositivos"""
    data = cargar_configuracion()
    return render_template('index.html', zonas=data.get('zonas', {}))

@app.route('/toggle/<zona>/<dispositivo_id>', methods=['POST'])
def toggle_dispositivo(zona, dispositivo_id):
    """Cambia el estado de una bombilla y lo publica en el ecosistema MQTT"""
    config = cargar_configuracion()
    zonas = config.get('zonas', {})
    
    if zona in zonas and dispositivo_id in zonas[zona]['dispositivos']:
        # 1. Mutar estado local/memoria
        estado_actual = zonas[zona]['dispositivos'][dispositivo_id]['estado']
        nuevo_estado = not estado_actual
        zonas[zona]['dispositivos'][dispositivo_id]['estado'] = nuevo_estado
        guardar_configuracion(config)
        
        # 2. Generar el Payload de control para los ESP32 (Estructura IoT Limpia)
        payload = {
            "zona": zona,
            "dispositivo": dispositivo_id,
            "estado": "ON" if nuevo_estado else "OFF",
            "tipo": zonas[zona]['dispositivos'][dispositivo_id].get('tipo', 'luz')
        }
        
        # 3. Publicar el mensaje vía MQTT
        # Usamos qos=1 (garantiza que el mensaje llegue al broker al menos una vez)
        mqtt_client.publish(MQTT_TOPIC_PUBLISH, json.dumps(payload), qos=1)
        
        return jsonify({
            "status": "success", 
            "zona": zona, 
            "dispositivo": dispositivo_id, 
            "nuevo_estado": nuevo_estado
        }), 200
        
    return jsonify({"status": "error", "message": "Dispositivo o Zona no encontrada"}), 404

@app.route('/zona/maestro/<zona_nombre>', methods=['POST'])
def maestro_zona(zona_nombre):
    """Control masivo de una zona completa y su respectivo envío MQTT masivo o por ráfaga"""
    req_data = request.get_json() or {}
    forzar_estado = req_data.get('estado') # Espera un booleano (true/false)
    
    config = cargar_configuracion()
    zonas = config.get('zonas', {})
    
    if zona_nombre in zonas:
        dispositivos = zonas[zona_nombre]['dispositivos']
        
        # Si no especifican estado, hacemos un toggle colectivo basado en el primer elemento
        if forzar_estado is None:
            primer_disp = list(dispositivos.keys())[0]
            forzar_estado = not dispositivos[primer_disp]['estado']
            
        # Actualizamos todos los dispositivos de la zona y disparamos comandos MQTT
        for disp_id in dispositivos:
            dispositivos[disp_id]['estado'] = forzar_estado
            
            payload = {
                "zona": zona_nombre,
                "dispositivo": disp_id,
                "estado": "ON" if forzar_estado else "OFF",
                "tipo": dispositivos[disp_id].get('tipo', 'luz')
            }
            mqtt_client.publish(MQTT_TOPIC_PUBLISH, json.dumps(payload), qos=1)
            
        guardar_configuracion(config)
        return jsonify({"status": "success", "zona": zona_nombre, "estado_colectivo": forzar_estado}), 200

    return jsonify({"status": "error", "message": "Zona maestra no válida"}), 404

# -------------------------------------------------------------------------
# ARRANQUE SEGURO
# -------------------------------------------------------------------------
if __name__ == '__main__':
    init_mqtt() # Levantamos el puente MQTT antes del servidor web
    try:
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    finally:
        # Al detener Flask de forma limpia, cerramos el hilo del cliente MQTT
        mqtt_client.loop_stop()
        mqtt_client.disconnect()