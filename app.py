from pathlib import Path
import os

from flask import Flask, jsonify, render_template, request
from sag_tension import DEFAULTS, analyze

BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


@app.get("/")
def index():
    return render_template("index.html", defaults=DEFAULTS)


@app.get("/health")
def health():
    return {"status": "ok"}, 200


@app.post("/api/calculate")
def calculate():
    try:
        data = request.get_json(force=True) or {}
        result = analyze(data)
        return jsonify(result)
    except (ValueError, ArithmeticError, ZeroDivisionError) as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
