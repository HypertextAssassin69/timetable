import os
import json
import base64
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# Import Gemini API library
try:
    import google.generativeai as genai
    HAS_GEMINI_LIB = True
except ImportError:
    HAS_GEMINI_LIB = False

# Course details for pre-filtering and prompt context
REGISTERED_COURSES = {
    "EE-261": "Electrical Systems Around Us (Moumita Das)",
    "EE-203": "Network Theory (Pratim Kundu)",
    "EE-311": "Device Electronics for Integrated Circuits (Robin Khosla)",
    "EE-260": "Signals and Systems (Satyajitsinh A. Thakor)",
    "EE-212": "Digital System Design (Srinivasu Bodapati)",
    "IC-272": "Machine Learning (Indu Joshi)",
    "EE-261P": "Electrical Systems Around Us — Lab (Moumita Das)",
    "IC-222P": "Physics Practicum / Practicals (Prabhakar Palni)",
    "IC-202P": "Design Practicum (Gajendra Singh)"
}

# Standardize search queries for candidate emails
KEYWORDS = [
    "timetable", "cancelled", "cancelled class", "cancel", "rescheduled", 
    "reschedule", "extra class", "room changed", "location change", 
    "Moumita", "Pratim", "Khosla", "Satyajitsinh", "Bodapati", "Indu", "Joshi", "Palni"
]

def refresh_gmail_token(client_id, client_secret, refresh_token):
    """Refreshes the OAuth2 token for Gmail API access via raw HTTP POST."""
    url = "https://oauth2.googleapis.com/token"
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["access_token"]
    except Exception as e:
        print(f"Error refreshing Gmail token: {e}")
        raise

