# Leak alerts

`FlumeLeakList` is the legacy leak helper. `get_leaks()` returns `list[Leak]`.
The helper accepts either `PersonalAuth` or `PortalAuth`; PersonalAuth is shown
first only because it is the original PyFlume authentication flow.

```python
import pyflume

auth = pyflume.PersonalAuth(
    username="your_email",
    password="your_password",
    client_id="your_client_id",
    client_secret="your_client_secret",
)
leaks = pyflume.FlumeLeakList(auth, device_id="your_device_id").get_leaks()
```

With portal auth:

```python
auth = pyflume.PortalAuth(
    username="your_email",
    password="your_password",
)
leaks = pyflume.FlumeLeakList(auth, device_id="your_device_id").get_leaks()
```

The returned `Leak` models expose known fields such as `id`, `device_id`,
`active`, and `created_datetime`, while preserving additional API fields.
`FlumeClient` also provides typed user-scoped and portal-route leak methods;
see the [API reference](api-reference.md).
