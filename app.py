from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
import os
import base64
from datetime import datetime
import mediapipe as mp
import math
import json  # <--- Added for Cloud Security

app = Flask(__name__)

# --- 1. CONFIGURATION (SECURITY UPDATE) ---
# This logic checks if we are on Local (Laptop) or Cloud (Render)
if not firebase_admin._apps:
    # Option A: Local Development (Look for the file)
    if os.path.exists("serviceAccountKey.json"):
        print("🔒 Using Local Key File")
        cred = credentials.Certificate("serviceAccountKey.json")
    
    # Option B: Cloud Deployment (Look for Environment Variable)
    else:
        print("☁️ Using Cloud Environment Variable")
        # Ensure you set 'FIREBASE_KEY_JSON' in Render Settings!
        key_content = os.environ.get('FIREBASE_KEY_JSON')
        if not key_content:
            raise ValueError("Error: FIREBASE_KEY_JSON not found in Environment Variables!")
        
        key_dict = json.loads(key_content)
        cred = credentials.Certificate(key_dict)

    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. AI SETUP ---
mp_face_mesh = mp.solutions.face_mesh
# refine_landmarks=True is REQUIRED for Iris detection
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5)

# Standard Face Classifier for ID Recognition
face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
recognizer = cv2.face.LBPHFaceRecognizer_create()

LOCAL_DB = "local_db"
known_names = {}

# --- 3. HELPER FUNCTIONS ---

def calculate_distance(p1, p2):
    """Calculates Euclidean distance between two MediaPipe landmarks"""
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)

def check_liveness(img):
    """
    Analyzes the face for two specific liveness cues:
    1. Smile (Mouth Width / Face Width ratio)
    2. Gaze (Iris position relative to eye corners)
    """
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(img_rgb)
    
    is_smiling = False
    is_looking = False
    
    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark
        
        # A. Smile Detection
        mouth_left = landmarks[61]
        mouth_right = landmarks[291]
        face_left = landmarks[234]
        face_right = landmarks[454]
        
        mouth_width = calculate_distance(mouth_left, mouth_right)
        face_width = calculate_distance(face_left, face_right)
        
        # If mouth is wide relative to face, user is smiling
        if (mouth_width / face_width) > 0.45: 
            is_smiling = True
            
        # B. Gaze Detection (Iris Tracking)
        left_iris = landmarks[468]
        left_inner = landmarks[33]
        left_outer = landmarks[133]
        
        eye_width = calculate_distance(left_inner, left_outer)
        d_inner = calculate_distance(left_iris, left_inner)
        d_outer = calculate_distance(left_iris, left_outer)
        
        # If iris is centered (not looking sideways)
        if d_inner > 0.3 * eye_width and d_outer > 0.3 * eye_width: 
            is_looking = True
            
        return True, is_smiling, is_looking
    
    return False, False, False

def train_model():
    """Loads images from local_db and trains the recognizer"""
    print("🧠 Training Model...")
    faces, ids = [], []
    
    # Ensure folder exists
    if not os.path.exists(LOCAL_DB): 
        os.makedirs(LOCAL_DB)
    
    for filename in os.listdir(LOCAL_DB):
        if filename.endswith('.jpg'):
            path = os.path.join(LOCAL_DB, filename)
            # Read in Grayscale for LBPH
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            try:
                # Filename format: Name_ID.jpg
                name = filename.split('_')[0]
                uid = int(filename.split('_')[1].split('.')[0])
                
                # Detect face in the training image
                detected = face_classifier.detectMultiScale(img, 1.1, 5)
                
                for (x, y, w, h) in detected:
                    faces.append(img[y:y+h, x:x+w])
                    ids.append(uid)
                    known_names[uid] = name
            except Exception as e:
                print(f"Skipped {filename}: {e}")
                
    if faces: 
        recognizer.train(faces, np.array(ids))
        print(f"🎉 Model Trained! Users Loaded: {len(known_names)}")
    else:
        print("⚠️ No data in local_db. Please register a user.")

# --- 4. ROUTES ---

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/process_frame', methods=['POST'])
def process_frame():
    """Receives image from browser, checks liveness, and recognizes user"""
    try:
        data = request.json
        # Decode the Base64 image
        header, encoded = data['image'].split(",", 1)
        binary = base64.b64decode(encoded)
        img_arr = np.frombuffer(binary, dtype=np.uint8)
        frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

        # 1. AI Analysis
        face_found, is_smiling, is_looking = check_liveness(frame)
        
        status = "Scanning..."
        name = "Unknown"
        color_code = "gray"

        if face_found:
            # 2. Identify User
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_classifier.detectMultiScale(gray, 1.1, 4)
            for (x, y, w, h) in faces:
                try:
                    id_pred, conf = recognizer.predict(gray[y:y+h, x:x+w])
                    # Confidence < 80 is a good match for LBPH
                    if conf < 80:
                        name = known_names.get(id_pred, "Unknown")
                except: pass
            
            # 3. Final Decision Logic
            if name != "Unknown":
                if is_looking or is_smiling:
                    status = "VERIFIED LIVE"
                    color_code = "green"
                    
                    # LOG TO FIREBASE
                    now = datetime.now()
                    doc_id = f"{now.strftime('%Y-%m-%d')}_{name}"
                    
                    # Log attendance (Using set() overwrites if exists, use update() if preferred)
                    db.collection('Attendance').document(doc_id).set({
                        'name': name,
                        'id': id_pred, # Save ID for reporting
                        'time': now.strftime("%H:%M:%S"), 
                        'date': now.strftime("%Y-%m-%d"),
                        'timestamp': now
                    })
                else:
                    status = "Look at Camera OR Smile"
                    color_code = "yellow"
            else:
                status = "Unknown User"
                color_code = "red"
        else:
            status = "No Face Detected"
            color_code = "gray"

        return jsonify({'status': status, 'name': name, 'color': color_code})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': "Error", 'color': "red"})

@app.route('/get_attendance_data', methods=['POST'])
def get_attendance_data():
    """Generates the Calendar Report for a specific user ID"""
    try:
        user_id = request.json.get('id')
        if not user_id: return jsonify({'error': 'No ID provided'})

        # Query Firebase for all logs matching this ID
        docs = db.collection('Attendance').where('id', '==', int(user_id)).stream()
        
        present_dates = []
        for doc in docs:
            data = doc.to_dict()
            present_dates.append(data.get('date')) # Collect "YYYY-MM-DD" strings
        
        # Calculate Stats
        total_days_in_month = 30 # Simplified for demo
        days_present = len(set(present_dates)) # Count unique days
        percentage = min((days_present / total_days_in_month) * 100, 100)

        return jsonify({
            'dates': present_dates,
            'percentage': round(percentage, 1),
            'days_present': days_present
        })
    except Exception as e:
        print(e)
        return jsonify({'error': 'User not found or DB error'})

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/save_user', methods=['POST'])
def save_user():
    """Saves a new user's photo to local_db and retrains model"""
    try:
        data = request.json
        name = data['name']
        uid = data['id']
        image_data = data['image']
        
        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        
        filename = f"{name}_{uid}.jpg"
        filepath = os.path.join(LOCAL_DB, filename)
        
        with open(filepath, "wb") as f:
            f.write(binary_data)
            
        train_model() # Retrain immediately
        return jsonify({'message': 'User Registered Successfully!'})
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'})

@app.route('/calendar')
def calendar():
    return render_template('calendar.html')

if __name__ == '__main__':
    train_model()
    app.run(debug=True)