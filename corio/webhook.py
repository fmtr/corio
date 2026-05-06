from corio import env, Constants
from corio.https import client


def notify(title, body, url=None):
    """

    Send simple debug notification

    """
    url = url or env.get(Constants.WEBHOOK_URL_NOTIFY_KEY)
    client.post(url, json=dict(title=title, body=body))


if __name__ == '__main__':
    notify('Title', 'Body')
    notify
