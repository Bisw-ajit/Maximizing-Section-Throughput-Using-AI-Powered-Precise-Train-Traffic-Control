"""
RAILOPTIX — XGBoost Model Training Script
==========================================
Run this on Google Colab (free GPU/CPU) after running generate_training_data.py.

STEPS ON COLAB:
  1. Upload this file + generate_training_data.py to Colab
  2. Run:  !pip install xgboost scikit-learn pandas numpy matplotlib seaborn
  3. Run:  !python generate_training_data.py --samples 50000
  4. Run:  !python train_xgboost.py
  5. Download:
       - models/delay_model.json
       - models/congestion_model.json
       - models/feature_columns.json
  6. Put those 3 files into: railoptix/backend/ml_models/

Two models are trained:
  1. delay_model.json      -> XGBRegressor  -> predicts next_delay_min (minutes)
  2. congestion_model.json -> XGBClassifier -> predicts congestion_risk (0 or 1)
"""

# ── Install (uncomment if running on Colab) ───────────────────────────────────
# !pip install xgboost scikit-learn pandas numpy matplotlib seaborn -q

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    classification_report, confusion_matrix, roc_auc_score
)
import xgboost as xgb

os.makedirs("models", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# PART 1: DELAY REGRESSION MODEL
# ─────────────────────────────────────────────────────────────────────────────

print("=" * 60)
print("  PART 1: Training Delay Prediction (XGBRegressor)")
print("=" * 60)

df_delay = pd.read_csv("data/delay_regression_data.csv")
print(f"Loaded {len(df_delay)} samples")
print(df_delay.describe())

# Features and Target
DELAY_FEATURES = [
    "current_delay_min",
    "section_length_km",
    "section_capacity",
    "section_occupancy",
    "is_single_track",
    "train_priority",
    "speed_kmh",
    "time_of_day_min",
    "is_peak_hour",
    "trains_ahead",
    "journey_progress",
    "sched_vs_actual_diff",
    "congestion_ratio",
    "speed_limit_kmh",
]
DELAY_TARGET = "next_delay_min"

X_delay = df_delay[DELAY_FEATURES]
y_delay = df_delay[DELAY_TARGET]

# Train/test split
X_tr, X_te, y_tr, y_te = train_test_split(X_delay, y_delay, test_size=0.2, random_state=42)
print(f"\nTrain: {len(X_tr)}  |  Test: {len(X_te)}")

# XGBoost Regressor
delay_model = xgb.XGBRegressor(
    n_estimators=400,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    gamma=0.1,
    reg_alpha=0.1,
    reg_lambda=1.0,
    objective="reg:squarederror",
    eval_metric="mae",
    early_stopping_rounds=30,
    random_state=42,
    n_jobs=-1,
    verbosity=1,
)

delay_model.fit(
    X_tr, y_tr,
    eval_set=[(X_te, y_te)],
    verbose=50,
)

# Evaluation
y_pred = delay_model.predict(X_te)
mae  = mean_absolute_error(y_te, y_pred)
rmse = np.sqrt(mean_squared_error(y_te, y_pred))
r2   = r2_score(y_te, y_pred)

print(f"\n{'─'*40}")
print(f"  DELAY MODEL RESULTS")
print(f"{'─'*40}")
print(f"  MAE  (Mean Abs Error)  : {mae:.3f} minutes")
print(f"  RMSE (Root Mean Sq Er) : {rmse:.3f} minutes")
print(f"  R²   (Explained Var)   : {r2:.4f}")
print(f"{'─'*40}")

# Feature Importance Plot
fi = pd.Series(delay_model.feature_importances_, index=DELAY_FEATURES).sort_values(ascending=False)
plt.figure(figsize=(10, 6))
sns.barplot(x=fi.values, y=fi.index, palette="Blues_d")
plt.title("Delay Model — Feature Importance")
plt.tight_layout()
plt.savefig("models/delay_feature_importance.png", dpi=150)
plt.show()
print("📊 Feature importance chart saved → models/delay_feature_importance.png")

# Prediction vs Actual scatter (sample 500 pts)
sample_idx = np.random.choice(len(y_te), size=500, replace=False)
plt.figure(figsize=(7, 7))
plt.scatter(y_te.values[sample_idx], y_pred[sample_idx], alpha=0.4, s=15)
plt.plot([0, y_te.max()], [0, y_te.max()], "r--", linewidth=1)
plt.xlabel("Actual Next Delay (min)")
plt.ylabel("Predicted Next Delay (min)")
plt.title(f"Delay Model — Actual vs Predicted  (R²={r2:.3f})")
plt.tight_layout()
plt.savefig("models/delay_actual_vs_predicted.png", dpi=150)
plt.show()

# Save model
delay_model.save_model("models/delay_model.json")
print("✅  Saved → models/delay_model.json")


# ─────────────────────────────────────────────────────────────────────────────
# PART 2: CONGESTION CLASSIFICATION MODEL
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("  PART 2: Training Congestion Risk (XGBClassifier)")
print("=" * 60)

df_cong = pd.read_csv("data/congestion_classification_data.csv")
print(f"Loaded {len(df_cong)} samples")
print("Class balance:")
print(df_cong["congestion_risk"].value_counts(normalize=True).rename({0: "No Risk", 1: "Risk"}))

CONG_FEATURES = [
    "section_length_km",
    "section_capacity",
    "section_occupancy",
    "is_single_track",
    "trains_approaching",
    "time_of_day_min",
    "is_peak_hour",
    "avg_delay_in_section",
    "congestion_ratio",
    "future_load",
    "total_trains_network",
    "speed_limit_kmh",
]
CONG_TARGET = "congestion_risk"

X_cong = df_cong[CONG_FEATURES]
y_cong = df_cong[CONG_TARGET]

# Compute scale_pos_weight for class imbalance
neg = (y_cong == 0).sum()
pos = (y_cong == 1).sum()
scale_pos_weight = neg / max(pos, 1)
print(f"  scale_pos_weight = {scale_pos_weight:.2f}  (neg={neg}, pos={pos})")

X_ctr, X_cte, y_ctr, y_cte = train_test_split(X_cong, y_cong, test_size=0.2,
                                               random_state=42, stratify=y_cong)

congestion_model = xgb.XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    gamma=0.1,
    scale_pos_weight=scale_pos_weight,
    objective="binary:logistic",
    eval_metric="auc",
    early_stopping_rounds=30,
    random_state=42,
    n_jobs=-1,
    verbosity=1,
    use_label_encoder=False,
)

