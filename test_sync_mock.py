import os
import json
from datetime import datetime
import sync_gmail

# Mock emails to test parsing
MOCK_EMAILS = [
    {
        "id": "mock_cancel_001",
        "subject": "EE-261 Class Cancelled on Monday 10th August",
        "from": "Moumita Das <moumita@iitmandi.ac.in>",
        "date": "Mon, 3 Aug 2026 09:15:00 +0530",
        "body": "Dear students,\n\nPlease note that the EE-261 (Electrical Systems Around Us) lecture scheduled for Monday, 10th August 2026 at 11:00 AM stands cancelled as I will be attending an academic council meeting.\n\nBest regards,\nMoumita Das"
    },
    {
        "id": "mock_reschedule_002",
        "subject": "Rescheduling of Network Theory (EE-203) class tomorrow",
        "from": "Pratim Kundu <pratim.kundu@iitmandi.ac.in>",
        "date": "Tue, 4 Aug 2026 14:20:00 +0530",
        "body": "Hi all,\n\nTomorrow's (Wednesday, 5th August) EE-203 class scheduled at 12:00 PM is rescheduled. We will instead meet at 3:00 PM - 4:00 PM (15:00 - 16:00) in Room A17-1A.\n\nHope this is fine with everyone.\n\nRegards,\nPratim Kundu"
    },
    {
        "id": "mock_location_003",
        "subject": "Venue Change for Machine Learning (IC-272) Lecture on Thursday",
        "from": "Indu Joshi <indu@iitmandi.ac.in>",
        "date": "Wed, 5 Aug 2026 10:10:00 +0530",
        "body": "Dear students,\n\nThe ML lecture on Thursday (6th August 2026) will be held in room A11-PC Lab instead of A13-3A, as we need to run some programming demos. Time remains 12:00 PM - 12:50 PM.\n\nThanks,\nIndu Joshi"
    },
    {
        "id": "mock_irrelevant_004",
        "subject": "Invitation to Robotics Workshop",
        "from": "Dean Students <dean_std@iitmandi.ac.in>",
        "date": "Wed, 5 Aug 2026 11:00:00 +0530",
        "body": "Hello Students,\n\nYou are invited to attend a guest lecture on Robotics in the seminar room on Friday at 4 PM. High tea will be served.\n\nBest,\nDean Office"
    },
    {
        "id": "mock_other_course_005",
        "subject": "CS-301 Midterm postponed",
        "from": "Instructor CS301 <cs301@iitmandi.ac.in>",
        "date": "Thu, 6 Aug 2026 09:00:00 +0530",
        "body": "Dear Computer Science students, the CS-301 database system exam scheduled for Friday is postponed to next Monday."
    }
]

def run_test():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        print("="*60)
        print("WARNING: GEMINI_API_KEY environment variable is not set!")
        print("To run the live Gemini parsing tests, set it via:")
        print("  Windows PowerShell: $env:GEMINI_API_KEY='your-api-key'")
        print("  Windows CMD: set GEMINI_API_KEY=your-api-key")
        print("="*60)
        return

    print(f"Loaded {len(MOCK_EMAILS)} mock emails for testing.")
    print("Initializing test run calling Gemini API...\n")

    for i, email in enumerate(MOCK_EMAILS, 1):
        print("-" * 50)
        print(f"TEST EMAIL #{i}: {email['subject']}")
        print(f"From: {email['from']} | Sent: {email['date']}")
        
        # 1. Test Pre-filter heuristic
        is_candidate = sync_gmail.is_potentially_relevant(email)
        print(f"Pre-filter Heuristic Check: {'PASS (Candidate)' if is_candidate else 'SKIP (Irrelevant)'}")
        
        if not is_candidate:
            print("Result: Skipped directly without calling Gemini.")
            continue
            
        # 2. Test Gemini parser
        print("Calling Gemini API for extraction...")
        try:
            result = sync_gmail.analyze_email_with_gemini(email, gemini_key)
            print("Gemini Parser Response JSON:")
            print(json.dumps(result, indent=2))
            
            # 3. Verify response schema compliance
            if result.get("relevant") is True:
                overrides = result.get("overrides", [])
                print(f"Status: SUCCESS! Extracted {len(overrides)} override(s).")
                for item in overrides:
                    print(f"  -> Course: {item.get('course')} | Action: {item.get('action')} | Date: {item.get('date')}")
                    print(f"     New Time: {item.get('new_time')} | New Venue: {item.get('new_venue')}")
                    print(f"     Note: {item.get('note')}")
            else:
                print("Status: SUCCESS! Correctly identified as not relevant to our whitelisted courses.")
                
        except Exception as e:
            print(f"FAIL: Error parsing with Gemini: {e}")

if __name__ == "__main__":
    run_test()
