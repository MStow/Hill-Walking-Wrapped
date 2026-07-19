"""
Hiking Club Stats App
----------------------
A Streamlit app that lets club members look up their own hiking stats.
Data is pulled live from a single Google Sheet with three tabs:
  1. "Individual Stats"    -- one row per person: attendance, distance, height gain
  2. "Award Leaderboards"  -- five side-by-side ranked lists (one per stat)
  3. "Leader Stats"        -- lead-type & route-grade breakdown, leaders only

No login required -- members just pick their name from a dropdown.
"""

import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ULtkN0Qw14pdg_LvVU9GB4P2hGu8Sxbdl1jAwDH60ro/edit?usp=sharing"

INDIVIDUAL_WS_NAME = "Individual Stats"
LEADERBOARD_WS_NAME = "Award Leaderboards"
LEADER_WS_NAME = "Leader Stats"

# Row/column layout of "Award Leaderboards" -- five Name/Value column pairs,
# side by side, with metadata in rows 1-3, headers in row 4, data from row 5.
# Column positions are 0-indexed (A=0, B=1, C=2, ...).
LEADERBOARD_DATA_START_ROW = 4  # 0-indexed row where data begins (row 5 in-sheet)
LEADERBOARD_CATEGORIES = [
    # (display label, name_column_index, value_column_index)
    ("Attendance Count", 1, 2),
    ("Total Distance", 3, 4),
    ("Total Height Gain", 5, 6),
    ("Mean Distance", 7, 8),
    ("Mean Height Gain", 9, 10),
]

# "Leader Stats" has a two-row header: row 1 has group labels ("Lead types",
# "Route grades"), row 2 has the actual sub-headers. Data starts row 3.
LEADER_HEADER_ROW = 1  # 0-indexed row with actual column names (row 2 in-sheet)
LEADER_DATA_START_ROW = 2  # 0-indexed row where data begins (row 3 in-sheet)
LEADER_NAME_COLUMN = "Leader Name"

# Columns from "Leader Stats" to show as pie charts
LEAD_TYPE_PIE_COLUMNS = ["Solo-lead", "Co-lead"]
ROUTE_TYPE_PIE_COLUMNS = [
    "Nav Course", "Green", "Yellow", "Red", "Technical Winter", "Expedition", "Fell Run",
]

# Colors for the route-type pie chart, matching each grade's real-world color.
# Route types without an obvious color get a distinct fallback color.
ROUTE_TYPE_COLORS = {
    "Green": "#2ca02c",
    "Yellow": "#f2c318",
    "Red": "#d62728",
    "D. Red": "#8b0000",
    "Nav Course": "#1f77b4",
    "Technical Winter": "#7fdbff",
    "Expedition": "#9467bd",
    "Fell Run": "#ff7f0e",
}

CACHE_TTL_SECONDS = 300  # re-pull from Google Sheets every 5 minutes

# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

