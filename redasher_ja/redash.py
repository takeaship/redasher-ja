# https://gist.githubusercontent.com/arikfr/91ce854f358b8d0cef60dcd1bfb60bf3/raw/ebdf6db2b19b3479901183325e2a840155c4abbe/redash.py
import requests
import os
from decorator import decorator
import itertools

class Redash(object):
    def __init__(self, redash_url, api_key):
        self.redash_url = redash_url
        self.session = requests.Session()
        self.session.headers.update({'Authorization': 'Key {}'.format(api_key)})

    def test_credentials(self):
        try:
            response = self._get('api/session')
            return True
        except requests.exceptions.HTTPError:
            return False

    def status(self):
        return self._get('status.json').json()

    def users(self):
        """GET api/users"""
        return self._paginated_get('api/users')

    def queries(self):
        """GET api/queries"""
        return self._paginated_get('api/queries')

    def dashboards(self):
        """GET api/dashboards"""
        return self._paginated_get('api/dashboards')

    def datasources(self):
        """GET api/data_sources"""
        return self._get('api/data_sources').json()

    def datasource(self, id):
        """GET api/data_sources/{id}"""
        return self._get('api/data_sources/{}'.format(id)).json()

    def dashboard(self, slug):
        """GET api/dashboards/{slug}"""
        return self._get('api/dashboards/{}'.format(slug)).json()

    def query(self, id):
        """GET api/dashboards/{id}"""
        return self._get('api/queries/{}'.format(id)).json()

    def create_query(self, data_source_id, query, is_draft, is_archived, schedule, name, description, options, **kwds):
        data = {
            "data_source_id": data_source_id,
            "query": query,
            "is_archived": is_archived,
            "is_draft": is_draft,
            "schedule": schedule,
            "description": description,
            "name": name,
            "options": options,
        }
        return self._post('api/queries', json=data).json()

    def create_visualization(self, query_id, type, name, description, options):
        data = {
            "name": name,
            "description": description,
            "options": options,
            "type": type,
            "query_id": query_id,
        }
        return self._post('api/visualizations', json=data).json()

    def update_visualization(self, visualization_id, query_id, type, name, description, options):
        data = {
            "name": name,
            "description": description,
            "options": options,
            "type": type,
            "query_id": query_id,
        }
        return self._post('api/visualizations/{}'.format(visualization_id), json=data).json()

    def create_dashboard(self, name):
        return self._post('api/dashboards', json={'name': name}).json()

    def update_dashboard(self, dashboard_id, properties):
        return self._post('api/dashboards/{}'.format(dashboard_id), json=properties).json()

    def create_widget(self, dashboard_id, visualization_id, text, options, width=1):
        data = {
            'dashboard_id': dashboard_id,
            'visualization_id': visualization_id,
            'text': text,
            'options': options,
            'width': width,
        }
        return self._post('api/widgets', json=data).json()

    def update_widget(self, widget_id, data):
        return self._post('api/widgets/{}'.format(widget_id), json=data).json()

    def duplicate_dashboard(self, slug, new_name=None):
        current_dashboard = self.dashboard(slug)

        if new_name is None:
            new_name = u'Copy of: {}'.format(current_dashboard['name'])

        new_dashboard = self.create_dashboard(new_name)
        if current_dashboard['tags']:
            self.update_dashboard(new_dashboard['id'], {'tags': current_dashboard['tags']})

        for widget in current_dashboard['widgets']:
            visualization_id = None
            if 'visualization' in widget:
                visualization_id = widget['visualization']['id']
            self.create_widget(new_dashboard['id'], visualization_id, widget['text'], widget['options'])

        return new_dashboard

    def scheduled_queries(self):
        """Loads all queries and returns only the scheduled ones."""
        return (query for query in self.queries() if query['schedule'] is not None)

    def update_query(self, query_id, data):
        """POST /api/queries/{query_id} with the provided data object."""
        path = 'api/queries/{}'.format(query_id)
        return self._post(path, json=data)

    def delete_dashboard(self, dashboard_id):
        return self._delete('api/dashboard/{}'.format(dashboard_id))

    def delete_query(self, query_id):
        return self._delete('api/query/{}'.format(query_id))

    def _paginated_get(self, path, **kwds):
        page_size=100
        for page in itertools.count(1):
            response =  self._get(path, params=dict(kwds,
                page=page,
                page_size=page_size,
            )).json()
            yield from response['results']
            if response['page'] * response['page_size'] >= response['count']:
                break

    def _delete(self, path, **kwargs):
        return self._request('DELETE', path, **kwargs)

    def _get(self, path, **kwargs):
        return self._request('GET', path, **kwargs)

    def _post(self, path, **kwargs):
        return self._request('POST', path, **kwargs)

    def _request(self, method, path, **kwargs):
        try:
            url = '{}/{}'.format(self.redash_url, path)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except:
            from yamlns import namespace as ns
            print("{} {}\n{}".format(
                method, path, ns(kwargs).dump()
            ))
            raise


if __name__ == '__main__':
    api_key = os.environ.get('REDASH_API_KEY')
    redash_url = os.environ.get('REDASH_URL')
    redash = Redash(redash_url, api_key)

    print(redash.test_credentials())
    print(len(list(redash.queries())))
    scheduled_queries = list(redash.scheduled_queries())

    query = scheduled_queries[0]
    print(query['schedule'])
    new_schedule = query['schedule'].copy()
    new_schedule['until'] = '2019-04-24'

    redash.update_query(query['id'], {'schedule': new_schedule})
