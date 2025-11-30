from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# Google Sheet configuration
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Kjo-jfEYdPc_KFoCa4kL_UtBrochTiBLFFYiPQ88lio/edit?usp=sharing"
WORKSHEET_NAME = "Copy of No CGM >2D - Vig, Vin"


def fetch_sheet():
    try:
        print("STEP 1: Loading credentials.json...")
        creds = Credentials.from_service_account_file("credentials.json", scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])

        print("STEP 2: Authorizing client...")
        gc = gspread.authorize(creds)

        print("STEP 3: Opening Google Sheet URL...")
        sh = gc.open_by_url(SHEET_URL)

        print("STEP 4: Opening worksheet...")
        ws = sh.worksheet(WORKSHEET_NAME)

        print("STEP 5: Reading data...")
        data = ws.get_all_values()

        df = pd.DataFrame(data)
        df.columns = df.iloc[0]  # Header
        df = df[1:]

        print("SUCCESS: Sheet loaded.")
        return df

    except Exception as e:
        print("🔥 GOOGLE SHEET ERROR:", e)
        return None

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/coaches")
def get_coaches():
    df = fetch_sheet()

    if df is None:
        return JSONResponse({"error": "Failed to load Google Sheet"}, status_code=500)

    if "Coach" not in df.columns:
        return {"error": "Column 'Coach' not found"}

    coaches = sorted(list(df["Coach"].dropna().unique()))
    return {"coaches": coaches}

