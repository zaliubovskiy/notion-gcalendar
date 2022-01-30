import authentication
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from notion_client import Client

import constants
import env


def notion_time():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def date_time_into_notion_format(date_time_value):
    return date_time_value.strftime(
        "%Y-%m-%dT%H:%M:%S-04:00")  # Change the last 5 characters to be representative of your timezone
    # ^^ has to be adjusted for when daylight savings is different if your area observes it


def google_query():
    return datetime.now().strftime(
        "%Y-%m-%dT%H:%M:%S") + "-04:00"  # Change the last 5 characters to be representative of your timezone
    # ^^ has to be adjusted for when daylight savings is different if your area observes it


database_id = env.DATABASE_ID
credentials = authentication.authenticate()
DEFAULT_EVENT_LENGTH = env.DEFAULT_EVENT_LENGTH
timezone = env.TIMEZONE
DEFAULT_EVENT_START = env.DEFAULT_EVENT_START
AllDayEventOption = env.ALL_DAY_EVENT
DEFAULT_CALENDAR_ID = env.DEFAULT_CALENDAR_ID
DEFAULT_CALENDAR_NAME = env.DEFAULT_CALENDAR_NAME
calendarDictionary = {
    DEFAULT_CALENDAR_NAME: DEFAULT_CALENDAR_ID,
}
DELETE_OPTION = env.DELETE_OPTION
# DATABASE SPECIFIC EDITS

# There needs to be a few properties on the Notion Database for this to work. Replace the values of each variable
# with the string of what the variable is called on your Notion dashboard The Last Edited Time column is a property
# of the notion pages themselves, you just have to make it a column The NeedGCalUpdate column is a formula column
# that works as such "if(prop("Last Edited Time") > prop("Last Updated Time"), true, false)" Please refer to the
# Template if you are confused: https://www.notion.so/akarri/2583098dfd32472ab6ca1ff2a8b2866d?v
# =3a1adf60f15748f08ed925a2eca88421


# TO DELETE:
Task_Notion_Name = constants.task_notion_name
Date_Notion_Name = constants.date_notion_name
Initiative_Notion_Name = constants.status_notion_name
ExtraInfo_Notion_Name = constants.extra_info_notion_name
On_GCal_Notion_Name = constants.on_gcal_notion_name
NeedGCalUpdate_Notion_Name = constants.need_gcal_update_notion_name
GCalEventId_Notion_Name = constants.gcal_event_id_notion_name
LastUpdatedTime_Notion_Name = constants.last_updated_time_notion_name
Calendar_Notion_Name = constants.calendar_notion_name
Current_Calendar_Id_Notion_Name = constants.current_calendar_id_notion_name
Delete_Notion_Name = constants.done_notion_name
LastEditedTime_Notion_Name = constants.last_edited_time_notion_name

#######################################################################################
# No additional user editing beyond this point is needed
#######################################################################################


# SET UP THE GOOGLE CALENDAR API INTERFACE

service = build("calendar", "v3", credentials=credentials)

# There could be a hiccup if the Google Calendar API token expires.
# If the token expires, the other python script GCalToken.py creates a new token for the program to use
# This is placed here because it can take a few seconds to start working and I want the most heavy tasks to occur first

calendar = service.calendars().get(calendarId=DEFAULT_CALENDAR_ID).execute()
# {'kind': 'calendar#calendar',
# 'etag': '"oT5UU-lbNuQvaRoOFYs2uSl7qpw"',
# 'id': 'cqc0c96hdsucuvlpfd7vfmtfbo@group.calendar.google.com',
# 'summary': 'Notion Automation',
# 'timeZone': 'Europe/Kiev',
# 'conferenceProperties': {'allowedConferenceSolutionTypes': ['hangoutsMeet']}
# }

# This is where we set up the connection with the Notion API
notion = Client(auth=env.NOTION_TOKEN)
today_date = datetime.today().strftime("%Y-%m-%d")


###########################################################################
# The Methods that we will use in this script are below
###########################################################################


######################################################################
# METHOD TO MAKE A CALENDAR EVENT DESCRIPTION
#
# This method can be edited as wanted. Whatever is returned from this method will be in the GCal event description
# Whatever you change up, be sure to return a string

def make_event_description(initiative, info):
    if initiative == '' and info == '':
        return ''
    elif info == '':
        return initiative
    elif initiative == '':
        return info
    else:
        return f'Initiative: {initiative} \n{info}'


######################################################################
# METHOD TO MAKE A TASK'S URL
# To make a url for the notion task, we have to take the id of the task and take away the hyphens from the string

def make_task_url(ending, url_root):
    return url_root + ending.replace('-', '')


######################################################################
# METHOD TO MAKE A CALENDAR EVENT


