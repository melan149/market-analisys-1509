import streamlit as st
import pandas as pd
from PIL import Image
import io

# Streamlit app: Market Analysis Competitor Comparison
# Expects a data file named "Data_Market analysis_2025_9.xlsx" or ".csv" in the same folder
# Expects an "images/" folder containing country flags and brand logos referenced in the data file.

st.set_page_config(layout="wide")

@st.cache_data
def load_data(path_xlsx="Data_Market analysis_2025_9.xlsx", path_csv="Data_Market analysis_2025_9.csv"):
    # Try Excel first, then CSV
    try:
        df = pd.read_excel(path_xlsx, engine="openpyxl")
        return df
    except Exception:
        try:
            df = pd.read_csv(path_csv)
            return df
        except Exception as e:
            st.error(f"Could not load data. Make sure '{path_xlsx}' or '{path_csv}' exists. Error: {e}")
            return pd.DataFrame()


def get_col(df, options):
    for o in options:
        if o in df.columns:
            return o
    return None

# Load dataframe
df = load_data()
if df.empty:
    st.stop()

# Map expected column names (as described by the user)
col_quarter = get_col(df, ["Quarter", "quarter"])
col_year = get_col(df, ["Year", "year"])
col_region = get_col(df, ["Region", "region"])
col_country = get_col(df, ["Country", "country"])
col_country_flag = get_col(df, ["Country Flag", "Country_Flag", "country_flag", "CountryFlag"])
col_brand = get_col(df, ["Brand name", "Brand", "brand name", "brand"])
col_brand_logo = get_col(df, ["Brand logo", "Brand_logo", "brand_logo", "BrandLogo"])

# The rest of the columns to display (order preserved). We will remove the ones shown separately above.
preserve_cols = [col_quarter, col_year, col_region, col_country, col_country_flag, col_brand, col_brand_logo]
remaining_cols = [c for c in df.columns if c not in (preserve_cols if preserve_cols else [])]

# --- Sidebar: selection controls ---
st.sidebar.title("Comparison selector")
num_comp = st.sidebar.slider("Number of competitors to compare", min_value=2, max_value=10, value=3)

# Shared dropdowns for filtering the universe (optional global filters)
st.sidebar.markdown("---")
unique_years = sorted(df[col_year].dropna().unique()) if col_year else []
unique_quarters = sorted(df[col_quarter].dropna().unique()) if col_quarter else []
unique_regions = sorted(df[col_region].dropna().unique()) if col_region else []
unique_countries = sorted(df[col_country].dropna().unique()) if col_country else []

# Allow global narrowing to reduce lists
global_year = st.sidebar.selectbox("Global: Year (optional)", options=["(all)"] + unique_years, index=0)
if global_year != "(all)":
    df = df[df[col_year] == global_year]
    # recompute dependent lists
    unique_quarters = sorted(df[col_quarter].dropna().unique()) if col_quarter else []
    unique_regions = sorted(df[col_region].dropna().unique()) if col_region else []
    unique_countries = sorted(df[col_country].dropna().unique()) if col_country else []

global_quarter = st.sidebar.selectbox("Global: Quarter (optional)", options=["(all)"] + unique_quarters, index=0)
if global_quarter != "(all)":
    df = df[df[col_quarter] == global_quarter]
    unique_regions = sorted(df[col_region].dropna().unique()) if col_region else []
    unique_countries = sorted(df[col_country].dropna().unique()) if col_country else []

global_region = st.sidebar.selectbox("Global: Region (optional)", options=["(all)"] + unique_regions, index=0)
if global_region != "(all)":
    df = df[df[col_region] == global_region]
    unique_countries = sorted(df[col_country].dropna().unique()) if col_country else []

st.sidebar.markdown("---")

# For each competitor create selection boxes: Country -> Brand -> (optionally other unique id if present)
selections = []
for i in range(num_comp):
    st.sidebar.markdown(f"**Competitor {i+1}**")
    # Country
    country_opts = ["(choose)"] + (sorted(df[col_country].dropna().unique()) if col_country else [])
    sel_country = st.sidebar.selectbox(f"Country #{i+1}", options=country_opts, key=f"country_{i}")

    # Filter df by chosen country for brand choices
    df_for_brand = df.copy()
    if sel_country != "(choose)":
        df_for_brand = df_for_brand[df_for_brand[col_country] == sel_country]

    brand_opts = ["(choose)"] + (sorted(df_for_brand[col_brand].dropna().unique()) if col_brand else [])
    sel_brand = st.sidebar.selectbox(f"Brand #{i+1}", options=brand_opts, key=f"brand_{i}")

    # Also allow selecting Year/Quarter per competitor if the dataset has multiple rows per brand
    sel_year = None
    sel_quarter = None
    if col_year:
        year_opts = ["(any)"] + sorted(df_for_brand[col_year].dropna().unique())
        sel_year = st.sidebar.selectbox(f"Year #{i+1}", options=year_opts, key=f"year_{i}")
        if sel_year != "(any)":
            df_for_brand = df_for_brand[df_for_brand[col_year] == sel_year]
    if col_quarter:
        q_opts = ["(any)"] + sorted(df_for_brand[col_quarter].dropna().unique())
        sel_quarter = st.sidebar.selectbox(f"Quarter #{i+1}", options=q_opts, key=f"quarter_{i}")
        if sel_quarter != "(any)":
            df_for_brand = df_for_brand[df_for_brand[col_quarter] == sel_quarter]

    # Attempt to pick a single row: if multiple remain, pick the first and warn in main area
    chosen_row = pd.DataFrame()
    if sel_brand != "(choose)":
        subset = df_for_brand[df_for_brand[col_brand] == sel_brand]
        if not subset.empty:
            chosen_row = subset.iloc[[0]]

    selections.append({
        "country": sel_country,
        "brand": sel_brand,
        "year": sel_year,
        "quarter": sel_quarter,
        "row": chosen_row
    })
    st.sidebar.markdown("---")

