"""Small standard-library HTTP wrapper for the repository's drag-error model."""

from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os

from ml.predictor import DragErrorPredictor


@lru_cache(maxsize=1)
def get_predictor():
    return DragErrorPredictor()


ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv(
        "AI_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
}


class AiHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = b"" if status == 204 else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(204, {})

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "model": "synthetic-gradient-boosting-demo"})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/predict":
            self._send_json(404, {"error": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 4096:
                raise ValueError("Request body is too large")
            payload = json.loads(self.rfile.read(size))
            values = {
                "altitude_km": (100.0, 5000.0),
                "f107": (0.0, 500.0),
                "kp": (0.0, 9.0),
                "b_star": (0.0, 0.1),
                "tle_age_days": (0.0, 365.0),
            }
            features = {}
            for name, (lower, upper) in values.items():
                value = float(payload[name])
                if not lower <= value <= upper:
                    raise ValueError(f"{name} must be between {lower} and {upper}")
                features[name] = value
            estimate = get_predictor().predict_error(
                features["altitude_km"], features["f107"], features["kp"],
                features["b_star"], features["tle_age_days"],
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})
            return
        self._send_json(200, {
            "predicted_along_track_error_m": estimate,
            "model": "gradient-boosting-demo",
            "training_data": "synthetic",
        })

    def log_message(self, format_string, *args):
        print(f"[AI API] {self.address_string()} - {format_string % args}")


if __name__ == "__main__":
    host = os.getenv("AI_HOST", "127.0.0.1")
    port = int(os.getenv("AI_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), AiHandler)
    print(f"OrbitGuard AI API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping OrbitGuard AI API")
        server.server_close()
