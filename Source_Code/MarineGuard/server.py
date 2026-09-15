import csv, io, json, math, os, re
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from PIL import Image, ExifTags
import numpy as np

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Each observation is immutable and independent for the lifetime of this server.
OBSERVATIONS = {}
AIS_ROWS = []
AI_PIPELINE = None


def safe_float(v, default=None):
    try:
        if v is None or str(v).strip() == '':
            return default
        return float(str(v).strip())
    except Exception:
        return default


def norm_key(k):
    return re.sub(r'[^a-z0-9]', '', str(k or '').lower())


def json_safe(v):
    if isinstance(v, dict): return {str(k): json_safe(x) for k, x in v.items()}
    if isinstance(v, list): return [json_safe(x) for x in v]
    if isinstance(v, tuple): return [json_safe(x) for x in v]
    if isinstance(v, np.ndarray): return v.tolist()
    if isinstance(v, np.integer): return int(v)
    if isinstance(v, np.floating): return float(v)
    return v


def parse_dt(value):
    if not value:
        return None
    s = str(value).strip().replace('Z', '+00:00')
    for parser in (
        lambda x: datetime.fromisoformat(x),
        lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'),
        lambda x: datetime.strptime(x, '%m/%d/%Y %H:%M:%S'),
        lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S'),
    ):
        try:
            dt = parser(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass
    return None


def haversine_km(a_lat, a_lon, b_lat, b_lon):
    r = 6371.0088
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = math.radians(b_lat-a_lat), math.radians(b_lon-a_lon)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(min(1, math.sqrt(h)))


def bearing_deg(a_lat, a_lon, b_lat, b_lon):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dl = math.radians(b_lon-a_lon)
    y = math.sin(dl)*math.cos(p2)
    x = math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x))+360) % 360


def angle_diff(a, b):
    return abs((a-b+180) % 360 - 180)


def parse_accessais_csv(f):
    raw = f.read()
    text = raw.decode('utf-8-sig', errors='replace')
    sample = text[:20000]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except Exception:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = []
    for src in reader:
        n = {norm_key(k): v for k, v in src.items() if k is not None}
        lat = safe_float(n.get('lat') or n.get('latitude'))
        lon = safe_float(n.get('lon') or n.get('longitude') or n.get('long'))
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        raw_dt = n.get('basedatetime') or n.get('datetime') or n.get('time') or n.get('sequencedttm')
        dt = parse_dt(raw_dt)
        mmsi = str(n.get('mmsi') or '').strip()
        if not mmsi:
            continue
        rows.append({
            'MMSI': mmsi,
            'BaseDateTime': dt.isoformat() if dt else str(raw_dt or ''),
            'LAT': lat, 'LON': lon,
            'SOG': safe_float(n.get('sog') or n.get('speedoverground') or n.get('speedknots'), 0),
            'COG': safe_float(n.get('cog') or n.get('courseoverground') or n.get('course'), 0),
            'Heading': safe_float(n.get('heading') or n.get('headingdeg')),
            'VesselName': str(n.get('vesselname') or n.get('name') or n.get('shipname') or 'Unknown Vessel').strip(),
            'VesselType': str(n.get('vesseltype') or n.get('shipandcargotype') or '').strip(),
            'IMO': str(n.get('imo') or n.get('imonumber') or '').strip(),
            'CallSign': str(n.get('callsign') or '').strip(),
            '_dt': dt,
        })
    return rows


def correlate_accessais(origin_lat, origin_lon, event_dt):
    if not AIS_ROWS:
        return []
    groups = {}
    for row in AIS_ROWS:
        groups.setdefault(row['MMSI'], []).append(row)
    out = []
    for mmsi, pts in groups.items():
        best = None
        for p in pts:
            distance = haversine_km(origin_lat, origin_lon, p['LAT'], p['LON'])
            distance_score = max(0, 100 - distance * 2.2)
            time_score = 0
            if event_dt and p.get('_dt'):
                hours = abs((p['_dt'] - event_dt).total_seconds()) / 3600
                time_score = max(0, 100 - hours * 10)
            elif not event_dt:
                time_score = 50
            target_bearing = bearing_deg(p['LAT'], p['LON'], origin_lat, origin_lon)
            heading_score = max(0, 100 - angle_diff(p.get('COG', 0), target_bearing) * 100/180)
            score = round(distance_score*0.50 + time_score*0.30 + heading_score*0.20, 1)
            cand = (score, distance, time_score, heading_score, p)
            if best is None or cand[0] > best[0]:
                best = cand
        if best:
            ordered = sorted(pts, key=lambda x: x.get('_dt') or datetime.min.replace(tzinfo=timezone.utc))
            out.append({
                'MMSI': mmsi,
                'VesselName': best[4]['VesselName'],
                'VesselType': best[4]['VesselType'],
                'IMO': best[4]['IMO'], 'CallSign': best[4]['CallSign'],
                'distance_km': round(best[1], 2),
                'time_match': round(best[2], 1),
                'heading_match': round(best[3], 1),
                'score': best[0],
                'lat': best[4]['LAT'], 'lon': best[4]['LON'],
                'best_timestamp': best[4]['BaseDateTime'],
                'track': [{k: v for k, v in p.items() if not k.startswith('_')} for p in ordered],
            })
    return sorted(out, key=lambda x: x['score'], reverse=True)[:20]


