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
immediately. `query_payload` is a typed `QueryPayload`, and `values` is a
`QueryValues` mapping from request IDs to numeric values or `None`.

For arbitrary queries, current flow, and portal root-device query routes, use
the typed `FlumeClient.query()`, `portal_query()`, `get_current_flow()`, and
`get_portal_current_flow()` methods documented in the
[API reference](api-reference.md).
