# Sag & Tension Calculator

Python/Flask web conversion of the original MATLAB sag-tension script. It calculates conductor tensions for the predefined weather-zone load cases and plots the conductor sag between two equal-height towers.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## GitHub

```bash
git init
git add .
git commit -m "Initial sag tension web app"
git branch -M main
git remote add origin https://github.com/hamedvf1992-sudo/sag-calc.git
git push -u origin main
```

If `origin` already exists, use:

```bash
git remote set-url origin https://github.com/hamedvf1992-sudo/sag-calc.git
```

## Hosting note

GitHub Pages hosts static HTML/CSS/JS and will not run this Flask/Python backend. Keep the code on GitHub, then deploy the repo to a Python-capable host such as Render, Railway, Fly.io, or a VPS. A typical production start command is:

```bash
gunicorn app:app
```

## Engineering note

The conductor graphic uses the standard equal-support parabolic approximation:

`f = w L^2 / (8 H)`

where `w` is resultant unit load, `L` is span, and `H` is horizontal tension. Verify units and design assumptions before using results for engineering decisions.


## Render deployment

- Service type: Web Service
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn --bind 0.0.0.0:$PORT app:app`
- Health check path: `/health`
- Leave Root Directory blank when `app.py` is at repository root.