def make_cal_event(eventName, eventDescription, eventStartTime, sourceURL, eventEndTime, calId):
    if eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime == eventStartTime:  # only startTime is given from the Notion Dashboard
        if AllDayEventOption == 1:
            eventStartTime = datetime.combine(eventStartTime, datetime.min.time()) + timedelta(
                hours=DEFAULT_EVENT_START)  ##make the events pop up at 8 am instead of 12 am
            eventEndTime = eventStartTime + timedelta(minutes=DEFAULT_EVENT_LENGTH)
            event = {
                'summary': eventName,
                'description': eventDescription,
                'start': {
                    'dateTime': eventStartTime.strftime("%Y-%m-%dT%H:%M:%S"),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': eventEndTime.strftime("%Y-%m-%dT%H:%M:%S"),
                    'timeZone': timezone,
                },
                'source': {
                    'title': 'Notion Link',
                    'url': sourceURL,
                }
            }
        else:
            eventEndTime = eventEndTime + timedelta(days=1)  # gotta make it to 12AM the day after
            event = {
                'summary': eventName,
                'description': eventDescription,
                'start': {
                    'date': eventStartTime.strftime("%Y-%m-%d"),
                    'timeZone': timezone,
                },
                'end': {
                    'date': eventEndTime.strftime("%Y-%m-%d"),
                    'timeZone': timezone,
                },
                'source': {
                    'title': 'Notion Link',
                    'url': sourceURL,
                }
            }
    elif eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime.hour == 0 and eventEndTime.minute == 0 and eventStartTime != eventEndTime:

        eventEndTime = eventEndTime + timedelta(days=1)  # gotta make it to 12AM the day after

        event = {
            'summary': eventName,
            'description': eventDescription,
            'start': {
                'date': eventStartTime.strftime("%Y-%m-%d"),
                'timeZone': timezone,
            },
            'end': {
                'date': eventEndTime.strftime("%Y-%m-%d"),
                'timeZone': timezone,
            },
            'source': {
                'title': 'Notion Link',
                'url': sourceURL,
            }
        }

    else:  # just 2 datetimes passed in from the method call that are not at 12 AM
        if eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime != eventStartTime:  # Start on Notion is 12 am and end is also given on Notion
            eventStartTime = eventStartTime  # start will be 12 am
            eventEndTime = eventEndTime  # end will be whenever specified
        elif eventStartTime.hour == 0 and eventStartTime.minute == 0:  # if the datetime fed into this is only a date or is at 12 AM, then the event will fall under here
            eventStartTime = datetime.combine(eventStartTime, datetime.min.time()) + timedelta(
                hours=DEFAULT_EVENT_START)  ##make the events pop up at 8 am instead of 12 am
            eventEndTime = eventStartTime + timedelta(minutes=DEFAULT_EVENT_LENGTH)
        elif eventEndTime == eventStartTime:  # this would meant that only 1 datetime was actually on the notion dashboard
            eventStartTime = eventStartTime
            eventEndTime = eventStartTime + timedelta(minutes=DEFAULT_EVENT_LENGTH)
        else:  # if you give a specific start time to the event
            eventStartTime = eventStartTime
            eventEndTime = eventEndTime

        event = {
            'summary': eventName,
            'description': eventDescription,
            'start': {
                'dateTime': eventStartTime.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': eventEndTime.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': timezone,
            },
            'source': {
                'title': 'Notion Link',
                'url': sourceURL,
            }
        }
    print('Adding this event to calendar: ', eventName)

    print(event)
    x = service.events().insert(calendarId=calId, body=event).execute()
    return x['id']


######################################################################
# METHOD TO UPDATE A CALENDAR EVENT

def upDateCalEvent(eventName, eventDescription, eventStartTime, sourceURL, eventId, eventEndTime, currentCalId, CalId):
    if eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime == eventStartTime:  # you're given a single date
        if AllDayEventOption == 1:
            eventStartTime = datetime.combine(eventStartTime, datetime.min.time()) + timedelta(
                hours=DEFAULT_EVENT_START)  ##make the events pop up at 8 am instead of 12 am
            eventEndTime = eventStartTime + timedelta(minutes=DEFAULT_EVENT_LENGTH)
            event = {
                'summary': eventName,
                'description': eventDescription,
                'start': {
                    'dateTime': eventStartTime.strftime("%Y-%m-%dT%H:%M:%S"),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': eventEndTime.strftime("%Y-%m-%dT%H:%M:%S"),
                    'timeZone': timezone,
                },
                'source': {
                    'title': 'Notion Link',
                    'url': sourceURL,
                }
            }
        else:
            eventEndTime = eventEndTime + timedelta(days=1)  # gotta make it to 12AM the day after
            event = {
                'summary': eventName,
                'description': eventDescription,
                'start': {
                    'date': eventStartTime.strftime("%Y-%m-%d"),
                    'timeZone': timezone,
                },
                'end': {
                    'date': eventEndTime.strftime("%Y-%m-%d"),
                    'timeZone': timezone,
                },
                'source': {
                    'title': 'Notion Link',
                    'url': sourceURL,
                }
            }
    elif eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime.hour == 0 and eventEndTime.minute == 0 and eventStartTime != eventEndTime:  # it's a multiple day event

        eventEndTime = eventEndTime + timedelta(days=1)  # gotta make it to 12AM the day after

        event = {
            'summary': eventName,
            'description': eventDescription,
            'start': {
                'date': eventStartTime.strftime("%Y-%m-%d"),
                'timeZone': timezone,
            },
            'end': {
                'date': eventEndTime.strftime("%Y-%m-%d"),
                'timeZone': timezone,
            },
            'source': {
                'title': 'Notion Link',
                'url': sourceURL,
            }
        }

    else:  # just 2 datetimes passed in
        if eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime != eventStartTime:  # Start on Notion is 12 am and end is also given on Notion
            eventStartTime = eventStartTime  # start will be 12 am
            eventEndTime = eventEndTime  # end will be whenever specified
        elif eventStartTime.hour == 0 and eventStartTime.minute == 0:  # if the datetime fed into this is only a date or is at 12 AM, then the event will fall under here
            eventStartTime = datetime.combine(eventStartTime, datetime.min.time()) + timedelta(
                hours=DEFAULT_EVENT_START)  ##make the events pop up at 8 am instead of 12 am
            eventEndTime = eventStartTime + timedelta(minutes=DEFAULT_EVENT_LENGTH)
        elif eventEndTime == eventStartTime:  # this would meant that only 1 datetime was actually on the notion dashboard
            eventStartTime = eventStartTime
            eventEndTime = eventStartTime + timedelta(minutes=DEFAULT_EVENT_LENGTH)
        else:  # if you give a specific start time to the event
            eventStartTime = eventStartTime
            eventEndTime = eventEndTime
        event = {
            'summary': eventName,
            'description': eventDescription,
            'start': {
                'dateTime': eventStartTime.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': eventEndTime.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': timezone,
            },
            'source': {
                'title': 'Notion Link',
                'url': sourceURL,
            }
        }
    print('Updating this event to calendar: ', eventName)

    if currentCalId == CalId:
        x = service.events().update(calendarId=CalId, eventId=eventId, body=event).execute()

    else:  # When we have to move the event to a new calendar. We must move the event over to the new calendar and then update the information on the event
        print('Event ' + eventId)
        print('CurrentCal ' + currentCalId)
        print('NewCal ' + CalId)
        x = service.events().move(calendarId=currentCalId, eventId=eventId, destination=CalId).execute()
        print('New event id: ' + x['id'])
        x = service.events().update(calendarId=CalId, eventId=eventId, body=event).execute()

    return x['id']


