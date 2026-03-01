from datetime import datetime
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from functions import *

SCOPES = ["https://www.googleapis.com/auth/calendar"]

creds = Credentials.from_authorized_user_file("token.json", SCOPES)
service = build("calendar", "v3", credentials=creds)

calenderID='c_6c58c8f5c874a7263ad4a1e80b5e6dd8ddf661dcd09227fe0df0e9807376f251@group.calendar.google.com'

ist = ZoneInfo("Asia/Kolkata")

start = datetime(2026, 2, 27, 11, 0, tzinfo=ist)
per=60
        
free = is_slot_available(start, per, service,calenderID)
print("Free?", free)
send_email("Hello testing here","satusrini@gmail.com","testing1")
# if free==False:
#     avail= find_nearby_free_slots(start,per,service,calendarID=calenderID)
#     print(avail[0])
#     create_event(service=service,calendarID=calenderID,start_time=avail[0][0],end_time=avail[0][1],title='Testing')
#     #print_slots(avail)



# calendar_list = service.calendarList().list().execute()

# for cal in calendar_list["items"]:
#     print("Name:", cal["summary"])
#     print("ID:  ", cal["id"])
#     print("Primary:", cal.get("primary", False))
#     print("-" * 40)

# events = []
# page_token = None

# while True:
#     response = service.events().list(
#         # calendarId="primary",
#         calendarId=calenderID,
#         singleEvents=True,
#         orderBy="startTime",
#         pageToken=page_token
#     ).execute()

#     events.extend(response.get("items", []))
#     page_token = response.get("nextPageToken")

#     if not page_token:
#         break

# print(f"Total events found: {len(events)}")


# with open("events.txt", "w", encoding="utf-8") as f:
#     if not events:
#         f.write("No upcoming events found.\n")
#     else:
#         for i, event in enumerate(events, start=1):
#             start = event["start"].get("dateTime", event["start"].get("date"))
#             end   = event["end"].get("dateTime", event["end"].get("date"))
#             title = event.get("summary", "(no title)")

#             f.write(f"{i}. {start} → {end} | {title}\n")