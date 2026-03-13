from flask import Flask, jsonify, request
from flask_cors import CORS
import fastf1
import pandas as pd
import os
import tempfile

app = Flask(__name__)
CORS(app)  # Permette al tuo HTML mobile di chiamare l'API

# Configura cache in directory temporanea (funziona su Render)
cache_dir = tempfile.mkdtemp()
fastf1.Cache.enable_cache(cache_dir)

print("🚀 Backend F1 avviato!")

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'online',
        'message': 'F1 Telemetry API - Pronta per TracingInsights style data'
    })

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    year = request.args.get('year', 2026, type=int)
    gp = request.args.get('gp', 'Chinese')
    session_code = request.args.get('session', 'SQ')
    driver = request.args.get('driver', 'HAM')
    lap = request.args.get('lap', None, type=int)
    
    try:
        # Mappa codici sessione
        session_map = {
            'FP1': 'Practice 1',
            'FP2': 'Practice 2', 
            'FP3': 'Practice 3',
            'Q': 'Qualifying',
            'SQ': 'Sprint Qualifying',
            'S': 'Sprint',
            'R': 'Race'
        }
        
        session_name = session_map.get(session_code, 'Race')
        print(f"📡 Caricamento: {year} {gp} - {session_name} - {driver}")
        
        # Carica sessione con FastF1
        f1_session = fastf1.get_session(year, gp, session_name)
        f1_session.load(telemetry=True, laps=True, weather=False)
        
        # Prendi i giri del pilota
        driver_laps = f1_session.laps.pick_driver(driver)
        
        if driver_laps.empty:
            return jsonify({'error': f'Pilota {driver} non trovato in questa sessione'}), 404
        
        # Seleziona giro
        if lap:
            lap_data = driver_laps[driver_laps['LapNumber'] == lap]
            if lap_data.empty:
                return jsonify({'error': f'Giro {lap} non trovato'}), 404
            lap_data = lap_data.iloc[0]
        else:
            lap_data = driver_laps.pick_fastest()
        
        # Ottieni telemetria
        telemetry = lap_data.get_telemetry().add_distance()
        
        # Calcola metriche stile TracingInsights
        total_time = lap_data['LapTime'].total_seconds()
        
        # Classifica ogni punto
        conditions = []
        for idx, row in telemetry.iterrows():
            if row['Brake'] > 0:
                conditions.append('brake')
            elif row['Throttle'] >= 98:
                if idx > 0 and row['Speed'] > telemetry['Speed'].iloc[idx-1]:
                    conditions.append('full_throttle')
                else:
                    conditions.append('super_clipping')
            elif row['Throttle'] == 0:
                conditions.append('lift_coast')
            else:
                conditions.append('cornering')
        
        from collections import Counter
        counts = Counter(conditions)
        
        result = {
            'driver': driver,
            'driver_full': lap_data['Driver'],
            'lap': int(lap_data['LapNumber']),
            'lap_time': str(lap_data['LapTime']),
            'sectors': {
                's1': str(lap_data['Sector1Time']),
                's2': str(lap_data['Sector2Time']),
                's3': str(lap_data['Sector3Time'])
            },
            'metrics': {
                'full_throttle': round(counts['full_throttle'] / len(conditions) * total_time, 3),
                'super_clipping': round(counts['super_clipping'] / len(conditions) * total_time, 3),
                'lift_coast': round(counts['lift_coast'] / len(conditions) * total_time, 3),
                'brake': round(counts['brake'] / len(conditions) * total_time, 3),
                'cornering': round(counts['cornering'] / len(conditions) * total_time, 3)
            },
            'telemetry': {
                'distance': telemetry['Distance'].tolist(),
                'throttle': telemetry['Throttle'].tolist(),
                'brake': telemetry['Brake'].tolist(),
                'speed': telemetry['Speed'].tolist(),
                'gear': telemetry['nGear'].tolist()
            }
        }
        
        print(f"✅ Dati inviati: {len(telemetry)} punti")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Errore: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    return jsonify([
        {'code': 'FP1', 'name': 'Practice 1'},
        {'code': 'FP2', 'name': 'Practice 2'},
        {'code': 'FP3', 'name': 'Practice 3'},
        {'code': 'Q', 'name': 'Qualifying'},
        {'code': 'SQ', 'name': 'Sprint Qualifying'},
        {'code': 'S', 'name': 'Sprint'},
        {'code': 'R', 'name': 'Race'}
    ])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)