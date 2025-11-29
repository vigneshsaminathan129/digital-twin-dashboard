from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import os

app = FastAPI()

# Allow all CORS (for UI access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Sheet Config
SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SHEET_ID = "1Kjo-jfEYdPc_KFoCa4kL_UtBrochTiBLFFYiPQ88lio"
RANGE = "'Copy of No CGM >2D - Vig, Vin'!A1:BJ300"


# -------------------------------------------------------
# Fetch Google Sheet data (Render-safe)
# -------------------------------------------------------
def fetch_sheet():
    print(">>> Loading Google credentials...")

    creds_path = os.path.join(os.getcwd(), "credentials.json")

    if not os.path.exists(creds_path):
        raise FileNotFoundError("credentials.json not found on Render!")

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        creds_path, SCOPE
    )

    service = build("sheets", "v4", credentials=credentials)

    print(">>> Fetching Google Sheet...")

    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=RANGE
    ).execute()

    rows = result.get("values", [])
    df = pd.DataFrame(rows)
    print(">>> Sheet loaded successfully.")
    return df


# -------------------------------------------------------
# Return Member List
# -------------------------------------------------------
@app.get("/members")
def get_members():
    df = fetch_sheet()
    member_ids = df[1].tolist()[1:]   # Column B contains MEMBER_ID
    return {"members": member_ids}


# -------------------------------------------------------
# Summary Builder
# -------------------------------------------------------
def build_summary(m):
    return f"""
Your Digital Twin shows moderate engagement, with {m['meal_log']} meal logging and {m['gfy']} GFY, {m['steps']} step consistency.
Sleep visibility is {m['sleep']} hours, protein {m['protein']}% and fiber {m['fiber']}%.

Your clinical data shows:
• HbA1c: {m['start_hba1c']} ➝ {m['latest_ea1c']}
• Weight: {m['start_weight']} ➝ {m['latest_weight']} lbs
• BMI: {m['start_bmi']} ➝ {m['latest_bmi']}
• Visceral Fat: {m['start_vfat']} ➝ {m['latest_vfat']}
• BP: {m['start_bp']} ➝ {m['latest_bp']}

You are supported with: {m['medicine']}

Keep logging meals, improving protein/fiber intake, maintaining step consistency, 
and using your sensors regularly. Your Digital Twin can only heal what it can see.
""".strip()


# -------------------------------------------------------
# Main Dashboard Endpoint
# -------------------------------------------------------
@app.get("/dashboard/{member_id}")
def dashboard(member_id: str):
    df = fetch_sheet()

    match = df[df[1] == member_id]

    if match.empty:
        return {"error": f"Member ID {member_id} not found."}

    r = match.index[0]

    # SAFELY handle missing columns
    def safe(df, row, col, default="0"):
        try:
            return df.iloc[row][col]
        except:
            return default

    metrics = {
        "meal_log": safe(df, r, 11),
        "gfy": safe(df, r, 12),
        "steps": safe(df, r, 37),
        "sleep": safe(df, r, 41),

        "protein": safe(df, r, 54),
        "fiber": safe(df, r, 53),

        "start_hba1c": safe(df, r, 15),
        "latest_ea1c": safe(df, r, 19),

        "start_weight": safe(df, r, 21),
        "latest_weight": safe(df, r, 23),

        "start_bmi": safe(df, r, 27),
        "latest_bmi": safe(df, r, 28),

        "start_vfat": safe(df, r, 59),
        "latest_vfat": safe(df, r, 60),

        "start_bp": f"{safe(df, r, 30)} / {safe(df, r, 32)}",
        "latest_bp": f"{safe(df, r, 31)} / {safe(df, r, 33)}",

        "medicine": safe(df, r, 52),
    }

    summary = build_summary(metrics)

    return {"metrics": metrics, "summary": summary}
