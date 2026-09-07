# PyFlumeNG

PyFlumeNG is a fork and superset of PyFlume. It uses the dedicated `pyflumeng`
import package and retains the legacy helpers while adding the customer-portal OAuth flow,
portal write operations, typed resource models, pagination, response/error
handling, rate-limit state, and the endpoint surface used by Flume's customer
portal.

Install PyFlumeNG from PyPI:

```bash
pip install PyFlumeNG
```

## Authentication

PyFlumeNG supports two ways to obtain a Flume bearer token. They are not tied
to separate sets of read helpers: ordinary reads such as devices,
notifications, leaks, usage alerts, and queries can be used with either auth
object. The main difference is how the token is obtained and what scopes Flume
grants it.

| Auth class | Credentials | Best fit | Portal-only writes |
| --- | --- | --- | --- |
| `PersonalAuth` / `FlumeAuth` | Email, password, API client ID, API client secret | Flume's documented Personal API flow | No |
| `PortalAuth` / `FlumePortalAuth` | Email and password | Customer-portal flow and code that needs the portal's broader token | Yes |

`PersonalAuth` and `FlumeAuth` are the same class. Use them when you want the
documented Personal API password-grant flow with credentials generated from
Flume's API Access settings:

```python
import pyflumeng

auth = pyflumeng.PersonalAuth(
    username="your_email",
    password="your_password",
    client_id="your_client_id",
    client_secret="your_client_secret",
)
client = pyflumeng.FlumeClient(auth)
```

`PortalAuth` and `FlumePortalAuth` are the same class. This flow uses the same
customer-portal OAuth path as Flume's web app and needs only the account
credentials:

```python
import pyflumeng

auth = pyflumeng.PortalAuth(
    username="your_email",
    password="your_password",
)
client = pyflumeng.FlumeClient(auth)
```

You can use that `PortalAuth` object for normal reads too. For example,
`client.list_notifications()`, `FlumeNotificationList(auth)`,
`client.list_devices()`, and `FlumeData(...)` all accept it. Portal auth becomes
required when an operation needs a scope that Flume does not grant to a normal
Personal API token, including the portal usage-alert rule write routes.

See [Authentication](docs/auth.md) for the full distinction, including which
auth mode to choose and how the legacy helpers behave.

## Typed API

Named resource methods return typed models. For example:

```python
user = client.get_user()  # Optional[User]
devices = client.list_devices()  # list[Device]
rules = client.list_usage_alert_rules("device")  # list[UsageAlertRule]
accuracy = client.get_meter_accuracy("device")  # list[AccuracyResult]
```

Models expose known API fields to type checkers and IDEs while remaining
forward-compatible with Flume additions. Unknown response fields remain
available as attributes or mapping keys and are preserved by `to_dict()`.

`pyflumeng` ships a `py.typed` marker so installed type checkers can consume the
package annotations. The complete method signatures and model fields are in the
[generated API reference](docs/api-reference.md).

## Endpoint coverage

`FlumeClient` includes the documented Personal API plus portal-discovered
routes for users, devices, current flow and queries, locations and location
profiles, notifications, usage alerts and rules, do-not-alert schedules,
budgets, subscriptions, emergency contacts, shared location access,
integrations and shutoff valves, spans and span types, feedback, meter
accuracy, support conversations, purchase options, insurers, professional
services, API clients, contacts, and subscription/Stripe portal operations.

List helpers follow Flume pagination and return all pages. `response()` exposes
the complete typed response envelope when pagination or metadata matters, and
`raw()` remains an escape hatch for routes added by Flume after this release.
See the [FlumeClient guide](docs/client.md) for the main interface.

## Legacy helpers

The original helper classes remain available and typed:

- [Data retrieval](docs/data.md)
- [Devices](docs/devices.md)
- [Leak alerts](docs/leak.md)
- [Notifications](docs/notifications.md)
- [Usage alerts](docs/usage.md)

## Examples

The [examples](examples/README.md) include an interactive portal utility that
lists usage-alert rules and explicitly enables or disables the selected rule.

## Development

The API reference is generated from source signatures and model annotations:

```bash
python scripts/generate_api_reference.py
python scripts/generate_api_reference.py --check
```

`tox` runs the tests, mypy, generated-reference check, and bytecode compilation.
