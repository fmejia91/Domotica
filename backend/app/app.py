import os
import yaml
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Ruta del archivo de configuración
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'settings.yaml')

def cargar_configuracion():
    """Carga la estructura de zonas y dispositivos desde el archivo YAML."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            # Retornamos solo el diccionario de zonas
            return config.get('zonas', {})
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo en {CONFIG_PATH}. Inicializando vacío.")
        return {}
    except yaml.YAMLError as e:
        print(f"Error al parsear el archivo YAML: {e}")
        return {}

# Mantenemos el estado del sistema en memoria global para esta fase de desarrollo
# En producción, esto se consultaría y guardaría en una Base de Datos o mediante MQTT
ESTADO_DOMOTICA = cargar_configuracion()


# =====================================================================
# RUTAS RESTful / ENDPOINTS
# =====================================================================

@app.route('/')
def index():
    """
    Ruta principal: Renderiza la interfaz gráfica HTML de la app de Smart Home.
    Envía el estado actual de los dispositivos para que el frontend se dibuje
    con los switches en su posición correcta (on/off).
    """
    # Renderiza index.html pasando el estado actual de la domótica
    return render_template('index.html', zonas=ESTADO_DOMOTICA)


@app.route('/api/estado', methods=['GET'])
def obtener_estado_json():
    """Endpoint auxiliar para obtener el estado completo de la casa en JSON."""
    return jsonify({"status": "success", "data": ESTADO_DOMOTICA}), 200


@app.route('/toggle/<zona>/<dispositivo>', methods=['POST'])
def toggle_dispositivo(zona, dispositivo):
    """
    Cambia (invierte) el estado de un dispositivo específico.
    Ejemplo: POST /toggle/entrada/luz_entrada
    """
    # Validar si la zona existe en nuestro estado
    if zona not in ESTADO_DOMOTICA:
        return jsonify({"status": "error", "message": f"La zona '{zona}' no existe."}), 404
        
    # Validar si el dispositivo existe en dicha zona
    if dispositivo not in ESTADO_DOMOTICA[zona]['dispositivos']:
        return jsonify({"status": "error", "message": f"El dispositivo '{dispositivo}' no existe en la zona '{zona}'."}), 404

    # Realizar el toggle (invertir el valor booleano)
    estado_actual = ESTADO_DOMOTICA[zona]['dispositivos'][dispositivo]['estado']
    nuevo_estado = not estado_actual
    ESTADO_DOMOTICA[zona]['dispositivos'][dispositivo]['estado'] = nuevo_estado

    # Aquí es donde en el futuro enviarías un comando MQTT: client.publish(f"casa/{zona}/{dispositivo}", "1" if nuevo_estado else "0")

    return jsonify({
        "status": "success",
        "message": f"Estado de {dispositivo} cambiado con éxito.",
        "zona": zona,
        "dispositivo": dispositivo,
        "nuevo_estado": nuevo_estado
    }), 200


@app.route('/zona/maestro/<nombre_zona>', methods=['POST'])
def control_maestro_zona(nombre_zona):
    """
    Control masivo para encender o apagar todos los dispositivos de una zona a la vez.
    Espera un JSON en el cuerpo de la petición con el estado objetivo.
    Ejemplo Body JSON: {"accion": "apagar"} o {"accion": "encender"}
    """
    # Validar si la zona existe
    if nombre_zona not in ESTADO_DOMOTICA:
        return jsonify({"status": "error", "message": f"La zona '{nombre_zona}' no existe."}), 404

    # Obtener la acción del cuerpo de la solicitud
    datos = request.get_json() or {}
    accion = datos.get('accion')

    if accion not in ['encender', 'apagar']:
        return jsonify({"status": "error", "message": "Acción inválida. Use 'encender' o 'apagar'."}), 400

    # Determinar el estado booleano objetivo
    estado_objetivo = True if accion == 'encender' else False

    # Modificar de forma masiva todos los dispositivos dentro de la zona seleccionada
    for disp_id in ESTADO_DOMOTICA[nombre_zona]['dispositivos']:
        ESTADO_DOMOTICA[nombre_zona]['dispositivos'][disp_id]['estado'] = estado_objetivo

    return jsonify({
        "status": "success",
        "message": f"Control maestro ejecutado: Todos los dispositivos de '{nombre_zona}' se han cambiado a {accion}.",
        "zona": nombre_zona,
        "estado_dispositivos": estado_objetivo
    }), 200


# =====================================================================
# EJECUCIÓN DEL SERVIDOR
# =====================================================================
if __name__ == '__main__':
    # Ejecutar en modo debug para desarrollo local en WSL 2
    # Escucha en 0.0.0.0 para que puedas acceder desde el navegador de Windows usando localhost:5000
    app.run(host='0.0.0.0', port=5000, debug=True)