# Agricultural Detection System

A multilingual web app that helps farmers analyze soil conditions, check plant health, and get crop recommendations. Supports **English**, **Hindi**, and **Kannada**.

## Features

- **Soil Detection** — Upload a land image to get land type, climate, water availability, pH, predicted yield, and crop suggestions
- **Plant Health Check** — Upload a plant image for health status, detected issues, and treatment recommendations
- **AI Chat Assistant** — Ask questions about soil, crops, and plant diseases in your selected language
- **Multilingual UI** — Full interface in English, Hindi, and Kannada

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, Tailwind CSS (CDN)
- **Production server:** Gunicorn

## Project Structure

```
crop_yield_detection/
├── app.py                 # Flask application and API routes
├── templates/
│   └── index.html         # Web UI
├── requirements.txt       # Python dependencies
├── runtime.txt            # Python version for deployment
├── Procfile               # Process file for Render/Heroku
├── render.yaml            # One-click deploy config for Render
└── README.md
```

## Local Setup

### Prerequisites

- Python 3.11+

### Run locally

```bash
# Clone the repository
git clone https://github.com/nisha-shetty03/Crop_yield_detector.git
cd Crop_yield_detector

# Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the development server
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

### Run with Gunicorn (production-like)

```bash
gunicorn app:app --bind 0.0.0.0:5000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main web interface |
| GET | `/get-translations/<lang>` | UI translations (`en`, `hi`, `kn`) |
| POST | `/predict-details-from-image` | Soil analysis (multipart form: `image`, `language`) |
| POST | `/predict-plant-health` | Plant health check (multipart form: `image`, `language`) |
| POST | `/chatbot` | Chat assistant (JSON: `message`, `language`) |

## Deploy for Public Use

The app is ready to deploy on [Render](https://render.com) (free tier available).

### Option 1: Deploy with Render (recommended)

1. Push this repository to GitHub (if not already):
   ```bash
   git add .
   git commit -m "Prepare app for deployment"
   git push origin main
   ```

2. Go to [render.com](https://render.com) and sign up / log in.

3. Click **New +** → **Blueprint** and connect your GitHub repo, or use **New Web Service** with these settings:

   | Setting | Value |
   |---------|-------|
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT` |
   | **Runtime** | Python 3 |

4. Add an environment variable (optional but recommended):
   - `SECRET_KEY` — a random secret string (Render can auto-generate this via `render.yaml`)

5. Click **Deploy**. Render will give you a public URL like `https://crop-yield-detector.onrender.com`.

If you use the included `render.yaml`, choose **Blueprint** deploy for one-click setup.

### Option 2: Deploy on Railway

1. Go to [railway.app](https://railway.app) and connect your GitHub repo.
2. Railway auto-detects Python. Set the start command:
   ```
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```
3. Deploy and share the generated URL.

### Option 3: Deploy on Heroku

```bash
heroku create your-app-name
git push heroku main
```

The included `Procfile` is used automatically.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | Auto-set by host | Port the server listens on |
| `SECRET_KEY` | Recommended | Flask secret key for sessions |
| `FLASK_DEBUG` | Optional | Set to `true` for local debug mode only |

## Important Note

Current predictions use **simulated analysis** (randomized demo data) for demonstration purposes. The uploaded images are not processed by a trained ML model yet. For production-grade accuracy, integrate trained models for soil classification and plant disease detection.

## License

Open source — use and modify freely.
