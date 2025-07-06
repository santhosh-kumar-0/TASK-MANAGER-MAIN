# config.py

# Email Notification Configuration (for Gmail)
# You will need to generate an App Password if using Gmail with 2-Factor Authentication.
# See: https://support.google.com/accounts/answer/185833
SENDER_EMAIL = "your_email@gmail.com"
SENDER_EMAIL_PASSWORD = "your_app_password" # Use app password for Gmail

# Twilio SMS Notification Configuration
# Sign up at Twilio.com to get your Account SID, Auth Token, and Twilio Phone Number.
TWILIO_ACCOUNT_SID = "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" # Replace with your Twilio Account SID
TWILIO_AUTH_TOKEN = "your_twilio_auth_token" # Replace with your Twilio Auth Token
TWILIO_PHONE_NUMBER = "+1234567890" # Replace with your Twilio Phone Number (e.g., +15017122661)

# File Paths
USERS_FILE = "users.json"
PROFILE_PHOTOS_DIR = "profile_photos"
DEFAULT_PROFILE_PHOTO = "default_profile.png"

import os
os.makedirs(PROFILE_PHOTOS_DIR, exist_ok=True)
# Users data file
USERS_FILE = "users.json"

# Gemini API Configuration
# Get your API key from Google AI Studio: https://makersuite.google.com/app/apikey
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY" # Replace with your actual Gemini API key
