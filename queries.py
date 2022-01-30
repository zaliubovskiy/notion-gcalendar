from datetime import datetime

import pytz

import constants
import env

time_zone = pytz.timezone(env.TIMEZONE)
today_date = datetime.today().strftime("%Y-%m-%d")
notion_time = datetime.now(time_zone).isoformat()

# BASE DICT TO UPDATE/CREATE Notin TASK
base_dict = {
    constants.status_notion_name: {
        'select': {
            "name": "Scheduled",
            "color": "yellow"
        }
    },
    constants.last_updated_time_notion_name: {
        "date": {
            'start': notion_time,
            'end': None,
        }
    }
}

# SEARCH QUERIES SEPARATELY

# Checks if the task hasn't been exported to Google Calendar yet
not_on_gcal_query = {
    "property": constants.on_gcal_notion_name,
    "checkbox": {
        "equals": False
    }
}

# Checks if the task has been exported to Google Calendar already
on_gcal_query = {
    "property": constants.on_gcal_notion_name,
    "checkbox": {
        "equals": True
    }
}

# Checks if the property 'Calendar' of Notion task has been deleted
calendar_name_default_query = {
    "property": constants.calendar_notion_name,
    "select": {
        "name": env.DEFAULT_CALENDAR_NAME
    }
}

# Checks if the task is 'Done'
not_done_query = {
    "property": constants.done_notion_name,
    "checkbox": {
        "equals": False
    }
}

done_query = {
    "property": constants.done_notion_name,
    "checkbox": {
        "equals": True
    }
}

# Get all the tasks that have start date set to today
today_date_query = {
    "property": constants.date_notion_name,
    "date": {
        "equals": today_date
    }
}

# Get all the tasks that have start date set to next week
next_week_query = {
    "property": constants.date_notion_name,
    "date": {
        "next_week": {}
    }
}

# Checks if the task has been edited
need_cal_update_query = {
    "property": constants.need_gcal_update_notion_name,
    "checkbox": {
        "equals": True
    }
}

not_need_cal_update_query = {
    "property": constants.need_gcal_update_notion_name,
    "checkbox": {
        "equals": False
    }
}

# Checks of the value Calendar is empty foe the task
empty_calendar_query = {
    "property": constants.calendar_notion_name,
    "select": {
        "is_empty": True
    }
}

gcal_event_id = {
    "property": constants.gcal_event_id_notion_name,
    "text": {
        "is_not_empty": True
    }
}


# SEARCH FUNCTIONS

# Retrieve new tasks for today and next week
def query_new_tasks(notion):

    notion_page = notion.databases.query(
        **{
            "database_id": env.DATABASE_ID,
            "filter": {
                "and": [
                    not_on_gcal_query,
                    {
                        "or": [
                            today_date_query,
                            next_week_query
                        ]
                    },
                    not_done_query
                ]
            }
        }
    )
    return notion_page


# Retrieve all the tasks where Calendar value is empty
def query_tasks_without_calendar(notion):

    notion_page = notion.databases.query(
        **{
            "database_id": env.DATABASE_ID,
            "filter": {
                "and": [
                    empty_calendar_query,
                    {
                        "or": [
                            today_date_query,
                            next_week_query
                        ]
                    },
                    not_done_query
                ]
            },
        }
    )

    return notion_page


# Retrieve all the tasks that on GCal already but need update
def get_tasks_to_update(notion):

    notion_page = notion.databases.query(
        **{
            "database_id": env.DATABASE_ID,
            "filter": {
                "and": [
                    need_cal_update_query,
                    on_gcal_query,
                    {
                        "or": [
                            today_date_query,
                            next_week_query
                        ]
                    },
                    not_done_query
                ]
            },
        }
    )
    return notion_page


# Retrieve tasks already in GCal, that don't need to be updated, and are today or in the next week
def query_tasks_already_synced(notion):

    notion_page = notion.databases.query(
        **{
            "database_id": env.DATABASE_ID,
            "filter": {
                "and": [
                    not_need_cal_update_query,
                    on_gcal_query,
                    {
                        "or": [
                            today_date_query,
                            next_week_query
                        ]
                    },
                    not_done_query
                ]
            }
        }
    )

    return notion_page


def query_all_tasks_this_week(notion):
    notion_page = notion.databases.query(
        **{
            "database_id": env.DATABASE_ID,
            "filter": {
                "or": [
                    today_date_query,
                    next_week_query
                ]
            }
        }
    )
    return notion_page


def query_all_tasks_done(notion):
    notion_page = notion.databases.query(
        **{
            "database_id": env.DATABASE_ID,
            "filter": {
                "and": [
                    gcal_event_id,
                    on_gcal_query,
                    done_query,
                    {
                        "or": [
                            today_date_query,
                            next_week_query
                        ]
                    },
                ]
            }
        }
    )
    return notion_page


def query_tasks_no_time(notion):
    notion_page = notion.databases.query(
        **{
            "database_id": env.DATABASE_ID,
            "filter": {
                "property": "Do Date",
                "date": {
                    "is_empty": True
                }
            }
        }
    )
    return notion_page
