from flask import Flask, render_template, request, redirect, url_for, flash
import pickle
import numpy as np
import os
import logging

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)

# ---------------- LOAD MODEL ----------------
def load_model():
    try:
        if os.path.exists("model.pkl"):
            with open("model.pkl", "rb") as f:
                model = pickle.load(f)
                logging.info("Model loaded successfully")
                return model
        else:
            logging.warning("model.pkl not found")
            return None
    except Exception as e:
        logging.error(f"Error loading model: {e}")
        return None

model = load_model()

# ---------------- LOAD EXTRA FILES ----------------
def load_file(filepath, default_value):
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return f.read()
        return default_value
    except:
        return default_value

best_model_name = load_file("best_model.txt", "Random Forest")
metrics = load_file("metrics.txt", "Metrics not available")

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template(
        "index.html",
        effort=None,
        cost=None,
        model_name=best_model_name,
        metrics=metrics,
        show_graphs=False
    )

# ---------------- PREDICT ----------------
@app.route('/predict', methods=['POST'])
def predict():
    global model

    if model is None:
        flash("⚠ Model not found")
        return redirect(url_for('home'))

    try:
        # -------- INPUTS --------
        loc = float(request.form.get('loc'))
        cplx = float(request.form.get('cplx'))
        acap = float(request.form.get('acap'))
        pcap = float(request.form.get('pcap'))

        # -------- VALIDATION --------
        if loc <= 0:
            flash("Invalid LOC value")
            return redirect(url_for('home'))

        # -------- PREDICTION --------
        features = np.array([[loc, cplx, acap, pcap]])
        effort = model.predict(features)[0]

        # -------- COST CALCULATION --------
        COST_PER_PM = 40000  # assumed cost
        cost = effort * COST_PER_PM

        # -------- RETURN --------
        return render_template(
            "index.html",
            effort=round(effort, 2),
            cost=round(cost, 2),
            model_name=best_model_name,
            metrics=metrics,
            show_graphs=True
        )

    except:
        flash("Error in input")
        return redirect(url_for('home'))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)