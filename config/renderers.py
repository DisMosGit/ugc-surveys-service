import json
from collections.abc import Mapping
from typing import Any

import orjson
from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder

DEFAULT_ENCODER = JSONEncoder()


def _encode(value: Any) -> Any:
    return DEFAULT_ENCODER.default(value)


class OrjsonRenderer(JSONRenderer):
    media_type = "application/json"
    format = "json"
    charset = None

    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: Mapping[str, Any] | None = None,
    ) -> bytes:
        if data is None:
            return b""

        option = orjson.OPT_NON_STR_KEYS | orjson.OPT_UTC_Z
        if renderer_context and renderer_context.get("indent"):
            option |= orjson.OPT_INDENT_2

        try:
            return orjson.dumps(data, default=_encode, option=option)
        except TypeError:
            return json.dumps(data, cls=JSONEncoder).encode()
