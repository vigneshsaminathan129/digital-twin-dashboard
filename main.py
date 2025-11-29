from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

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
# FETCH GOOGLE SHEET
# -------------------------------------------------------
def fetch_sheet():
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", SCOPE
    )
    service = build("sheets", "v4", credentials=credentials)

    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=RANGE
    ).execute()

    rows = result.get("values", [])
    df = pd.DataFrame(rows)
    return df


# -------------------------------------------------------
# NEW ENDPOINT — RETURN LIST OF MEMBER IDs
# -------------------------------------------------------
@app.get("/members")
def get_members():
    df = fetch_sheet()
    member_ids = df[1].tolist()[1:]   # Column B contains MEMBER_ID
    return {"members": member_ids}


# -------------------------------------------------------
# SUMMARY BUILDER
# -------------------------------------------------------
def build_summary(m):
    return f"""
Your Digital Twin shows moderate engagement, with {m['meal_log']} meal logging and {m['gfy']} GFY, {m['steps']} step consistency.
Sleep visibility is {m['sleep']} hours, protein {m['protein']}%, and fiber {m['fiber']}%, which limits your Twin’s ability
to understand recovery patterns and how your meals support blood sugar stability.

Your clinical data shows that your starting HbA1c was {m['start_hba1c']}%, and your latest eA1c is {m['latest_ea1c']}%.
Your weight changed from {m['start_weight']} ➝ {m['latest_weight']} lbs and your BMI improved from {m['start_bmi']} ➝ {m['latest_bmi']}.
Visceral fat changed from {m['start_vfat']} ➝ {m['latest_vfat']}. Your blood pressure changed from {m['start_bp']} ➝ {m['latest_bp']}.

You are currently supported with {m['medicine']}, which provides temporary support while your metabolism continues healing.
Long-term improvement depends on strengthening meal consistency, improving protein and fiber habits, and ensuring full visibility.

To accelerate your progress, continue logging meals, increase protein and fiber daily, maintain strong step consistency,
and track sleep so your Twin can guide you with precision.

Your Digital Twin can only heal what it can see. With consistent engagement, your Twin will guide you toward
deeper metabolic healing and long-term stability.
""".strip()


# -------------------------------------------------------
# MAIN ENDPOINT — RETURN MEMBER DASHBOARD DATA
# -------------------------------------------------------
@app.get("/dashboard/{member_id}")
def dashboard(member_id: str):
    df = fetch_sheet()

    # Find the row matching the Member ID (Column B = index 1)
    matched_rows = df[df[1] == member_id]

    if matched_rows.empty:
        return {"error": f"Member ID {member_id} not found."}

    r = matched_rows.index[0]

    metrics = {
        "meal_log": df.iloc[r][11],
        "gfy": df.iloc[r][12],
        "steps": df.iloc[r][37],
        "sleep": df.iloc[r][41],

        "protein": df.iloc[r][54] if len(df.columns) > 54 else "0",
        "fiber": df.iloc[r][53] if len(df.columns) > 53 else "0",

        "start_hba1c": df.iloc[r][15],
        "latest_ea1c": df.iloc[r][19],

        "start_weight": df.iloc[r][21],
        "latest_weight": df.iloc[r][23],

        "start_bmi": df.iloc[r][27],
        "latest_bmi": df.iloc[r][28],

        "start_vfat": df.iloc[r][59],
        "latest_vfat": df.iloc[r][60],

        "start_bp": f"{df.iloc[r][30]} / {df.iloc[r][32]}",
        "latest_bp": f"{df.iloc[r][31]} / {df.iloc[r][33]}",

        "medicine": df.iloc[r][52],
    }

    summary = build_summary(metrics)

    return {"metrics": metrics, "summary": summary}
