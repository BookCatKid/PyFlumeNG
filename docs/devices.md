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

For new code, `FlumeClient` exposes typed user-scoped and portal root-device
routes, current flow, purchase options, meter accuracy, integrations, spans,
feedback, and query methods. See the [API reference](api-reference.md) for the
complete method list and return types.

`FlumeClient.list_devices()` uses the user-scoped device route and can be used
with either auth object. `list_portal_devices()` represents the root route used
by the customer portal.
