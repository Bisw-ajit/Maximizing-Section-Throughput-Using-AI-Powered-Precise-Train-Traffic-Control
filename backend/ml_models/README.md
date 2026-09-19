# RAILOPTIX — ML Models Directory

Place your Colab-trained XGBoost model files here:

| File | Description | Size (approx) |
|---|---|---|
| `delay_model.json` | XGBRegressor — predicts next-station delay (minutes) | ~500KB |
| `congestion_model.json` | XGBClassifier — predicts section congestion risk (0/1) | ~400KB |
| `feature_columns.json` | Feature metadata & model metrics | ~2KB |

## How to Get These Files

1. Open Google Colab
2. Upload `railoptix/colab/generate_training_data.py` and `railoptix/colab/train_xgboost.py`
3. Run: `!python generate_training_data.py --samples 50000`
4. Run: `!python train_xgboost.py`
5. Download the 3 files from the `models/` folder in Colab
6. Place them in THIS directory

## Without Model Files

The system uses a **heuristic fallback** automatically — no errors, no crashes.
Check `/api/predictions/status` to see current mode.
