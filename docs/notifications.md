# Notifications

`FlumeNotificationList` preserves the original paginated helper API while
returning typed `Notification` models.

**Notifications do not require PersonalAuth.** `FlumeNotificationList` accepts
both `PersonalAuth` and `PortalAuth`, and `FlumeClient.list_notifications()` can
likewise be used with either auth object. Choose the auth flow based on the rest
of your integration and whether you need portal-only writes.

## With PersonalAuth

```python
import pyflume

auth = pyflume.PersonalAuth(
    username="your_email",
    password="your_password",
    client_id="your_client_id",
    client_secret="your_client_secret",
)
notifications = pyflume.FlumeNotificationList(auth)
first_page = notifications.notification_list
if notifications.has_next:
    second_page = notifications.get_next_notifications()
```

## With PortalAuth

The same helper works with the customer-portal token and does not require a
Personal API client ID or secret:

```python
import pyflume

auth = pyflume.PortalAuth(
    username="your_email",
    password="your_password",
)
notifications = pyflume.FlumeNotificationList(auth)
first_page = notifications.notification_list
```

The legacy helper requests 50 notifications at a time. `notification_list`
contains the first page, `has_next` tells you whether another page exists, and
`get_next_notifications()` fetches that next page.

## FlumeClient

For new code, `FlumeClient.list_notifications()` follows pagination for you and
returns one `list[Notification]` containing all pages:

```python
client = pyflume.FlumeClient(auth)  # auth may be PersonalAuth or PortalAuth
notifications = client.list_notifications(read=False)
```

There are also two route families:

- `list_notifications()` and `get_notification()` use the user-scoped routes;
- `list_portal_notifications()` and `get_portal_notification()` use the root
  routes used by Flume's customer portal.

The unprefixed read methods are not PersonalAuth-only. Portal auth can use the
ordinary user-scoped notification reads as well.

Notification mutation helpers are separate. Portal-root update/delete methods
require `PortalAuth` because `FlumeClient` checks for the `portal_writes`
capability. `set_notification_read(..., portal=True)` uses that portal write
path by default; pass `portal=False` to use the user-scoped update route.

All exact signatures and return types are generated in the
[API reference](api-reference.md).