@st.cache_resource
def get_gspread_client():
    """Authenticate once using a Google service account (see README)."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_individual_stats() -> pd.DataFrame:
    client = get_gspread_client()
    ws = client.open_by_url(SPREADSHEET_URL).worksheet(INDIVIDUAL_WS_NAME)
    records = ws.get_all_records()  # single clean header row -- easy case
    return pd.DataFrame(records)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_leaderboard_raw() -> list:
    """Return the raw grid (list of rows) for the leaderboard sheet."""
    client = get_gspread_client()
    ws = client.open_by_url(SPREADSHEET_URL).worksheet(LEADERBOARD_WS_NAME)
    return ws.get_all_values()


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_leader_stats() -> pd.DataFrame:
    client = get_gspread_client()
    ws = client.open_by_url(SPREADSHEET_URL).worksheet(LEADER_WS_NAME)
    values = ws.get_all_values()
    headers = [LEADER_NAME_COLUMN] + values[LEADER_HEADER_ROW][1:]
    data_rows = values[LEADER_DATA_START_ROW:]
    df = pd.DataFrame(data_rows, columns=headers)
    df = df[df[LEADER_NAME_COLUMN].astype(str).str.strip() != ""]
    return df


def find_row(df: pd.DataFrame, name_column: str, name: str) -> pd.DataFrame:
    if name_column not in df.columns:
        return pd.DataFrame()
    return df[df[name_column].astype(str).str.strip().str.lower() == name.strip().lower()]


def find_leaderboard_positions(raw_grid: list, name: str) -> list:
    """
    For each leaderboard category, scan its Name column top-to-bottom and
    report this person's rank (their position in that sorted column) and
    value, if they appear.
    """
    results = []
    data_rows = raw_grid[LEADERBOARD_DATA_START_ROW:]
    for label, name_col, value_col in LEADERBOARD_CATEGORIES:
        rank = None
        value = None
        position = 0
        for row in data_rows:
            if name_col >= len(row) or not row[name_col]:
                continue
            position += 1
            if row[name_col].strip().lower() == name.strip().lower():
                rank = position
                value = row[value_col] if value_col < len(row) else None
                break
        if rank is not None:
            results.append({"label": label, "rank": rank, "value": value})
    return results


def make_pie_chart(row: pd.Series, columns: list, title: str, color_map: dict = None):
    """Build a Plotly pie chart from selected columns of a row, skipping zeros.
    If color_map is given, slices use those colors (matching by label);
    any label not in color_map falls back to Plotly's default palette.
    """
    labels, values = [], []
    for col in columns:
        if col not in row.index:
            continue
        try:
            val = float(row[col])
        except (ValueError, TypeError):
            val = 0
        if val > 0:
            labels.append(col)
            values.append(val)
    if not values:
        return None
    fig = px.pie(
        names=labels,
        values=values,
        title=title,
        color=labels if color_map else None,
        color_discrete_map=color_map,
    )
    fig.update_traces(textinfo="label+value")
    return fig


# ---------------------------------------------------------------------------
# APP
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Hiking Club Stats", page_icon="🥾", layout="centered")
st.title("DUHWS Hill Walking Wrapped")
st.caption("Find your personal hiking stats for 2025/2026 below")

try:
    individual_df = load_individual_stats()
    leaderboard_raw = load_leaderboard_raw()
    leader_df = load_leader_stats()
except Exception as e:
    st.error(
        "Couldn't load data from Google Sheets. Double-check the spreadsheet URL, "
        "tab names, and that the service account has viewer access.\n\n"
        f"Details: {e}"
    )
    st.stop()

if "Name" not in individual_df.columns:
    st.error(f'Column "Name" not found in Individual Stats. '
              f"Available columns: {list(individual_df.columns)}")
    st.stop()

names = sorted(individual_df["Name"].dropna().astype(str).unique())
selected_name = st.selectbox("Select your name", options=["-- choose your name --"] + names)

if selected_name and selected_name != "-- choose your name --":
    st.divider()
    st.subheader(f"Stats for {selected_name}")

    # --- Individual Stats ---
    row = find_row(individual_df, "Name", selected_name)
    if row.empty:
        st.warning("Couldn't find your stats. Contact the club organiser if this looks wrong.")
    else:
        r = row.iloc[0]
        stats_display = pd.DataFrame({"Stat": r.index, "Value": r.values})
        stats_display = stats_display[stats_display["Stat"] != "Name"]
        st.table(stats_display.set_index("Stat"))

    # --- Leaderboard positions ---
    st.subheader("🏆 Leaderboard Rankings")
    positions = find_leaderboard_positions(leaderboard_raw, selected_name)
    if positions:
        board_display = pd.DataFrame([
            {"Category": p["label"], "Rank": p["rank"], "Value": p["value"]}
            for p in positions
        ])
        st.table(board_display.set_index("Category"))
    else:
        st.info("Not currently placed on any leaderboard — keep hiking!")

    # --- Leader Stats (only if they're a leader) ---
    leader_row = find_row(leader_df, LEADER_NAME_COLUMN, selected_name)
    if not leader_row.empty:
        st.subheader("🧭 Leader Stats")
        r = leader_row.iloc[0]
        leader_display = pd.DataFrame({"Stat": r.index, "Value": r.values})
        leader_display = leader_display[leader_display["Stat"] != LEADER_NAME_COLUMN]
        # Drop stats that are zero across the board for readability
        leader_display = leader_display[leader_display["Value"].astype(str) != "0"]
        st.table(leader_display.set_index("Stat"))

        col1, col2 = st.columns(2)
        with col1:
            lead_type_fig = make_pie_chart(r, LEAD_TYPE_PIE_COLUMNS, "Lead Type")
            if lead_type_fig:
                st.plotly_chart(lead_type_fig, use_container_width=True)
            else:
                st.caption("No solo/co-lead data yet.")
        with col2:
            route_type_fig = make_pie_chart(
                r, ROUTE_TYPE_PIE_COLUMNS, "Route Type", color_map=ROUTE_TYPE_COLORS
            )
            if route_type_fig:
                st.plotly_chart(route_type_fig, use_container_width=True)
            else:
                st.caption("No route-type data yet.")

st.divider()
st.caption("Built for the club — data pulled live from Google Sheets.")
