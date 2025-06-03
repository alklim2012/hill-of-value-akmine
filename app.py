import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(layout="wide")
st.title("NPVision – Strategic Scenario Tool")

# --- File Uploads ---
gtc_file = st.sidebar.file_uploader("Upload Grade-Tonnage Curve (CSV)", type="csv")
capex_curve_file = st.sidebar.file_uploader("Upload CAPEX vs Production (CSV)", type="csv")

# --- Parameter Inputs ---
st.sidebar.header("Input Parameters")
cutoff_range = st.sidebar.slider("Cut-off Grade Range (%)", 0.1, 2.0, (0.2, 1.0), 0.1)
prod_range = st.sidebar.slider("Production Range (Mtpa)", 0.5, 10.0, (2.0, 6.0), 0.5)
metal_price_mean = st.sidebar.number_input("Metal Price (mean $/t)", value=4000)
metal_price_std = st.sidebar.number_input("Price Std Dev", value=500)
recovery_mean = st.sidebar.number_input("Recovery (mean %)", value=85)
recovery_std = st.sidebar.number_input("Recovery Std Dev", value=5)
opex = st.sidebar.number_input("OPEX ($/t)", value=40)
discount_rate = st.sidebar.number_input("Discount Rate (%)", value=8.0)

# --- Optional Curve Loaders ---
use_curve = False
if gtc_file:
    gtc_df = pd.read_csv(gtc_file)
    use_curve = True

def grade_tonnage_curve(cutoff):
    if use_curve:
        nearest = gtc_df.iloc[(gtc_df['Cutoff'] - cutoff).abs().argsort()[:1]]
        return float(nearest['Tonnage']), float(nearest['Grade'])
    else:
        a = 500
        b = 0.7
        tonnage = a * (cutoff ** -b)
        grade = np.maximum(1.5 - cutoff * 0.5, 0.2)
        return tonnage, grade

capex_df = None
def estimate_capex(production):
    if capex_curve_file:
        global capex_df
        capex_df = pd.read_csv(capex_curve_file)
        row = capex_df.iloc[(capex_df['Production'] - production).abs().argsort()[:1]]
        return float(row['CAPEX'])
    return 1000 + 150 * production

def estimate_capex_schedule(total_capex, years):
    return [total_capex / 2 if t < 2 else 0 for t in range(int(np.ceil(years)))]

def calculate_npv(tonnage, grade, price, recovery, opex, production, discount_rate):
    metal_content = tonnage * grade / 100
    revenue = metal_content * recovery / 100 * price
    years = tonnage / production
    annual_cashflow = (revenue - opex * tonnage) / years
    capex = estimate_capex(production)
    capex_schedule = estimate_capex_schedule(capex, years)
    cashflows = [annual_cashflow] * int(np.ceil(years))
    npv = sum([(cashflows[t] - capex_schedule[t]) / ((1 + discount_rate / 100) ** (t + 1)) for t in range(len(cashflows))])
    return npv, years, capex

# Scenario Generation
cutoff_vals = np.arange(cutoff_range[0], cutoff_range[1] + 0.001, 0.1)
prod_vals = np.arange(prod_range[0], prod_range[1] + 0.001, 0.5)

scenarios = []
for cutoff in cutoff_vals:
    for prod in prod_vals:
        npvs, years_list, capex_list = [], [], []
        for _ in range(100):
            price = np.random.normal(metal_price_mean, metal_price_std)
            recovery = np.random.normal(recovery_mean, recovery_std)
            tonnage, grade = grade_tonnage_curve(cutoff)
            npv, yrs, capex_val = calculate_npv(tonnage, grade, price, recovery, opex, prod, discount_rate)
            npvs.append(npv)
            years_list.append(yrs)
            capex_list.append(capex_val)
        scenarios.append({"Cutoff": cutoff, "Production": prod, "Avg NPV": np.mean(npvs), "Avg Life": np.mean(years_list), "CAPEX": np.mean(capex_list)})

result_df = pd.DataFrame(scenarios)
st.dataframe(result_df, use_container_width=True, height=300)

# 3D Surface Plot
z_data = result_df.pivot_table(index='Cutoff', columns='Production', values='Avg NPV').values
fig3 = go.Figure(data=[
    go.Surface(
        z=z_data,
        x=prod_vals,
        y=cutoff_vals,
        colorscale='Viridis',
        hovertemplate="<b>Cutoff</b>: %{y}<br><b>Production</b>: %{x}<br><b>NPV</b>: %{z:.2f}M",
        showscale=True
    )
])
fig3.update_layout(
    title="Hill of Value – 3D Surface", autosize=False,
    width=1000, height=700,
    scene=dict(
        xaxis_title='Production (Mtpa)',
        yaxis_title='Cut-off Grade (%)',
        zaxis_title='Avg NPV ($M)',
        camera_eye=dict(x=1.3, y=1.3, z=0.6)
    )
)
st.plotly_chart(fig3, use_container_width=True)

# Download section
st.download_button("Download Scenarios CSV", data=result_df.to_csv(index=False), file_name="hill_scenarios.csv", mime="text/csv")

# Optional edit tables
if capex_df is not None:
    st.subheader("Edit CAPEX vs Production")
    edited_df = st.data_editor(capex_df, num_rows="dynamic")
    st.write("Updated CAPEX table:")
    st.dataframe(edited_df)
