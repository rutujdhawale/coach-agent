"""End-to-end demo script for the Sri Lankan Grade 7 test student (lk_g7_kavindu)."""
import json

from fastapi.testclient import TestClient

from app.main import app


def main():
    student_id = "lk_g7_kavindu"
    with TestClient(app) as client:
        print("1. Health check:", client.get("/health").json())

        profile = client.get(f"/api/v1/students/{student_id}").json()
        print("\n2. Student profile:\n", json.dumps(profile, indent=2))

        progress = client.get(f"/api/v1/students/{student_id}/progress").json()
        print("\n3. Student progress:\n", json.dumps(progress, indent=2))

        prompt = (
            "Hi Coach! I am Kavindu in Grade 7 (student_id: lk_g7_kavindu). "
            "Please check my term test history, identify my weak topics, "
            "and give me 2 practice questions for my weakest topic."
        )
        print(f"\n4. Sending chat to ADK coach for {student_id}...")
        chat_resp = client.post(
            "/api/v1/coach/chat",
            json={"student_id": student_id, "message": prompt},
        )
        print("Status:", chat_resp.status_code)
        print("Coach response:\n", chat_resp.json().get("response", chat_resp.text))


if __name__ == "__main__":
    main()
