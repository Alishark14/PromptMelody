# 🎵 PromptMelody: Autonomous AI Music Pipeline

An autonomous, stateful AI agent that manages the end-to-end production of AI-generated music. Built with **LangGraph**, it acts as an asynchronous pipeline that reads prompts from a Google Sheet, generates high-fidelity audio via the **ElevenLabs API**, stores the `.mp3` files securely in **Google Drive**, and updates the database with shareable links.

## 🧠 Why this architecture?
Instead of a simple linear script, this project uses **LangGraph** to construct a resilient, stateful workflow. 
- **Cost-Efficient & Idempotent:** By using Google Sheets as the system's "memory", the agent knows which tracks are already completed. If the workflow drops or new prompts are added, it picks up exactly where it left off without duplicating API calls.
- **Human-in-the-Loop Ready:** The graph architecture allows for easy pauses, rate-limit handling, and batch processing.
- **Secure Auth:** Implements OAuth 2.0 desktop flow for secure, delegated access to Google Workspace.

## 🛠️ Tech Stack
- **Orchestration:** LangGraph / Python
- **Generative AI:** ElevenLabs Music API
- **Database & Storage:** Google Sheets API, Google Drive API
- **Authentication:** Google OAuth 2.0 (`google-auth-oauthlib`)

## 🚀 How it Works
1. **Fetch:** The agent scans the Google Sheet for rows containing prompts but missing a URL.
2. **Generate:** Sends the prompt and duration parameters to ElevenLabs to generate the audio bytes.
3. **Store:** Decodes the Base64 audio, uploads the `.mp3` to Google Drive, and configures public reader permissions.
4. **Update:** Writes the generated Google Drive URL back to the specific row in the Google Sheet.
5. **Loop/End:** Respects API rate limits by pausing, then routes to the next pending track or ends the graph execution.

## 📋 Setup & Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/your-username/PromptMelody.git
   cd PromptMelody
2. Install dependencies:
   ```bash
    pip install -r requirements.txt
3. Set up your Google Cloud Project (Enable Sheets & Drive APIs) and download your OAuth 2.0 credentials.json to the project directory.
4. Set your ElevenLabs API Key as an environment variable:
   ```bash
    export ELEVENLABS_API_KEY="your_api_key_here"
5. Update the SPREADSHEET_ID and DRIVE_FOLDER_ID in main.py.
Run the agent:
  ```bash
    python main.py
