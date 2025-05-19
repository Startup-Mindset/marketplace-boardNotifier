import os
from datetime import datetime
from dotenv import load_dotenv
import pywhatkit as kit
from notion_client import Client

# Load environment variables
load_dotenv()

# Initialize Notion client
notion = Client(auth=os.getenv("NOTION_TOKEN"))

def format_notion_date(date_obj):
    """Formats Notion date object into human-readable string."""
    if not date_obj:
        return "No Date"
    
    start_str = date_obj.get("start")
    end_str = date_obj.get("end")
    
    if not start_str:
        return "No Date"
    
    try:
        start_date = datetime.fromisoformat(start_str)
        start_formatted = start_date.strftime("%b %d, %Y")
        
        if end_str and end_str != start_str:  # It's a date range
            end_date = datetime.fromisoformat(end_str)
            # Same month/year: "May 10 - 12, 2024"
            if start_date.month == end_date.month and start_date.year == end_date.year:
                return f"{start_date.strftime('%b %d')} - {end_date.strftime('%d, %Y')}"
            # Same year: "May 10 - Jun 12, 2024"
            elif start_date.year == end_date.year:
                return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
            # Different years: "Dec 30, 2023 - Jan 2, 2024"
            else:
                return f"{start_formatted} - {end_date.strftime('%b %d, %Y')}"
        return start_formatted  # Single date
    except ValueError:
        return "Invalid Date"

def fetch_assigned_tasks():
    """Fetch tasks where 'Assign' is not empty and status is 'In progress' or 'Assigned'."""
    query = {
        "filter": {
            "and": [
                {
                    "property": "Assign",
                    "people": {"is_not_empty": True}  # Changed to is_not_empty
                },
                {
                    "or": [
                        {"property": "Status", "status": {"equals": "In progress"}},
                        {"property": "Status", "status": {"equals": "Assigned"}}
                    ]
                }
            ]
        }
    }
    
    results = notion.databases.query(database_id=os.getenv("DATABASE_ID"), **query).get("results", [])
    
    tasks_by_assignee = {}
    
    for page in results:
        props = page.get("properties", {})
        
        # Extract assignee name (first person if multiple)
        assignees = props.get("Assign", {}).get("people", [])
        if not assignees:  # This shouldn't happen due to our filter, but just in case
            continue
        assignee_name = assignees[0].get("name", "Unassigned")
        
        # Extract task details
        task = props.get("Task", {}).get("title", [{}])[0].get("text", {}).get("content", "No Task")
        status = props.get("Status", {}).get("status", {}).get("name", "No Status")
        date_str = format_notion_date(props.get("Start Date", {}).get("date"))
        
        # Group by assignee
        if assignee_name not in tasks_by_assignee:
            tasks_by_assignee[assignee_name] = []
        tasks_by_assignee[assignee_name].append((task, status, date_str))
    
    return tasks_by_assignee

def send_whatsapp_messages(tasks_by_assignee):
    """Send formatted messages to the configured WhatsApp number."""
    if not tasks_by_assignee:
        print("No assigned tasks found.")
        return
    
    try:
        phone_number = os.getenv("WHATSAPP_NUMBER")
        if not phone_number:
            raise ValueError("WHATSAPP_NUMBER not configured in environment variables")
        
        for assignee, tasks in tasks_by_assignee.items():
            header = f"`Tasks played by {assignee}`\n\n"
            headers_line = "_Task_ | _Status_ | _Start Date_\n\n"
            task_lines = [
                f"{i+1}. {task} *|* {status} *|* {date}\n"
                for i, (task, status, date) in enumerate(tasks)
            ]
            message = header + headers_line + "\n".join(task_lines)
            
            kit.sendwhatmsg_instantly(
                phone_no=phone_number,
                message=message,
                wait_time=11,
                tab_close=True
            )
            print(f"Sent {len(tasks)} tasks for {assignee}")
            
    except Exception as e:
        print(f"Failed to send WhatsApp message: {str(e)}")

if __name__ == "__main__":
    assigned_tasks = fetch_assigned_tasks()
    send_whatsapp_messages(assigned_tasks)