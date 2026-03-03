import requests

FORM_URL = "https://docs.google.com/forms/d/e/YOUR_FORM_ID/formResponse"

FIELDS = {
    "name": "entry.575335391",
    "lesson": "entry.1320852544",
    "task": "entry.705949827",
    "result": "entry.856775041",
}

def submit_result(name, lesson, task, result):
    payload = {
        FIELDS["name"]: name,
        FIELDS["lesson"]: lesson,
        FIELDS["task"]: task,
        FIELDS["result"]: result,
    }

    response = requests.post(FORM_URL, data=payload)

    if response.status_code == 200:
        return True
    return False