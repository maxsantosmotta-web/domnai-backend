from __future__ import annotations

from pathlib import Path

from starlette.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles


class FrontendStaticFiles(StaticFiles):
    """Serve the SPA without allowing a stale index.html to survive a deploy."""

    def file_response(
        self,
        full_path: str,
        stat_result,
        scope,
        status_code: int = 200,
    ) -> Response:
        path = Path(full_path)

        # The HTML contains the current hashed asset names. Returning 304 for it
        # can make a browser keep references to bundles removed by a new deploy.
        if path.name == "index.html":
            return FileResponse(
                full_path,
                status_code=status_code,
                stat_result=stat_result,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )

        response = super().file_response(full_path, stat_result, scope, status_code)

        # Vite assets are content-addressed by their filename hash and may be
        # cached aggressively without risking references to stale content.
        if "assets" in path.parts and response.status_code in {200, 304}:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        return response