# --- Main comparison area ---
st.title("Market Analysis — Competitor Comparison")

# Validate that at least two valid selections were made
valid_rows = [s for s in selections if not s['row'].empty]
if len(valid_rows) < 2:
    st.warning("Please select at least two competitors (Country + Brand) to compare.")
    st.stop()

# Prepare header with brand logos and flags
cols = st.columns(len(selections))
for i, s in enumerate(selections):
    with cols[i]:
        if s['brand'] != "(choose)":
            st.markdown(f"**{s['brand']}**")
        if not s['row'].empty and col_brand_logo and pd.notna(s['row'].iat[0, s['row'].columns.get_loc(col_brand_logo)]):
            logo_path = s['row'].iat[0, s['row'].columns.get_loc(col_brand_logo)]
            try:
                img = Image.open(f"images/{logo_path}")
                st.image(img, caption=f"{s['brand']} logo", use_container_width=True)
            except Exception:
                st.write("(logo not found)")
        # Country + flag
        if s['country'] != "(choose)":
            st.write(s['country'])
            if not s['row'].empty and col_country_flag and pd.notna(s['row'].iat[0, s['row'].columns.get_loc(col_country_flag)]):
                flag_path = s['row'].iat[0, s['row'].columns.get_loc(col_country_flag)]
                try:
                    fimg = Image.open(f"images/{flag_path}")
                    st.image(fimg, width=60)
                except Exception:
                    st.write("(flag not found)")

# --- Build comparison table: first rows Country, Country Flag, Brand, Brand logo, then all remaining cols ---
st.subheader("Comparison table")
# Column header
table_cols = st.columns([2] + [len(selections)] * len(selections))
with table_cols[0]:
    st.markdown("**Parameter**")
for i, s in enumerate(selections):
    with table_cols[i + 1]:
        name = s['brand'] if s['brand'] != "(choose)" else f"Competitor {i+1}"
        st.markdown(f"**{name}**")

# Helper to get value or '-'
def get_val(s, col_name):
    row = s['row']
    if row.empty or col_name not in row.columns:
        return "-"
    v = row.iloc[0][col_name]
    return v if pd.notna(v) else "-"

# Ordered parameters
ordered_params = []
# First Country
if col_country:
    ordered_params.append((col_country, "Country"))
# Country Flag
if col_country_flag:
    ordered_params.append((col_country_flag, "Country Flag"))
# Brand name
if col_brand:
    ordered_params.append((col_brand, "Brand"))
# Brand logo
if col_brand_logo:
    ordered_params.append((col_brand_logo, "Brand logo"))

# Then the rest
for c in remaining_cols:
    ordered_params.append((c, c))

# Render rows
for col_name, display_name in ordered_params:
    row_cols = st.columns([2] + [len(selections)] * len(selections))
    with row_cols[0]:
        st.markdown(f"**{display_name}**")
    for i, s in enumerate(selections):
        with row_cols[i + 1]:
            if col_name == col_country_flag or col_name == col_brand_logo:
                # show image if possible
                val = get_val(s, col_name)
                if val != "-":
                    try:
                        img = Image.open(f"images/{val}")
                        st.image(img, width=120, use_container_width=True)
                    except Exception:
                        st.write(val)
                else:
                    st.write("-")
            else:
                st.write(get_val(s, col_name))

# --- CSV download of comparison ---
st.markdown("---")
export_df = pd.DataFrame()
for i, s in enumerate(selections):
    label = s['brand'] if s['brand'] != "(choose)" else f"Competitor_{i+1}"
    if not s['row'].empty:
        row_flat = s['row'].copy()
        row_flat.columns = [f"{label} - {c}" for c in row_flat.columns]
        export_df = pd.concat([export_df, row_flat.reset_index(drop=True)], axis=1)

csv_bytes = export_df.to_csv(index=False).encode('utf-8')
st.download_button("Download comparison CSV", data=csv_bytes, file_name="market_comparison.csv", mime="text/csv")

st.caption("App built to use 'Data_Market analysis_2025_9' dataset and an images/ folder with flags and logos.")