###########################################################################
# Part 1: Take Notion Events not on GCal and move them over to GCal
###########################################################################


# Note that we are only querying for events that are today or in the next week so the code can be efficient. # If
# you just want all Notion events to be on GCal, then you'll have to edit the query so it is only checking the 'On
# GCal?' property

my_page = notion.databases.query(
    **{
        "database_id": database_id,
        "filter": {
            "and": [
                {
                    "property": On_GCal_Notion_Name,
                    "checkbox": {
                        "equals": False
                    }
                },
                {
                    "or": [
                        {
                            "property": Date_Notion_Name,
                            "date": {
                                "equals": today_date
                            }
                        },
                        {
                            "property": Date_Notion_Name,
                            "date": {
                                "next_week": {}
                            }
                        }
                    ]
                },
                {
                    "property": Delete_Notion_Name,
                    "checkbox": {
                        "equals": False
                    }
                }
            ]
        }
    }
)
resultList = my_page['results']

TaskNames = []
start_Dates = []
end_Times = []
Initiatives = []
ExtraInfo = []
URL_list = []
calEventIdList = []
CalendarList = []

if len(resultList) > 0:

    for i, el in enumerate(resultList):
        print('\n')
        print(el)
        print('\n')

        TaskNames.append(el['properties'][Task_Notion_Name]['title'][0]['text']['content'])
        start_Dates.append(el['properties'][Date_Notion_Name]['date']['start'])

        if el['properties'][Date_Notion_Name]['date']['end'] is not None:
            end_Times.append(el['properties'][Date_Notion_Name]['date']['end'])
        else:
            end_Times.append(el['properties'][Date_Notion_Name]['date']['start'])

        try:
            Initiatives.append(el['properties'][Initiative_Notion_Name]['select']['name'])
        except KeyError:
            Initiatives.append("")

        try:
            ExtraInfo.append(el['properties'][ExtraInfo_Notion_Name]['rich_text'][0]['text']['content'])
        except KeyError:
            ExtraInfo.append("")
        URL_list.append(make_task_url(el['id'], env.URL_ROOT))

        try:
            CalendarList.append(calendarDictionary[el['properties'][Calendar_Notion_Name]['select']['name']])
        except KeyError:
            CalendarList.append(calendarDictionary[DEFAULT_CALENDAR_NAME])

        pageId = el['id']
        # This checks ON that the event has been put on Google Calendar
        my_page = notion.pages.update(
            **{
                "page_id": pageId,
                "properties": {
                    On_GCal_Notion_Name: {
                        "checkbox": True
                    },
                    LastUpdatedTime_Notion_Name: {
                        "date": {
                            'start': notion_time(),
                            'end': None,
                        }
                    },
                },
            },
        )

        # 2 Cases: Start and End are both either date or date+time
        # Have restriction that the calendar events don't cross days
        try:
            # start and end are both dates
            calEventId = make_cal_event(TaskNames[i], make_event_description(Initiatives[i], ExtraInfo[i]),
                                        datetime.strptime(start_Dates[i], '%Y-%m-%d'), URL_list[i],
                                        datetime.strptime(end_Times[i], '%Y-%m-%d'), CalendarList[i])
        except:
            try:
                # start and end are both date+time
                calEventId = make_cal_event(TaskNames[i], make_event_description(Initiatives[i], ExtraInfo[i]),
                                            datetime.strptime(start_Dates[i][:-6], "%Y-%m-%dT%H:%M:%S.000"),
                                            URL_list[i],
                                            datetime.strptime(end_Times[i][:-6], "%Y-%m-%dT%H:%M:%S.000"),
                                            CalendarList[i])
            except:
                calEventId = make_cal_event(TaskNames[i], make_event_description(Initiatives[i], ExtraInfo[i]),
                                            datetime.strptime(start_Dates[i][:-6], "%Y-%m-%dT%H:%M:%S.%f"), URL_list[i],
                                            datetime.strptime(end_Times[i][:-6], "%Y-%m-%dT%H:%M:%S.%f"),
                                            CalendarList[i])

        calEventIdList.append(calEventId)

        # this means that there is no calendar # assigned on Notion
        if CalendarList[i] == calendarDictionary[DEFAULT_CALENDAR_NAME]:
            # This puts the the GCal Id into the Notion Dashboard
            my_page = notion.pages.update(
                **{
                    "page_id": pageId,
                    "properties": {
                        GCalEventId_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': calEventIdList[i]
                                }
                            }]
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': CalendarList[i]
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": DEFAULT_CALENDAR_NAME
                            },
                        },
                    },
                },
            )
        else:  # just a regular update
            my_page = notion.pages.update(
                **{
                    "page_id": pageId,
                    "properties": {
                        GCalEventId_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': calEventIdList[i]
                                }
                            }]
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': CalendarList[i]
                                }
                            }]
                        }
                    },
                },
            )

