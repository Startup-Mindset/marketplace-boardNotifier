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
        
        if end_str and end_str != start_str:
            end_date = datetime.fromisoformat(end_str)
            if start_date.month == end_date.month and start_date.year == end_date.year:
                return f"{start_date.strftime('%b %d')} - {end_date.strftime('%d, %Y')}"
            elif start_date.year == end_date.year:
                return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
            else:
                return f"{start_formatted} - {end_date.strftime('%b %d, %Y')}"
        return start_formatted
    except ValueError:
        return "Invalid Date"

def fetch_unassigned_tasks():
    """Fetch tasks where Status = 'Not started' and group by Epica."""
    query = {
    "filter": {
        "property": "Status",
        "status": {"equals": "Not started"}
        }
    }
    results = notion.databases.query(database_id=os.getenv("DATABASE_ID"), **query).get("results", [])
    
    tasks_by_epic = {}
    
    for page in results:
        props = page.get("properties", {})
        
        # Extract epic name
        epic = props.get("Epica", {}).get("status", {}).get("name", "No Epica")
        
        # Extract task details
        task = props.get("Task", {}).get("title", [{}])[0].get("text", {}).get("content", "No Task")
        date_str = format_notion_date(props.get("Start Date", {}).get("date"))
        
        if epic not in tasks_by_epic:
            tasks_by_epic[epic] = []
        tasks_by_epic[epic].append((task, date_str))
    
    return tasks_by_epic

def send_whatsapp_messages(tasks_by_epic):
    """Send formatted messages to individual WhatsApp number."""
    phone_number = os.getenv("WHATSAPP_NUMBER")
    
    for epic, tasks in tasks_by_epic.items():
        header = f"`{epic}` | *{len(tasks)}* cards to play\n\n"
        task_lines = [
            f"{i+1}. {task}"
            for i, (task, _) in enumerate(tasks)
        ]
        message = header + "\n".join(task_lines)
        
        try:
            kit.sendwhatmsg_instantly(
                phone_no=phone_number,
                message=message,
                wait_time=11,
                tab_close=True
            )
            print(f"Sent unassigned tasks for epic '{epic}'")
        except Exception as e:
            print(f"Failed to send tasks for epic '{epic}': {str(e)}")

if __name__ == "__main__":
    tasks_by_epic = fetch_unassigned_tasks()
    send_whatsapp_messages(tasks_by_epic)