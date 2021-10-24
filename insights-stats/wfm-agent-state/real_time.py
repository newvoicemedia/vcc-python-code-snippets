import sys
import getopt
from collections import namedtuple
from itertools import groupby
from datetime import datetime, timedelta
from operator import itemgetter
from pyrecord import Record
from requests import get
import schedule
from sqlite3 import Cursor, connect
import time


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
    ''', itemgetter('agentId', 'start', 'duration', 'state', 'description')(item))


def save_items(cursor: Cursor, agent_id, items):
    start = items[0]['start']
    cursor.execute('''
        DELETE FROM wfm_agent_state
        WHERE agent_id = ?
        AND start >= ?"
    ''', agent_id, start)

    for item in items:
        save_item(cursor, item)


def save_offset(offset: str):
    with open('.offset', 'w') as file:
        file.write(offset)


def read_offset() -> str:
    with open('.offset', 'r') as file:
        return file.readline()


Options = Record.create_type(
    'Options', 'base_url', 'bearer_token', 'page_size')


def read_options() -> Options:
    # options = Options('https://nam.api.newvoicemedia.com', None, 100)
    options = Options('http://localhost:8000', None, 100)

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
    current_page = 1
    offset = read_offset()
    now = f'{datetime.utcnow().isoformat()}Z'
    headers = {'Accept': 'application/vnd.newvoicemedia.v3+json',
               'Authorization': f'Bearer {options.bearer_token}',
               'x-external-id': '<Your integration name>'}
    items = []

    print(f'Fetching records updated since {offset} from {options.base_url}/stats/wfm/agent-states/')

    while True:
        query = {'limit': options.page_size,
                 'page': f'{current_page}',
                 'start': offset,
                 'end': now,
                 'include': 'Processed'}
        # response = get(url=f'{options.base_url}/stats/wfm/agent-states',
        response = get(url=f'{options.base_url}/wfm/agent-states',
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

    agent_groups = groupby(items, itemgetter('agentId'))

    for agent_id, items in agent_groups:
        save_items(cursor, agent_id, items)

    save_offset(json['upTo'])

    connection.commit()

    print(f'{len(items)} records saved')


def main():
    connection, cursor = ensure_database()
    options = read_options()

    save_offset(f'{(datetime.utcnow() - timedelta(seconds=15)).isoformat()}Z')

    schedule.every(5).seconds.do(read_data, connection, cursor, options)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