else:
    print("Nothing new added to GCal")

###########################################################################
# Part 2: Updating GCal Events that Need To Be Updated (Changed on Notion but need to be changed on GCal)
###########################################################################


# Just gotta put a fail-safe in here in case people deleted the Calendar Variable
# this queries items in the next week where the Calendar select thing is empty
my_page = notion.databases.query(
    **{
        "database_id": database_id,
        "filter": {
            "and": [
                {
                    "property": Calendar_Notion_Name,
                    "select": {
                        "is_empty": True
                    }
                },
                {
                    "or": [
                        {
                            "property": Date_Notion_Name,
                            "date": {
                                "equals": today_date
                            }
                        },
                        {
                            "property": Date_Notion_Name,
                            "date": {
                                "next_week": {}
                            }
                        }
                    ]
                },
                {
                    "property": Delete_Notion_Name,
                    "checkbox": {
                        "equals": False
                    }
                }
            ]
        },
    }
)
resultList = my_page['results']

if len(resultList) > 0:
    for i, el in enumerate(resultList):
        pageId = el['id']
        # This checks off that the event has been put on Google Calendar
        my_page = notion.pages.update(
            **{
                "page_id": pageId,
                "properties": {
                    Calendar_Notion_Name: {
                        'select': {
                            "name": DEFAULT_CALENDAR_NAME
                        },
                    },
                    LastUpdatedTime_Notion_Name: {
                        "date": {
                            'start': notion_time(),
                            'end': None,
                        }
                    },
                },
            },
        )

# Filter events that have been updated since the GCal event has been made

# this query will return a dictionary that we will parse for information that we want
# look for events that are today or in the next week
my_page = notion.databases.query(
    **{
        "database_id": database_id,
        "filter": {
            "and": [
                {
                    "property": NeedGCalUpdate_Notion_Name,
                    "checkbox": {
                        "equals": True
                    }
                },
                {
                    "property": On_GCal_Notion_Name,
                    "checkbox": {
                        "equals": True
                    }
                },
                {
                    "or": [
                        {
                            "property": Date_Notion_Name,
                            "date": {
                                "equals": today_date
                            }
                        },
                        {
                            "property": Date_Notion_Name,
                            "date": {
                                "next_week": {}
                            }
                        }
                    ]
                },
                {
                    "property": Delete_Notion_Name,
                    "checkbox": {
                        "equals": False
                    }
                }
            ]
        },
    }
)
resultList = my_page['results']

updatingNotionPageIds = []
updatingCalEventIds = []

for result in resultList:
    print(result)
    print('\n')
    pageId = result['id']
    updatingNotionPageIds.append(pageId)
    print('\n')
    print(result)
    print('\n')
    try:
        calId = result['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content']
    except:
        calId = DEFAULT_CALENDAR_ID
    print(calId)
    updatingCalEventIds.append(calId)

TaskNames = []
start_Dates = []
end_Times = []
Initiatives = []
ExtraInfo = []
URL_list = []
CalendarList = []
CurrentCalList = []

