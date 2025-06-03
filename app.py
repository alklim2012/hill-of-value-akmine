import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("NPVision: Hill of Value Optimizer")

# --- Sidebar Inputs ---
st.sidebar.header("Input Parameters")
cutoff_min = st.sidebar.number_input("Min Cut-off", 0.1, 2.0, 0.2, 0.1)
cutoff_max = st.sidebar.number_input("Max Cut-off", cutoff_min + 0.1, 3.0, 1.0, 0.1)
prod_min = st.sidebar.number_input("Min Production (Mtpa)", 0.5, 20.0, 2.0, 0.5)
prod_max = st.sidebar.number_input("Max Production (Mtpa)", prod_min + 0.5, 25.0, 6.0, 0.5)
metal_price_mean = st.sidebar.number_input("Mean Metal Price ($/t)", 0, 10000, 4000)
metal_price_std = st.sidebar.number_input("Price Std Dev ($/t)", 0, 5000, 500)
recovery_mean = st.sidebar.number_input("Mean Recovery (%)", 0.0, 100.0, 85.0)
recovery_std = st.sidebar.number_input("Recovery Std Dev (%)", 0.0, 20.0, 5.0)
opex = st.sidebar.number_input("OPEX ($/t)", 0.0, 500.0, 40.0)
discount_rate = st.sidebar.number_input("Discount Rate (%)", 0.0, 50.0, 8.0)
simulations = st.sidebar.slider("# Monte Carlo Simulations", 50, 1000, 250)

uploaded_file = st.sidebar.file_uploader("Upload Grade-Tonnage Curve CSV", type="csv")
use_curve = uploaded_file is not None

if use_curve:
    user_curve = pd.read_csv(uploaded_file)
    st.sidebar.success("Grade-tonnage curve loaded")

# --- Helper Functions ---
def grade_tonnage_curve(cutoff):
    if use_curve:
        nearest = user_curve.iloc[(user_curve['Cutoff'] - cutoff).abs().argsort()[:1]]
        return float(nearest['Tonnage']), float(nearest['Grade'])
    else:
        a = 500  # adjustable
        b = 0.7
        tonnage = a * (cutoff ** -b)
        grade = np.maximum(1.5 - cutoff * 0.5, 0.2)
        return tonnage, grade

def estimate_capex(production):
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
    npv = 0
    for t in range(int(np.ceil(years))):
        npv += (cashflows[t] - capex_schedule[t]) / ((1 + discount_rate / 100) ** (t + 1))
    return npv, years, capex

# --- Run Simulations ---
cutoff_vals = np.arange(cutoff_min, cutoff_max + 0.001, 0.1)
prod_vals = np.arange(prod_min, prod_max + 0.001, 0.5)

results = []
progress = st.progress(0.0)
total = len(cutoff_vals) * len(prod_vals)
counter = 0

for cutoff in cutoff_vals:
    for prod in prod_vals:
        npvs, years_list, capex_list = [], [], []
        for _ in range(simulations):
            price = np.random.normal(metal_price_mean, metal_price_std)
            recovery = np.random.normal(recovery_mean, recovery_std)
            tonnage, grade = grade_tonnage_curve(cutoff)
            npv, yrs, capex_val = calculate_npv(tonnage, grade, price, recovery, opex, prod, discount_rate)
            npvs.append(npv)
            years_list.append(yrs)
            capex_list.append(capex_val)
        results.append({"Cutoff": cutoff, "Production": prod,
                        "Avg NPV": np.mean(npvs), "Avg Life": np.mean(years_list),
                        "CAPEX": np.mean(capex_list)})
        counter += 1
        progress.progress(counter / total)

st.success("✅ Simulation complete")
df = pd.DataFrame(results)
st.dataframe(df)

# --- Visuals ---
st.subheader("3D Hill of Value")
z_data = df.pivot_table(index='Cutoff', columns='Production', values='Avg NPV').values
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
    scene=dict(
        xaxis_title='Production (Mtpa)',
        yaxis_title='Cut-off Grade (%)',
        zaxis_title='Avg NPV ($M)'
    ),
    margin=dict(l=0, r=0, t=50, b=0),
    height=700
)
st.plotly_chart(fig3, use_container_width=True)

# --- Export ---
st.download_button("Download Scenario CSV", df.to_csv(index=False), "hill_of_value_results.csv")
