"""Generate OpenAPI specification from the FastAPI app."""

import json
import sys
from pathlib import Path


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from pp.server.server import app

    output_path = Path("docs/openapi.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(app.openapi(), f, indent=2)

    print(f"OpenAPI spec written to {output_path}")


if __name__ == "__main__":
    main()
