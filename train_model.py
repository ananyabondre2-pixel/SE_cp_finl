import pandas as pd
import pickle
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import r2_score

# ---------------- LOAD DATA ----------------
df = pd.read_csv("cocomo81_large.csv", sep=",")

# 🔥 FIX: if entire row is read as one column
if len(df.columns) == 1:
    df = df.iloc[:, 0].str.split(",", expand=True)
    df.columns = [
        "rely","data","cplx","time","stor","virt","turn",
        "acap","aexp","pcap","vexp","lexp","modp","tool",
        "sced","loc","actual"
    ]

# Convert all values to numeric
df = df.apply(pd.to_numeric)

# Debug check
print("Columns:", df.columns)

# ---------------- SELECT FEATURES ----------------
X = df[["loc", "cplx", "acap", "pcap"]]
y = df["actual"]

# ---------------- SPLIT ----------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ---------------- MODELS ----------------
models = {
    "Linear Regression": LinearRegression(),
    "Random Forest": RandomForestRegressor(n_estimators=100),
    "SVR": SVR(),
    "Decision Tree": DecisionTreeRegressor()
}

best_model = None
best_score = -1
best_name = ""
results_text = ""

# ---------------- TRAIN & EVALUATE ----------------
for name, model in models.items():
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    score = r2_score(y_test, preds)
    results_text += f"{name}: R2 = {round(score, 3)}\n"

    if score > best_score:
        best_score = score
        best_model = model
        best_name = name
        best_preds = preds

# ---------------- SAVE MODEL ----------------
pickle.dump(best_model, open("model.pkl", "wb"))

with open("metrics.txt", "w") as f:
    f.write(results_text)

with open("best_model.txt", "w") as f:
    f.write(best_name)

# ---------------- GRAPH 1 ----------------
plt.figure()
plt.scatter(y_test, best_preds)
plt.xlabel("Actual Effort")
plt.ylabel("Predicted Effort")
plt.title("Actual vs Predicted Effort")
plt.savefig("static/graph1.png")

# ---------------- GRAPH 2 ----------------
features = ["LOC", "CPLX", "ACAP", "PCAP"]

# For tree-based models
if hasattr(best_model, "feature_importances_"):
    importances = best_model.feature_importances_

# For linear models
elif hasattr(best_model, "coef_"):
    importances = best_model.coef_

# Fallback
else:
    importances = [0.25, 0.25, 0.25, 0.25]

plt.figure()
plt.bar(features, importances)
plt.title("Feature Importance")
plt.savefig("static/graph2.png")

print("✅ Model trained successfully!")
print("Best Model:", best_name)