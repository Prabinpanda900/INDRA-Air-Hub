from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor


ROOT = Path(__file__).resolve().parents[1]
TARGETS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]


def main() -> None:
    table_path = ROOT / "data" / "processed" / "station_training_table.csv"
    if not table_path.exists():
        raise SystemExit("Run scripts/06_build_training_table.py first.")

    df = pd.read_csv(table_path)
    targets = [col for col in TARGETS if col in df.columns]
    if not targets:
        raise SystemExit("No pollutant target columns found.")

    feature_cols = [
        col
        for col in df.select_dtypes(include=[np.number]).columns
        if col not in targets
    ]
    if not feature_cols:
        raise SystemExit("No numeric feature columns found. Add satellite/met data first.")

    model_df = df[feature_cols + targets].dropna()
    x = model_df[feature_cols]
    y = model_df[targets]

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
    model = MultiOutputRegressor(
        RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)
    )
    model.fit(x_train, y_train)
    pred = pd.DataFrame(model.predict(x_test), columns=targets, index=y_test.index)

    rows = []
    for target in targets:
        rmse = float(np.sqrt(mean_squared_error(y_test[target], pred[target])))
        mae = mean_absolute_error(y_test[target], pred[target])
        r2 = r2_score(y_test[target], pred[target])
        r = pearsonr(y_test[target], pred[target]).statistic if len(y_test) > 2 else np.nan
        bias = float((pred[target] - y_test[target]).mean())
        rows.append({"pollutant": target, "RMSE": rmse, "MAE": mae, "R2": r2, "R": r, "Bias": bias})

    model_path = ROOT / "outputs" / "models" / "baseline_pollutant_model.joblib"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": feature_cols, "targets": targets}, model_path)

    metrics_path = ROOT / "outputs" / "tables" / "validation_metrics.csv"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(metrics_path, index=False)
    print(f"Wrote {model_path}")
    print(f"Wrote {metrics_path}")


if __name__ == "__main__":
    main()
