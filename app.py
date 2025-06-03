# Streamlit Hill of Value App with UI and Smooth 3D Plot

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Sidebar input
st.sidebar.title("Input Parameters")
cutoff_range = st.sidebar.slider("Cutoff Range (%)", 0.1, 2.0, (0.2, 1.0), step=0.1)
prod_range = st.sidebar.slider("Production Range (Mtpa)", 0.5, 10.0, (2.0, 6.0), step=0.5)
metal_price_mean = st.sidebar.number_input("Metal Price Mean ($/t)", 1000, 10000, 4000)
metal_price_std = st.sidebar.number_input("Metal Price Std Dev ($/t)", 0, 5000, 500)
recovery_mean = st.sidebar.number_input("Recovery Mean (%)", 10, 100, 85)
recovery_std = st.sidebar.number_input("Recovery Std Dev (%)", 0, 20, 5)
discount_rate = st.sidebar.number_input("Discount Rate (%)", 1, 30, 8)
opex = st.sidebar.number_input("OPEX ($/t)", 1, 200, 40)
uploaded_file = st.sidebar.file_uploader("Upload Grade-Tonnage Curve CSV", type=["csv"])

use_curve = uploaded_file is not None
if use_curve:
    user_curve = pd.read_csv(uploaded_file)

def grade_tonnage_curve(cutoff):
    if use_curve:
        nearest = user_curve.iloc[(user_curve['Cutoff'] - cutoff).abs().argsort()[:1]]
        return float(nearest['Tonnage']), float(nearest['Grade'])
    else:
        a = 500
        b = 0.7
        tonnage = a * (cutoff ** -b)
        grade = np.maximum(1.5 - cutoff * 0.5, 0.2)
        return tonnage, grade

def estimate_capex_schedule(total_capex, years):
    return [total_capex / 2 if t < 2 else 0 for t in range(int(np.ceil(years)))]

def estimate_capex(production):
    return 1000 + 150 * production

def calculate_npv(tonnage, grade, price, recovery, opex, production, discount_rate):
    metal_content = tonnage * grade / 100
    revenue = metal_content * recovery / 100 * price
    years = tonnage / production
    annual_cashflow = (revenue - opex * tonnage) / years
    capex = estimate_capex(production)
    capex_schedule = estimate_capex_schedule(capex, years)
    cashflows = [annual_cashflow] * int(np.ceil(years))
    npv = 0
    for t in range(int(np.ceil(years))):
        npv += (cashflows[t] - capex_schedule[t]) / ((1 + discount_rate / 100) ** (t + 1))
    return npv, years, capex

cutoff_vals = np.arange(cutoff_range[0], cutoff_range[1] + 0.01, 0.1)
prod_vals = np.arange(prod_range[0], prod_range[1] + 0.01, 0.5)

scenarios = []
for cutoff in cutoff_vals:
    for prod in prod_vals:
        npvs, years_list, capex_list = [], [], []
        for _ in range(250):
            price = np.random.normal(metal_price_mean, metal_price_std)
            recovery = np.random.normal(recovery_mean, recovery_std)
            tonnage, grade = grade_tonnage_curve(cutoff)
            npv, yrs, capex_val = calculate_npv(tonnage, grade, price, recovery, opex, prod, discount_rate)
            npvs.append(npv)
            years_list.append(yrs)
            capex_list.append(capex_val)
        scenarios.append({
            "Cutoff": cutoff, "Production": prod,
            "Avg NPV": np.mean(npvs),
            "Avg Life": np.mean(years_list),
            "CAPEX": np.mean(capex_list)
        })

df = pd.DataFrame(scenarios)
st.download_button("Download CSV", df.to_csv(index=False), file_name="hill_of_value_scenarios.csv")

fig3 = go.Figure(data=[
    go.Surface(
        z=df.pivot_table(index='Cutoff', columns='Production', values='Avg NPV').values,
        x=prod_vals,
        y=cutoff_vals,
        colorscale='Viridis',
        hovertemplate="<b>Cutoff</b>: %{y}<br><b>Production</b>: %{x}<br><b>NPV</b>: %{z:.2f}M",
        showscale=True
    )
])
fig3.update_layout(
    title="Hill of Value - 3D Surface",
    scene=dict(
        xaxis_title='Production (Mtpa)',
        yaxis_title='Cut-off Grade (%)',
        zaxis_title='Avg NPV ($M)'
    ),
    autosize=True,
    height=900,
    margin=dict(l=10, r=10, t=50, b=10),
    scene_camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
)
st.plotly_chart(fig3, use_container_width=True)

st.success("✅ Model executed successfully.")