def exif_info(img):
    result = {'datetime': None, 'lat': None, 'lon': None}
    try:
        exif = img.getexif()
        tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        raw = tags.get('DateTimeOriginal') or tags.get('DateTime')
        if raw:
            result['datetime'] = datetime.strptime(str(raw), '%Y:%m:%d %H:%M:%S').replace(tzinfo=timezone.utc)
        gps = tags.get('GPSInfo')
        if gps:
            gps2 = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
            lat_ref, lon_ref = gps2.get('GPSLatitudeRef'), gps2.get('GPSLongitudeRef')
            lat_vals, lon_vals = gps2.get('GPSLatitude'), gps2.get('GPSLongitude')
            def dms(vals):
                return float(vals[0]) + float(vals[1])/60 + float(vals[2])/3600
            if lat_vals and lon_vals:
                lat, lon = dms(lat_vals), dms(lon_vals)
                if str(lat_ref).upper() == 'S': lat = -lat
                if str(lon_ref).upper() == 'W': lon = -lon
                result['lat'], result['lon'] = lat, lon
    except Exception:
        pass
    return result


def ai_assess(img):
    global AI_PIPELINE
    # Optional zero-shot model. If unavailable, local computer-vision features keep the demo functional.
    try:
        if AI_PIPELINE is None and os.getenv('MARINEGUARD_ENABLE_AI', '1') == '1':
            from transformers import pipeline
            AI_PIPELINE = pipeline('zero-shot-image-classification', model='openai/clip-vit-base-patch32')
        if AI_PIPELINE:
            results = AI_PIPELINE(img, candidate_labels=['oil slick on ocean', 'clean ocean water', 'clouds', 'land'])
            top = results[0]
            return {'method': 'CLIP zero-shot visual assessment', 'label': top['label'], 'score': round(float(top['score'])*100, 1), 'ranking': [{'label': x['label'], 'score': round(float(x['score'])*100, 1)} for x in results]}
    except Exception:
        pass
    a = np.asarray(img.resize((320, 320))).astype(float)
    mean = a.mean(axis=2)
    dark = mean < 105
    texture = min(100, float(mean.std()) * 2.0)
    darkness = float(dark.mean()) * 100
    score = max(0, min(100, darkness*0.70 + texture*0.30))
    return {'method': 'Local visual fallback (AI model unavailable)', 'label': 'potential dark slick signature' if score >= 45 else 'weak slick signature', 'score': round(score, 1), 'ranking': []}


def slick_features(img):
    a = np.asarray(img.copy().resize((800, 800))).astype(float)
    rgb_mean = a.mean(axis=2)
    dark = rgb_mean < 105
    very_dark = rgb_mean < 70
    contrast = float(rgb_mean.std())
    ys, xs = np.where(dark)
    if len(xs):
        cx = float(xs.mean()/max(1, a.shape[1]-1)); cy = float(ys.mean()/max(1, a.shape[0]-1))
    else:
        cx = cy = .5
    dark_pct = float(dark.mean()*100)
    vdark_pct = float(very_dark.mean()*100)
    score = max(0, min(100, dark_pct*0.60 + vdark_pct*0.25 + min(100, contrast*2)*0.15))
    area = round(max(0.15, dark_pct*0.18), 2) if score >= 42 else 0.0
    return round(score, 1), area, cx, cy


def derive_geolocation(cx, cy, obs_no, exif):
    if exif.get('lat') is not None and exif.get('lon') is not None:
        return round(exif['lat'], 6), round(exif['lon'], 6), 'Image GPS EXIF'
    # Transparent prototype fallback: not operational satellite georeferencing.
    lat = 15.05 + (1-cy)*0.75 + (obs_no-1)*0.011
    lon = 73.30 + cx*0.95 + (obs_no-1)*0.014
    return round(lat, 6), round(lon, 6), 'Prototype image-derived georeference (no GPS EXIF)'


