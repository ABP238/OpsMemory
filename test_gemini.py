import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

chat = client.chats.create(
    model="gemini-3.8-flash"
)

response = chat.send_message(
    message="Reply with exactly: Gemini connection successful!"
)

print("GEMINI RESPONSE:")
print(response.text)