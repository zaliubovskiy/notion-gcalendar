from functions import export_tasks_notion_to_gcal, update_tasks_notion_to_gcal, update_tasks_gcal_to_notion, \
    export_tasks_gcal_to_notion, done_tasks_change_color, update_tasks_no_time


def runner(event, context):
    # Synchronization N2GCal
    export_tasks_notion_to_gcal()
    update_tasks_notion_to_gcal()
    # Synchronization GCal2N
    update_tasks_gcal_to_notion()
    export_tasks_gcal_to_notion()
    # To set color of completed tasks to 'Graphite'
    done_tasks_change_color()
    # To set GCalEventID to 'notInCalendar'
    update_tasks_no_time()
