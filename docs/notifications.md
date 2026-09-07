# Notifications

`FlumeNotificationList` preserves the original paginated helper API while
returning typed `Notification` models.

**Notifications do not require PersonalAuth.** `FlumeNotificationList` accepts
both `PersonalAuth` and `PortalAuth`, and `FlumeClient.list_notifications()` can
likewise be used with either auth object. Choose the auth flow based on the rest
of your integration and whether you need portal-only writes.

## With PersonalAuth

```python
import pyflumeng

auth = pyflumeng.PersonalAuth(
    username="your_email",
    password="your_password",
    client_id="your_client_id",
    client_secret="your_client_secret",
)
notifications = pyflumeng.FlumeNotificationList(auth)
first_page = notifications.notification_list
if notifications.has_next:
    second_page = notifications.get_next_notifications()
```

## With PortalAuth

The same helper works with the customer-portal token and does not require a
Personal API client ID or secret:

```python
import pyflumeng

auth = pyflumeng.PortalAuth(
    username="your_email",
    password="your_password",
)
notifications = pyflumeng.FlumeNotificationList(auth)
first_page = notifications.notification_list
```

The legacy helper requests 50 notifications at a time. `notification_list`
contains the first page, `has_next` tells you whether another page exists, and
`get_next_notifications()` fetches that next page.

## FlumeClient

For new code, `FlumeClient.list_notifications()` follows pagination for you and
returns one `list[Notification]` containing all pages:

```python
client = pyflumeng.FlumeClient(auth)  # auth may be PersonalAuth or PortalAuth
notifications = client.list_notifications(read=False)
```

`list_notifications()` uses the user-scoped collection route and works with
either auth mode. The live API does **not** implement a matching
`GET /notifications/{id}` route even though PATCH and DELETE are supported on
that path, so `get_notification()` follows the paginated collection and filters
the result by ID. `list_portal_notifications()` and
`get_portal_notification()` delegate to those same working reads.

Notification mutation helpers are separate. Methods marked as portal writes
require `PortalAuth` because `FlumeClient` checks for the `portal_writes`
capability. These write routes have not been live-mutated as part of the
read-only validation, so the generated reference documents their current
implementation without claiming they were write-tested.

All exact signatures and return types are generated in the
[API reference](api-reference.md).