def gmail_api_request(url, access_token):
    """Makes a GET request to the Gmail API using urllib."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Gmail API Request failed for URL {url}: {e}")
        return None

def extract_body(payload):
    """Recursively decodes the body content of a Gmail MIME payload."""
    body_text = ""
    
    # 1. Check if direct body data exists (often in plain text parts)
    if "body" in payload and "data" in payload["body"]:
        try:
            raw_data = payload["body"]["data"]
            # Base64url decode
            decoded = base64.urlsafe_b64decode(raw_data).decode("utf-8", errors="ignore")
            body_text += decoded
        except Exception as e:
            print(f"Error decoding body data: {e}")
            
    # 2. Check if multipart subparts exist and recursively extract
    if "parts" in payload:
        for part in payload["parts"]:
            body_text += extract_body(part)
            
    return body_text

def get_email_details(message_id, access_token):
    """Fetches details (From, Subject, Date, Body) of a specific email message."""
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=full"
    msg_data = gmail_api_request(url, access_token)
    if not msg_data:
        return None
        
    headers = msg_data.get("payload", {}).get("headers", [])
    
    subject = ""
    sender = ""
    date_str = ""
    
    for h in headers:
        name = h.get("name", "").lower()
        if name == "subject":
            subject = h.get("value", "")
        elif name == "from":
            sender = h.get("value", "")
        elif name == "date":
            date_str = h.get("value", "")
            
    body = extract_body(msg_data.get("payload", {}))
    # Basic cleanup: remove double spaces/newlines
    body = re.sub(r'\n+', '\n', body)
    
    return {
        "id": message_id,
        "subject": subject,
        "from": sender,
        "date": date_str,
        "body": body[:5000] # Limit size for token constraints
    }

def is_potentially_relevant(email):
    """Performs a quick heuristic pre-filter before invoking the Gemini API."""
    text_to_check = (email["subject"] + " " + email["body"]).lower()
    
    # Check if at least one keyword is present
    has_keyword = any(kw.lower() in text_to_check for kw in KEYWORDS)
    if not has_keyword:
        return False
        
    # Check if it mentions any course code
    has_course = any(code.lower() in text_to_check for code in REGISTERED_COURSES.keys())
    # Or matches names of teachers
    has_teacher = any(name.split()[-1].lower() in text_to_check for name in [
        "Moumita Das", "Pratim Kundu", "Robin Khosla", "Satyajitsinh A. Thakor", 
        "Srinivasu Bodapati", "Indu Joshi", "Prabhakar Palni", "Gajendra Singh"
    ])
    
    return has_course or has_teacher

def analyze_email_with_gemini(email, gemini_api_key):
    """Uses Gemini API to parse email text and output structured schedule overrides."""
    if not HAS_GEMINI_LIB:
        print("google-generativeai library not installed. Attempting raw HTTP fallback...")
        return analyze_email_raw_http(email, gemini_api_key)
        
    genai.configure(api_key=gemini_api_key)
    
    # Configure JSON response type
    generation_config = {
        "response_mime_type": "application/json"
    }
    
    # System instructions describing task and constraints
    system_instruction = (
        "You are an AI assistant tracking college schedules. Analyze emails and extract schedule adjustments "
        "only for our courses. Ignore anything about other classes. Return a JSON structure. "
        "A schedule override can be of these Action Types: CANCEL, RESCHEDULE, EXTRA, LOCATION_CHANGE. "
        "Compute the exact date (YYYY-MM-DD) for each override. If the email was sent on a certain date and refers "
        "to a relative time like 'tomorrow' or 'this Friday', calculate the actual date of the change. "
        "Only extract changes if they concern one of the registered courses. If the email contains no timetable changes "
        "concerning our courses, return '{\"relevant\": false}'."
    )
    
    prompt = f"""
    Context Info:
    Registered Courses Whitelist:
    - EE-261: Electrical Systems Around Us (Moumita Das)
    - EE-203: Network Theory (Pratim Kundu)
    - EE-311: Device Electronics for Integrated Circuits (Robin Khosla)
    - EE-260: Signals and Systems (Satyajitsinh A. Thakor)
    - EE-212: Digital System Design (Srinivasu Bodapati)
    - IC-272: Machine Learning (Indu Joshi)
    - EE-261P: Lab (Moumita Das)
    - IC-222P: Lab (Prabhakar Palni)
    - IC-202P: Design Practicum (Gajendra Singh)

    Reference Time details:
    - The email sent date: {email['date']}
    
    Please evaluate this email:
    Subject: {email['subject']}
    From: {email['from']}
    Body:
    {email['body']}

    Expected Schema Format (If relevant):
    {{
      "relevant": true,
      "overrides": [
        {{
          "course": "EE-261",
          "action": "CANCEL" | "RESCHEDULE" | "EXTRA" | "LOCATION_CHANGE",
          "date": "YYYY-MM-DD",
          "new_time": "14:00 - 15:00" (or null if CANCEL/LOCATION_CHANGE),
          "new_venue": "A17-1A" (or null if CANCEL/no change),
          "note": "Reason provided by teacher"
        }}
      ]
    }}
    
    Otherwise return:
    {{
      "relevant": false
    }}
    """
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            system_instruction=system_instruction
        )
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"Error calling Gemini SDK: {e}")
        # Try raw HTTP fallback
        return analyze_email_raw_http(email, gemini_api_key)

def analyze_email_raw_http(email, gemini_api_key):
    """Alternative raw HTTP POST request to Gemini API (failsafe)."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
    
    system_instruction = (
        "Analyze emails and extract schedule adjustments "
        "only for our courses: EE-261, EE-203, EE-311, EE-260, EE-212, IC-272, EE-261P, IC-222P, IC-202P. "
        "Ignore any other courses. Compute exact calendar dates (YYYY-MM-DD) relative to sent date. "
        "Return structured JSON matching: "
        '{"relevant": true, "overrides": [{"course": "EE-261", "action": "CANCEL", "date": "YYYY-MM-DD", "new_time": null, "new_venue": null, "note": "text"}]} '
        'or {"relevant": false}.'
    )
    
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Sent Date: {email['date']}\nSubject: {email['subject']}\nFrom: {email['from']}\nBody:\n{email['body']}"
            }]
        }],
        "systemInstruction": {
            "parts": [{
                "text": system_instruction
            }]
        },
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
    except Exception as e:
        print(f"Gemini API raw HTTP request failed: {e}")
        return {"relevant": False}

