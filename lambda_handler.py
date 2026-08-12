from __future__ import annotations

from mangum import Mangum

from mettle.web.app import create_app


handler = Mangum(create_app(), lifespan="off", api_gateway_base_path="/")
