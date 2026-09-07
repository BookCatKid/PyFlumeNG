# Data retrieval

`FlumeData` is the original polling/query helper. It accepts either auth mode
and maintains typed `values` for its standard query windows.

The `PersonalAuth` object in the first example is only one valid choice. If the
rest of your application uses `PortalAuth`, pass that same object to
`FlumeData`; you do not need separate Personal API credentials just for data
queries.

```python
from datetime import timedelta
import pyflume

auth = pyflume.PersonalAuth(
    username="your_email",
    password="your_password",
    client_id="your_client_id",
    client_secret="your_client_secret",
)

data = pyflume.FlumeData(
    flume_auth=auth,
    device_id="your_device_id",
    device_tz="America/Los_Angeles",
    scan_interval=timedelta(minutes=60),
)
print(data.values)
```

Equivalent setup with portal auth:

```python
auth = pyflume.PortalAuth(
    username="your_email",
    password="your_password",
)

data = pyflume.FlumeData(
    flume_auth=auth,
    device_id="your_device_id",
    device_tz="America/Los_Angeles",
    scan_interval=timedelta(minutes=60),
)
```

`update()` applies the legacy rate limiter. `update_force()` performs the query
immediately. The default `scan_interval` is 60 minutes. When you pass a custom
`query_payload`, PyFlumeNG sends that payload unchanged on every update and the
scan interval is not used. `query_payload` is a typed `QueryPayload`, and
`values` is a `QueryValues` mapping from request IDs to numeric values or
`None`.

To start from PyFlumeNG's standard query set and customize it, generate the
payload without constructing a `FlumeData` instance:

```python
payload = pyflume.FlumeData.generate_api_query_payload(
    timedelta(minutes=60),
    "America/Los_Angeles",
)
payload["queries"].append(
    {
        "request_id": "custom_window",
        "bucket": "HR",
        "since_datetime": "2026-09-01 00:00:00",
        "until_datetime": "2026-09-02 00:00:00",
        "operation": "SUM",
        "units": "GALLONS",
    }
)

data = pyflume.FlumeData(
    flume_auth=auth,
    device_id="your_device_id",
    device_tz="America/Los_Angeles",
    query_payload=payload,
)
```

For arbitrary queries and current flow, use the typed `FlumeClient.query()` and
`get_current_flow()` methods documented in the [API reference](api-reference.md).
The `portal_query()` and `get_portal_current_flow()` convenience methods now
delegate to those same working user-scoped routes; live testing found that the
guessed root-device query routes are not valid portal reads.
`portal_query()` also divides payloads containing more than ten queries into
the same ten-query batches used by the web application and combines their
results.
