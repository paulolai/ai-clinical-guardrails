import os

import uvicorn

if __name__ == "__main__":
    # Ensure reports directory exists
    os.makedirs("reports", exist_ok=True)

    print("\n[API Server] Starting Clinical Guardrails FastAPI Server...")
    print("[API Server] Swagger UI: http://localhost:8000/docs")
    print("[API Server] ReDoc: http://localhost:8000/redoc")

    # Run the FastAPI app
    # host 0.0.0.0 for container support, port 8000
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
