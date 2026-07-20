"""
Test Groq API Connection
"""
import os
from dotenv import load_dotenv
from groq import Groq

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

api_key = os.getenv("GROQ_API_KEY")

print("="*50)
print("GROQ API TEST")
print("="*50)
print(f"API Key found: {'Yes' if api_key else 'No'}")
print(f"API Key: ****{api_key[-4:]}" if api_key else "N/A")

if not api_key:
    print("\n[ERROR] No GROQ_API_KEY found!")
    print("Get free key at: https://console.groq.com")
    exit(1)

try:
    client = Groq(api_key=api_key)
    
    # Test with simple prompt
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": "Say 'Hello from Groq! API is working.' in one sentence."}
        ],
        temperature=0.7,
        max_tokens=50,
    )
    
    result = response.choices[0].message.content
    print(f"\n[SUCCESS] API Response: {result}")
    print("\nGroq API is ready to use!")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
