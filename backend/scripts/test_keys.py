# test_keys.py
import os
from dotenv import load_dotenv
import voyageai

load_dotenv()

# Test Voyage AI
voyage = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
result = voyage.embed(["hello world"], model="voyage-code-3")
print("Voyage AI ✅ embedding length:", len(result.embeddings[0]))
