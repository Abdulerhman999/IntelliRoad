from fastapi import FastAPI, UploadFile
import shutil
from pdf_parser import parse_pdf
from utils.gemini_fill import complete_missing
from utils.boq_generator import generate_boq
from utils.pdf_output import generate_output_pdf
from models import insert_project, insert_ml_training_row, insert_prediction
from ml.inference import predict_cost
import json
import os

app = FastAPI()

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile):
    os.makedirs("temp", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    temp_path = f"temp/{file.filename}"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    fields = parse_pdf(temp_path)

    if None in fields.values():
        filled = complete_missing(fields)
        fields.update(json.loads(filled))

    project_id = insert_project({
        "road_length_m": float(fields["road_length_m"]),
        "road_width_m": float(fields["road_width_m"]),
        "project_type": fields["project_type"],
        "location_id": 1
    })

    features = {
        "road_length_m": float(fields["road_length_m"]),
        "road_width_m": float(fields["road_width_m"])
    }

    pred_cost = predict_cost(features)

    insert_prediction(project_id, pred_cost)

    boq = generate_boq(
        float(fields["road_length_m"]),
        float(fields["road_width_m"]),
        2025
    )

    out_path = f"output/{project_id}.pdf"
    generate_output_pdf(out_path, {
        "length": fields["road_length_m"],
        "width": fields["road_width_m"],
        "location": fields.get("location_name", "Unknown"),
        "ptype": fields["project_type"]
    }, f"Predicted Cost: {pred_cost}\n\nBOQ:\n{boq}")

    return {"project_id": project_id, "prediction": pred_cost}
