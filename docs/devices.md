# Devices

`FlumeDeviceList` keeps the original PyFlume interface and now returns
`list[Device]` instead of untyped JSON dictionaries.

It accepts both `PersonalAuth` and `PortalAuth`. The PersonalAuth example below
does not mean the device helper requires that flow.

```python
import pyflume

auth = pyflume.PersonalAuth(
    username="your_email",
    password="your_password",
    client_id="your_client_id",
    client_secret="your_client_secret",
)
devices = pyflume.FlumeDeviceList(auth).get_devices()
print(devices[0].id)
```

If you are already authenticated through the customer portal, the equivalent
code is simply:

```python
auth = pyflume.PortalAuth(
    username="your_email",
    password="your_password",
)
devices = pyflume.FlumeDeviceList(auth).get_devices()
```

For new code, `FlumeClient` exposes typed device reads, current flow, purchase
options, meter accuracy, integrations, spans, feedback, and query methods. See
the [API reference](api-reference.md) for the complete method list and return
types.

`FlumeClient.list_devices()` uses the user-scoped device route and can be used
with either auth object. `list_portal_devices()` is a convenience alias for the
same user-scoped read and is useful when the caller is already using
`PortalAuth`. Live testing found that a guessed root `/devices` read is not the
portal equivalent.

Some device-adjacent reads really are portal-only even though they remain under
`/users/{user_id}/...`. For example, meter accuracy and purchase options were
accepted by `PortalAuth` on a supported device while the Personal API token got
404 for the same routes.

Portal usage spans follow the same pattern. `FlumeClient.list_spans()` requires
`since_datetime` and `until_datetime` in `YYYY-MM-DD HH:MM:SS` form, defaults to
gallons and the portal's current span classifications, and returns `list[Span]`.
Each `Span.data` item is a typed `SpanDataPoint` containing `datetime` and
numeric `value` fields. Live validation returned span data with `PortalAuth` and
404 for the same endpoint with `PersonalAuth`.
