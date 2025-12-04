import firebase_admin
from firebase_admin import credentials, db
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, "firebase-key.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://rice-813b5-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })
