import os
import urllib.request
import urllib.parse
import json
import re
import base64
import sync_gmail

def main():
    print("Running Gmail Debug Printer...")
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        print("Missing credentials.")
        return

    try:
        access_token = sync_gmail.refresh_gmail_token(client_id, client_secret, refresh_token)
    except Exception as e:
        print(f"Auth failed: {e}")
        return

    query = "(timetable OR class OR cancel OR reschedule OR extra OR room OR venue OR Moumita OR Pratim OR Khosla OR Satyajitsinh OR Bodapati OR Indu OR Joshi OR Palni OR Dwijasish) newer_than:2d"
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={urllib.parse.quote(query)}"
    res = sync_gmail.gmail_api_request(url, access_token)
    
    messages = res.get("messages", [])
    if not messages:
        log_content = "No matching emails found in the last 2 days."
    else:
        log_content = f"Found {len(messages)} emails in the last 2 days:\n\n"
        for msg in messages[:15]:
            msg_id = msg["id"]
            email = sync_gmail.get_email_details(msg_id, access_token)
            if email:
                log_content += f"Message ID: {msg_id}\n"
                log_content += f"From: {email['from']}\n"
                log_content += f"Date: {email['date']}\n"
                log_content += f"Subject: {email['subject']}\n"
                # Strip HTML if present and show a small snippet of the body
                body_snippet = re.sub('<[^<]+?>', '', email['body'])[:300].strip()
                log_content += f"Snippet: {body_snippet}\n"
                log_content += f"Pre-filter Potentially Relevant: {sync_gmail.is_potentially_relevant(email)}\n"
                log_content += "-" * 60 + "\n\n"

    with open("email_log.txt", "w", encoding="utf-8") as f:
        f.write(log_content)
    print("Logged to email_log.txt successfully.")

if __name__ == "__main__":
    main()
