# 👁️ PRIVALENS: Intelligent Offline-First Attendance System

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=googlebard&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Vision-orange?style=for-the-badge)
![Heroku](https://img.shields.io/badge/Heroku-Deployment-430098?style=for-the-badge&logo=heroku&logoColor=white)

##  Overview <a name="overview"></a>
**Privalens** is a fraud-proof, privacy-focused facial attendance system designed for unstable network environments. It solves the problem of "proxy" attendance and internet dependency by combining **Edge AI** for instant liveness detection with a **Hybrid Sync Engine**. The system ensures 100% uptime by logging data locally and syncing to the cloud only when connectivity is available, while **Google Gemini** provides intelligent analytics on the backend.

---

##  Features <a name="features"></a>
* **Zero-Latency Liveness Check:** Instant verification of "Blink" and "Smile" gestures using **Google MediaPipe** (works in <50ms).
* **Offline-First Architecture:** Automatically switches between Local Storage and Cloud Database based on network availability.
* **Smart Sync Engine:** Queues attendance logs offline and pushes them to **Firebase** the moment Wi-Fi is restored.
* **Gemini AI Analytics:** Generates natural language summaries of attendance patterns (e.g., identifying frequent latecomers) to assist administrators.
* **Anti-Spoofing:** Depth and motion analysis prevents using photos or screens to fake attendance.

---

##  Problem Statement & Impact <a name="problem statement and impact"></a>

### **Problems Solved**
* ** The "Proxy" Problem:** Standard attendance systems are easy to fool with static photos. Privalens uses **Liveness Detection (Blink & Smile)** to ensure physical presence, making "buddy punching" impossible.
* ** The "No Signal" Barrier:** Most biometric apps crash without internet. Our **Offline-First Architecture** ensures 100% functionality in rural areas or basements, bridging the digital divide.
* ** The "Ghost Data" Issue:** Raw logs are hard to analyze. We use **Gemini AI** to transform data into actionable insights (e.g., *"Student X is late every Monday"*), enabling proactive intervention.

### **Contribution to Society**
* ** Educational Integrity:** Guarantees accurate records for schools, helping identify disengaged students early.
* ** Digital Inclusion:** Runs on low-end hardware (via TensorFlow Lite) and works offline, bringing high-tech security to under-funded or remote institutions.
* ** Privacy:** Processes facial features on the **Edge** (on-device) rather than streaming video to the cloud, respecting user privacy.

---



## 💻 Tech Stack <a name="tech stack"></a>

### **Backend** <a name="backend"></a>
![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)
 ![MediaPipe](https://img.shields.io/badge/MediaPipe-Vision-orange?style=for-the-badge)
 ![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=googlebard&logoColor=white)
 ![Firebase](https://img.shields.io/badge/Firebase-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
* **Language:** Python 3.9+ 
* **Framework:** Flask (Micro-framework)
* **Computer Vision:** Google MediaPipe & OpenCV 
* **AI/LLM:** Google Gemini Pro API 
* **Database (Cloud):** Google Firebase Firestore 
* **Database (Local):** JSON / Local File Storage (Encrypted)

### **Frontend** <a name="frontend"></a>
![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)
  ![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)
  ![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)
* **Core:** HTML5, CSS3, JavaScript
* **Templating:** Jinja2 (Flask default)
* **Styling:** Custom Responsive CSS

### **Tooling & Deployment** <a name="tooling and deployment"></a>
 ![Heroku](https://img.shields.io/badge/Heroku-Deployment-430098?style=for-the-badge&logo=heroku&logoColor=white)
* **Deployment:** Heroku 
* **IDE:** VS Code
* **Version Control:** Git & GitHub
* **Development:** Google Colab (Model Training)

---

## 📂 File Structure <a name="file structure"></a>

```bash
PRIVALENS/
├── local_db/               # Local storage for registered user images
│   ├── .gitkeep            # Ensures folder exists in repo
│   └── [user_images]       # (Stored locally)
├── static/                 # Static Assets
│   ├── css/                # Stylesheets
│   ├── js/                 # Client-side scripts
│   └── images/             # UI Assets
├── templates/              # HTML Frontend Pages
│   ├── calendar.html       # Attendance calendar view
│   ├── dashboard.html      # Main Admin Dashboard
│   ├── index.html          # Login & Landing page
│   └── register.html       # New user registration interface
├── app.py                  # Main Flask application entry point
├── Procfile                # Heroku deployment configuration
├── requirements.txt        # List of Python dependencies
├── runtime.txt             # Python version specification
├── serviceAccountKey.json  # Firebase Admin Keys (Sensitive - Do not commit)
└── .gitignore              # Git exclusion rules
```
### 🚀 Getting Started <a name="getting started"></a>
-Follow these instructions to set up the project on your local machine.

## 1. Clone the Repository
```bash
git clone [https://github.com/Kowalskiye/PRIVALENS.git](https://github.com/Kowalskiye/PRIVALENS.git)
cd PRIVALENS
```

## 2. Install Dependencies
-Ensure you have Python installed, then run:
```bash
pip install -r requirements.txt
```
## 3. Configuration (Critical)
This project requires sensitive API keys to function.

### **Firebase Setup:**

-Go to Firebase Console.

-Navigate to Project Settings -> Service Accounts.

-Generate a new Private Key.

-Rename the downloaded file to serviceAccountKey.json and place it in the root folder.

### **Gemini AI Setup:**

-Ensure you have a valid Google AI Studio API Key.

-Configure it in your environment variables (or .env file if configured).

## 4. Run the Application
```bash
python app.py
```
-The server will start at http://127.0.0.1:5000/.

--Note: Allow camera permissions in your browser when prompted.

## 🧭 Navigation Guide <a name="navigation guide"></a>

Once the application is running, here is how to use the different features:

### 1. Register a New User
* **Navigate to:** Click "Register" on the home page.
* **Action:**
    1.  Enter the user's **Name** and **ID**.
    2.  The camera will activate. Align your face within the frame.
    3.  Click **"Capture & Save"**.
* **Result:** The system extracts your face embeddings and saves them to the local secure database.

### 2. Verify Attendance (Liveness Check)
* **Navigate to:** Home Page.
* **Action:**
    1.  Look at the camera.
    2.  **Liveness Challenge:** The system will ask you to **"Blink"** or **"Smile"** to prove you are human.
    3.  Once the gesture is detected, the system matches your face against the database.
* **Result:** You will see a green **"VERIFIED"** badge and your attendance is marked.

### 3. Check History (Calendar)
* **Navigate to:** Click on the Sign in buuton and log in with your account and once done click on it.
* **Action:** Enter the ID number and fetch.
* **Result:** Displays a visual calendar marking "Present" (Green).
