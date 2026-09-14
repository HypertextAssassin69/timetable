import os
import json
import base64
import re
from datetime import datetime, timedelta

# Import Composio
from composio import ComposioToolSet

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
    "EE-261P": "Electrical Systems Around Us — Lab (Dwijasish Das)",
    "IC-222P": "Physics Practicum / Practicals (Prabhakar Palni)",
    "IC-202P": "Design Practicum (Gajendra Singh)"
}

def extract_body(payload):
    """Recursively decodes the body content of a Gmail MIME payload."""
    body_text = ""
    
    if "body" in payload and "data" in payload["body"]:
        try:
            raw_data = payload["body"]["data"]
            # Base64url decode (fix padding if necessary)
            raw_data += "=" * ((4 - len(raw_data) % 4) % 4)
            decoded = base64.urlsafe_b64decode(raw_data).decode("utf-8", errors="ignore")
            body_text += decoded
        except Exception as e:
            print(f"Error decoding body data: {e}")
            
    if "parts" in payload:
        for part in payload["parts"]:
            body_text += extract_body(part)
            
    return body_text

def is_potentially_relevant(subject, body):
    """Checks if the email mentions any whitelisted course codes or instructor names."""
    text_to_check = (subject + " " + body).lower()
    
    has_course = any(code.lower() in text_to_check for code in REGISTERED_COURSES.keys())
    
    teachers = [
        "Moumita", "Das", "Pratim", "Kundu", "Robin", "Khosla", "Satyajitsinh", "Thakor", 
        "Srinivasu", "Bodapati", "Indu", "Joshi", "Prabhakar", "Palni", "Gajendra", "Singh", "Dwijasish"
    ]
    has_teacher = any(name.lower() in text_to_check for name in teachers)
    
    return has_course or has_teacher

def normalizeTime(time_str):
    return time_str

def analyze_email_with_gemini(email, gemini_api_key):
    """Uses Gemini API to parse email text and output structured schedule overrides."""
    if not HAS_GEMINI_LIB:
        print("google-generativeai library not installed. Attempting raw HTTP fallback...")
        return analyze_email_raw_http(email, gemini_api_key)
        
    genai.configure(api_key=gemini_api_key)
    generation_config = {"response_mime_type": "application/json"}
    
    system_instruction = (
        "You are an AI assistant tracking college schedules. Analyze emails and extract schedule adjustments "
        "only for our courses. Ignore anything about other classes.\n"
        "RULES:\n"
        "1. Course Code Formatting: Whitelisted courses use hyphens (e.g. EE-203, IC-272, EE-261). Instructors might write them with spaces or no separators (e.g. 'EE 203', 'EE203', 'IC 272', 'EE 261'). You must match these and normalize the output to the whitelisted course code (strictly using the hyphenated code, like 'EE-203').\n"
        "2. Sender Authority: Emails may be sent directly by instructors OR by academic secretaries (e.g., Aditya Tayal), student representatives, or the academic office on behalf of the instructors or courses. Treat these as authoritative if they mention one of our whitelisted courses.\n"
        "3. Action Types: Overrides must be one of: CANCEL, RESCHEDULE, EXTRA, LOCATION_CHANGE.\n"
        "4. Date Calculation: Compute the exact date (YYYY-MM-DD) for each override. If the email refers to a relative time (like 'tomorrow', 'this Wednesday', or 'on 03-08'), calculate the actual date of the change relative to the Sent Date header of the email.\n"
        "5. Output Format: Return a JSON structure. If the email contains no schedule changes for our whitelisted courses, return '{\"relevant\": false}'."
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
    - EE-261P: Lab (Dwijasish Das)
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
            model_name="gemini-2.5-flash",
            generation_config=generation_config,
            system_instruction=system_instruction
        )
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"Error calling Gemini SDK: {e}")
        return analyze_email_raw_http(email, gemini_api_key)

