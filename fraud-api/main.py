import os
import sys
from pathlib import Path

import joblib
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

_here = Path(__file__).resolve().parent
if (_here / "scripts" / "fraud_ml_common.py").exists():
    REPO_ROOT = _here
else:
    REPO_ROOT = _here.parent

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from fraud_ml_common import align_feature_matrix, build_single_prediction_frame

MODEL_PATH = Path(os.getenv("FRAUD_MODEL_PATH", str(REPO_ROOT / "models" / "fraud_model.joblib")))
API_SECRET = os.getenv("FRAUD_API_SECRET", "")

app = FastAPI(title="Shop fraud inference")

_artifact = None


def load_artifact():
    global _artifact
    if _artifact is None:
        if not MODEL_PATH.exists():
            raise RuntimeError(f"Model not found at {MODEL_PATH}")
        _artifact = joblib.load(MODEL_PATH)
    return _artifact


class PredictBody(BaseModel):
    order: dict
    customer: dict


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/predict")
def predict(
    body: PredictBody,
    x_fraud_secret: str | None = Header(default=None, alias="X-Fraud-Api-Secret"),
):
    if API_SECRET and x_fraud_secret != API_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing API secret")

    art = load_artifact()
    pipeline = art["pipeline"]
    threshold = float(art["threshold"])
    expected_features = list(art["features"])

    X_raw, _ = build_single_prediction_frame(body.order, body.customer)
    X = align_feature_matrix(X_raw, expected_features)

    proba = float(pipeline.predict_proba(X)[0, 1])
    predicted = int(proba >= threshold)
    return {
        "fraud_probability": proba,
        "predicted_fraud": predicted,
        "threshold": threshold,
        "model_name": art.get("model_name"),
    }
