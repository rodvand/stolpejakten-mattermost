import requests
import argparse
from dotenv import load_dotenv
from os import path, environ

load_dotenv()

API_URL = environ.get("STOLPEJAKTEN_API")
DB_FILE = environ.get("DB_FILE")
MATTERMOST_URL = environ.get("MATTERMOST_URL")
MATTERMOST_HOOK = environ.get("MATTERMOST_HOOK")
STOLPEJAKTEN_USER = environ.get("STOLPEJAKTEN_USER")
STOLPEJAKTEN_PASSWORD = environ.get("STOLPEJAKTEN_PASSWORD")
STOLPEJAKTEN_GROUP = environ.get("STOLPEJAKTEN_GROUP")


def auth(username, password):
    url = "{}auth".format(API_URL)
    data = {
        'username': username,
        'password': password,
        'version': 2
    }
    r = requests.post(url, json=data)

    if r.status_code == requests.codes.ok:
        return r.json()['token']
    else:
        return None


def get_group(token, group_id):
    url = "{}toplists/affiliations?kommune=0&id={}".format(API_URL, group_id)
    headers = {"Authorization": "Bearer {}".format(token)}
    r = requests.get(url, headers=headers)

    if r.status_code == requests.codes.ok:
        return r.json()
    else:
        return None


def create_table_output(data):
    # Create table output
    top = sorted(data.items(), key=lambda x: x[1], reverse=True)
    table_output = "|User|Stolper|\n"
    table_output += "|:------------ | -----:|\n"
    for user, stolper in top:
        table_output += "|{}|{}|\n".format(user, stolper)

    return table_output


if __name__ == '__main__':
    # Ready the mm integration
    from matterhook import Webhook
    mwh = Webhook(MATTERMOST_URL, MATTERMOST_HOOK)

    parser = argparse.ArgumentParser(description='Print stolpejakten data to Mattermost')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug the application')
    parser.add_argument('-t', '--toplist', action='store_true', help='Send top list only')
    parser.add_argument('-m', '--mattermost', action='store_false', help='Send data to mattermost')

    args = parser.parse_args()
    if args.debug:
        print("Debug is ON")
    if args.mattermost:
        print("Sending data to mattermost")
    else:
        print("Not sending data to mattermost")
    if args.toplist:
        print("Sending top list even if no change")

    # Check if we have existing data
    group_view = None
    if path.exists(DB_FILE):
        if args.debug:
            print("Found existing {} file.".format(DB_FILE))
        with open(DB_FILE, 'r') as f:
            data = f.readlines()
            group_view = {}
            for line in data:
                user, stolper, rank = map(str.strip, line.split(','))
                group_view[user] = int(float(stolper))

    token = auth(STOLPEJAKTEN_USER, STOLPEJAKTEN_PASSWORD)
    group_info = get_group(token, STOLPEJAKTEN_GROUP)
    group_data = {}
    output = ""
    change = False
    for gi in group_info['results']:
        user, stolper, rank = gi['user_name'], gi['score'], gi['rank']
        if args.debug:
            print(user, stolper, rank)
        group_data[user] = int(float(stolper))
        if group_view:
            if group_view[user] < stolper:
                diff = int(stolper) - int(group_view[user])
                text = "{} has {} more stolper than last check. " \
                       "New overall rank is {}. Total number of stolper: {}".format(user, diff, rank, stolper)
                if args.debug:
                    print(text)
                change = True
                if args.mattermost:
                    mwh.send(text)

        output += "{},{},{}\n".format(user, stolper, rank)

    if change or args.debug or args.toplist:
        table_output = create_table_output(group_data)
        if args.mattermost:
            mwh.send(table_output)
        if args.debug:
            print(table_output)

    fi = open(DB_FILE, 'w')
    fi.write(output)
    fi.close()
    if args.debug:
        print(group_info)

