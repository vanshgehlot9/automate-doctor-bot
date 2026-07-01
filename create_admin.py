import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Path to your service account key
cred = credentials.Certificate("whatsapp-doctor-booking-firebase-adminsdk-fbsvc-6829c11a41.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# Replace this with the UID from the Firebase Authentication console
# Looking at your screenshot, the UID for gehlotvansh560@gmail.com starts with 'cNCCMzZJVab...'
user_uid = "cNCCMzZJVabE7HR5cc1ftPoatlp1" # PLEASE UPDATE THIS WITH YOUR ACTUAL UID!

# The user profile data
user_profile = {
    "uid": user_uid,
    "email": "gehlotvansh560@gmail.com",
    "name": "Vansh Gehlot",
    "role": "super_admin",
    "tenantId": "global",
    "hospitalId": "global"
}

# Create or update the document in the 'users' collection
db.collection("users").document(user_uid).set(user_profile)

print(f"Successfully created Super Admin profile for {user_profile['email']}")