def analyze_email_raw_http(email, gemini_api_key):
    """Alternative raw HTTP POST request to Gemini API (failsafe)."""
    import urllib.request, urllib.parse
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
    system_instruction = (
        "Analyze emails and extract schedule adjustments "
        "only for our courses: EE-261, EE-203, EE-311, EE-260, EE-212, IC-272, EE-261P, IC-222P, IC-202P.\n"
        "RULES:\n"
        "1. Course Formatting: Match variations like 'EE 203', 'EE203', 'IC 272' and normalize to hyphenated code (e.g. 'EE-203', 'IC-272').\n"
        "2. Senders: Accept emails sent by academic secretaries (Aditya Tayal) or student reps on behalf of the course.\n"
        "3. Compute exact date (YYYY-MM-DD) for overrides relative to the email Sent Date.\n"
        "4. Return JSON structure matching '{\"relevant\": true, \"overrides\": [...]}' or '{\"relevant\": false}'."
    )
    payload = {
        "contents": [{"parts": [{"text": f"Sent Date: {email['date']}\\nSubject: {email['subject']}\\nFrom: {email['from']}\\nBody:\\n{email['body']}"}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {"responseMimeType": "application/json"}
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
    print("Starting Gmail Sync Script with Composio...")
    
    # 1. Load Secrets
    composio_api_key = os.environ.get("COMPOSIO_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not all([composio_api_key, gemini_key]):
        print("Missing required environment secrets. Please set COMPOSIO_API_KEY and GEMINI_API_KEY.")
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

    # 3. Authenticate with Composio
    print("Initializing Composio ToolSet...")
    try:
        toolset = ComposioToolSet(api_key=composio_api_key)
    except Exception as e:
        print(f"Composio ToolSet initialization failed: {e}")
        return

    # 4. Search Gmail Inbox via Composio
    query = "(timetable OR class OR cancel OR reschedule OR extra OR room OR venue OR Moumita OR Pratim OR Khosla OR Satyajitsinh OR Bodapati OR Indu OR Joshi OR Palni OR Dwijasish) newer_than:2d"
    print(f"Searching Gmail via Composio with query: '{query}'")
    
    try:
        res = toolset.execute_action(
            action="GMAIL_FETCH_EMAILS", 
            params={
                "query": query,
                "max_results": 10,
                "include_payload": False,
                "verbose": False
            }
        )
    except Exception as e:
        print(f"Failed to fetch emails via Composio: {e}")
        return
        
    messages = res.get("data", {}).get("messages", [])
    if not messages:
        print("No matching emails found.")
        return
        
    print(f"Found {len(messages)} candidate emails. Filtering new items...")
    
    new_overrides_count = 0
    
    for msg in messages:
        msg_id = msg.get("messageId")
        if not msg_id:
            continue
            
        if msg_id in processed_emails:
            continue
            
        subject = msg.get("subject", "")
        sender = msg.get("sender", "")
        date_str = msg.get("messageTimestamp", "")
        
        print(f"Fetching full details for email {msg_id}...")
        try:
            full_msg_res = toolset.execute_action(
                action="GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID", 
                params={
                    "message_id": msg_id,
                    "format": "full"
                }
            )
            full_msg_data = full_msg_res.get("data", {})
        except Exception as e:
            print(f"Failed to fetch full message {msg_id}: {e}")
            continue
            
        body = extract_body(full_msg_data.get("payload", {}))
        body = re.sub(r'\\n+', '\\n', body)
        
        if not is_potentially_relevant(subject, body):
            print(f"Skipping email {msg_id} (pre-filter deemed irrelevant)")
            processed_emails.append(msg_id)
            continue
            
        email_obj = {
            "id": msg_id,
            "subject": subject,
            "from": sender,
            "date": date_str,
            "body": body[:5000]
        }
            
        print(f"Analyzing content of email {msg_id} with Gemini...")
        result = analyze_email_with_gemini(email_obj, gemini_key)
        
        if result and result.get("relevant") is True:
            parsed_list = result.get("overrides", [])
            print(f"Gemini matched {len(parsed_list)} schedule override(s)!")
            
            for item in parsed_list:
                item["id"] = f"gmail_{msg_id}_{new_overrides_count}"
                item["source"] = "gmail_sync"
                
                duplicate = any(
                    o.get("date") == item.get("date") and 
                    o.get("course") == item.get("course") and 
                    o.get("action") == item.get("action") and
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
            
        processed_emails.append(msg_id)

    # 5. Save changes
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
        database["metadata"]["processed_emails"] = processed_emails
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(database, f, indent=2)

if __name__ == "__main__":
    main()
