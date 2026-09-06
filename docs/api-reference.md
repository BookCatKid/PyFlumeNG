# API reference

This file is generated from the public signatures and model annotations in the source tree.
Run `python scripts/generate_api_reference.py` after changing public APIs, or use `--check` to verify it is current.

## Public classes

### `FlumeAuth`

Interact with API Authentication.

- `FlumeAuth(username: str, password: str, client_id: str, client_secret: str, flume_token: Optional[Mapping[str, Any]] = None, http_session: Optional[Session] = None, timeout: float = DEFAULT_TIMEOUT) -> None`
  Initialize the data object.
- `token: Optional[FlumeToken]` (property)
      Return authorization token for session.
- `refresh_token() -> None`
  Refresh authorization token for session.
- `refresh() -> None`
  Refresh through the common PyFlumeNG auth interface.
- `ensure_valid() -> None`
  Refresh when the token expires within twelve hours.
- `retrieve_token() -> None`
  Return authorization token for session.

### `FlumePortalAuth`

Authenticate using the customer portal OAuth authorization-code flow.

- `FlumePortalAuth(username: str, password: str, flume_token: Optional[Mapping[str, Any]] = None, http_session: Optional[Session] = None, timeout: float = DEFAULT_TIMEOUT) -> None`
  Initialize portal authentication.
- `token: Optional[FlumeToken]` (property)
  Return the current portal token response.
- `retrieve_token() -> None`
  Authenticate through the portal and exchange the authorization code.
- `refresh_token() -> None`
  Refresh the portal token using its form-encoded refresh flow.
- `refresh() -> None`
  Refresh through the common PyFlumeNG auth interface.
- `ensure_valid() -> None`
  Refresh when the token expires within twelve hours.

### `FlumeClient`

Call Flume endpoints with a PersonalAuth or PortalAuth object.

- `FlumeClient(auth: Union[FlumeAuth, FlumePortalAuth], http_session: Optional[Session] = None, base_url: str = API_BASE_URL, timeout: float = 30) -> None`
- `request(method: str, path: str, params: Optional[RequestParams] = None, json: Optional[JSONValue] = None, data: Any = None, **kwargs: Any) -> JSONDict`
  Return the complete Flume response envelope.
- `data(method: str, path: str, model: Type[ModelT], **kwargs: Any) -> Union[ModelT, List[ModelT]]`
- `data(method: str, path: str, model: None = None, **kwargs: Any) -> JSONValue`
- `response(method: str, path: str, model: Type[ModelT], **kwargs: Any) -> FlumeResponse[ModelT]`
- `response(method: str, path: str, model: None = None, **kwargs: Any) -> FlumeResponse[JSONValue]`
- `data_one(method: str, path: str, model: Type[ModelT], **kwargs: Any) -> Optional[ModelT]`
  Return the first parsed resource, matching portal ``model()`` calls.
- `list_all(path: str, params: Optional[RequestParams], model: Type[ModelT]) -> List[ModelT]`
- `list_all(path: str, params: Optional[RequestParams] = None) -> List[FlumeModel]`
- `iter_pages(path: str, params: Optional[RequestParams], model: Type[ModelT]) -> Iterator[FlumeResponse[ModelT]]`
- `iter_pages(path: str, params: Optional[RequestParams] = None) -> Iterator[FlumeResponse[FlumeModel]]`
- `get_user() -> Optional[User]`
- `list_devices(**params: JSONValue) -> List[Device]`
- `list_portal_devices(**params: JSONValue) -> List[Device]`
  List devices using the user-scoped route with portal auth data.
- `get_device(device_id: ResourceId, **params: JSONValue) -> Optional[Device]`
- `get_portal_device(device_id: ResourceId, **params: JSONValue) -> Optional[Device]`
  Fetch one device using the user-scoped route with portal auth data.
- `query(device_id: ResourceId, payload: JSONDict) -> List[QueryResult]`
- `portal_query(device_id: ResourceId, payload: JSONDict) -> List[QueryResult]`
  Run the read-only device query using the user-scoped route.
- `get_current_flow(device_id: ResourceId) -> Optional[CurrentFlow]`
- `get_portal_current_flow(device_id: ResourceId) -> Optional[CurrentFlow]`
  Read current flow using the user-scoped route with portal auth.
