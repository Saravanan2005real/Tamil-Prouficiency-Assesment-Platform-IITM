# Tamil Listening Module - Single Server Setup

## Quick Start

Simply run the Flask server and everything will work:

```bash
cd Backend
python app.py
```

Then open your browser and go to: **http://127.0.0.1:5000**

## What Changed

- **Removed separate frontend server** - No need to run `python -m http.server 8000`
- **Flask serves everything** - HTML, CSS, JS, and API endpoints all from one server
- **All URLs are relative** - No hardcoded `http://127.0.0.1:5000` in the frontend code
- **Single command to run** - Just `python Backend/app.py`

## File Structure

```
tamil-listening-module/
├── index.html          # Frontend HTML (served by Flask)
├── script.js           # Frontend JavaScript (served by Flask)
├── style.css           # Frontend CSS (served by Flask)
└── Backend/
    ├── app.py          # Flask server (serves everything)
    ├── data/
    │   └── questions/  # Question JSON files
    └── uploads/
        └── audio/      # Audio files
```

## How It Works

1. Flask app (`Backend/app.py`) serves:
   - `/` → `index.html`
   - `/script.js` → `script.js`
   - `/style.css` → `style.css`
   - `/api/*` → API endpoints
   - `/audio/*` → Audio files
   - `/questions/*` → Question JSON files

2. All frontend code uses relative URLs (e.g., `/api/test` instead of `http://127.0.0.1:5000/api/test`)

3. Everything runs on port 5000

## Troubleshooting

If you get errors:
1. Make sure you're in the `Backend` directory when running `python app.py`
2. Check that `index.html`, `script.js`, and `style.css` are in the project root
3. Verify Python and Flask are installed: `pip install flask flask-cors`

