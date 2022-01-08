from datetime import datetime

from googleapiclient.discovery import build

import authentication
import env

now = datetime.utcnow().isoformat() + 'Z'
service = build("calendar", "v3", credentials=authentication.authenticate())
calendar = service.calendars().get(calendarId=env.DEFAULT_CALENDAR_ID).execute()
events = service.events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
                               orderBy='startTime').execute()

if __name__ == '__main__':
    print("It's the Notion Token", env.NOTION_TOKEN)
    print("It's the GCal Api ID", env.GCAL_API_ID)
    print(authentication.authenticate())