- `list_locations(**params: JSONValue) -> List[Location]`
- `list_portal_locations(**params: JSONValue) -> List[Location]`
  List locations using the user-scoped route with portal auth data.
- `get_location_profiles() -> Optional[LocationProfiles]`
  Fetch the portal's appliance/profile metadata.
- `get_location(location_id: ResourceId) -> Optional[Location]`
- `get_portal_location(location_id: ResourceId) -> Optional[Location]`
  Fetch one location using the user-scoped route with portal auth data.
- `create_location(payload: JSONDict) -> JSONValue`
- `create_portal_location(payload: JSONDict) -> JSONValue`
  Create a location through the portal's root location route.
- `update_location(location_id: ResourceId, payload: JSONDict) -> JSONValue`
- `update_portal_location(location_id: ResourceId, payload: JSONDict) -> JSONValue`
  Update a location through the portal's root location route.
- `update_user(payload: JSONDict) -> JSONValue`
- `update_portal_user(payload: JSONDict) -> JSONValue`
  Update the current user through the portal's collection route.
- `update_password(payload: JSONDict) -> JSONValue`
- `update_email(payload: JSONDict) -> JSONValue`
- `list_notifications(**params: JSONValue) -> List[Notification]`
- `list_portal_notifications(**params: JSONValue) -> List[Notification]`
  List notifications using the user-scoped route with portal auth data.
- `get_notification(notification_id: ResourceId) -> Optional[Notification]`
- `get_portal_notification(notification_id: ResourceId) -> Optional[Notification]`
  Fetch one notification using the user-scoped route with portal auth.
- `update_notification(notification_id: ResourceId, payload: JSONDict) -> JSONValue`
- `update_portal_notification(notification_id: ResourceId, payload: JSONDict) -> JSONValue`
  Update a notification through the portal's root route.
- `delete_notification(notification_id: ResourceId) -> JSONValue`
- `delete_portal_notification(notification_id: ResourceId) -> JSONValue`
  Delete a notification through the portal's root route.
- `set_notification_read(notification_id: ResourceId, read: bool = True, portal: bool = True) -> JSONValue`
  Set notification read state using the portal's frontend payload.
- `list_usage_alerts(**params: JSONValue) -> List[UsageAlert]`
- `list_event_rules(device_id: ResourceId, **params: JSONValue) -> List[UsageAlertRule]`
- `list_usage_alert_rules(device_id: ResourceId, **params: JSONValue) -> List[UsageAlertRule]`
- `list_portal_usage_alert_rules(device_id: ResourceId, **params: JSONValue) -> List[UsageAlertRule]`
  List usage rules using the user-scoped route with portal auth data.
- `get_usage_alert_rule(device_id: ResourceId, rule_id: ResourceId) -> Optional[UsageAlertRule]`
- `get_portal_usage_alert_rule(device_id: ResourceId, rule_id: ResourceId) -> Optional[UsageAlertRule]`
  Fetch one usage rule using the user-scoped route with portal auth.
- `create_usage_alert_rule(device_id: ResourceId, payload: JSONDict) -> JSONValue`
- `create_portal_usage_alert_rule(device_id: ResourceId, payload: JSONDict) -> JSONValue`
  Create a rule through the portal's root device route.
- `update_usage_alert_rule(device_id: ResourceId, rule_id: ResourceId, payload: JSONDict) -> JSONValue`
- `update_portal_usage_alert_rule(device_id: ResourceId, rule_id: ResourceId, payload: JSONDict) -> JSONValue`
  Update a rule using the portal service's collection PATCH form.
- `delete_usage_alert_rule(device_id: ResourceId, rule_id: ResourceId) -> JSONValue`
- `delete_portal_usage_alert_rule(device_id: ResourceId, rule_id: ResourceId) -> JSONValue`
  Delete a rule through the portal service's collection route.
- `set_usage_alert_rule_active(device_id: ResourceId, rule_id: ResourceId, active: bool) -> JSONValue`
- `set_portal_usage_alert_rule_active(device_id: ResourceId, rule_id: ResourceId, active: bool) -> JSONValue`
  Toggle a rule using the portal service's collection PATCH form.
- `list_leaks(device_id: ResourceId) -> Optional[Leak]`
- `list_portal_leaks(device_id: ResourceId) -> List[Leak]`
  Read active leaks through the portal's user-scoped route.
