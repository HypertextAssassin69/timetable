import os
import urllib.request
import json

# Import Gemini SDK if available
try:
    import google.generativeai as genai
    HAS_SDK = True
except ImportError:
    HAS_SDK = False

def test():
    status = ""
    key = os.environ.get("GEMINI_API_KEY")
    
    if not key:
        status += "ERROR: GEMINI_API_KEY environment variable is missing on the runner!\n"
        print("API Key missing.")
    else:
        status += f"GEMINI_API_KEY is present (Length: {len(key)} characters).\n"
        
        # Test Standard SDK
        if HAS_SDK:
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content("Verify API key connection. Respond with the word 'CONNECTED'.")
                status += f"Standard SDK Test: SUCCESS (Response: '{response.text.strip()}')\n"
            except Exception as e:
                status += f"Standard SDK Test: FAILED (Error: {e})\n"
        else:
            status += "Standard SDK Test: SKIPPED (SDK not installed)\n"
            
        # Test Raw HTTP API fallback
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        payload = {
            "contents": [{
                "parts": [{
                    "text": "Verify raw HTTP connection. Respond with the word 'CONNECTED_HTTP'."
                }]
            }]
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                status += f"Raw HTTP Test: SUCCESS (Response: '{text}')\n"
        except Exception as e:
            status += f"Raw HTTP Test: FAILED (Error: {e})\n"

    with open("gemini_status.txt", "w", encoding="utf-8") as f:
        f.write(status)
    print("Logged status to gemini_status.txt")

if __name__ == "__main__":
    test()
