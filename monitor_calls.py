#!/usr/bin/env python3
import os
import sys
import json
import hashlib
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

# File to store previous notification data
LAST_NOTIFICATION_FILE = "/tmp/twilio_last_notification.json"

def format_duration(seconds_str):
    """Format seconds into a human-readable duration."""
    if seconds_str is None:
        return "In progress"
    
    # Convert string to integer - Twilio returns duration as a string
    try:
        seconds = int(seconds_str)
    except (ValueError, TypeError):
        return str(seconds_str)  # Return as is if conversion fails
    
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def calculate_notification_hash(long_calls, in_progress_calls):
    """Calculate a hash of the call data to track duplicates."""
    combined_data = []
    
    # Add long calls data
    for call in long_calls:
        combined_data.append(f"{call['sid']}:{call['duration']}")
    
    # Add in-progress calls data
    for call in in_progress_calls:
        combined_data.append(f"{call['sid']}:{call['status']}")
    
    # Sort for consistency
    combined_data.sort()
    
    # Create a single string and hash it
    data_string = "|".join(combined_data)
    return hashlib.md5(data_string.encode()).hexdigest()

def is_duplicate_notification(long_calls, in_progress_calls):
    """Check if this notification is a duplicate of the previous one."""
    current_hash = calculate_notification_hash(long_calls, in_progress_calls)
    
    try:
        # Check if we have a previous notification file
        if os.path.exists(LAST_NOTIFICATION_FILE):
            with open(LAST_NOTIFICATION_FILE, 'r') as f:
                last_data = json.load(f)
                last_hash = last_data.get('hash', '')
                last_time = last_data.get('time', '')
                
                # If hash matches, it's a duplicate
                if current_hash == last_hash:
                    print(f"Duplicate notification detected. Last sent at {last_time}")
                    return True
    except Exception as e:
        print(f"Error checking duplicate notification: {e}")
    
    # Save current notification data
    try:
        with open(LAST_NOTIFICATION_FILE, 'w') as f:
            data = {
                'hash': current_hash,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'long_calls_count': len(long_calls),
                'in_progress_calls_count': len(in_progress_calls)
            }
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving notification data: {e}")
    
    return False

def send_notification(long_calls, in_progress_calls):
    """Send email notification about detected calls."""
    if not long_calls and not in_progress_calls:
        print("No calls to report.")
        return
    
    # Check if this is a duplicate notification
    if is_duplicate_notification(long_calls, in_progress_calls):
        print("Skipping duplicate notification")
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
    
    try:
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Define window for recent call data (last 10 minutes)
        window_start = datetime.utcnow() - timedelta(minutes=10)

        # Fetch calls (adjust limit as needed)
        calls = client.calls.list(limit=100)

        long_calls = []
        in_progress_calls = []

        for call in calls:
            # Parse start and end times
            start_dt = call.start_time.replace(tzinfo=None) if call.start_time else None
            end_dt = call.end_time.replace(tzinfo=None) if getattr(call, 'end_time', None) else None

            # Detect in-progress calls that started within the window
            if call.status in ['in-progress', 'ringing', 'queued']:
                if start_dt and start_dt >= window_start:
                    call_info = {
                        'sid': call.sid,
                        'from_number': call.from_formatted,
                        'to_number': call.to_formatted,
                        'status': call.status,
                        'start_time': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'duration': 'In progress'
                    }
                    in_progress_calls.append(call_info)
                continue

            # Detect completed long calls that ended within the window
            if call.status == 'completed' and end_dt and end_dt >= window_start:
                try:
                    if call.duration and int(call.duration) >= LONG_CALL_THRESHOLD:
                        call_info = {
                            'sid': call.sid,
                            'from_number': call.from_formatted,
                            'to_number': call.to_formatted,
                            'status': call.status,
                            'start_time': start_dt.strftime('%Y-%m-%d %H:%M:%S') if start_dt else 'Unknown',
                            'duration': format_duration(call.duration)
                        }
                        long_calls.append(call_info)
                except (ValueError, TypeError) as e:
                    print(f"Error processing duration for call {call.sid}: {e}")

        # Print summary
        print(f"Found {len(long_calls)} calls longer than 10 minutes in last 10 minutes")
        print(f"Found {len(in_progress_calls)} calls currently in progress within last 10 minutes")
        
        # Send notification if needed
        if long_calls or in_progress_calls:
            send_notification(long_calls, in_progress_calls)
        
    except Exception as e:
        print(f"Error in monitor_calls: {e}")
        sys.exit(1)
    
    print("Monitoring completed.")

if __name__ == "__main__":
    monitor_calls()