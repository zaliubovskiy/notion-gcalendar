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
service = build("calendar", "v3", credentials=credentials)
calendar = service.calendars().get(calendarId=env.DEFAULT_CALENDAR_ID).execute()
calendar_dictionary = {
    env.DEFAULT_CALENDAR_NAME: env.DEFAULT_CALENDAR_ID,
}

# task_names = []
# start_dates = []
# end_times = []
# initiatives = []
# extra_info = []
# url_list = []
# cal_event_id_list = []
# calendar_list = []


def notion_time():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def make_task_url(ending, url_root):
    return url_root + ending.replace('-', '')


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
                        'start': notion_time(),
                        'end': None,
                    }
                }
            }
        }
    )
    return


def make_event_description(initiative, info):
    if initiative == '' and info == '':
        return ''
    elif info == '':
        return initiative
    elif initiative == '':
        return info
    else:
        return f'Initiative: {initiative} \n{info}'


def update_notion_page(page_id, cal_event_id, calendar_name):
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
                            'content': calendar_name
                        }
                    }]
                },
                constants.calendar_notion_name: {
                    'select': {
                        "name": env.DEFAULT_CALENDAR_NAME
                    }
                }
            }
        }
    )
    return


# TO DEBUG and DELETE
def update_notion_page_2(page_id, cal_event_id, calendar_name):
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
                            'content': calendar_name
                        }
                    }]
                }
            },
        },
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
            end_time = el['properties'][constants.date_notion_name]['date']['end']
        except KeyError:
            end_time = start_date
        if end_time is None:
            end_time = start_date
        try:
            initiative = el['properties'][constants.initiative_notion_name]['select']['name']
        except KeyError:
            initiative = ''
        try:
            extra_info = el['properties'][constants.extra_info_notion_name]['rich_text'][0]['text']['content']
        except (KeyError, IndexError):
            extra_info = ''
        try:
            calendar_name = calendar_dictionary[el['properties'][constants.calendar_notion_name]['select']['name']]
        except KeyError:
            calendar_name = calendar_dictionary[env.DEFAULT_CALENDAR_NAME]
        print("I am el", el)

        try:
            current_calendar_name = el['properties'][
                constants.current_calendar_id_notion_name]['rich_text'][0]['text']['content']
        except IndexError:
            current_calendar_name = None
        try:
            event_id = el['properties'][constants.gcal_event_id_notion_name]['rich_text'][0]['text']['content']
        except IndexError:
            event_id = None

        description = make_event_description(initiative, extra_info)

        print("I am current_calendar_name", current_calendar_name)
        print(task_name, start_date, end_time, description, calendar_name, "end")

        # Parse datetime value
        if (len(start_date) and len(end_time)) == 29:
            converted_start_date = datetime.strptime(start_date[:-6], '%Y-%m-%dT%H:%M:%S.%f')
            converted_end_date = datetime.strptime(end_time[:-6], '%Y-%m-%dT%H:%M:%S.%f')
        elif (len(start_date) and len(end_time)) == 10:
            converted_start_date = datetime.strptime(start_date, '%Y-%m-%d')
            converted_end_date = datetime.strptime(end_time, '%Y-%m-%d')
        else:
            print("Unexpected datetime format")
            break

        if calendar_name == current_calendar_name:
            cal_event_id = create_or_update_event(task_name, description, converted_start_date,
                                                  url_link, converted_end_date, calendar_name,
                                                  current_calendar_name, event_id)
        else:
            cal_event_id = create_or_update_event(task_name, description, converted_start_date,
                                                  url_link, converted_end_date, calendar_name)

        # VERY BAD SOLUTION. TO DEBUG!
        if calendar_name == calendar_dictionary[env.DEFAULT_CALENDAR_NAME]:
            update_notion_page(page_id, cal_event_id, calendar_name)
        else:
            update_notion_page_2(page_id, cal_event_id, calendar_name)

        # Function to check ON that the event has been put on Google Calendar
        turn_on_gcal(page_id)
    return


def create_or_update_event(event_name, event_description,
                           event_start_time, source_url,
                           event_end_time, calendar_name,
                           current_calendar_name=None, event_id=None):

    # Only date of the task provided:
    if event_start_time.hour == 0 and event_start_time.minute == 0:

        # Start date without time, no end date
        if event_end_time == event_start_time:

            # Would be treated as all-day event
            if env.ALL_DAY_EVENT == 0:
                date_time_value = 'dateTime'
                event_start = event_start_time.strftime("%Y-%m-%dT%H:%M:%S")
                event_end = (event_end_time + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")

            # Would be assigned default time values for start and length: (12am and 1 hour)
            else:
                date_time_value = 'date'
                event_start = (datetime.combine(event_start_time, datetime.min.time()) + timedelta(
                    hours=env.DEFAULT_EVENT_START)).strftime("%Y-%m-%d")
                event_end = (event_start_time + timedelta(minutes=env.DEFAULT_EVENT_LENGTH)).strftime("%Y-%m-%d")

        # Start and end dates without time -> multiple-days event
        else:
            event_end = (event_end_time + timedelta(days=1)).strftime("%Y-%m-%d")
            event_start = event_start_time.strftime("%Y-%m-%d")
            date_time_value = 'date'

    # Date and time provided:
    else:
        event_start = event_start_time.strftime("%Y-%m-%dT%H:%M:%S")
        date_time_value = 'dateTime'

        # Event's time set, but it is the same for start and end dates
        if event_end_time == event_start_time:
            event_end = (event_start_time + timedelta(
                minutes=env.DEFAULT_EVENT_LENGTH)).strftime("%Y-%m-%dT%H"":%M:%S")
        # If a specific start time to the event given
        else:
            event_end = event_end_time.strftime("%Y-%m-%dT%H:%M:%S")

    # The event instance that would be passed to GCalendar
    event = {
        'summary': event_name,
        'description': event_description,
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
    if current_calendar_name and event_id:

        # If the event is in another calendar
        if calendar_name != current_calendar_name:
            service.events().move(calendarId=current_calendar_name, destination=calendar_name,
                                  eventId=event_id).execute()
        execution_instance = service.events().update(calendarId=calendar_name, body=event,
                                                     eventId=event_id).execute()

    #  Create event
    else:
        print("I am here creating event")
        execution_instance = service.events().insert(calendarId=calendar_name, body=event).execute()

    return execution_instance['id']


def export_new_notion_tasks():

    notion_page = queries.query_new_tasks(notion)
    result_list = notion_page['results']

    if len(result_list) > 0:
        retrieve_events(result_list)
        return print(f"Success: {len(result_list)} tasks have been exported GCal -> Notion")
    return print("No new tasks found")


def check_need_for_update():

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
                                'start': notion_time(),
                                'end': None,
                            }
                        }
                    }
                }
            )


def update_notion_tasks():

    notion_page = queries.get_tasks_to_update(notion)
    result_list = notion_page['results']

    if len(result_list) > 0:
        retrieve_events(result_list)
        return print(f"Success: {len(result_list)} tasks have been updated GCal -> Notion")
    return print("No tasks to update")


if __name__ == '__main__':
    export_new_notion_tasks()
    check_need_for_update()
    update_notion_tasks()
