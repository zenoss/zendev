import requests
import json
import os
from getpass import getpass
from uuid import getnode as get_mac


class GithubAuthException(Exception):
    pass


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
        mac = get_mac()
        fingerprint = ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))
        response = requests.post(
            "https://api.github.com/authorizations",
            data=json.dumps({
                "scopes": ["repo"],
                "note": "Europa Development Environment",
                "fingerprint": fingerprint
            }),
            auth=(username, password))
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            print "HTTPError: %s" % ex
            message = "%s authenticating against GitHub. Response text: %s" % (
                ex, response.text
            )
            print message
            raise GithubAuthException(message)
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
