# AI forecast service

The Orbital dashboard calls the Python predictor through a small HTTP service.
Run both the service and the frontend during local development.

From the repository root, install the Python dependencies and start the API:

```sh
python -m pip install -r requirements.txt
python -m ml.api
```

In a second terminal, start the frontend:

```sh
cd orbital-dance
npm install
npm run dev
```

The frontend uses `http://127.0.0.1:8000` by default. To use a separately
hosted API, set `VITE_AI_API_URL` before starting the frontend. Set
`AI_CORS_ORIGINS` on the API to a comma-separated list of allowed frontend
origins.

The current `DragErrorPredictor` is trained on generated synthetic examples.
Its output is a demo integration and is not validated for operational use.
