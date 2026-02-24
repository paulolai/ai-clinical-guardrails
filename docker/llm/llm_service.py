#!/usr/bin/env python3
"""LLM extraction service."""

import json
from typing import Any

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

app = FastAPI(title="LLM Extraction Service")

# Configuration
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"  # Change to 70B if using that
model: AutoModelForCausalLM | None = None
tokenizer: AutoTokenizer | None = None

device = "cuda" if torch.cuda.is_available() else "cpu"


@app.on_event("startup")
async def startup_event() -> None:
    global model, tokenizer
    print(f"Loading LLM: {MODEL_NAME}")
    print(f"Device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, torch_dtype=torch.float16 if device == "cuda" else torch.float32, device_map="auto"
    )
    print("LLM loaded successfully")


class ExtractRequest(BaseModel):
    transcript: str
    patient_id: str


class Medication(BaseModel):
    name: str
    dosage: str
    frequency: str
    route: str


class ExtractionResponse(BaseModel):
    medications: list[Medication]
    conditions: list[str]
    allergies: list[str]
    confidence: float


@app.get("/health")
async def health_check() -> dict[str, Any]:
    return {"status": "healthy", "model": MODEL_NAME, "device": device}


@app.post("/extract", response_model=ExtractionResponse)
async def extract_clinical_data(request: ExtractRequest) -> ExtractionResponse:
    """Extract structured clinical data from transcript."""
    try:
        # Build prompt
        prompt = f"""<|system|>
You are a clinical data extraction assistant. Extract structured information from the following transcript.
Respond ONLY with valid JSON in this exact format:
{{
  "medications": [{{"name": "...", "dosage": "...", "frequency": "...", "route": "..."}}],
  "conditions": ["..."],
  "allergies": ["..."]
}}

<|user|>
Patient transcript: {request.transcript}

<|assistant|>
"""

        # Generate - model and tokenizer are initialized at startup
        assert tokenizer is not None, "Tokenizer not initialized"
        assert model is not None, "Model not initialized"
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        outputs = model.generate(**inputs, max_new_tokens=512, temperature=0.1, do_sample=True)

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Parse JSON from response (after assistant marker)
        json_str = response.split("<|assistant|>")[-1].strip()
        data = json.loads(json_str)

        # Convert to response model
        medications = [Medication(**m) for m in data.get("medications", [])]

        return ExtractionResponse(
            medications=medications,
            conditions=data.get("conditions", []),
            allergies=data.get("allergies", []),
            confidence=0.85,  # Simple heuristic
        )

    except Exception:
        return ExtractionResponse(medications=[], conditions=[], allergies=[], confidence=0.0)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
