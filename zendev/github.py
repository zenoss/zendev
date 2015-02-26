import requests
import json
import os
from getpass import getpass

def get_oauth_token():
    """
    Get or create an OAuth token for making pull requests.
    """
    cache = os.path.join(os.path.expanduser("~"), ".zendev.gitauth")
    try:
        result = open(cache, 'r').read().strip()
    except IOError:
        username = raw_input("GitHub username: ")
        password = getpass("GitHub password: ")
        response = requests.post(
            "https://api.github.com/authorizations",
            data=json.dumps({
                "scopes": ["repo"],
                "note": "Europa Development Environment"
            }),
            auth=(username, password))
        result = response.json().get('token')
        with open(cache, 'w') as f:
            f.write(result)
    return result


def perform(method, url, data=None, params=None):
    token = get_oauth_token()
    response = requests.request(
        method, "https://api.github.com" + url, data=data, params=params,
        headers={"Authorization": "token %s" % token}
    )
    return response.headers, response.json()

