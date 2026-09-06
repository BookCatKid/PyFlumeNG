# PyFlumeNG
## Overview
PyFlumeNG is a fork and superset of PyFlume. It preserves the original
`pyflume` import package and APIs while adding the customer-portal OAuth flow,
portal-only write operations, complete response/error handling, pagination, and
additional Flume endpoints discovered in the portal application.

Install the fork with:

```bash
pip install PyFlumeNG
```

The Python import remains `pyflume` for compatibility:

```python
import pyflume

auth = pyflume.FlumeAuth(
    username="your_email",
    password="your_password",
)
flume = pyflume.FlumeClient(auth)
```

## Retrieve API Key
`FlumeAuth` remains the original documented Personal API password-grant
authentication for drop-in compatibility. `PersonalAuth` is its explicit alias
and still requires a client ID and client secret from the API Access settings
page. `PortalAuth` uses the customer portal OAuth flow and supports portal-only
operations such as updating usage-alert rules.

## Modules
Below are the details of each module, each documented in its corresponding file:

### Notifications
Retrieve notifications from the Flume API, including filtering based on the read status.
- [Read the Notifications documentation](https://github.com/ChrisMandich/PyFlume/blob/master/docs/notifications.md)

### Usage Alerts
Manage and retrieve usage alert notifications from the Flume API.
- [Read the Usage Alerts documentation](https://github.com/ChrisMandich/PyFlume/blob/master/docs/usage.md)

### Devices
Retrieve information related to Flume devices, including their list from the API.
- [Read the Devices documentation](https://github.com/ChrisMandich/PyFlume/blob/master/docs/devices.md)

### Leak Alerts
Manage and retrieve leak notifications from the Flume API.
- [Read the Leak Alerts documentation](https://github.com/ChrisMandich/PyFlume/blob/master/docs/leak.md)

### Data Retrieval
Retrieve and update data from the Flume API, working with authentication and various data endpoints.
- [Read the Data Retrieval documentation](https://github.com/ChrisMandich/PyFlume/blob/master/docs/data.md)

### Authentication
Authentication module to handle tokens and user credentials within the Flume environment.
- [Read the Authentication documentation](https://github.com/ChrisMandich/PyFlume/blob/master/docs/auth.md)

## Getting Started
To get started with the Flume API Integration, refer to the individual documentation files for each module. They provide detailed information on dependencies, initialization, methods, and example usage.

Every endpoint extracted from the current Flume portal is represented by a
named `FlumeClient` method. `FlumeClient.raw()` remains available only as a
forward-compatibility escape hatch for future Flume routes added after this
release. It returns the complete Flume response envelope, while named methods
return the envelope's `data` field.

For any questions or additional support, refer to the official Flume API
documentation or contact the development team.

## Contributing
Feel free to contribute to the codebase by opening issues, submitting pull requests, or suggesting improvements.