- `get_leak(device_id: ResourceId, leak_id: ResourceId) -> Optional[Leak]`
- `get_portal_leak(device_id: ResourceId, leak_id: ResourceId) -> Optional[Leak]`
  Read one active leak through the portal's user-scoped route.
- `list_budgets(device_id: ResourceId, **params: JSONValue) -> List[Budget]`
- `list_portal_budgets(device_id: ResourceId, **params: JSONValue) -> List[Budget]`
  List budgets using the user-scoped route with portal auth data.
- `get_budget(device_id: ResourceId, budget_id: ResourceId) -> Optional[Budget]`
- `get_portal_budget(device_id: ResourceId, budget_id: ResourceId) -> Optional[Budget]`
  Fetch one budget using the user-scoped route with portal auth.
- `create_budget(device_id: ResourceId, payload: JSONDict) -> JSONValue`
- `create_portal_budget(device_id: ResourceId, payload: JSONDict) -> JSONValue`
  Create a budget through the portal's root device route.
- `update_budget(device_id: ResourceId, budget_id: ResourceId, payload: JSONDict) -> JSONValue`
- `update_portal_budget(device_id: ResourceId, budget_id: ResourceId, payload: JSONDict) -> JSONValue`
  Update a budget using the portal service's collection PATCH form.
- `delete_budget(device_id: ResourceId, budget_id: ResourceId) -> JSONValue`
- `delete_portal_budget(device_id: ResourceId, budget_id: ResourceId) -> JSONValue`
  Delete a budget using the portal service's collection route.
- `list_subscriptions(**params: JSONValue) -> List[Subscription]`
- `list_portal_subscriptions(**params: JSONValue) -> List[Subscription]`
  List subscriptions using the user-scoped route with portal auth data.
- `get_subscription(subscription_id: ResourceId) -> Optional[Subscription]`
- `get_portal_subscription(subscription_id: ResourceId) -> Optional[Subscription]`
  Fetch a subscription using the user-scoped route with portal auth.
- `create_location_subscription(location_id: ResourceId, payload: JSONDict) -> JSONValue`
- `create_portal_subscription(location_id: ResourceId, payload: JSONDict) -> JSONValue`
  Create a subscription through the portal's root location route.
- `update_subscription(subscription_id: ResourceId, payload: JSONDict) -> JSONValue`
- `update_portal_subscription(subscription_id: ResourceId, payload: JSONDict) -> JSONValue`
  Update a subscription through the portal's collection PATCH form.
- `delete_subscription(subscription_id: ResourceId) -> JSONValue`
- `delete_portal_subscription(subscription_id: ResourceId) -> JSONValue`
  Delete a subscription through the portal's collection route.
- `create_stripe_portal(return_url: str) -> JSONValue`
- `subscribe(return_url: str) -> JSONValue`
- `list_do_not_alert_schedules(device_id: ResourceId, **params: JSONValue) -> List[DoNotAlertSchedule]`
- `list_portal_do_not_alert_schedules(device_id: ResourceId, **params: JSONValue) -> List[DoNotAlertSchedule]`
  List DNA schedules through the portal's user-scoped route.
- `create_do_not_alert_schedule(device_id: ResourceId, payload: JSONDict) -> JSONValue`
- `create_portal_do_not_alert_schedule(device_id: ResourceId, payload: JSONDict) -> JSONValue`
  Create a DNA schedule using the portal payload.
- `update_do_not_alert_schedule(device_id: ResourceId, schedule_id: ResourceId, payload: JSONDict) -> JSONValue`
- `update_portal_do_not_alert_schedule(device_id: ResourceId, schedule_id: ResourceId, payload: JSONDict) -> JSONValue`
  Update a DNA schedule using the portal collection PATCH form.
- `delete_do_not_alert_schedule(device_id: ResourceId, schedule_id: ResourceId) -> JSONValue`
- `delete_portal_do_not_alert_schedule(device_id: ResourceId, schedule_id: ResourceId) -> JSONValue`
  Delete a DNA schedule using the portal collection route.
- `update_rule_schedules(device_id: ResourceId, rule_id: ResourceId, payload: JSONDict) -> JSONValue`
- `toggle_usage_alert_schedule(device_id: ResourceId, rule_id: ResourceId, schedule_id: ResourceId, active: bool) -> JSONValue`
  Associate a DNA schedule with a rule and set its active state.