congestion_model.fit(
    X_ctr, y_ctr,
    eval_set=[(X_cte, y_cte)],
    verbose=50,
)

# Evaluation
y_cpred = congestion_model.predict(X_cte)
y_cprob = congestion_model.predict_proba(X_cte)[:, 1]
auc = roc_auc_score(y_cte, y_cprob)

print(f"\n{'─'*40}")
print(f"  CONGESTION MODEL RESULTS")
print(f"{'─'*40}")
print(f"  ROC-AUC : {auc:.4f}")
print(classification_report(y_cte, y_cpred, target_names=["No Risk", "Risk"]))
print(f"{'─'*40}")

# Confusion matrix
cm = confusion_matrix(y_cte, y_cpred)
plt.figure(figsize=(5, 4))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=["Predicted: No Risk", "Predicted: Risk"],
            yticklabels=["Actual: No Risk", "Actual: Risk"])
plt.title(f"Congestion Model — Confusion Matrix  (AUC={auc:.3f})")
plt.tight_layout()
plt.savefig("models/congestion_confusion_matrix.png", dpi=150)
plt.show()

# Feature importance
fi_c = pd.Series(congestion_model.feature_importances_, index=CONG_FEATURES).sort_values(ascending=False)
plt.figure(figsize=(10, 6))
sns.barplot(x=fi_c.values, y=fi_c.index, palette="Oranges_d")
plt.title("Congestion Model — Feature Importance")
plt.tight_layout()
plt.savefig("models/congestion_feature_importance.png", dpi=150)
plt.show()
print("📊 Congestion charts saved to models/")

# Save model
congestion_model.save_model("models/congestion_model.json")
print("✅  Saved → models/congestion_model.json")


# ─────────────────────────────────────────────────────────────────────────────
# PART 3: Save Feature Column Metadata
# ─────────────────────────────────────────────────────────────────────────────

metadata = {
    "delay_model": {
        "features": DELAY_FEATURES,
        "target":   DELAY_TARGET,
        "model_type": "XGBRegressor",
        "metrics": {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4)},
    },
    "congestion_model": {
        "features": CONG_FEATURES,
        "target":   CONG_TARGET,
        "model_type": "XGBClassifier",
        "metrics": {"roc_auc": round(auc, 4)},
        "threshold": 0.5,
    },
}

with open("models/feature_columns.json", "w") as f:
    json.dump(metadata, f, indent=2)
print("✅  Saved → models/feature_columns.json")

# ─────────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("  TRAINING COMPLETE!")
print("=" * 60)
print("\n📦 Download these 3 files from Colab:")
print("   models/delay_model.json")
print("   models/congestion_model.json")
print("   models/feature_columns.json")
print("\n📁 Put them inside:")
print("   railoptix/backend/ml_models/")
print("\n✅ FastAPI will auto-load them at startup.")
