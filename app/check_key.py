"""Prints every model this API key can use. Run once to confirm setup."""

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

for model in client.models.list():
    print(model.name)
