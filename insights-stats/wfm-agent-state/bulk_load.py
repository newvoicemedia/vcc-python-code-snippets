import sys
import getopt
from collections import namedtuple
from datetime import datetime, timedelta
from sqlite3 import Cursor, connect
from requests import get
from pyrecord import Record


def ensure_database():
    connection = connect('wfm_agent_state.db')
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wfm_agent_state (
        agent_id int,
        start text,
        duration int,
        state text,
        description text,
        UNIQUE(agent_id, start)
    )
    ''')
    return connection, cursor


def save_item(cursor: Cursor, item):
    cursor.execute('''
    INSERT INTO wfm_agent_state (
        agent_id,
        start,
        duration,
        state,
        description
    )
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(agent_id, start) DO UPDATE SET duration=excluded.duration
    ''', (item['agentId'], item['start'], item['duration'], item['state'],
          item['description']))


Options = Record.create_type(
    'Options', 'base_url', 'bearer_token', 'page_size')

QueryRange = namedtuple('QueryRange', 'start end')


def read_options() -> Options:
    options = Options('https://nam.api.newvoicemedia.com', None, 5000)

    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'u:t:p:')
    except getopt.GetoptError:
        print('bulk_load.py [-u <base-url>] [-t <bearer-token>] [-p <page-size>]')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-u':
            options.base_url = arg
        if opt == '-t':
            options.bearer_token = arg
        if opt == '-p':
            options.page_size = arg

    if options.bearer_token is None:
        options.bearer_token = input('Please enter your bearer token: ')

    return options


def read_data(connection, cursor, options):
    utcnow_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    query_range = QueryRange(
        start=utcnow_hour - timedelta(hours=1),
        end=utcnow_hour)
    current_page = 1
    headers = {'Accept': 'application/vnd.newvoicemedia.v3+json',
               'Authorization': f'Bearer {options.bearer_token}',
               'x-external-id': '<Your integration name>'}
    items = []

    print(f'Fetching records updated between {query_range.start} and \
{query_range.end} from {options.base_url}/stats/wfm/agent-states/')

    while True:
        query = {'limit': options.page_size,
                 'page': f'{current_page}',
                 'start': f"{query_range.start.isoformat()}Z",
                 'end': f"{query_range.end.isoformat()}Z",
                 'include': 'Processed'}
        response = get(url=f'{options.base_url}/stats/wfm/agent-states',
                       params=query,
                       headers=headers)

        if (response.status_code != 200):
            print(f'API responded with status code {response.status_code}')
            sys.exit(2)

        json = response.json()
        meta = json['meta']

        for item in json['items']:
            items.append(item)

        if meta['page'] >= meta['pageCount']:
            break

        current_page = current_page + 1

    for item in sorted(items, key=lambda x: x['agentId']):
        save_item(cursor, item)

    connection.commit()

    print(f'{len(items)} records saved')


def main():
    connection, cursor = ensure_database()
    options = read_options()
    read_data(connection, cursor, options)


if __name__ == '__main__':
    main()