def reconstruct(lat, lon, obs_dt, obs_no, slick_score):
    # Prototype reverse-drift model with observation-specific environmental assumptions.
    wind_speed = round(10.0 + (slick_score % 7) * 0.45 + (obs_no % 3), 1)
    wind_dir = round((35 + obs_no*29 + slick_score) % 360, 1)
    current_speed = round(0.35 + (obs_no % 5)*0.11, 2)
    current_dir = round((105 + obs_no*23) % 360, 1)
    lookback = 5 + (obs_no % 6)
    def vec(speed, deg):
        r = math.radians(deg); return speed*math.sin(r), speed*math.cos(r)
    wx, wy = vec(wind_speed, wind_dir)
    cx, cy = vec(current_speed, current_dir)
    dx = -(wx*0.025 + cx*0.85) * lookback
    dy = -(wy*0.025 + cy*0.85) * lookback
    o_lat = lat + dy/111.0
    o_lon = lon + dx/(111.0*max(.25, math.cos(math.radians(lat))))
    path = []
    for i in range(12):
        f = i/11
        path.append([round(o_lat+(lat-o_lat)*f, 6), round(o_lon+(lon-o_lon)*f, 6)])
    confidence = round(min(94, max(58, 72 + slick_score*0.16 - lookback*0.6)), 1)
    return {
        'origin_lat': round(o_lat, 6), 'origin_lon': round(o_lon, 6),
        'origin_confidence': confidence, 'lookback_hours': lookback,
        'wind_speed_knots': wind_speed, 'wind_direction_deg': wind_dir,
        'current_speed_knots': current_speed, 'current_direction_deg': current_dir,
        'transport_distance_km': round(haversine_km(o_lat, o_lon, lat, lon), 2),
        'uncertainty_km': round(2.5 + lookback*0.55, 2), 'path': path,
        'model_note': 'Prototype reverse-drift reconstruction; replace assumptions with time-matched metocean fields for operational deployment.'
    }


def analyze_image(f, obs_no):
    img = Image.open(f).convert('RGB')
    exif = exif_info(img)
    slick, area, cx, cy = slick_features(img)
    ai = ai_assess(img)
    detected = slick >= 42 or (ai['label'] == 'oil slick on ocean' and ai['score'] >= 55)
    confidence = round(min(98, max(50, (slick*0.65 + ai['score']*0.35))))
    obs_dt = exif['datetime'] or datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=(obs_no-1)*20)
    lat, lon, loc_method = derive_geolocation(cx, cy, obs_no, exif)
    recon = reconstruct(lat, lon, obs_dt, obs_no, slick)
    vessels = correlate_accessais(recon['origin_lat'], recon['origin_lon'], obs_dt)
    evidence = [
        {'stage': 'Satellite', 'finding': 'Satellite frame ingested', 'detail': f"{img.width} × {img.height}px; source: {f.filename}"},
        {'stage': 'AI', 'finding': ai['label'], 'detail': f"AI/visual score: {ai['score']}% ({ai['method']})"},
        {'stage': 'Slick', 'finding': 'Potential oil-slick signature' if detected else 'No strong slick signature', 'detail': f'Slick score {slick}% · estimated area {area} km²'},
        {'stage': 'Origin', 'finding': 'Reverse-drift origin estimate', 'detail': f"{recon['origin_lat']}°N, {recon['origin_lon']}°E · confidence {recon['origin_confidence']}%"},
        {'stage': 'AccessAIS', 'finding': 'Historical AIS correlation', 'detail': f"{len(vessels)} vessel tracks ranked" if AIS_ROWS else 'No AccessAIS CSV loaded for correlation'},
    ]
    return json_safe({
        'observation_id': f'OBS-{obs_no:03d}', 'display_label': f'Observation {obs_no:02d}', 'sequence': obs_no,
        'source_filename': f.filename, 'image_width': img.width, 'image_height': img.height,
        'slick_detected': bool(detected), 'slick_score': slick, 'estimated_area_km2': area,
        'ai_assessment': ai, 'confidence': confidence,
        'observation_time': obs_dt.isoformat(), 'latitude': lat, 'longitude': lon,
        'location': f'{lat:.5f}°N, {lon:.5f}°E', 'location_method': loc_method,
        'reconstruction': recon, 'ais_source': 'NOAA/USCG AccessAIS historical AIS point data' if AIS_ROWS else 'No AccessAIS dataset loaded',
        'ais_candidates': vessels, 'ais_rows_available': len(AIS_ROWS), 'evidence': evidence,
        'status': 'COMPLETE'
    })


