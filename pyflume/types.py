"""Shared public typing aliases for PyFlumeNG."""

from typing import Dict, List, Mapping, Optional, TypedDict, Union

JSONPrimitive = Union[None, bool, int, float, str]
JSONValue = Union[JSONPrimitive, List["JSONValue"], Dict[str, "JSONValue"]]
JSONDict = Dict[str, JSONValue]
JSONList = List[JSONValue]
ResourceId = Union[int, str]
RequestParams = Mapping[str, JSONValue]
QueryValues = Dict[str, Optional[float]]


class _RequiredQuerySpec(TypedDict):
    """Fields required by every Flume device-query entry."""

    request_id: str


class QuerySpec(_RequiredQuerySpec, total=False):
    """One query in a Flume device-query payload."""

    bucket: str
    since_datetime: str
    until_datetime: str
    operation: str
    units: str


class QueryPayload(TypedDict):
    """Payload accepted by the legacy :class:`FlumeData` query helper."""

    queries: List[QuerySpec]


class _RequiredFlumeToken(TypedDict):
    """Fields every successful Flume OAuth token response must contain."""

    access_token: str


class FlumeToken(_RequiredFlumeToken, total=False):
    """OAuth token fields returned by Flume's Personal and Portal flows."""

    refresh_token: str
    token_type: str
    scope: str
    expires_in: int
