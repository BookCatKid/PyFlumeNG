# FlumeClient

`FlumeClient` is the main interface for new PyFlumeNG code. Named methods cover
the documented Personal API and the endpoint families used by Flume's customer
portal.

It accepts either `PersonalAuth` or `PortalAuth`. The auth object does not
select a completely different client API. Most user-scoped reads work with
either token; methods that perform known portal-only writes explicitly require
the `portal_writes` capability.

```python
import pyflumeng

auth = pyflumeng.PortalAuth(
    username="your_email",
    password="your_password",
)
client = pyflumeng.FlumeClient(auth)

devices = client.list_devices()
rules = client.list_usage_alert_rules(devices[0].id)
accuracy = client.get_meter_accuracy(devices[0].id)
```

The example uses `PortalAuth` because it gives access to both ordinary reads
and the portal surface. You could replace it with `PersonalAuth` for ordinary
reads such as `list_devices()`, `list_notifications()`, `get_current_flow()`,
and queries.

## User-scoped reads with either token

Several early portal helpers were named as if the customer portal used a
parallel set of root read routes. Live testing shows that many portal reads use
the same user-scoped route as the Personal API. For example:

```python
client.list_devices()  # /users/{user_id}/devices
client.list_portal_devices()  # delegates to list_devices()

client.list_notifications()  # /users/{user_id}/notifications
client.list_portal_notifications()  # delegates to list_notifications()
```

The unprefixed read methods are not “PersonalAuth-only.” `PortalAuth` can be
used with them as well. Portal-only functionality is determined by what the
token and endpoint accept, not by whether the URL starts at a root resource.

Some additional reads are portal-only while still living below
`/users/{user_id}/...`, including endpoints such as do-not-alert schedules,
integrations, meter accuracy, purchase options, and location span types. The
library keeps these as named typed methods and lets Flume report when a device
does not support one of them.

### Usage spans

The portal span endpoint requires a time window, units, and a comma-separated
classification filter. `list_spans()` now builds that request explicitly
instead of accepting an undocumented bag of query parameters:

```python
spans = client.list_spans(
    device_id,
    since_datetime="2026-09-01 00:00:00",
    until_datetime="2026-09-02 00:00:00",
)

print(spans[0].type)
print(spans[0].total)
print(spans[0].data[0].datetime, spans[0].data[0].value)
```

The date strings use the exact `YYYY-MM-DD HH:MM:SS` format used by Flume's
current customer portal. `units` defaults to `"gallons"`. If `span_types` is
omitted, PyFlumeNG sends the portal's current classification set (`OUTDOOR`,
`INDOOR`, `SHOWER`, `TOILET`, `SOFTENER`, `CLOTHES_WASHER`, `DISH_WASHER`,
`POOL`, and `REVERSE_OSMOSIS`). Pass your own sequence of strings to filter it.

Live portal responses contained `id`, `type`, `start`, `end`, `data`,
`is_editable`, `max_flowrate`, `mode_gpm`, `origin`, `total`, `value`, and
`version`. Each `data` entry is a typed `SpanDataPoint` with `datetime` and a
numeric `value`. PersonalAuth returned 404 for this endpoint during live
validation, while PortalAuth returned the span data on a supported device.

For writes where the portal's broader token is known to be required,
`FlumeClient` checks the auth capability before making the request. Examples
include portal usage-alert rule writes and portal notification/location/account
mutations. See [Authentication](auth.md) for the auth model.

The client covers users and account updates; devices, current flow and queries;
locations and profiles; notifications; usage alerts, rules and do-not-alert
schedules; leaks; budgets and subscriptions; emergency contacts and shared
access; integrations and shutoff valves; spans and classifications; feedback;
meter accuracy and support conversations; purchase options; insurers;
professional services; generated API clients; contacts; and Stripe/subscription
operations.

List methods use `list_all()` and follow pagination until all records are
returned. Use `iter_pages()` when page boundaries or response metadata matter.
Use `response()` for a typed Flume envelope, `raw()` for an unwrapped future
route that does not yet have a named helper, and `raw_response()` when the
underlying `requests.Response` is required.

## Typed results

Named methods model known response fields rather than returning anonymous JSON
for every resource. For example:

```python
devices = client.list_devices()  # list[Device]
alerts = client.list_usage_alerts()  # list[UsageAlert]
rules = client.list_usage_alert_rules(device_id)  # list[UsageAlertRule]
accuracy = client.get_meter_accuracy(device_id)  # list[AccuracyResult]
```

On a live supported meter, `get_meter_accuracy()` returned a one-item list
whose object contained exactly `type`, `title`, and `description`. The model
also has optional comparison fields because related accuracy flows may return
them, but callers should not assume those fields are present on the GET.

Known fields are discoverable in an IDE and checked by static type checkers.
Models remain open to new fields added by Flume: unknown response keys remain
available and are preserved by `to_dict()`.

The [generated API reference](api-reference.md) is the canonical inventory of
public signatures and typed model fields.
