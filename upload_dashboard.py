#!/usr/bin/env python3

from redash_gitstudio.redash import Redash
from consolemsg import step
from yamlns import namespace as  ns

def uploadDashboardYaml(c, yamlfile):
    r = Redash(c.url, c.apikey)
    datasource = 1 # TODO
    c.queryMap = dict()
    visualizationMap = dict()

    old_dashboard = ns.load('plantmonitor.yaml')

    new_dashboard = ns(r.create_dashboard(old_dashboard.name))

    dashboard_params = {
        param: old_dashboard[param]
        for param in [
            "slug",
            "tags",
            "dashboard_filters_enabled",
            #"is_archived",
            #"is_favorite",
            #"can_edit",
            #"layout",
        ]
        if param in old_dashboard
    }
    if dashboard_params:
        r.update_dashboard(new_dashboard.id, dashboard_params)

    if old_dashboard.tags:
        r.update_dashboard(new_dashboard.id, dict(
            tags = old_dashboard.tags,
        ))

    # TODO: Adhoc adding a filter query
    c.queryMap[2] = ns(r.create_query(
        name = "All plants",
        description = None,
        data_source_id = c.dataSourceMap[1],
        query = "SELECT name from plant;",
        schedule = None,
        is_archived = False,
        is_draft = False,
        options = {},
        #tags = old_query.tags,
    ))

    for old_widget in old_dashboard.widgets:
        old_widget = ns(old_widget)
        old_visualization = old_widget.get('visualization', None)
        if old_visualization is None:
            step(" Text widget\n{}", old_widget.text)
            new_visualization = None
        else:
            step(" widget: '{name}' ({type})", **old_visualization)
            old_query = old_visualization.query

            if old_query.id not in c.queryMap:
                for parameter in old_query.options.get('parameters', []):
                    if 'queryId' in parameter:
                        parameter.queryId = c.queryMap[parameter.queryId].id
                c.queryMap[old_query.id] = ns(r.create_query(
                    name = old_query.name,
                    description = old_query.description,
                    data_source_id = c.dataSourceMap[old_query.data_source_id],
                    query = old_query.query,
                    schedule = old_query.schedule,
                    is_archived = old_query.is_archived,
                    is_draft = old_query.is_draft,
                    options = old_query.options,
                    #tags = old_query.tags,
                ))
                
            new_query = c.queryMap[old_query.id]
            step("  query: '{name}'", **new_query)

            if old_visualization.id not in visualizationMap:
                visualizationMap[old_visualization.id] = ns(r.create_visualization(
                    query_id = new_query.id,
                    name = old_visualization.name,
                    description = old_visualization.description,
                    type = old_visualization.type,
                    options = old_visualization.options,
                ))

            new_visualization = visualizationMap[old_visualization.id]

        new_widget = ns(r.create_widget(
            dashboard_id = new_dashboard.id,
            visualization_id = new_visualization and new_visualization.id,
            text = old_widget.text,
            #width = old_widget.width,
            options = old_widget.options,
        ))

c = ns.load("config.yaml")
uploadDashboardYaml(c, 'plantmonitor.yaml')


