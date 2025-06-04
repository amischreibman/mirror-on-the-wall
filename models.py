import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")  # שנה לפי שם המפתח שלך

genai.configure(api_key=api_key)

models = genai.list_models()

for model in models:
    print(model.name)
