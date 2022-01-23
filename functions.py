from datetime import datetime, timedelta

from googleapiclient.discovery import build
from notion_client import Client

import authentication
import constants
import env
import queries

credentials = authentication.authenticate()
notion = Client(auth=env.NOTION_TOKEN)
today_date = datetime.today().strftime("%Y-%m-%d")
time_min = (datetime.today() - timedelta(hours=env.HOURS_BEFORE)).isoformat() + 'Z'
time_max = (datetime.today() + timedelta(days=env.DAYS_AFTER)).isoformat() + 'Z'
service = build("calendar", "v3", credentials=credentials)
calendar = service.calendars().get(calendarId=env.DEFAULT_CALENDAR_ID).execute()
calendar_dictionary = {
    env.DEFAULT_CALENDAR_NAME: env.DEFAULT_CALENDAR_ID,
}


def datetime_to_notion(date):
    # Check if the date and time is given
    if date.hour == 0 and date.minute == 0:
        # Only date is given
        converted_date = date.strftime("%Y-%m-%d")
    else:
        converted_date = date.isoformat()
    return converted_date


def parse_datetime(date):
    # Check if the date and time is given
    if len(date) == 10:
        # Only date is given
        converted_date = datetime.strptime(date[:10], '%Y-%m-%d')
    else:
        converted_date = datetime.strptime(date[:19], '%Y-%m-%dT%H:%M:%S')

    return converted_date


def make_task_url(ending, url_root):
    return url_root + ending.replace('-', '')


def calendar_selector(calendar_name):
    calendar_id = env.DEFAULT_CALENDAR_ID

    calendars = service.calendarList().list().execute()
    for cal in calendars['items']:
        if calendar_name == cal['summary']:
            calendar_id = cal['id']
    return calendar_id


def turn_on_gcal(page_id):
    notion.pages.update(
        **{
            "page_id": page_id,
            "properties": {
                constants.on_gcal_notion_name: {
                    "checkbox": True
                },
                constants.last_updated_time_notion_name: {
                    "date": {
                        'start': queries.notion_time,
                        'end': None,
                    }
                }
            }
        }
    )
    return


def update_notion_page(page_id, cal_event_id, calendar_id, calendar_name):
    notion.pages.update(
        **{
            "page_id": page_id,
            "properties": {
                constants.gcal_event_id_notion_name: {
                    "rich_text": [{
                        'text': {
                            'content': cal_event_id
                        }
                    }]
                },
                constants.current_calendar_id_notion_name: {
                    "rich_text": [{
                        'text': {
                            'content': calendar_id
                        }
                    }]
                },
                constants.calendar_notion_name: {
                    'select': {
                        "name": calendar_name
                    }
                }
            }
        }
    )
    return


def retrieve_events(result_list):
    # Parse all the needed elements from the json object returned by Notion
    for i, el in enumerate(result_list):
        page_id = el['id']
        task_name = el['properties'][constants.task_notion_name]['title'][0]['text']['content']
        start_date = el['properties'][constants.date_notion_name]['date']['start']
        url_link = make_task_url(el['id'], env.URL_ROOT)
        try:
            end_date = el['properties'][constants.date_notion_name]['date']['end']
        except KeyError:
            end_date = start_date
        if end_date is None:
            end_date = start_date
        try:
            current_calendar_id = el['properties'][
                constants.current_calendar_id_notion_name]['rich_text'][0]['text']['content']
        except IndexError:
            current_calendar_id = None
        try:
            # the Calendar is selected:
            calendar_name = el['properties'][constants.calendar_notion_name]['select']['name']
            calendar_id = calendar_selector(calendar_name)
            print("I am calendar SELECTED YO!")
        except KeyError:
            # the Calendar not set:
            print("I AM  NOT SELECTED")
            calendar_name = env.DEFAULT_CALENDAR_NAME
            calendar_id = env.DEFAULT_CALENDAR_ID

        print("I am el", el)

        try:
            event_id = el['properties'][constants.gcal_event_id_notion_name]['rich_text'][0]['text']['content']
        except IndexError:
            event_id = None

        # Parse datetime value
        converted_start_date = parse_datetime(start_date)
        converted_end_date = parse_datetime(end_date)

        # Perform Post or Patch request to GCal API -> create or update GCal event
        cal_event_id = create_or_update_event_notion_to_gcal(task_name, converted_start_date,
                                                             url_link, converted_end_date,
                                                             current_calendar_id, event_id, calendar_id)

        # To Patch Notion Page with
        update_notion_page(page_id, cal_event_id, calendar_id, calendar_name)
        print(page_id, cal_event_id, calendar_id, calendar_name)

        # Function to check ON that the event has been put on Google Calendar
        turn_on_gcal(page_id)
    return