- `update_rule_shutoff_config(device_id: ResourceId, rule_id: ResourceId, payload: JSONDict) -> JSONValue`
- `list_location_access(location_id: ResourceId, **params: JSONValue) -> List[LocationAccess]`
- `list_portal_location_access(location_id: ResourceId, **params: JSONValue) -> List[LocationAccess]`
  List sharing records using the user-scoped route with portal auth.
- `get_location_access(location_id: ResourceId, access_id: ResourceId) -> Optional[LocationAccess]`
- `get_portal_location_access(location_id: ResourceId, access_id: ResourceId) -> Optional[LocationAccess]`
  Fetch a sharing record using the user-scoped route with portal auth.
- `grant_location_access(location_id: ResourceId, payload: JSONDict) -> JSONValue`
- `grant_portal_location_access(location_id: ResourceId, payload: JSONDict) -> JSONValue`
  Grant sharing access through the portal's root location route.
- `revoke_location_access(location_id: ResourceId, access_id: ResourceId) -> JSONValue`
- `revoke_portal_location_access(location_id: ResourceId, access_id: ResourceId) -> JSONValue`
  Revoke sharing access through the portal collection route.
- `list_integrations(device_id: ResourceId, **params: JSONValue) -> List[Integration]`
- `list_portal_integrations(device_id: ResourceId, **params: JSONValue) -> List[Integration]`
  List integrations through the portal's user-scoped route.
- `get_integration(device_id: ResourceId, integration_id: ResourceId) -> Optional[Integration]`
- `get_portal_integration(device_id: ResourceId, integration_id: ResourceId) -> Optional[Integration]`
- `command_integration(device_id: ResourceId, integration_id: ResourceId, state: JSONValue) -> JSONValue`
- `command_portal_integration(device_id: ResourceId, integration_id: ResourceId, state: JSONValue) -> JSONValue`
- `refresh_integration(device_id: ResourceId, integration_id: ResourceId) -> JSONValue`
- `refresh_portal_integration(device_id: ResourceId, integration_id: ResourceId) -> JSONValue`
- `delete_integration(device_id: ResourceId, integration_id: ResourceId) -> JSONValue`
- `unlink_portal_integration(device_id: ResourceId, integration_id: Optional[ResourceId] = None, payload: Optional[JSONDict] = None) -> JSONValue`
  Unlink an integration using the portal's collection DELETE form.
- `list_shutoff_integrations(device_id: ResourceId) -> List[Integration]`
  List portal shutoff-valve integrations.
- `list_spans(device_id: ResourceId, since_datetime: str, until_datetime: str, units: str = 'gallons', span_types: Optional[Sequence[str]] = None) -> List[Span]`
  List portal usage spans for a time range and classification set.
- `update_span(device_id: ResourceId, span_id: ResourceId, payload: JSONDict) -> JSONValue`
- `update_span_type(device_id: ResourceId, span_id: ResourceId, span_type: str) -> JSONValue`
  Set a span's type using the portal's exact payload shape.
- `list_span_types(location_id: ResourceId, **params: JSONValue) -> List[SpanType]`
- `submit_feedback(device_id: ResourceId, payload: JSONDict) -> JSONValue`
- `submit_device_feedback(device_id: ResourceId, payload: JSONDict) -> JSONValue`
  Submit device feedback through the portal route.
- `get_meter_accuracy(device_id: ResourceId) -> List[AccuracyResult]`
- `submit_meter_accuracy(device_id: ResourceId, payload: JSONDict) -> JSONValue`
- `submit_meter_accuracy_readings(device_id: ResourceId, since_datetime: str, until_datetime: str, since_reading: float, until_reading: float, since_image: str, until_image: str, units: str) -> JSONValue`
  Submit the portal meter-accuracy form payload.
- `initiate_accuracy_conversation(payload: JSONDict) -> JSONValue`
- `start_accuracy_conversation(message: str, since_url: str, since_datetime: str, since_reading: float, until_url: str, until_datetime: str, until_reading: float, units: str, reading_diff: float, queried_diff: float, accuracy: float) -> JSONValue`
  Start the portal's accuracy-support conversation payload.
- `list_purchase_options(device_id: ResourceId, **params: JSONValue) -> List[PurchaseOption]`
- `get_purchase_options(device_id: ResourceId) -> List[PurchaseOption]`
  Fetch device purchase options through the portal route.
