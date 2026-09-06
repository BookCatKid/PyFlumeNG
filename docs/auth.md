# Authentication

PyFlumeNG supports the documented Personal API flow and the customer-portal
OAuth flow. Both auth objects can be passed to `FlumeClient` and the legacy
helper classes.

The auth classes do **not** divide the library into “PersonalAuth endpoints” and
“PortalAuth endpoints.” They are two ways of obtaining a bearer token with
different credentials and scopes. A large part of the API, especially reads,
works with either token.

## Which one should I use?

| | `PersonalAuth` / `FlumeAuth` | `PortalAuth` / `FlumePortalAuth` |
| --- | --- | --- |
| Login inputs | Email, password, API client ID, API client secret | Email and password |
| OAuth flow | Documented Personal API password grant | Customer-portal authorization-code flow |
| Normal user-scoped reads | Yes | Yes |
| Legacy helpers | Yes | Yes |
| Portal-root reads | Not the intended token | Yes |
| Portal-only writes | No | Yes |

For example, these are all normal read operations and may be used with either
auth object:

- device listing and device queries;
- notifications;
- leak alerts;
- usage alerts and usage-alert rule reads;
- the legacy `FlumeData`, `FlumeDeviceList`, `FlumeLeakList`,
  `FlumeNotificationList`, and `FlumeUsageAlertList` helpers.

Use `PortalAuth` when you need the customer-portal route surface or a write that
requires the portal token's broader scope. The most important known example is
creating, editing, enabling/disabling, or deleting usage-alert rules through
the portal routes.

## Personal API

`FlumeAuth` and `PersonalAuth` are aliases for the same class. Use the client ID
and client secret generated from Flume's API Access settings:

```python
import pyflume

auth = pyflume.PersonalAuth(
    username="your_email",
    password="your_password",
    client_id="your_client_id",
    client_secret="your_client_secret",
)
auth.retrieve_token()
```

The token produced by this flow has the normal Personal API scope. It is a good
choice for integrations that only need the documented API surface. It is not a
requirement for reads: if your application already uses `PortalAuth`, you do
not need a second Personal API token just to read notifications, devices, or
other ordinary resources.

The auth object refreshes expiring tokens automatically when used through
`FlumeClient`. Its `RateLimitState` starts with the Personal API baseline of 120
requests and is updated from Flume's rate-limit response headers when present.

## Customer portal

`FlumePortalAuth` and `PortalAuth` are aliases for the portal authorization-code
flow used by Flume's customer web application:

```python
import pyflume

auth = pyflume.PortalAuth(
    username="your_email",
    password="your_password",
)
client = pyflume.FlumeClient(auth)
```

Portal auth does not take your Personal API client ID or secret. PyFlumeNG uses
the customer-portal client and follows the login/authorization-code exchange
used by Flume's web application.

The resulting auth object has `personal_api`, `portal_api`, and
`portal_writes` capabilities. That is why it can be passed to the same
user-scoped read helpers as `PersonalAuth` while also being able to call the
portal routes. Its `RateLimitState` starts with the portal baseline of 72,000
requests and, like PersonalAuth, is replaced by values reported in response
headers.

Portal auth is required for operations that Flume rejects when performed with
a normal Personal API token. Usage-alert rule writes are the clearest example:

```python
auth = pyflume.PortalAuth(
    username="your_email",
    password="your_password",
)
client = pyflume.FlumeClient(auth)

client.set_portal_usage_alert_rule_active(
    device_id="your_device_id",
    rule_id="your_rule_id",
    active=False,
)
```

`FlumeClient` performs an explicit `portal_writes` capability check for the
portal write helpers it knows require that scope, so using `PersonalAuth` for
one of those methods fails before the HTTP request.

## The same read with either auth mode

Notifications are a useful example because they do not require PersonalAuth.
Both of these are valid library configurations:

```python
# Personal API token
personal = pyflume.PersonalAuth(
    username="your_email",
    password="your_password",
    client_id="your_client_id",
    client_secret="your_client_secret",
)
personal_client = pyflume.FlumeClient(personal)
notifications = personal_client.list_notifications()
```

```python
# Customer-portal token
portal = pyflume.PortalAuth(
    username="your_email",
    password="your_password",
)
portal_client = pyflume.FlumeClient(portal)
notifications = portal_client.list_notifications()
```

The same applies to the legacy notification helper:

```python
notifications = pyflume.FlumeNotificationList(portal)
```

There is no need to create a Personal API application simply because you want
to read notifications.

## Aliases

The public names exist so code can either retain the original PyFlume naming or
make the auth mode explicit:

```python
pyflume.FlumeAuth is pyflume.PersonalAuth
pyflume.FlumePortalAuth is pyflume.PortalAuth
```

Both auth classes expose token state, the current user ID, authorization
headers, refresh helpers, capabilities, and rate-limit state. See the
[generated API reference](api-reference.md) for exact signatures.