def create_or_update_event_notion_to_gcal(event_name, event_start_time,
                                          source_url, event_end_time,
                                          current_calendar_id, event_id, calendar_id):
    # Only date of the task provided:
    if event_start_time.hour == 0 and event_start_time.minute == 0:

        date_time_value = 'date'
        event_start = event_start_time.strftime("%Y-%m-%d")
        event_end = (event_end_time + timedelta(days=1)).strftime("%Y-%m-%d")

    # Date and time provided:
    else:
        date_time_value = 'dateTime'
        event_start = event_start_time.strftime("%Y-%m-%dT%H:%M:%S")

        # Event's time set, but it is the same for start and end dates
        if event_end_time == event_start_time:
            event_end = (event_start_time + timedelta(
                minutes=env.DEFAULT_EVENT_LENGTH)).strftime("%Y-%m-%dT%H:%M:%S")
        # If a specific start time to the event given
        else:
            event_end = event_end_time.strftime("%Y-%m-%dT%H:%M:%S")

    # The event instance that would be passed to GCalendar
    event = {
        'summary': event_name,
        'start': {
            date_time_value: event_start,
            'timeZone': env.TIMEZONE,
        },
        'end': {
            date_time_value: event_end,
            'timeZone': env.TIMEZONE,
        },
        'source': {
            'title': 'Notion Link',
            'url': source_url,
        }
    }

    # Update event
    if current_calendar_id and event_id:
        print("I am here updating event")

        # # If the event is in another calendar, we move it
        if calendar_id != current_calendar_id:
            service.events().move(calendarId=current_calendar_id, destination=calendar_id,
                                  eventId=event_id).execute()
        execution_instance = service.events().update(calendarId=current_calendar_id, body=event,
                                                     eventId=event_id).execute()

    #  Create event
    else:
        print("I am here creating event")
        execution_instance = service.events().insert(calendarId=calendar_id, body=event).execute()

    return execution_instance['id']


def export_tasks_notion_to_gcal():
    notion_page = queries.query_new_tasks(notion)
    result_list = notion_page['results']

    if len(result_list) > 0:
        retrieve_events(result_list)
        return print(f"Success: {len(result_list)} tasks have been exported GCal -> Notion")
    return print("No new Notion tasks found")


def check_tasks_without_calendar():
    notion_page = queries.query_tasks_without_calendar(notion)

    result_list = notion_page['results']

    if len(result_list) > 0:
        for i, el in enumerate(result_list):
            page_id = el['id']
            notion.pages.update(
                **{
                    "page_id": page_id,
                    "properties": {
                        constants.calendar_notion_name: {
                            'select': {
                                "name": env.DEFAULT_CALENDAR_NAME
                            },
                        },
                        constants.last_updated_time_notion_name: {
                            "date": {
                                'start': queries.notion_time,
                                'end': None,
                            }
                        }
                    }
                }
            )


def get_google_calendar_info(gcal_instance):
    gcal_task_name = gcal_instance['summary']
    gcal_cal_id = gcal_instance['organizer']['email']

    try:
        gcal_start_date = gcal_instance['start']['dateTime'][:19]
        gcal_start_date = parse_datetime(gcal_start_date)
    except KeyError:
        gcal_start_date = parse_datetime(gcal_instance['start']['date'][:10])

    try:
        gcal_end_date = parse_datetime(gcal_instance['end']['dateTime'][:19])
    except KeyError:
        gcal_end_date = parse_datetime(gcal_instance['end']['date'][:10])

    try:
        gcal_calendar_name = gcal_instance['organizer']['displayName']
    except KeyError:
        gcal_calendar_name = env.NAME_OF_MAIN_CALENDAR

    return gcal_task_name, gcal_cal_id, gcal_start_date, gcal_end_date, gcal_calendar_name


def get_notion_info(notion_instance):
    notion_task_name = notion_instance['properties'][constants.task_notion_name]['title'][0]['text']['content']
    notion_gcal_id = notion_instance['properties'][
        constants.current_calendar_id_notion_name]['rich_text'][0]['text']['content']

    notion_start_date = notion_instance['properties'][constants.date_notion_name]['date']['start']
    notion_start_date = parse_datetime(notion_start_date)

    notion_end_date = notion_instance['properties'][constants.date_notion_name]['date']['end']
    if notion_end_date:
        notion_end_date = parse_datetime(notion_end_date)
    else:
        notion_end_date = notion_start_date
        if notion_start_date.hour == 0 and notion_start_date.minute == 0:
            notion_end_date += timedelta(days=1)

    notion_calendar_name = notion_instance['properties'][constants.calendar_notion_name]['select']['name']

    return notion_task_name, notion_gcal_id, notion_start_date, notion_end_date, notion_calendar_name