- `list_pro_services(**params: JSONValue) -> List[ProService]`
- `list_insurers(**params: JSONValue) -> List[Insurer]`
- `list_portal_insurers(**params: JSONValue) -> List[Insurer]`
  List insurers through the portal root route.
- `list_clients(**params: JSONValue) -> List[ApiClient]`
- `list_portal_clients(**params: JSONValue) -> List[ApiClient]`
  List API clients through the portal root route.
- `create_client(payload: Optional[JSONDict] = None) -> JSONValue`
- `generate_api_client() -> JSONValue`
  Generate a portal API client using the portal's empty payload.
- `get_contact_info(**params: JSONValue) -> List[Contact]`
- `raw(method: str, path: str, **kwargs: Any) -> JSONDict`
  Call any current or future Flume endpoint without a new wrapper.
- `raw_response(method: str, path: str, **kwargs: Any) -> Response`
  Call an endpoint and return the underlying Requests response.

### `FlumeData`

Get the latest data and update the states.

- `FlumeData(flume_auth: Union[FlumeAuth, FlumePortalAuth], device_id: ResourceId, device_tz: str, scan_interval: timedelta = timedelta(minutes=60), update_on_init: bool = True, http_session: Optional[Session] = None, timeout: float = DEFAULT_TIMEOUT, query_payload: Optional[QueryPayload] = None) -> None`
  Initialize the data object.
- `update() -> None`
  Return updated value for session.
- `update_force() -> None`
  Return updated value for session without auto retry or limits.
- `generate_api_query_payload(scan_interval: timedelta, device_tz: str) -> QueryPayload`
  Generate API Query payload to support getting data from Flume API.

### `FlumeDeviceList`

Get Flume Device List from API.

- `FlumeDeviceList(flume_auth: Union[FlumeAuth, FlumePortalAuth], http_session: Optional[Session] = None, timeout: float = DEFAULT_TIMEOUT) -> None`
  Initialize the data object.
- `get_devices() -> List[Device]`
  Return all available devices from Flume API.

### `FlumeLeakList`

Get Flume Flume Leak Notifications from API.

- `FlumeLeakList(flume_auth: Union[FlumeAuth, FlumePortalAuth], device_id: ResourceId, http_session: Optional[Session] = None, timeout: float = DEFAULT_TIMEOUT, read: str = 'false') -> None`
  Initialize the data object.
- `get_leaks() -> List[Leak]`
  Return all leak alerts from devices owned by the user.

### `FlumeNotificationList`

Get Flume Notifications list from API.

- `FlumeNotificationList(flume_auth: Union[FlumeAuth, FlumePortalAuth], http_session: Optional[Session] = None, timeout: float = DEFAULT_TIMEOUT, read: str = 'false', sort_direction: str = 'ASC') -> None`
  Initialize the FlumeNotificationList object.
- `get_notifications() -> List[Notification]`
  Return all notifications from devices owned by the user.
- `get_next_notifications() -> List[Notification]`
  Return next page of notification from devices owned by the user.

### `FlumeUsageAlertList`

Get Flume Usage Alert list from API.

- `FlumeUsageAlertList(flume_auth: Union[FlumeAuth, FlumePortalAuth], http_session: Optional[Session] = None, timeout: float = DEFAULT_TIMEOUT, read: str = 'false') -> None`
  Initialize the data object.
- `get_usage_alerts() -> List[UsageAlert]`
  Return initial page of usage alerts from devices owned by the user.
- `get_next_usage_alerts() -> List[UsageAlert]`
  Return next page of usage alerts from devices owned by the user.
- `get_usage_alert_rules(device_id: ResourceId) -> List[UsageAlertRule]`
  Return usage alert rules configured for a device.
- `get_usage_alert_rule(device_id: ResourceId, rule_id: ResourceId) -> List[UsageAlertRule]`
  Return a single usage alert rule for a device.
- `update_usage_alert_rule(device_id: ResourceId, rule_id: ResourceId, payload: JSONDict) -> JSONValue`
  Update a usage alert rule for a device.
- `set_usage_alert_rule_active(device_id: ResourceId, rule_id: ResourceId, active: bool) -> JSONValue`
  Enable or disable a usage alert rule for a device.

### `RateLimitState`

Track a baseline and the latest server-advertised quota.

