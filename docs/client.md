# FlumeClient

`FlumeClient` is the main interface for new PyFlumeNG code. Named methods cover
the documented Personal API and the endpoint families used by Flume's customer
portal.

It accepts either `PersonalAuth` or `PortalAuth`. The auth object does not
select a completely different client API. Most user-scoped reads work with
either token; methods that perform known portal-only writes explicitly require
the `portal_writes` capability.

```python
import pyflume

auth = pyflume.PortalAuth(
    username="your_email",
    password="your_password",
)
client = pyflume.FlumeClient(auth)

devices = client.list_devices()
rules = client.list_usage_alert_rules(devices[0].id)
accuracy = client.get_meter_accuracy(devices[0].id)
```

The example uses `PortalAuth` because it gives access to both ordinary reads
and the portal surface. You could replace it with `PersonalAuth` for ordinary
reads such as `list_devices()`, `list_notifications()`, `get_current_flow()`,
and queries.

## User-scoped and portal route variants

Some resources have two named methods because Flume's documented/user-scoped
API and its customer portal use different route shapes. For example:

```python
client.list_devices()  # /users/{user_id}/devices
client.list_portal_devices()  # /devices

client.list_notifications()  # /users/{user_id}/notifications
client.list_portal_notifications()  # /notifications
```

The unprefixed read methods are not “PersonalAuth-only.” `PortalAuth` can be
used with them as well. The `portal` name describes the route used by Flume's
customer web application, not a blanket restriction on every other method.

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

Known fields are discoverable in an IDE and checked by static type checkers.
Models remain open to new fields added by Flume: unknown response keys remain
available and are preserved by `to_dict()`.

The [generated API reference](api-reference.md) is the canonical inventory of
public signatures and typed model fields.
