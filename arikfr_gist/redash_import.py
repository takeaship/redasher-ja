import json
import os
import sys
import peewee
import gzip
import click
from tqdm import tqdm
from funcy import project
from dateutil import parser as dt_parser
from collections import defaultdict

try:
    from redash import models
except:
    print "This script needs re:dash code in path."
    exit()


class IdentityMap(object):
    def __init__(self):
        self.identity_map = defaultdict(dict)

    def set(self, model, old_id, new_id):
        self.identity_map[model.__name__][str(old_id)] = new_id

    def get(self, model, old_id):
        if isinstance(model, basestring):
            name = model.capitalize()
            if name == 'Datasource':
                name = 'DataSource'
        else:
            name = model.__name__

        if name not in self.identity_map:
            return None

        return self.identity_map[name].get(str(old_id))

identities = IdentityMap()

def parse_dt(s):
    if s is None:
        return None

    return dt_parser.parse(s)


def create_group(org, model, line):
    group = model.create(org=org, type=models.Group.BUILTIN_GROUP, name=line['name'],
                 permissions=line['permissions'], created_at=parse_dt(line['created_at']))

    identities.set(model, line['id'], group.id)

    return group


def create_data_source(org, model, line):
    ds = model.create(org=org, name=line['name'], type=line['type'], options=line['options'], created_at=parse_dt(line['created_at']))
    identities.set(model, line['id'], ds.id)

    ds.add_group(org.default_group)

    return ds


def create_user(org, model, line):
    # add groups,
    groups = []
    for group_name in line['groups']:
        group = models.Group.get(models.Group.org==org, models.Group.name==group_name)
        groups.append(group.id)

    user = model.create(org=org, name=line['name'], email=line['email'],
                        password_hash=line['password_hash'], groups=groups,
                        api_key=line['api_key'])

    identities.set(model, line['id'], user.id)

    return user


def create_query_result(org, model, line):
    args = project(line, ("query_hash", "query", "data", "runtime"))
    args['retrieved_at'] = parse_dt(line['retrieved_at'])
    args['org'] = org
    args['data_source'] = identities.get(models.DataSource, line['data_source'])

    qr = model.create(**args)

    identities.set(model, line['id'], qr.id)

    return qr


def create_query(org, model, line):
    args = project(line, ("name", "description", "query", "query_hash", "api_key", "is_archived", "schedule"))

    args['org'] = org
    args['data_source'] = identities.get(models.DataSource, line['data_source'])
    args['latest_query_data'] = identities.get(models.QueryResult, line['latest_query_data'])
    args['user'] = identities.get(models.User, line['user'])
    args['last_modified_by'] = identities.get(models.User, line['last_modified_by'])
    args['created_at'] = parse_dt(line['created_at'])
    args['updated_at'] = parse_dt(line['updated_at'])

    query = model.create(**args)

    identities.set(model, line['id'], query.id)

    return query


def create_alert(org, model, line):
    args = project(line, ("name", "options", "state", "rearm"))

    # if args['rearm']:
    #     args['rearm'] = int(args['rearm'])
    # else:
    #     args['rearm'] = None

    args['org'] = org
    args['user'] = identities.get(models.User, line['user'])
    args['query'] = identities.get(models.Query, line['query'])
    args['last_triggered_at'] = parse_dt(line['last_triggered_at'])
    args['created_at'] = parse_dt(line['created_at'])
    args['updated_at'] = parse_dt(line['updated_at'])

    alert = model.create(**args)
    identities.set(model, line['id'], alert.id)

    return alert


def create_alert_subscription(org, model, line):
    model.create(created_at=parse_dt(line['created_at']),
                 updated_at=parse_dt(line['updated_at']),
                 user=identities.get(models.User, line['user']),
                 alert=identities.get(models.Alert, line['alert']))


def create_dashboard(org, model, line):
    args = project(line, ("slug", "name", "dashboard_filters_enabled", "is_archived", "layout"))

    args['org'] = org
    args['user'] = identities.get(models.User, line['user'])

    dashboard = model.create(**args)
    identities.set(model, line['id'], dashboard.id)

    return dashboard


def create_visualization(org, model, line):
    args = project(line, ("type", "name", "description", "options"))
    args['query'] = identities.get(models.Query, line['query'])

    vis = model.create(**args)
    identities.set(model, line['id'], vis.id)

    return vis

def create_widget(org, model, line):
    args = project(line, ("text", "width", "options"))
    args['dashboard'] = identities.get(models.Dashboard, line['dashboard'])
    args['visualization'] = identities.get(models.Visualization, line['visualization'])

    widget = model.create(**args)
    identities.set(model, line['id'], widget.id)

    return widget


def create_event(org, model, line):
    args = project(line, ("action", "object_type", "object_id", "additional_properties"))
    args['org'] = org
    args['user'] = identities.get(models.User, line['user'])
    args['created_at'] = parse_dt(line['created_at'])

    if args['object_id']:
        args['object_id'] = identities.get(args['object_type'], line['object_id'])

    model.create(**args)


processors = {
    models.Group: create_group,
    models.DataSource: create_data_source,
    models.User: create_user,
    models.QueryResult: create_query_result,
    models.Query: create_query,
    models.Alert: create_alert,
    models.AlertSubscription: create_alert_subscription,
    models.Dashboard: create_dashboard,
    models.Visualization: create_visualization,
    models.Widget: create_widget,
    models.Event: create_event
}


def get_line_count(filename):
    count = 0
    with gzip.open(filename, 'r') as f:
        for l in f:
            count += 1

    return count

def import_model(org, model, path):
    name = model.__name__
    # todo: share this with exporter
    filename = os.path.join(path, "{}_export.jsonl.gz".format(name.lower()))

    with gzip.open(filename, 'r') as f:
        for raw_line in tqdm(f, total=get_line_count(filename)):
            try:
                line = json.loads(raw_line)
                processors[model](org, model, line)
            except peewee.InternalError as ex:
                print ex
                exit()
            except Exception as ex:
                print ".. Failed with row: {} ({}, {})".format(line['id'], ex.__class__.__name__, ex.message)


def fix_dashboards(org):
    for dashboard in models.Dashboard.select():
        old_layout = json.loads(dashboard.layout)
        layout = []

        for row in old_layout:
            new_row = []
            if row is None:
                continue

            for widget in row:
                new_row.append(identities.get(models.Widget, widget))
            layout.append(new_row)

        dashboard.layout = json.dumps(layout)
        dashboard.save()


@click.command()
@click.option('--path', default=".", help='Directory of the exported tables.')
def import_org(path):
    with models.db.database.transaction():
        org = models.Organization.get_by_slug('default')

        all_models =  [models.Group, models.DataSource, models.User, models.QueryResult,
                      models.Query, models.Alert, models.AlertSubscription, models.Dashboard,
                      models.Visualization, models.Widget, models.Event]

        for model in all_models:
            if model.__name__ == 'Organization':
                continue

            print "Importing: {}".format(model.__name__)

            filename = import_model(org, model, path)

        fix_dashboards(org)

        with open('identities_{}.json'.format(org.slug), 'wb') as f:
            json.dump(identities.identity_map, f)


if __name__ == '__main__':
    import_org()