- `RateLimitState(baseline: int) -> None`
- `reset_at: Optional[datetime]` (property)
  Return reset time as a UTC datetime, if available.
- `update_from_headers(headers: Mapping[str, str]) -> None`
  Update values from standard Flume rate-limit headers.
- `to_dict() -> Dict[str, Optional[Union[int, str]]]`
  Return serializable rate-limit state.

## Resource models

All resource models inherit `FlumeModel`. Known fields are typed below. Unknown fields returned by Flume are also retained, available through attribute or mapping access, and included by `to_dict()`.

### `FlumeResponse`

Flume response envelope with typed data and preserved metadata.

| Field | Type |
| --- | --- |
| `success` | `bool` |
| `code` | `Optional[int]` |
| `message` | `Optional[str]` |
| `http_code` | `Optional[int]` |
| `http_message` | `Optional[str]` |
| `detailed` | `JSONValue` |
| `data` | `Union[ResponseT, List[ResponseT], JSONValue]` |
| `count` | `int` |
| `pagination` | `Optional[JSONDict]` |

### `User`

Portal user resource.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `email_address` | `str` |
| `first_name` | `str` |
| `last_name` | `str` |
| `type` | `Optional[str]` |
| `phone` | `Optional[str]` |
| `status` | `Optional[str]` |
| `signup_datetime` | `Optional[str]` |
| `invalidate_datetime` | `Optional[str]` |
| `plan` | `Optional['UserPlan']` |
| `referral_link` | `Optional[str]` |

### `UserPlan`

Subscription/entitlement details returned with portal user reads.

| Field | Type |
| --- | --- |
| `entitlement` | `str` |
| `expire_datetime` | `Optional[str]` |
| `frequency` | `Optional[str]` |
| `one_time_purchase` | `bool` |
| `origin` | `str` |
| `prev_origin` | `Optional[str]` |
| `price` | `Optional[Union[int, float, str]]` |
| `renews` | `bool` |
| `subscribed` | `bool` |
| `trial` | `bool` |

### `Coordinates`

Latitude/longitude pair returned on portal location reads.

| Field | Type |
| --- | --- |
| `latitude` | `float` |
| `longitude` | `float` |

### `LocationFeatures`

Feature flags returned for a portal location.

| Field | Type |
| --- | --- |
| `compatible_meter` | `bool` |
| `disaggregation` | `str` |
| `free_batteries` | `str` |
| `monthly_emails` | `bool` |
| `use_profile_for_disag` | `bool` |

### `LocationProfile`

Household fixture/profile values returned with portal locations.

| Field | Type |
| --- | --- |
| `residents` | `int` |
| `bathrooms` | `int` |
| `auto_fill_pool` | `bool` |
| `bathtub` | `bool` |
| `clothes_washer` | `bool` |
| `dish_washer` | `bool` |
| `drip_irrigation` | `bool` |
| `evaporative_cooler` | `bool` |
| `faucet` | `bool` |
| `hose_irrigation` | `bool` |
| `humidifier` | `bool` |
| `ice_maker` | `bool` |
| `manual_fill_pool` | `bool` |
| `non_wifi_irrigation_controller` | `bool` |
| `ro_system` | `bool` |
| `shower` | `bool` |
| `soaker_hose` | `bool` |
| `sprinklers` | `bool` |
| `toilet` | `bool` |
| `water_softener` | `bool` |
| `wifi_irrigation_controller` | `bool` |

### `Location`

Flume location/home resource.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `user_id` | `Optional[ResourceId]` |
| `name` | `str` |
| `primary_location` | `bool` |
| `address` | `Optional[str]` |
| `address_2` | `Optional[str]` |
| `city` | `Optional[str]` |
| `state` | `Optional[str]` |
| `postal_code` | `Optional[str]` |
| `country` | `Optional[str]` |
| `tz` | `Optional[str]` |
| `installation` | `JSONValue` |
| `insurer_id` | `Optional[ResourceId]` |
| `building_type` | `Optional[str]` |
| `away_mode` | `bool` |
| `usage_profile` | `JSONValue` |
| `coords` | `Optional[Coordinates]` |
| `geo` | `Optional[Coordinates]` |
| `features` | `Optional[LocationFeatures]` |
| `has_irrigation` | `bool` |
| `has_pool` | `bool` |
| `profile` | `Optional[LocationProfile]` |