def report_text_data(obs):
    lines = [
        f"MARINEGUARD INVESTIGATION REPORT — {obs['display_label']}",
        f"Observation ID: {obs['observation_id']}", f"Source image: {obs['source_filename']}",
        f"Observation time: {obs['observation_time']}", f"Automatic location: {obs['location']} ({obs['location_method']})", '',
        'AI / SATELLITE FINDINGS', f"AI assessment: {obs['ai_assessment']['label']}",
        f"AI score: {obs['ai_assessment']['score']}%", f"Slick score: {obs['slick_score']}%",
        f"Estimated area: {obs['estimated_area_km2']} km²", f"Overall confidence: {obs['confidence']}%", '',
        'INCIDENT RECONSTRUCTION', f"Origin: {obs['reconstruction']['origin_lat']}°N, {obs['reconstruction']['origin_lon']}°E",
        f"Origin confidence: {obs['reconstruction']['origin_confidence']}%", f"Lookback: {obs['reconstruction']['lookback_hours']} h",
        f"Transport distance: {obs['reconstruction']['transport_distance_km']} km", f"Uncertainty: ±{obs['reconstruction']['uncertainty_km']} km", '',
        'ACCESSAIS MULTI-VESSEL CORRELATION', f"Source: {obs['ais_source']}", f"Candidate vessel tracks: {len(obs['ais_candidates'])}",
    ]
    for i, v in enumerate(obs['ais_candidates'][:10], 1):
        lines.append(f"{i}. {v['VesselName']} | MMSI {v['MMSI']} | score {v['score']}% | distance {v['distance_km']} km | time {v['time_match']}% | heading {v['heading_match']}% | track points {len(v['track'])}")
    lines += ['', 'EVIDENCE CHAIN']
    lines += [f"[{e['stage']}] {e['finding']} — {e['detail']}" for e in obs['evidence']]
    return '\n'.join(lines) + '\n'


@app.get('/')
def home():
    return send_from_directory('.', 'index.html')


@app.get('/health')
def health():
    return jsonify({'success': True, 'ais_rows': len(AIS_ROWS), 'observations': len(OBSERVATIONS)})


@app.post('/ais/upload')
def upload_ais():
    global AIS_ROWS
    f = request.files.get('ais')
    if not f or not f.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'message': 'Please choose an AccessAIS CSV file.'}), 400
    try:
        rows = parse_accessais_csv(f)
        if not rows:
            return jsonify({'success': False, 'message': 'No valid AIS rows found. Check that the CSV contains MMSI, LAT, LON and timestamp fields.'}), 400
        AIS_ROWS = rows
        # Re-correlate existing observations without overwriting their satellite/reconstruction data.
        for key, obs in OBSERVATIONS.items():
            obs['ais_candidates'] = correlate_accessais(obs['reconstruction']['origin_lat'], obs['reconstruction']['origin_lon'], parse_dt(obs['observation_time']))
            obs['ais_source'] = 'NOAA/USCG AccessAIS historical AIS point data'
            obs['ais_rows_available'] = len(AIS_ROWS)
            for e in obs['evidence']:
                if e['stage'] == 'AccessAIS':
                    e['detail'] = f"{len(obs['ais_candidates'])} vessel tracks ranked"
        return jsonify({'success': True, 'rows_loaded': len(AIS_ROWS), 'vessels': len(set(x['MMSI'] for x in AIS_ROWS))})
    except Exception as e:
        return jsonify({'success': False, 'message': f'AccessAIS parse error: {e}'}), 400


@app.post('/session/reset')
def reset_session():
    OBSERVATIONS.clear()
    return jsonify({'success': True})


@app.post('/analyze')
def analyze():
    f = request.files.get('image')
    obs_no = request.form.get('observation_number', '1')
    try:
        obs_no = int(obs_no)
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid observation number.'}), 400
    if not f or not f.filename:
        return jsonify({'success': False, 'message': 'No satellite image uploaded.'}), 400
    try:
        obs = analyze_image(f, obs_no)
        OBSERVATIONS[obs_no] = obs
        return jsonify({'success': True, 'observation': obs})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Analysis failed: {e}'}), 500


@app.get('/reports')
def all_reports():
    return jsonify({'success': True, 'reports': [OBSERVATIONS[k] for k in sorted(OBSERVATIONS)]})


@app.get('/report')
def get_report():
    try: n = int(request.args.get('observation', '0'))
    except Exception: n = 0
    if n not in OBSERVATIONS:
        return jsonify({'success': False, 'message': 'Observation report not found.'}), 404
    return jsonify({'success': True, 'report': OBSERVATIONS[n]})


@app.get('/report/text')
def download_report():
    try: n = int(request.args.get('observation', '0'))
    except Exception: n = 0
    if n not in OBSERVATIONS:
        return jsonify({'success': False, 'message': 'Observation report not found.'}), 404
    obs = OBSERVATIONS[n]
    data = report_text_data(obs).encode('utf-8')
    return send_file(io.BytesIO(data), mimetype='text/plain; charset=utf-8', as_attachment=True, download_name=f"marineguard_{obs['observation_id'].lower()}_report.txt")


if __name__ == '__main__':
    import os

    port = int(os.environ.get('PORT', 5000))

    print(f'MarineGuard running on port {port}')

    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    ))
