from fmtr.tools import environment_tools, Constants
from fmtr.tools.http_tools import client


def notify(title, body, url=None):
    """

    Send simple debug notification

    """
    url = url or environment_tools.get(Constants.WEBHOOK_URL_NOTIFY_KEY)
    client.post(url, json=dict(title=title, body=body))


if __name__ == '__main__':
    notify('Title', 'Body')
    notify