if len(resultList) > 0:

    for i, el in enumerate(resultList):
        print('\n')
        print(el)
        print('\n')

        TaskNames.append(el['properties'][Task_Notion_Name]['title'][0]['text']['content'])
        start_Dates.append(el['properties'][Date_Notion_Name]['date']['start'])

        if el['properties'][Date_Notion_Name]['date']['end'] is not None:
            end_Times.append(el['properties'][Date_Notion_Name]['date']['end'])
        else:
            end_Times.append(el['properties'][Date_Notion_Name]['date']['start'])

        try:
            Initiatives.append(el['properties'][Initiative_Notion_Name]['select']['name'])
        except:
            Initiatives.append("")

        try:
            ExtraInfo.append(el['properties'][ExtraInfo_Notion_Name]['rich_text'][0]['text']['content'])
        except:
            ExtraInfo.append("")
        URL_list.append(make_task_url(el['id'], env.URL_ROOT))

        print(el)
        # CalendarList.append(calendarDictionary[el['properties'][Calendar_Notion_Name]['select']['name']])
        try:
            CalendarList.append(calendarDictionary[el['properties'][Calendar_Notion_Name]['select']['name']])
        except:  # keyerror occurs when there's nothing put into the calendar in the first place
            CalendarList.append(calendarDictionary[DEFAULT_CALENDAR_NAME])

        CurrentCalList.append(el['properties'][Current_Calendar_Id_Notion_Name]['rich_text'][0]['text']['content'])

        pageId = el['id']

        ##depending on the format of the dates, we'll update the gCal event as necessary
        try:
            calEventId = upDateCalEvent(TaskNames[i], make_event_description(Initiatives[i], ExtraInfo[i]),
                                        datetime.strptime(start_Dates[i], '%Y-%m-%d'), URL_list[i],
                                        updatingCalEventIds[i], datetime.strptime(end_Times[i], '%Y-%m-%d'),
                                        CurrentCalList[i], CalendarList[i])
        except:
            try:
                calEventId = upDateCalEvent(TaskNames[i], make_event_description(Initiatives[i], ExtraInfo[i]),
                                            datetime.strptime(start_Dates[i][:-6], "%Y-%m-%dT%H:%M:%S.000"),
                                            URL_list[i], updatingCalEventIds[i],
                                            datetime.strptime(end_Times[i][:-6], "%Y-%m-%dT%H:%M:%S.000"),
                                            CurrentCalList[i], CalendarList[i])
            except:
                calEventId = upDateCalEvent(TaskNames[i], make_event_description(Initiatives[i], ExtraInfo[i]),
                                            datetime.strptime(start_Dates[i][:-6], "%Y-%m-%dT%H:%M:%S.%f"), URL_list[i],
                                            updatingCalEventIds[i],
                                            datetime.strptime(end_Times[i][:-6], "%Y-%m-%dT%H:%M:%S.%f"),
                                            CurrentCalList[i], CalendarList[i])

        my_page = notion.pages.update(  ##### This updates the last time that the page in Notion was updated by the code
            **{
                "page_id": pageId,
                "properties": {
                    LastUpdatedTime_Notion_Name: {
                        "date": {
                            'start': notion_time(),  # has to be adjusted for when daylight savings is different
                            'end': None,
                        }
                    },
                    Current_Calendar_Id_Notion_Name: {
                        "rich_text": [{
                            'text': {
                                'content': CalendarList[i]
                            }
                        }]
                    },
                },
            },
        )


else:
    print("Nothing new updated to GCal")

today_date = datetime.today().strftime("%Y-%m-%d")

###########################################################################
# Part 3: Sync GCal event updates for events already in Notion back to Notion!
###########################################################################

# Query notion tasks already in Gcal, don't have to be updated, and are today or in the next week
my_page = notion.databases.query(
    **{
        "database_id": database_id,
        "filter": {
            "and": [
                {
                    "property": NeedGCalUpdate_Notion_Name,
                    "formula": {
                        "checkbox": {
                            "equals": False
                        }
                    }
                },
                {
                    "property": On_GCal_Notion_Name,
                    "checkbox": {
                        "equals": True
                    }
                },
                {
                    "or": [
                        {
                            "property": Date_Notion_Name,
                            "date": {
                                "equals": today_date
                            }
                        },
                        {
                            "property": Date_Notion_Name,
                            "date": {
                                "next_week": {}
                            }
                        }
                    ]
                },
                {
                    "property": Delete_Notion_Name,
                    "checkbox": {
                        "equals": False
                    }
                }
            ]
        },
    }
)

resultList = my_page['results']

# Comparison section:
# We need to see what times between GCal and Notion are not the same, so we are going to convert all of the
# notion date/times into datetime values and then compare that against the datetime value of the GCal event.
# If they are not the same, then we change the Notion event as appropriate
notion_IDs_List = []
notion_start_datetimes = []
notion_end_datetimes = []
notion_gCal_IDs = []  # we will be comparing this against the gCal_datetimes
gCal_start_datetimes = []
gCal_end_datetimes = []

notion_gCal_CalIds = []  # going to fill this in from the select option, not the text option.
notion_gCal_CalNames = []
gCal_CalIds = []

for result in resultList:
    notion_IDs_List.append(result['id'])
    notion_start_datetimes.append(result['properties'][Date_Notion_Name]['date']['start'])
    notion_end_datetimes.append(result['properties'][Date_Notion_Name]['date']['end'])
    notion_gCal_IDs.append(result['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content'])
    try:
        notion_gCal_CalIds.append(calendarDictionary[result['properties'][Calendar_Notion_Name]['select']['name']])
        notion_gCal_CalNames.append(result['properties'][Calendar_Notion_Name]['select']['name'])
    except:  # keyerror occurs when there's nothing put into the calendar in the first place
        notion_gCal_CalIds.append(calendarDictionary[DEFAULT_CALENDAR_NAME])
        notion_gCal_CalNames.append(result['properties'][Calendar_Notion_Name]['select']['name'])

# the reason we take off the last 6 characters is so we can focus in on just the date and time instead of any extra info
for i in range(len(notion_start_datetimes)):
    try:
        notion_start_datetimes[i] = datetime.strptime(notion_start_datetimes[i], "%Y-%m-%d")
    except:
        try:
            notion_start_datetimes[i] = datetime.strptime(notion_start_datetimes[i][:-6], "%Y-%m-%dT%H:%M:%S.000")
        except:
            notion_start_datetimes[i] = datetime.strptime(notion_start_datetimes[i][:-6], "%Y-%m-%dT%H:%M:%S.%f")

