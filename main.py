import os
import time
import requests
import datetime
import io
import base64
from typing import List, Dict, Any, TypedDict, Optional

# --- NEW COLAB AUTH IMPORTS ---
from google.colab import auth
import google.auth

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# --- 1. SETTINGS & SECRETS ---
try:
    from google.colab import userdata
    ELEVEN_API_KEY = userdata.get('ELEVENLABS_API_KEY')
except Exception:
    ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "your_elevenlabs_api_key_here")

SPREADSHEET_ID = "your_google_sheet_id_here"
DRIVE_FOLDER_ID = "your_google_drive_folder_id_here"

# --- 2. AUTHENTICATION (Colab Native) ---
print("🔑 Triggering Google Colab Authentication...")
# This creates a native Colab popup asking you to allow access
auth.authenticate_user()

# Once you click allow, this grabs your personal credentials!
creds, _ = google.auth.default()

sheets_service = build('sheets', 'v4', credentials=creds)
drive_service = build('drive', 'v3', credentials=creds)

print("✅ Authentication successful!")

# --- 3. STATE & GRAPH NODES ---
class MusicState(TypedDict):
    track_queue: List[Dict[str, Any]]
    current_item: Optional[Dict[str, Any]]
    audio_data_b64: Optional[str]
    file_url: Optional[str]

def fetch_pending_tracks(state: MusicState):
    print("📋 Reading Google Sheet...")
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="A2:E100"
        ).execute()
        rows = result.get('values',[])
    except Exception as e:
        print(f"❌ Error fetching tracks from Google Sheet: {e}")
        raise

    pending =[]
    for idx, row in enumerate(rows):
        title = row[0] if len(row) > 0 else f"Unknown_Track_{idx}"
        prompt = row[1] if len(row) > 1 else ""

        try:
            duration = int(row[2]) if len(row) > 2 else 60000
        except ValueError:
            duration = 60000

        has_url = len(row) > 3 and row[3].strip() != ""

        if not has_url and prompt:
            pending.append({
                "title": title,
                "prompt": prompt,
                "duration": duration,
                "row_index": idx + 2
            })

    print(f"🔍 Found {len(pending)} pending tracks.")
    return {"track_queue": pending}

def generate_music_elevenlabs(state: MusicState):
    item = state["track_queue"][0]
    print(f"\n🎵 Generating music for: '{item['title']}'...")

    url = "https://api.elevenlabs.io/v1/music"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
    payload = {
        "prompt": item["prompt"],
        "music_length_ms": item["duration"],
        "model_id": "music_v1"
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"❌ Error from ElevenLabs: {response.text}")
        response.raise_for_status()

    b64_audio = base64.b64encode(response.content).decode('utf-8')

    return {
        "audio_data_b64": b64_audio,
        "current_item": item,
        "track_queue": state["track_queue"][1:]
    }

def upload_to_google_drive(state: MusicState):
    item = state["current_item"]
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    clean_title = "".join(c for c in item['title'] if c.isalnum() or c in " _-").strip()
    filename = f"song_{clean_title}_{date_str}.mp3"

    print(f"☁️ Uploading '{filename}' to Google Drive...")

    audio_bytes = base64.b64decode(state["audio_data_b64"])

    file_metadata = {'name': filename, 'parents': [DRIVE_FOLDER_ID]}
    media = MediaIoBaseUpload(io.BytesIO(audio_bytes), mimetype='audio/mpeg')

    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()

    # FIX: Changed 'viewer' to 'reader'
    drive_service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()

    file_url = file.get('webViewLink')
    print(f"✅ Uploaded successfully. URL: {file_url}")
    return {"file_url": file_url}

def update_sheet_and_wait(state: MusicState):
    row_idx = state["current_item"]["row_index"]
    print(f"📝 Updating Sheet row {row_idx} with URL...")

    body = {"values": [[state["file_url"]]]}
    sheets_service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"D{row_idx}",
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

    print("⏳ Success. Waiting 60 seconds to respect API limits...\n")
    time.sleep(60)

    return {"audio_data_b64": None, "file_url": None, "current_item": None}

# --- 4. FLOW LOGIC ---
def router(state: MusicState):
    if state.get("track_queue"):
        return "continue"
    return "end"

builder = StateGraph(MusicState)
builder.add_node("fetch", fetch_pending_tracks)
builder.add_node("generate", generate_music_elevenlabs)
builder.add_node("upload", upload_to_google_drive)
builder.add_node("update", update_sheet_and_wait)

builder.set_entry_point("fetch")
builder.add_conditional_edges("fetch", router, {"continue": "generate", "end": END})
builder.add_edge("generate", "upload")
builder.add_edge("upload", "update")
builder.add_conditional_edges("update", router, {"continue": "generate", "end": END})

memory = MemorySaver()
app = builder.compile(checkpointer=memory)

# --- 5. RUN ---
if __name__ == "__main__":
    session_id = f"colab_session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config = {"configurable": {"thread_id": session_id}}

    print("🚀 Starting Music Generation Workflow...")
    app.invoke({"track_queue": []}, config=config)