### `Device`

Flume bridge or water-sensor device.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `type` | `Optional[int]` |
| `location_id` | `Optional[ResourceId]` |
| `user_id` | `Optional[ResourceId]` |
| `bridge_id` | `Optional[ResourceId]` |
| `name` | `Optional[str]` |
| `description` | `Optional[str]` |
| `registered` | `Optional[bool]` |
| `added_datetime` | `Optional[str]` |
| `oriented` | `bool` |
| `last_seen` | `str` |
| `connected` | `bool` |
| `battery_level` | `Optional[str]` |
| `product` | `Optional[str]` |
| `supports_ap` | `bool` |
| `supports_bluetooth` | `bool` |
| `user` | `Optional[User]` |
| `location` | `Optional[Location]` |

### `Notification`

Portal notification resource.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `device_id` | `Optional[ResourceId]` |
| `user_id` | `Optional[ResourceId]` |
| `type` | `Optional[int]` |
| `message` | `str` |
| `created_datetime` | `Optional[str]` |
| `title` | `str` |
| `read` | `bool` |
| `extra` | `Optional['NotificationExtra']` |
| `event_rule` | `JSONValue` |
| `event_rule_id` | `Optional[int]` |
| `event_triggered` | `bool` |

### `NotificationQuery`

Query metadata embedded in notification ``extra`` payloads.

| Field | Type |
| --- | --- |
| `bucket` | `str` |
| `request_id` | `str` |
| `since_datetime` | `str` |
| `tz` | `str` |
| `until_datetime` | `str` |

### `NotificationExtra`

Known fields in the portal notification ``extra`` object.

| Field | Type |
| --- | --- |
| `advanced_low_flow` | `bool` |
| `budget_start` | `Optional[str]` |
| `budget_type` | `Optional[str]` |
| `event_rule_name` | `Optional[str]` |
| `percentage` | `Optional[int]` |
| `query` | `Optional[NotificationQuery]` |

### `UsageAlert`

Triggered usage-alert event.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `device_id` | `Optional[ResourceId]` |
| `triggered_datetime` | `Optional[str]` |
| `flume_leak` | `bool` |
| `query` | `JSONValue` |
| `event_rule_name` | `Optional[str]` |

### `QueryResult`

Query result whose keys are the caller-supplied request IDs.

Flume does not publish a stable field schema for this resource. The model intentionally remains open and preserves every key returned by the API.

### `CurrentFlow`

Current flow-rate reading.

| Field | Type |
| --- | --- |
| `active` | `bool` |
| `gpm` | `float` |
| `datetime` | `Optional[str]` |

### `ShutoffConfig`

Usage-alert shutoff configuration.

| Field | Type |
| --- | --- |
| `active` | `bool` |

### `UsageAlertSchedule`

Compact schedule association nested in a usage-alert rule.

| Field | Type |
| --- | --- |
| `schedule_id` | `Optional[ResourceId]` |
| `active` | `bool` |
| `name` | `str` |
| `description` | `str` |

### `UsageAlertRule`

Portal usage-alert rule, including portal-derived display helpers.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `device_id` | `Optional[ResourceId]` |
| `name` | `str` |
| `active` | `bool` |
| `flow_rate` | `float` |
| `duration` | `int` |
| `notify_every` | `int` |
| `advanced_low_flow` | `bool` |
| `notification_type` | `Optional[str]` |
| `shutoff_config` | `Optional[ShutoffConfig]` |
| `schedules` | `List[UsageAlertSchedule]` |
| `expected_usage_config` | `JSONValue` |
| `descHTML` | `str` |
| `notifyHTML` | `str` |

### `Budget`

Daily, weekly, or monthly water budget.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `name` | `str` |
| `type` | `Optional[str]` |
| `value` | `Union[int, float]` |
| `thresholds` | `List[int]` |
| `actual` | `Optional[float]` |
| `start_date` | `Optional[str]` |
| `end_date` | `Optional[str]` |
| `recur_multiplier` | `Optional[int]` |

### `Subscription`

Notification subscription or emergency contact.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `user_id` | `Optional[ResourceId]` |
| `alert_type` | `Optional[str]` |
| `alert_info` | `JSONValue` |
| `device_id` | `Optional[ResourceId]` |
| `notification_types` | `int` |
| `created_datetime` | `Optional[str]` |
| `updated_datetime` | `Optional[str]` |
| `emergency_contact` | `bool` |
| `contact_name` | `Optional[str]` |