def main():
    print("Starting Gmail Sync Script...")
    
    # 1. Load Secrets
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not all([client_id, client_secret, refresh_token, gemini_key]):
        print("Missing required environment secrets. Please set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, and GEMINI_API_KEY.")
        return

    # 2. Load timetable database
    db_path = "timetable.json"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} database not found.")
        return
        
    with open(db_path, "r", encoding="utf-8") as f:
        database = json.load(f)
        
    processed_emails = database.get("metadata", {}).get("processed_emails", [])
    overrides = database.get("overrides", [])

    # 3. Authenticate with Gmail
    print("Authenticating with Gmail API...")
    try:
        access_token = refresh_gmail_token(client_id, client_secret, refresh_token)
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # 4. Search Gmail Inbox
    # Subject matching terms, check emails from last 7 days to cover periods of action failure/maintenance
    query = "subject:(timetable OR class OR cancel OR reschedule OR extra OR room OR venue)"
    print(f"Searching Gmail with query: '{query}'")
    
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={urllib.parse.quote(query)}"
    res = gmail_api_request(url, access_token)
    
    messages = res.get("messages", [])
    if not messages:
        print("No matching emails found.")
        return
        
    print(f"Found {len(messages)} candidate emails. Filtering new items...")
    
    new_overrides_count = 0
    
    # Process messages (up to 10 to prevent rate limit bottlenecks)
    for msg in messages[:10]:
        msg_id = msg["id"]
        
        # Idempotency check: skip already processed email IDs
        if msg_id in processed_emails:
            continue
            
        print(f"Fetching details for email {msg_id}...")
        email = get_email_details(msg_id, access_token)
        if not email:
            continue
            
        # Quick heuristic filter
        if not is_potentially_relevant(email):
            print(f"Skipping email {msg_id} (pre-filter deemed irrelevant)")
            processed_emails.append(msg_id)
            continue
            
        # Parse content with Gemini
        print(f"Analyzing content of email {msg_id} with Gemini...")
        result = analyze_email_with_gemini(email, gemini_key)
        
        if result and result.get("relevant") is True:
            parsed_list = result.get("overrides", [])
            print(f"Gemini matched {len(parsed_list)} schedule override(s)!")
            
            for item in parsed_list:
                # Add metadata parameters
                item["id"] = f"gmail_{msg_id}_{new_overrides_count}"
                item["source"] = "gmail_sync"
                
                # Check for duplicates in existing overrides to prevent double inserts
                duplicate = any(
                    o["date"] == item["date"] and 
                    o["course"] == item["course"] and 
                    o["action"] == item["action"] and
                    normalizeTime(o.get("new_time")) == normalizeTime(item.get("new_time"))
                    for o in overrides
                )
                
                if not duplicate:
                    overrides.append(item)
                    new_overrides_count += 1
                else:
                    print(f"Duplicate override skipped: {item['course']} {item['action']} on {item['date']}")
        else:
            print(f"Email {msg_id} deemed irrelevant by Gemini.")
            
        # Mark email as processed
        processed_emails.append(msg_id)

    # 5. Save changes back to timetable.json
    if new_overrides_count > 0:
        print(f"Added {new_overrides_count} new overrides from Gmail sync.")
        database["overrides"] = overrides
        database["metadata"]["last_synced"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        database["metadata"]["processed_emails"] = processed_emails
        
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(database, f, indent=2)
        print("Database updated successfully.")
    else:
        print("No new schedule changes detected. Database unchanged.")
        # Save processed email list even if no overrides added
        database["metadata"]["processed_emails"] = processed_emails
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(database, f, indent=2)

if __name__ == "__main__":
    main()
