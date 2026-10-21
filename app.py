import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Nassau Candy | Route Efficiency", page_icon="🍬", layout="wide")
st.title("🍬 Nassau Candy Distributor")
st.subheader("Factory-to-Customer Shipping Route Efficiency Analysis")
st.caption("Unified Mentor | Data analysis and logistics intelligence dashboard")

DATA_PATH = "nassau_candy_cleaned_working.csv"

@st.cache_data
def load_data():
    d = pd.read_csv(DATA_PATH)
    d["Order Date Parsed"] = pd.to_datetime(d["Order Date Parsed"], errors="coerce")
    d["Ship Date Parsed"] = pd.to_datetime(d["Ship Date Parsed"], errors="coerce")
    return d

try:
    df = load_data()
except Exception as e:
    st.error(f"Could not load {DATA_PATH}. Keep the CSV in the same folder as this app. Details: {e}")
    st.stop()

st.warning(
    "Data-quality limitation: the supplied Order Date and Ship Date fields produce lead times mostly above 900 days. "
    "Do not interpret these as real delivery durations. Lead-time rankings and delay KPIs are marked provisional until "
    "the source dates are verified. The dashboard still supports shipment-volume, sales, profit, factory, state, region "
    "and ship-mode exploration."
)

with st.sidebar:
    st.header("Filters")
    dmin = df["Order Date Parsed"].min().date()
    dmax = df["Order Date Parsed"].max().date()
    date_range = st.date_input("Order date range", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    regions = sorted(df["Region"].dropna().unique().tolist())
    selected_regions = st.multiselect("Region", regions, default=regions)
    states = sorted(df["State/Province"].dropna().unique().tolist())
    selected_states = st.multiselect("State / Province", states, default=states)
    modes = sorted(df["Ship Mode"].dropna().unique().tolist())
    selected_modes = st.multiselect("Ship mode", modes, default=modes)
    factories = sorted(df["Factory"].dropna().unique().tolist())
    selected_factories = st.multiselect("Factory", factories, default=factories)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start, end = df["Order Date Parsed"].min(), df["Order Date Parsed"].max()

f = df[
    df["Order Date Parsed"].between(start, end)
    & df["Region"].isin(selected_regions)
    & df["State/Province"].isin(selected_states)
    & df["Ship Mode"].isin(selected_modes)
    & df["Factory"].isin(selected_factories)
].copy()

if f.empty:
    st.info("No records match the selected filters.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Shipment records", f"{len(f):,}")
c2.metric("Unique orders", f"{f['Order ID'].nunique():,}")
c3.metric("Sales", f"${f['Sales'].sum():,.2f}")
c4.metric("Gross profit", f"${f['Gross Profit'].sum():,.2f}")

st.markdown("### Route Efficiency Overview")
route = (f.groupby(["Factory", "State/Province"], dropna=False)
         .agg(Shipment_Records=("Order ID", "size"),
              Unique_Orders=("Order ID", "nunique"),
              Sales=("Sales", "sum"),
              Gross_Profit=("Gross Profit", "sum"),
              Units=("Units", "sum"),
              Raw_Mean_Lead_Time=("Shipping Lead Time (Days)", "mean"))
         .reset_index())
route["Route"] = route["Factory"].astype(str) + " → " + route["State/Province"].astype(str)
left, right = st.columns(2)
with left:
    st.markdown("**Highest-volume factory → state routes**")
    top = route.sort_values("Shipment_Records", ascending=False).head(10)
    fig = px.bar(top.sort_values("Shipment_Records"), x="Shipment_Records", y="Route", orientation="h",
                 title="Top 10 routes by shipment records", labels={"Shipment_Records":"Shipment records","Route":"Route"})
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.markdown("**Sales by factory**")
    fac = f.groupby("Factory", as_index=False).agg(Sales=("Sales","sum"), Gross_Profit=("Gross Profit","sum"))
    fig = px.bar(fac, x="Factory", y="Sales", title="Sales contribution by factory")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### Ship Mode Comparison")
mode = f.groupby("Ship Mode", as_index=False).agg(
    Shipment_Records=("Order ID","size"), Unique_Orders=("Order ID","nunique"),
    Sales=("Sales","sum"), Gross_Profit=("Gross Profit","sum"),
    Raw_Mean_Lead_Time=("Shipping Lead Time (Days)","mean")
)
a, b = st.columns(2)
with a:
    fig = px.bar(mode, x="Ship Mode", y="Shipment_Records", title="Shipment records by ship mode")
    st.plotly_chart(fig, use_container_width=True)
with b:
    fig = px.bar(mode, x="Ship Mode", y="Gross_Profit", title="Gross profit by ship mode")
    st.plotly_chart(fig, use_container_width=True)
st.dataframe(mode, use_container_width=True, hide_index=True)

st.markdown("### Geographic Shipping Insights")
geo = f.groupby(["State/Province","Region"], as_index=False).agg(
    Shipment_Records=("Order ID","size"), Sales=("Sales","sum"), Gross_Profit=("Gross Profit","sum")
)
fig = px.treemap(geo, path=["Region","State/Province"], values="Shipment_Records",
                 color="Shipment_Records", title="Shipment volume by region and state")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Route Drill-Down")
chosen_route = st.selectbox("Select route", sorted(route["Route"].unique()))
route_orders = f[(f["Factory"].astype(str) + " → " + f["State/Province"].astype(str)) == chosen_route]
st.write(f"**Records:** {len(route_orders):,} | **Unique orders:** {route_orders['Order ID'].nunique():,} | "
         f"**Sales:** ${route_orders['Sales'].sum():,.2f} | **Gross profit:** ${route_orders['Gross Profit'].sum():,.2f}")
st.dataframe(route_orders[["Order ID","Order Date","Ship Date","Ship Mode","Factory","City","State/Province",
                           "Region","Product Name","Sales","Units","Gross Profit","Shipping Lead Time (Days)","Date Quality Flag"]],
             use_container_width=True, hide_index=True)

st.markdown("### Date Quality Audit")
audit = f["Date Quality Flag"].value_counts().rename_axis("Date Quality Flag").reset_index(name="Records")
fig = px.bar(audit, x="Date Quality Flag", y="Records", title="Lead-time validity classification")
st.plotly_chart(fig, use_container_width=True)
st.dataframe(audit, use_container_width=True, hide_index=True)

st.markdown("### Interpretation")
st.write(
    "Route volume and commercial performance can be compared with this dataset. The raw date-derived lead time is not "
    "reliable enough to identify the fastest/slowest routes because the source date ranges are inconsistent. Verify the "
    "original data source before making delay, delivery-speed or cost-time trade-off claims."
)
st.download_button("Download filtered data as CSV", data=f.to_csv(index=False).encode("utf-8"),
                   file_name="nassau_filtered_data.csv", mime="text/csv")
