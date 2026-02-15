import os
import pytest
from pathlib import Path
from unittest import mock

PATH_FIXTURES = Path('fixtures')

SERIALIZATION_DATA = {
    "Unicode": "👨👩👧👧",
    "Reservations": [
        {
            "Groups": [],
            "OwnerId": "197828489041",
            "ReservationId": "r-0b6752f9a69f3ba08"
        }
    ],
    "ResponseMetadata": {
        "RequestId": "5cd271e5-3631-4e4c-a07d-78d169514e39",
        "HTTPStatusCode": 200,
        "HTTPHeaders": {
            "x-amzn-requestid": "5cd271e5-3631-4e4c-a07d-78d169514e39",
            "cache-control": "no-cache, no-store",
            "strict-transport-security": "max-age=31536000; includeSubDomains",
            "content-type": "text/xml;charset=UTF-8",
            "content-length": "7803",
            "vary": "accept-encoding",
            "date": "Thu, 26 Aug 2021 00:02:15 GMT",
            "server": "AmazonEC2"
        },
        "RetryAttempts": 0
    }
}

parametrize = pytest.mark.parametrize


def patch_environment(clear=False, **kwargs):
    return mock.patch.dict(os.environ, kwargs, clear=clear)
