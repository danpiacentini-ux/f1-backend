from flask import Flask, jsonify, request
from flask_cors import CORS
import fastf1
import pandas as pd
import os
import tempfile

app = Flask(__name__)
CORS(app)

# Configura cache
cache_dir = tempfile.mkdtemp()
fastf1.Cache.enable_cache(cache_dir)

@app.route('/')
def home():
    return jsonify({'status': 'online', 'message': 'F1 Telemetry API'})

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    year = request.args.get('year', 2026, type=int)
    gp = request.args.get('gp', 'Chinese')
    session_code = request.args.get('session', 'SQ')
    driver = request.args.get('driver', 'HAM')
    
    session_map = {
        'FP1': 'Practice 1', 'FP2': 'Practice 2', 'FP3': 'Practice 3',
        'Q': 'Qualifying', 'SQ': 'Sprint Qualifying', 'S': 'Sprint', 'R': 'Race'
    }
    
    session_name = session_map.get(session_code, 'Race')
    
    try:
        f1_session = fastf1.get_session(year, gp, session_name)
        f1_session.load(telemetry=True, laps=True)
        
        driver_laps = f1_session.laps.pick_driver(driver)
        if driver_laps.empty:
            return jsonify({'error': 'Pilota non trovato'}), 404
        
        lap_data = driver_laps.pick_fastest()
        telemetry = lap_data.get_telemetry().add_distance()
        
        result = {
            'driver': driver,
            'lap': int(lap_data['LapNumber']),
            'lap_time': str(lap_data['LapTime']),
            'telemetry': {
                'distance': telemetry['Distance'].tolist(),
                'throttle': telemetry['Throttle'].tolist(),
                'brake': telemetry['Brake'].tolist(),
                'speed': telemetry['Speed'].tolist()
            }
        }
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