for i in range(len(notion_end_datetimes)):
    if notion_end_datetimes[i] != None:
        try:
            notion_end_datetimes[i] = datetime.strptime(notion_end_datetimes[i], "%Y-%m-%d")
        except:
            try:
                notion_end_datetimes[i] = datetime.strptime(notion_end_datetimes[i][:-6], "%Y-%m-%dT%H:%M:%S.000")
            except:
                notion_end_datetimes[i] = datetime.strptime(notion_end_datetimes[i][:-6], "%Y-%m-%dT%H:%M:%S.%f")
    else:
        notion_end_datetimes[i] = notion_start_datetimes[
            i]  # the reason we're doing this weird ass thing is because when we put the end time into the update or make GCal event, it'll be representative of the date

##We use the gCalId from the Notion dashboard to get retrieve the start Time from the gCal event
value = ''
exitVar = ''
for gCalId in notion_gCal_IDs:

    for calendarID in calendarDictionary.keys():  # just check all of the calendars of interest for info about the event
        print('Trying ' + calendarID + ' for ' + gCalId)
        try:
            x = service.events().get(calendarId=calendarDictionary[calendarID], eventId=gCalId).execute()
        except:
            print('Event not found')
            x = {'status': 'unconfirmed'}
        if x['status'] == 'confirmed':
            gCal_CalIds.append(calendarID)
            value = x
        else:
            continue

    print(value)
    print('\n')
    try:
        gCal_start_datetimes.append(datetime.strptime(value['start']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S"))
    except:
        date = datetime.strptime(value['start']['date'], "%Y-%m-%d")
        x = datetime(date.year, date.month, date.day, 0, 0, 0)
        # gCal_start_datetimes.append(datetime.strptime(x, "%Y-%m-%dT%H:%M:%S"))
        gCal_start_datetimes.append(x)
    try:
        gCal_end_datetimes.append(datetime.strptime(value['end']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S"))
    except:
        date = datetime.strptime(value['end']['date'], "%Y-%m-%d")
        x = datetime(date.year, date.month, date.day, 0, 0, 0) - timedelta(days=1)
        # gCal_end_datetimes.append(datetime.strptime(value['end']['date'][:-6], "%Y-%m-%dT%H:%M:%S"))
        gCal_end_datetimes.append(x)

# Now we iterate and compare the time on the Notion Dashboard and the start time of the GCal event
# If the datetimes don't match up,  then the Notion  Dashboard must be updated

new_notion_start_datetimes = [''] * len(notion_start_datetimes)
new_notion_end_datetimes = [''] * len(notion_end_datetimes)

for i in range(len(new_notion_start_datetimes)):
    if notion_start_datetimes[i] != gCal_start_datetimes[i]:
        new_notion_start_datetimes[i] = gCal_start_datetimes[i]

    if notion_end_datetimes[i] != gCal_end_datetimes[i]:  # this means that there is no end time in notion
        new_notion_end_datetimes[i] = gCal_end_datetimes[i]

print('test')
print(new_notion_start_datetimes)
print(new_notion_end_datetimes)
print('\n')
for i in range(len(notion_gCal_IDs)):
    print(notion_start_datetimes[i], gCal_start_datetimes[i], notion_gCal_IDs[i])

for i in range(len(new_notion_start_datetimes)):
    if new_notion_start_datetimes[i] != '' and new_notion_end_datetimes[
        i] != '':  # both start and end time need to be updated
        start = new_notion_start_datetimes[i]
        end = new_notion_end_datetimes[i]

        if start.hour == 0 and start.minute == 0 and start == end:  # you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = notion.pages.update(
                # update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        Date_Notion_Name: {
                            "date": {
                                'start': start.strftime("%Y-%m-%d"),
                                'end': None,
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date": {
                                'start': notion_time(),  # has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
        elif start.hour == 0 and start.minute == 0 and end.hour == 0 and end.minute == 0:  # you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = notion.pages.update(
                # update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        Date_Notion_Name: {
                            "date": {
                                'start': start.strftime("%Y-%m-%d"),
                                'end': end.strftime("%Y-%m-%d"),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date": {
                                'start': notion_time(),  # has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
        else:  # update Notin using datetime format
            my_page = notion.pages.update(
                # update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        Date_Notion_Name: {
                            "date": {
                                'start': date_time_into_notion_format(start),
                                'end': date_time_into_notion_format(end),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date": {
                                'start': notion_time(),  # has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
    elif new_notion_start_datetimes[i] != '':  # only start time need to be updated
        start = new_notion_start_datetimes[i]
        end = notion_end_datetimes[i]

        if start.hour == 0 and start.minute == 0 and start == end:  # you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = notion.pages.update(
                # update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        Date_Notion_Name: {
                            "date": {
                                'start': start.strftime("%Y-%m-%d"),
                                'end': None,
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date": {
                                'start': notion_time(),  # has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
        elif start.hour == 0 and start.minute == 0 and end.hour == 0 and end.minute == 0:  # you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = notion.pages.update(
                # update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        Date_Notion_Name: {
                            "date": {
                                'start': start.strftime("%Y-%m-%d"),
                                'end': end.strftime("%Y-%m-%d"),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date": {
                                'start': notion_time(),  # has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
        else:  # update Notin using datetime format
            my_page = notion.pages.update(
                # update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        Date_Notion_Name: {
                            "date": {
                                'start': date_time_into_notion_format(start),
                                'end': date_time_into_notion_format(end),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date": {
                                'start': notion_time(),  # has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
    elif new_notion_end_datetimes[i] != '':  # only end time needs to be updated
        start = notion_start_datetimes[i]
        end = new_notion_end_datetimes[i]

        if start.hour == 0 and start.minute == 0 and start == end:  # you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = notion.pages.update(
                # update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        Date_Notion_Name: {
                            "date": {
                                'start': start.strftime("%Y-%m-%d"),
                                'end': None,
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date": {
                                'start': notion_time(),  # has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
        elif start.hour == 0 and start.minute == 0 and end.hour == 0 and end.minute == 0:  # you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = notion.pages.update(
                # update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        Date_Notion_Name: {
                            "date": {
                                'start': start.strftime("%Y-%m-%d"),
                                'end': end.strftime("%Y-%m-%d"),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date": {
                                'start': notion_time(),  # has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
        else:  # update Notin using datetime format
            my_page = notion.pages.update(
                # update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        Date_Notion_Name: {
                            "date": {
                                'start': date_time_into_notion_format(start),
                                'end': date_time_into_notion_format(end),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date": {
                                'start': notion_time(),  # has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
    else:  # nothing needs to be updated here
        continue

print(notion_IDs_List)
print('\n')
print(gCal_CalIds)

CalNames = list(calendarDictionary.keys())
CalIds = list(calendarDictionary.values())

for i, gCalId in enumerate(
        gCal_CalIds):  # instead of checking, just update the notion datebase with whatever calendar the event is on
    print('GcalId: ' + gCalId)
    my_page = notion.pages.update(  ##### This puts the the GCal Id into the Notion Dashboard
        **{
            "page_id": notion_IDs_List[i],
            "properties": {
                Current_Calendar_Id_Notion_Name: {  # this is the text
                    "rich_text": [{
                        'text': {
                            'content': CalIds[CalNames.index(gCalId)]
                        }
                    }]
                },
                Calendar_Notion_Name: {  # this is the select
                    'select': {
                        "name": gCalId
                    },
                },
                LastUpdatedTime_Notion_Name: {
                    "date": {
                        'start': notion_time(),  # has to be adjsuted for when daylight savings is different
                        'end': None,
                    }
                }
            },
        },
    )

###########################################################################
##### Part 4: Bring events (not in Notion already) from GCal to Notion
###########################################################################

##First, we get a list of all of the GCal Event Ids from the Notion Dashboard.

my_page = notion.databases.query(
    **{
        "database_id": database_id,
        "filter": {
            "and": [
                {
                    "property": GCalEventId_Notion_Name,
                    "text": {
                        "is_not_empty": True
                    }
                },
                {
                    "property": Delete_Notion_Name,
                    "checkbox": {
                        "equals": False
                    }
                }
            ]
        },
    }
)

my_page = notion.databases.query(
    **{
        "database_id": database_id,
        "filter": {
            "property": GCalEventId_Notion_Name,
            "text": {
                "is_not_empty": True
            }
        },
    }
)

resultList = my_page['results']

ALL_notion_gCal_Ids = []

for result in resultList:
    ALL_notion_gCal_Ids.append(result['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content'])

# Get the GCal Ids and other Event Info from Google Calendar

events = []
for el in calendarDictionary.keys():  # get all the events from all calendars of interest
    x = service.events().list(calendarId=calendarDictionary[el], maxResults=2000, timeMin=google_query()).execute()
    events.extend(x['items'])

print(events)

# calItems = events['items']
calItems = events

calName = [item['summary'] for item in calItems]

gCal_calendarId = [item['organizer']['email'] for item in
                   calItems]  # this is to get all of the calendarIds for each event

CalNames = list(calendarDictionary.keys())
CalIds = list(calendarDictionary.values())
gCal_calendarName = [CalNames[CalIds.index(x)] for x in gCal_calendarId]

calStartDates = []
calEndDates = []
for el in calItems:
    try:
        calStartDates.append(datetime.strptime(el['start']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S"))
    except:
        date = datetime.strptime(el['start']['date'], "%Y-%m-%d")
        x = datetime(date.year, date.month, date.day, 0, 0, 0)
        # gCal_start_datetimes.append(datetime.strptime(x, "%Y-%m-%dT%H:%M:%S"))
        calStartDates.append(x)
    try:
        calEndDates.append(datetime.strptime(el['end']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S"))
    except:
        date = datetime.strptime(el['end']['date'], "%Y-%m-%d")
        x = datetime(date.year, date.month, date.day, 0, 0, 0)
        # gCal_end_datetimes.append(datetime.strptime(value['end']['date'][:-6], "%Y-%m-%dT%H:%M:%S"))
        calEndDates.append(x)

calIds = [item['id'] for item in calItems]
# calDescriptions = [item['description'] for item in calItems]
calDescriptions = []
for item in calItems:
    try:
        calDescriptions.append(item['description'])
    except:
        calDescriptions.append(' ')

# Now, we compare the Ids from Notion and Ids from GCal. If the Id from GCal is not in the list from Notion, then
## we know that the event does not exist in Notion yet, so we should bring that over. 

for i in range(len(calIds)):
    if calIds[i] not in ALL_notion_gCal_Ids:

        if calStartDates[i] == calEndDates[i] - timedelta(days=1):  # only add in the start DATE
            # Here, we create a new page for every new GCal event
            end = calEndDates[i] - timedelta(days=1)
            my_page = notion.pages.create(
                **{
                    "parent": {
                        "database_id": database_id,
                    },
                    "properties": {
                        Task_Notion_Name: {
                            "type": 'title',
                            "title": [
                                {
                                    "type": 'text',
                                    "text": {
                                        "content": calName[i],
                                    },
                                },
                            ],
                        },
                        Date_Notion_Name: {
                            "type": 'date',
                            'date': {
                                'start': calStartDates[i].strftime("%Y-%m-%d"),
                                'end': None,
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "type": 'date',
                            'date': {
                                'start': notion_time(),
                                'end': None,
                            }
                        },
                        ExtraInfo_Notion_Name: {
                            "type": 'rich_text',
                            "rich_text": [{
                                'text': {
                                    'content': calDescriptions[i]
                                }
                            }]
                        },
                        GCalEventId_Notion_Name: {
                            "type": "rich_text",
                            "rich_text": [{
                                'text': {
                                    'content': calIds[i]
                                }
                            }]
                        },
                        On_GCal_Notion_Name: {
                            "type": "checkbox",
                            "checkbox": True
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': gCal_calendarId[i]
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": gCal_calendarName[i]
                            },
                        }
                    },
                },
            )

        elif calStartDates[i].hour == 0 and calStartDates[i].minute == 0 and calEndDates[i].hour == 0 and calEndDates[
            i].minute == 0:  # add start and end in DATE format
            # Here, we create a new page for every new GCal event
            end = calEndDates[i] - timedelta(days=1)

            my_page = notion.pages.create(
                **{
                    "parent": {
                        "database_id": database_id,
                    },
                    "properties": {
                        Task_Notion_Name: {
                            "type": 'title',
                            "title": [
                                {
                                    "type": 'text',
                                    "text": {
                                        "content": calName[i],
                                    },
                                },
                            ],
                        },
                        Date_Notion_Name: {
                            "type": 'date',
                            'date': {
                                'start': calStartDates[i].strftime("%Y-%m-%d"),
                                'end': end.strftime("%Y-%m-%d"),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "type": 'date',
                            'date': {
                                'start': notion_time(),
                                'end': None,
                            }
                        },
                        ExtraInfo_Notion_Name: {
                            "type": 'rich_text',
                            "rich_text": [{
                                'text': {
                                    'content': calDescriptions[i]
                                }
                            }]
                        },
                        GCalEventId_Notion_Name: {
                            "type": "rich_text",
                            "rich_text": [{
                                'text': {
                                    'content': calIds[i]
                                }
                            }]
                        },
                        On_GCal_Notion_Name: {
                            "type": "checkbox",
                            "checkbox": True
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': gCal_calendarId[i]
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": gCal_calendarName[i]
                            },
                        }
                    },
                },
            )

        else:  # regular datetime stuff
            # Here, we create a new page for every new GCal event
            my_page = notion.pages.create(
                **{
                    "parent": {
                        "database_id": database_id,
                    },
                    "properties": {
                        Task_Notion_Name: {
                            "type": 'title',
                            "title": [
                                {
                                    "type": 'text',
                                    "text": {
                                        "content": calName[i],
                                    },
                                },
                            ],
                        },
                        Date_Notion_Name: {
                            "type": 'date',
                            'date': {
                                'start': date_time_into_notion_format(calStartDates[i]),
                                'end': date_time_into_notion_format(calEndDates[i]),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "type": 'date',
                            'date': {
                                'start': notion_time(),
                                'end': None,
                            }
                        },
                        ExtraInfo_Notion_Name: {
                            "type": 'rich_text',
                            "rich_text": [{
                                'text': {
                                    'content': calDescriptions[i]
                                }
                            }]
                        },
                        GCalEventId_Notion_Name: {
                            "type": "rich_text",
                            "rich_text": [{
                                'text': {
                                    'content': calIds[i]
                                }
                            }]
                        },
                        On_GCal_Notion_Name: {
                            "type": "checkbox",
                            "checkbox": True
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': gCal_calendarId[i]
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": gCal_calendarName[i]
                            },
                        }
                    },
                },
            )

        print(f'Added this event to Notion: {calName[i]}')

###########################################################################
##### Part 5: Deletion Sync -- If marked Done in Notion, then it will delete the GCal event (and the Notion event once Python API updates)
###########################################################################


my_page = notion.databases.query(
    **{
        "database_id": database_id,
        "filter": {
            "and": [
                {
                    "property": GCalEventId_Notion_Name,
                    "text": {
                        "is_not_empty": True
                    }
                },
                {
                    "property": On_GCal_Notion_Name,
                    "checkbox": {
                        "equals": True
                    }
                },
                {
                    "property": Delete_Notion_Name,
                    "checkbox": {
                        "equals": True
                    }
                }
            ]
        },
    }
)

resultList = my_page['results']

if DELETE_OPTION == 0 and len(resultList) > 0:  # delete gCal event (and Notion task once the Python API is updated)
    CalendarList = []
    CurrentCalList = []

    for i, el in enumerate(resultList):
        calendarID = calendarDictionary[el['properties'][Calendar_Notion_Name]['select']['name']]
        eventId = el['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content']

        pageId = el['id']

        print(calendarID, eventId)

        try:
            service.events().delete(calendarId=calendarID, eventId=eventId).execute()
        except:
            continue

        my_page = notion.pages.update(  ##### Delete Notion task (diesn't work yet)
            **{
                "page_id": pageId,
                "archived": True,
                "properties": {}
            },
        )

        print(my_page)