### `DoNotAlertSchedule`

Portal Do Not Alert schedule.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `device_id` | `Optional[ResourceId]` |
| `name` | `str` |
| `description` | `str` |
| `currently_active` | `bool` |
| `start_time` | `str` |
| `end_time` | `str` |
| `last_start` | `str` |
| `last_end` | `str` |
| `next_start` | `str` |
| `next_end` | `str` |
| `span_types` | `List[str]` |
| `rrule_str` | `str` |
| `rrule_obj` | `'RecurrenceRule'` |
| `created_datetime` | `str` |
| `updated_datetime` | `Optional[str]` |

### `RecurrenceRule`

Recurrence fields returned in a Do Not Alert schedule.

| Field | Type |
| --- | --- |
| `tzid` | `str` |
| `dtstart` | `str` |
| `freq` | `str` |
| `interval` | `int` |
| `byweekday` | `List[str]` |
| `byhour` | `int` |
| `byminute` | `int` |
| `bysecond` | `int` |

### `LocationAccess`

Shared location access record.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `user_id` | `Optional[ResourceId]` |
| `location_id` | `Optional[ResourceId]` |
| `email_address` | `Optional[str]` |

### `Integration`

External device integration, including shutoff valves.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `type` | `Optional[str]` |
| `state` | `JSONValue` |
| `status` | `JSONValue` |
| `device_id` | `Optional[ResourceId]` |

### `SpanDataPoint`

One time/value sample inside a portal water-usage span.

| Field | Type |
| --- | --- |
| `datetime` | `str` |
| `value` | `Union[int, float]` |

### `Span`

Water-usage span returned by the customer portal.

| Field | Type |
| --- | --- |
| `id` | `str` |
| `type` | `str` |
| `start` | `str` |
| `end` | `str` |
| `data` | `List[SpanDataPoint]` |
| `is_editable` | `bool` |
| `max_flowrate` | `float` |
| `mode_gpm` | `float` |
| `origin` | `str` |
| `total` | `float` |
| `value` | `float` |
| `version` | `str` |

### `SpanType`

Available span classification metadata.

| Field | Type |
| --- | --- |
| `name` | `str` |
| `display_name` | `str` |
| `labeled_as` | `str` |
| `can_relabel` | `bool` |
| `can_view` | `bool` |

### `Leak`

Leak status or leak event.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `device_id` | `Optional[ResourceId]` |
| `active` | `bool` |
| `created_datetime` | `Optional[str]` |
| `expected_usage_config_enabled` | `bool` |
| `suppressed` | `bool` |

### `PurchaseOption`

Device purchase option exposed by the customer portal.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `type` | `Optional[str]` |
| `link` | `Optional[str]` |
| `price` | `Optional[str]` |

### `Contact`

Flume support contact information.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `category` | `Optional[str]` |
| `type` | `Optional[str]` |
| `detail` | `JSONValue` |

### `Insurer`

Insurer metadata returned by the root insurer list.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `name` | `str` |

### `ApiClient`

Undocumented API-client metadata; all returned fields remain accessible.

Flume does not publish a stable field schema for this resource. The model intentionally remains open and preserves every key returned by the API.

### `ProService`

Local professional service listing displayed by the portal.

| Field | Type |
| --- | --- |
| `id` | `Optional[ResourceId]` |
| `name` | `str` |
| `description` | `str` |
| `discount` | `int` |
| `provider` | `str` |
| `url` | `str` |

### `AccuracyResult`

Meter-accuracy precheck or comparison result.

| Field | Type |
| --- | --- |
| `type` | `Optional[str]` |
| `title` | `Optional[str]` |
| `description` | `Optional[str]` |
| `accuracy` | `Optional[float]` |
| `since_url` | `Optional[str]` |
| `until_url` | `Optional[str]` |
| `reading_diff` | `Optional[float]` |
| `queried_diff` | `Optional[float]` |

### `LocationProfiles`

Appliance/profile metadata returned by ``/location-profiles``.

| Field | Type |
| --- | --- |
| `residents` | `JSONValue` |
| `bathrooms` | `JSONValue` |
| `indoor` | `List[JSONValue]` |
| `outdoor` | `List[JSONValue]` |