def update_tasks_notion_to_gcal():

    check_tasks_without_calendar()

    notion_page = queries.get_tasks_to_update(notion)
    result_list = notion_page['results']

    if len(result_list) > 0:
        retrieve_events(result_list)
        return print(f"Success: {len(result_list)} tasks have been updated GCal -> Notion")
    return print("No GCal -> Notion tasks to update")


def compare_gcal_notion_tasks(result_list):
    for result in result_list:
        # TO COMPARE: task_name, current_calendar_id, calendar, date,
        # page_id = result['id']
        # event_id = result['properties'][constants.gcal_event_id_notion_name]['rich_text'][0]['text']['content']
        # task_name = result['properties'][constants.task_notion_name]['title'][0]['text']['content']
        # start_date = result['properties'][constants.date_notion_name]['date']['start']
        # try:
        #     end_date = result['properties'][constants.date_notion_name]['date']['end']
        # except KeyError:
        #     end_date = start_date
        # if end_date is None:
        #     end_date = start_date
        # current_calendar_id = result['properties'][
        #         constants.current_calendar_id_notion_name]['rich_text'][0]['text']['content']
        # calendar_name = result['properties'][constants.calendar_notion_name]['select']['name']
        # calendar_id = calendar_selector(calendar_name)
        #
        # print("I am result", result)
        #
        # # Parse datetime value
        # converted_start_date, converted_end_date = parse_notion_datetime(start_date, end_date)
        #
        # # try:
        # gcal_instance = service.events().get(calendarId=current_calendar_id, eventId=event_id).execute()
        # gcal_start_date = gcal_instance['start']

        # Prepare all the needed information to compare task instance GCal -> Notion
        page_id = result['id']
        event_id = result['properties'][constants.gcal_event_id_notion_name]['rich_text'][0]['text']['content']
        current_calendar_id = result['properties'][constants.current_calendar_id_notion_name]['rich_text'][0]['text'][
            'content']
        gcal_instance = service.events().get(calendarId=current_calendar_id, eventId=event_id).execute()

        # GET NOTION VALUES
        notion_task_name, notion_gcal_id, notion_start_date, notion_end_date, notion_calendar_name = get_notion_info(result)

        # GET GCAL VALUES
        gcal_task_name, gcal_cal_id, gcal_start_date, gcal_end_date, gcal_calendar_name = get_google_calendar_info(gcal_instance)

        # PREPARE BASE UPDATE QUERY

        properties_dict = queries.base_dict.copy()

        # COMPARE TWO SETS OF DATA AND ADD IT TO THE UPDATE QUERY

        # We need 3 different queries for 3 cases when updating DateTime
        # 1. Start AND End datetime changed:
        if gcal_start_date != notion_start_date and gcal_end_date != notion_end_date:
            print("START DATE AND END DATE")
            if notion_end_date - notion_start_date == timedelta(days=1):
                properties_dict[constants.date_notion_name] = {
                    "date": {
                        "start": datetime_to_notion(gcal_start_date),
                    }
                }
                print("TimeDelta = 1 DAY")
            else:
                if notion_start_date.hour == 0 and notion_start_date.minute == 0:
                    gcal_end_date -= timedelta(days=1)
                properties_dict[constants.date_notion_name] = {
                    "date": {
                        "start": datetime_to_notion(gcal_start_date),
                        "end": datetime_to_notion(gcal_end_date)
                    }
                }
                print("TimeDelta != 1 DAY")
        # 2. Start datetime changed ONLY
        elif gcal_start_date != notion_start_date and gcal_end_date == notion_end_date:
            print("START DATE ONLY")
            properties_dict[constants.date_notion_name] = {
                "date": {
                    "start": datetime_to_notion(gcal_start_date),
                }
            }
        # 3. End datetime changed ONLY
        elif gcal_end_date != notion_end_date and gcal_start_date == notion_start_date:
            if not gcal_end_date - notion_end_date == timedelta(days=1):
                print("END DATE ONLY")
                print("gcal_end_date", gcal_end_date)
                print("notion_end_date", notion_end_date)
                properties_dict[constants.date_notion_name] = {
                    "date": {
                        "start": datetime_to_notion(gcal_start_date),
                        "end": datetime_to_notion(gcal_end_date)
                    }
                }
            else:
                print("I am just compensating the Notion -> Gcal conversion")

        if gcal_task_name != notion_task_name:
            print("TASK NAME")
            properties_dict[constants.task_notion_name] = {
                "title": [{
                    "text": {
                        "content": gcal_task_name
                    }
                }]
            }

        if gcal_cal_id != notion_gcal_id:
            print("CALENDAR ID")
            properties_dict[constants.current_calendar_id_notion_name] = {
                "rich_text": [{
                    'text': {
                        'content': gcal_cal_id
                    }
                }]
            }

        if gcal_calendar_name != notion_calendar_name:
            print("CALENDAR NAME")
            properties_dict[constants.calendar_notion_name] = {
                "select": {
                    "name": gcal_calendar_name
                }
            }

        # Now we proceed if there is anything changed only
        if queries.base_dict != properties_dict:
            print("I have something to change")
            # This function updates the Notion task with only needed information
            notion.pages.update(
                **{
                    "page_id": page_id,
                    "properties": properties_dict
                }
            )
            return print(f"Success: {len(result_list)} tasks have been updated Notion -> GCal")
        else:
            print("No Notion -> GCal tasks to update")


