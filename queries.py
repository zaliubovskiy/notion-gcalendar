from datetime import datetime

import constants
import env

today_date = datetime.today().strftime("%Y-%m-%d")

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
done_query = {
    "property": constants.delete_notion_name,
    "checkbox": {
        "equals": False
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


# Checks of the value Calendar is empty foe the task
empty_calendar_query = {
    "property": constants.calendar_notion_name,
    "select": {
        "is_empty": True
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
                    done_query
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
                    done_query
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
                    done_query
                ]
            },
        }
    )
    return notion_page
