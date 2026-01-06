import os
import json
import base64
import math
import time
import requests
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import mediapipe as mp
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- 1. CONFIGURATION ---remove spaces between the dots in token 
DISCORD_TOKEN = "MTQ1NzY2MjUzMzYwNjQ0NTE0NQ . GBVSbj . U1B7LL3Hg0034FxhqWNLSoLaGB3u1cegnPNuYQ"
CHANNEL_ID = "1457670836193464434"
FIREBASE_KEY = os.environ.get("FIREBASE_KEY_JSON") 

# --- 2. FIREBASE INIT ---
if not firebase_admin._apps:
    if FIREBASE_KEY:
        cred = credentials.Certificate(json.loads(FIREBASE_KEY))
        firebase_admin.initialize_app(cred)
    elif os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    else:
        print("⚠️ No Database Key Found! Running Offline.")

db = firestore.client() if firebase_admin._apps else None

# --- 3. DISCORD STORAGE ENGINE ---
class DiscordStorage:
    def __init__(self, token, channel_id):
        self.base_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        self.headers = {"Authorization": f"Bot {token}"}

    def upload_image(self, filename, img_bytes):
        if not self.headers['Authorization']: return None
        files = {'file': (filename, img_bytes, 'image/jpeg')}
        try:
            r = requests.post(self.base_url, headers=self.headers, files=files)
            if r.status_code == 200:
                return r.json()['id']
        except Exception as e: print(f"Error: {e}")
        return None

    def get_fresh_url(self, msg_id):
        if not self.headers['Authorization']: return None
        try:
            r = requests.get(f"{self.base_url}/{msg_id}", headers=self.headers)
            if r.status_code == 200:
                attachments = r.json().get('attachments', [])
                if attachments: return attachments[0]['url']
        except: pass
        return None

storage = DiscordStorage(DISCORD_TOKEN, CHANNEL_ID)

# --- 4. AI & LIVENESS SETUP ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5)
face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
recognizer = cv2.face.LBPHFaceRecognizer_create()

LOCAL_DB = "local_db"
if not os.path.exists(LOCAL_DB): os.makedirs(LOCAL_DB)
known_names = {}

# --- STATE TRACKING ---
# 0 = Waiting for Blink
# 1 = Blink Detected (Waiting for Smile)
# 2 = Verified
user_states = {} 

def calculate_distance(p1, p2):
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)

def get_eye_ratio(landmarks, eye_points):
    """Calculates Eye Aspect Ratio (EAR) to detect blinking"""
    v1 = calculate_distance(landmarks[eye_points[1]], landmarks[eye_points[5]])
    v2 = calculate_distance(landmarks[eye_points[2]], landmarks[eye_points[4]])
    h = calculate_distance(landmarks[eye_points[0]], landmarks[eye_points[3]])
    return (v1 + v2) / (2.0 * h) if h > 0 else 0

def check_liveness_blink_smile(landmarks, ip_address):
    """
    FLOW:
    1. Detect BLINK (EAR < 0.22) -> Proves Liveness
    2. Detect SMIRK/SMILE -> Triggers Log
    """
    if ip_address not in user_states:
        user_states[ip_address] = {'stage': 0, 'last_update': datetime.now()}

    current_stage = user_states[ip_address]['stage']
    
    # 1. BLINK CHECK
    left_eye_idxs = [33, 160, 158, 133, 153, 144]
    right_eye_idxs = [362, 385, 387, 263, 373, 380]
    
    left_ear = get_eye_ratio(landmarks, left_eye_idxs)
    right_ear = get_eye_ratio(landmarks, right_eye_idxs)
    avg_ear = (left_ear + right_ear) / 2.0

    # 2. SMILE/SMIRK CHECK
    mouth_left = landmarks[61]
    mouth_right = landmarks[291]
    face_left = landmarks[234]
    face_right = landmarks[454]
    
    mouth_w = calculate_distance(mouth_left, mouth_right)
    face_w = calculate_distance(face_left, face_right)
    mouth_ratio = mouth_w / face_w
    
    corner_avg_y = (mouth_left.y + mouth_right.y) / 2
    lip_center_y = landmarks[13].y
    is_smirking = (mouth_ratio > 0.38) or (corner_avg_y <= lip_center_y + 0.03)

    # LOGIC FLOW
    if current_stage == 0:
        if avg_ear < 0.22: # Blink Threshold
            user_states[ip_address]['stage'] = 1
            return False, "Blink Detected! Now Smile."
        else:
            return False, "Please Blink to verify liveness"

    elif current_stage == 1:
        if is_smirking:
            user_states[ip_address]['stage'] = 2
            return True, "Verified"
        else:
            return False, "Blink Confirmed. Now Smile!"

    return True, "Verified"