def update_tasks_gcal_to_notion():
    # Query notion tasks already in Gcal, don't have to be updated, and are today or in the next week
    notion_page = queries.query_tasks_already_synced(notion)

    result_list = notion_page['results']

    if len(result_list) > 0:
        compare_gcal_notion_tasks(result_list)
        return
    return


def export_tasks_gcal_to_notion():
    notion_page = queries.query_all_tasks_not_done(notion)

    result_list = notion_page['results']

    # We take all the GCal event IDs from the Notion
    list_of_event_ids = []
    for result in result_list:
        try:
            event_id = result['properties'][constants.gcal_event_id_notion_name]['rich_text'][0]['text']['content']
        except IndexError:
            continue
        list_of_event_ids.append(event_id)
    print("i am a list_of_event_ids", list_of_event_ids)
    google_events = []

    # We take all the calendars from Google Calendar, one by one
    for e in calendar_dictionary.keys():
        current_calendar_id = calendar_dictionary[e]

        # Get all the tasks from the current calendar in the timeframe time_min - time_max
        events = service.events().list(calendarId=current_calendar_id,
                                       timeMin=time_min,
                                       timeMax=time_max,
                                       maxResults=100).execute()
        # We take all the events one by one and check if they are on Notion:
        for event in events['items']:
            event_id = event['id']
            # If they are not on Notion, we create the Task
            if event_id not in list_of_event_ids:
                print("I am exporting the task:", event['summary'])
                gcal_instance = service.events().get(calendarId=current_calendar_id, eventId=event_id).execute()

                gcal_task_name, gcal_cal_id, gcal_start_date, gcal_end_date, gcal_calendar_name = get_google_calendar_info(gcal_instance)

                properties_dict = queries.base_dict.copy()

                properties_dict[constants.gcal_event_id_notion_name] = {
                    "rich_text": [{
                        'text': {
                            'content': event_id
                        }
                    }]
                }
                properties_dict[constants.task_notion_name] = {
                    "title": [{
                        "text": {
                            "content": gcal_task_name
                        }
                    }]
                }
                properties_dict[constants.current_calendar_id_notion_name] = {
                    "rich_text": [{
                        'text': {
                            'content': gcal_cal_id
                        }
                    }]
                }
                properties_dict[constants.calendar_notion_name] = {
                    "select": {
                        "name": gcal_calendar_name
                    }
                }
                properties_dict[constants.date_notion_name] = {
                    "date": {
                        "start": datetime_to_notion(gcal_start_date),
                        "end": datetime_to_notion(gcal_end_date)
                    }
                }
                properties_dict[constants.on_gcal_notion_name] = {
                    "checkbox": True
                }

                # This function create the Notion task with the needed information
                notion.pages.create(
                    **{
                        "parent": {
                            "database_id": env.DATABASE_ID,
                        },
                        "properties": properties_dict
                    }
                )



def done_tasks_change_color():
    notion_page = queries.query_all_tasks_done(notion)


if __name__ == '__main__':
    # Function to set GCalEventID to 'notInCalendar'

    # Synchronization N2GCal
    # export_tasks_notion_to_gcal()
    # update_tasks_notion_to_gcal()
    # Synchronization GCal2N
    # update_tasks_gcal_to_notion()
    # export_tasks_gcal_to_notion()
    done_tasks_change_color()