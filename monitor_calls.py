#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta
from twilio.rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Twilio credentials
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')

# SendGrid credentials
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
NOTIFICATION_EMAIL = os.environ.get('NOTIFICATION_EMAIL')
FROM_EMAIL = os.environ.get('FROM_EMAIL')

# Threshold for long calls (10 minutes in seconds)
LONG_CALL_THRESHOLD = 10 * 60

def format_duration(seconds):
    """Format seconds into a human-readable duration."""
    if seconds is None:
        return "In progress"
    
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def send_notification(long_calls, in_progress_calls):
    """Send email notification about detected calls."""
    if not long_calls and not in_progress_calls:
        print("No calls to report.")
        return
    
    # Create message content
    subject = "Twilio Call Monitor Alert"
    
    content = []
    content.append("Twilio Call Monitor has detected the following calls:\n")
    
    if long_calls:
        content.append("🔴 Calls longer than 10 minutes:")
        for call in long_calls:
            content.append(f"  • From: {call['from_number']}")
            content.append(f"    To: {call['to_number']}")
            content.append(f"    Duration: {call['duration']}")
            content.append(f"    Started: {call['start_time']}")
            content.append("")
    
    if in_progress_calls:
        content.append("🟡 Calls currently in progress:")
        for call in in_progress_calls:
            content.append(f"  • From: {call['from_number']}")
            content.append(f"    To: {call['to_number']}")
            content.append(f"    Started: {call['start_time']}")
            content.append(f"    Status: {call['status']}")
            content.append("")
    
    content.append("This is an automated notification from Twilio Call Monitor.")
    
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=NOTIFICATION_EMAIL,
        subject=subject,
        plain_text_content="\n".join(content)
    )
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent with status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")

def monitor_calls():
    """Monitor Twilio calls and detect long or in-progress calls."""
    # Validate required environment variables
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, SENDGRID_API_KEY, NOTIFICATION_EMAIL, FROM_EMAIL]):
        print("Error: Missing required environment variables.")
        print("Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, SENDGRID_API_KEY, NOTIFICATION_EMAIL, and FROM_EMAIL.")
        sys.exit(1)
    
    print(f"Starting Twilio call monitoring at {datetime.now()}")
    
    # Initialize Twilio client
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    # Get recent calls (adjust limit as needed)
    calls = client.calls.list(limit=50)
    
    long_calls = []
    in_progress_calls = []
    
    for call in calls:
        # Basic call information
        call_info = {
            'sid': call.sid,
            'from_number': call.from_formatted,
            'to_number': call.to_formatted,
            'status': call.status,
            'start_time': call.start_time.strftime('%Y-%m-%d %H:%M:%S') if call.start_time else "Unknown",
            'duration': format_duration(call.duration) if call.duration else None
        }
        
        # Check for in-progress calls
        if call.status in ['in-progress', 'ringing', 'queued']:
            in_progress_calls.append(call_info)
        
        # Check for long calls (duration > threshold)
        if call.duration and int(call.duration) > LONG_CALL_THRESHOLD:
            long_calls.append(call_info)
    
    # Print summary
    print(f"Found {len(long_calls)} calls longer than 10 minutes")
    print(f"Found {len(in_progress_calls)} calls currently in progress")
    
    # Send notification if needed
    if long_calls or in_progress_calls:
        send_notification(long_calls, in_progress_calls)
    
    print("Monitoring completed.")

if __name__ == "__main__":
    monitor_calls()