# --- 5. SYNC ON STARTUP ---
def sync_on_startup():
    print("⏳ Background Sync Started...")
    if not db: return
    try:
        users = db.collection('Users').stream()
        faces, ids = [], []
        for doc in users:
            data = doc.to_dict()
            msg_id = data.get('discord_msg_id')
            name = data.get('name')
            uid = data.get('id')
            if msg_id:
                filename = f"{name}_{uid}.jpg"
                local_path = os.path.join(LOCAL_DB, filename)
                if not os.path.exists(local_path):
                    fresh_url = storage.get_fresh_url(msg_id)
                    if fresh_url:
                        try:
                            with open(local_path, "wb") as f:
                                f.write(requests.get(fresh_url).content)
                            time.sleep(0.1) 
                        except: pass
                if os.path.exists(local_path):
                    try:
                        img = cv2.imread(local_path, cv2.IMREAD_GRAYSCALE)
                        dets = face_classifier.detectMultiScale(img, 1.1, 5)
                        for (x,y,w,h) in dets:
                            faces.append(img[y:y+h, x:x+w])
                            ids.append(int(uid))
                            known_names[str(uid)] = name
                    except: pass
        if faces:
            recognizer.train(faces, np.array(ids))
            print(f"✅ Brain Restored! Known Users: {len(known_names)}")
    except Exception as e: print(f"❌ Background Sync Error: {e}")

# --- 6. ROUTES ---
@app.route('/')
def dashboard(): return render_template('dashboard.html')

@app.route('/register')
def register(): return render_template('register.html')

@app.route('/calendar')
def calendar(): return render_template('calendar.html')

@app.route('/process_frame', methods=['POST'])
def process():
    try:
        user_ip = request.remote_addr
        
        # Timeout Reset (15s inactivity)
        if user_ip in user_states:
            if (datetime.now() - user_states[user_ip]['last_update']).total_seconds() > 15:
                user_states[user_ip]['stage'] = 0
            user_states[user_ip]['last_update'] = datetime.now()

        data = request.json
        _, encoded = data['image'].split(",", 1)
        frame = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), cv2.IMREAD_COLOR)
        
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(img_rgb)
        status, name, uid, color = "Scanning...", "Unknown", "--", "gray"
        
        if results.multi_face_landmarks:
            is_live, msg = check_liveness_blink_smile(results.multi_face_landmarks[0].landmark, user_ip)
            
            if is_live:
                # Recognition
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_classifier.detectMultiScale(gray, 1.1, 4)
                for (x,y,w,h) in faces:
                    if len(known_names) > 0:
                        id_pred, conf = recognizer.predict(gray[y:y+h, x:x+w])
                        if conf < 85:
                            uid = str(id_pred)
                            name = known_names.get(uid, "Unknown")
                
                if name != "Unknown":
                    # --- CHANGE MADE HERE: Added ID to the Status String ---
                    status, color = f"VERIFIED: {name} (ID: {uid})", "green"
                    
                    if db:
                        now_str = datetime.now()
                        doc_id = f"{now_str.strftime('%Y-%m-%d')}_{uid}"
                        db.collection('Attendance').document(doc_id).set({
                            'name': name, 'id': int(uid),
                            'date': now_str.strftime('%Y-%m-%d'),
                            'time': now_str.strftime('%I:%M %p'),
                            'timestamp': firestore.SERVER_TIMESTAMP
                        })
                    
                    user_states[user_ip]['stage'] = 0 
                else: status, color = "Unknown Face", "red"
            else: 
                status, color = msg, "yellow"
        else: 
            status, color = "No Face", "gray"
        
        return jsonify({'status': status, 'name': name, 'id': uid, 'color': color})
    except: return jsonify({'status': "Error", 'color': "red"})

@app.route('/save_user', methods=['POST'])
def save_user():
    try:
        data = request.json
        name, uid, b64 = data['name'], data['id'], data['image']
        _, encoded = b64.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        
        msg_id = storage.upload_image(f"{name}_{uid}.jpg", img_bytes)
        
        if msg_id and db:
            db.collection('Users').document(f"{name}_{uid}").set({
                'name': name, 'id': int(uid),
                'discord_msg_id': msg_id
            })
            local_path = os.path.join(LOCAL_DB, f"{name}_{uid}.jpg")
            with open(local_path, "wb") as f: f.write(img_bytes)
            try:
                img = cv2.imread(local_path, cv2.IMREAD_GRAYSCALE)
                dets = face_classifier.detectMultiScale(img, 1.1, 5)
                new_faces, new_ids = [], []
                for (x,y,w,h) in dets:
                    new_faces.append(img[y:y+h, x:x+w])
                    new_ids.append(int(uid))
                if new_faces:
                    recognizer.update(new_faces, np.array(new_ids))
                    known_names[str(uid)] = name
            except: pass
            return jsonify({'message': 'Saved to Cloud!'})
        else:
            return jsonify({'message': 'Cloud Error. Check Token.'})
    except Exception as e: return jsonify({'message': str(e)})

@app.route('/get_attendance_data', methods=['POST'])
def get_attendance_data():
    try:
        user_id = request.json.get('id')
        if not user_id: return jsonify({'error': 'No ID provided'})
        if not db: return jsonify({'dates': [], 'percentage': 0, 'days_present': 0})

        docs = db.collection('Attendance').where('id', '==', int(user_id)).stream()
        present_dates = []
        for doc in docs:
            data = doc.to_dict()
            if 'date' in data: present_dates.append(data['date'])
        
        days_present = len(set(present_dates))
        total_days = 30
        return jsonify({
            'dates': present_dates,
            'percentage': round(min((days_present / total_days) * 100, 100), 1),
            'days_present': days_present
        })
    except: return jsonify({'error': 'Fetch Failed'})

if __name__ == '__main__':
    threading.Thread(target=sync_on_startup, daemon=True).start()
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 Web Server Starting on Port {port}...")
    app.run(host='0.0.0.0', port=port)


