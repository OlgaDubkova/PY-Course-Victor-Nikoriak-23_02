import requests
import uuid

API_URL = "https://script.google.com/macros/s/AKfycbzRQlksfFUKNmbA_ITbLbbhoLcOusTAr96UXAeyNcPPY-b0DiIaX78V00Hsud1iWyrU/exec"

class CourseClient:

    def __init__(self, name, lesson_id):
        self.name = name
        self.lesson_id = lesson_id
        self.token = self._start_session()

    def _start_session(self):
        r = requests.get(API_URL, params={
            "name": self.name,
            "lesson_id": self.lesson_id
        })
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError("Cannot start session")
        return data["token"]

    def submit(self, task_id, result, progress=None):
        payload = {
            "token": self.token,
            "task_id": task_id,
            "result": result,
            "progress": progress or {},
            "client_ts": int(__import__("time").time() * 1000),
            "nonce": str(uuid.uuid4())
        }
        r = requests.post(API_URL, json=payload)
        return r.json()


def get_all_scores(lesson_id, admin_key=None):
    """Fetch all submissions for a lesson (requires backend all_scores action)."""
    params = {"action": "all_scores", "lesson_id": lesson_id}
    if admin_key:
        params["key"] = admin_key
    r = requests.get(API_URL, params=params)
    return r.json()

