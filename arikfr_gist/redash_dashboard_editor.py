import os
import sys
import requests
import json
import time

REDASH_HOST = os.environ.get('REDASH_HOST', 'https://app.redash.io/account')
API_KEY = '...'


def url(resource, resource_id):
    return '{}/api/{}/{}?api_key={}'.format(REDASH_HOST, resource, resource_id, API_KEY)
    

def get_dashboard(dashboard_slug):
    return requests.get(url('dashboards', dashboard_slug)).json()


size_map = {1: 2, 2: 1, 3: 4, 4: 3}

def widgets_from_dashboard(dashboard):
    widgets = {}
    for row in dashboard['widgets']:
        for widget in row:
            widgets[widget['id']] = widget

    return widgets


def update_widget(widget, new_size):
    widget['visualization_id'] = widget.get('visualization', {}).get('id')
    widget.pop('visualization')

    response = requests.post(url('widgets', widget['id']), json=widget)
    if response.status_code != 200:
        return False

    return True


def update_widget_sizes(dashboard, new_layout):
    new_layout = json.loads(new_layout)
    widgets_map = widgets_from_dashboard(dashboard)

    for row in new_layout:
        widgets_count = len(row)
        if widgets_count < 1 or widgets_count > 4:
            print "You can place at most 4 widgets on a row and at least 1."
            exit()

        new_size = size_map[widgets_count]

        for widget_id in row:
            widget = widgets_map.get(widget_id)

            if not widget:
               print "Couldn't find widget: {}".format(widget_id) 
               continue

            update_widget(widget, new_size)


def update_layout(dashboard_slug, new_layout):
    current = get_dashboard(dashboard_slug)
    print "Current layout: {}".format(current['layout'])

    if not new_layout:
        print "No new layout given, skipping."
        return

    # update_widget_sizes(current, new_layout)
    response = requests.post(url('dashboards', current['id']), json={'name': current['name'], 'layout': new_layout})

    if response.status_code != 200:
        print "Failed updating:"
        print response.content

    print "Updated."
        


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Missing arguments. Example usage:"
        print 'python dashboard_editor.py test "[[3017, 3019, 3020], [3018, 3022, 3042], [3021], [3043]]"'
        exit()

    dashboard_slug = sys.argv[1]
    new_layout = sys.argv[2]
    print "Updating dashbaord: {}".format(dashboard_slug)
    print "New Layout: {}".format(new_layout)

    update_layout(dashboard_slug, new_layout)