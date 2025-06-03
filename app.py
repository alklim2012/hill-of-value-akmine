import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="NPVision - Hill of Value", layout="wide")

st.title("⛏️ NPVision: Hill of Value Simulator")

# --- Sidebar Inputs ---
st.sidebar.header("Input Parameters")
cutoff_range = st.sidebar.slider("Cut-off Grade (%)", 0.1, 1.5, (0.2, 1.0), 0.1)
prod_range = st.sidebar.slider("Production (Mtpa)", 1.0, 10.0, (2.0, 6.0), 0.5)
metal_price_mean = st.sidebar.number_input("Metal Price ($/t)", 1000, 10000, 4000)
metal_price_std = st.sidebar.number_input("Price Std Dev", 0, 5000, 500)
recovery_mean = st.sidebar.slider("Recovery (%)", 50, 95, 85)
recovery_std = st.sidebar.slider("Recovery Std Dev (%)", 0, 15, 5)
discount_rate = st.sidebar.slider("Discount Rate (%)", 5.0, 15.0, 8.0)
capex = st.sidebar.number_input("CAPEX ($M)", 100, 5000, 1500)
opex = st.sidebar.number_input("OPEX ($/t)", 10, 150, 40)

uploaded_file = st.sidebar.file_uploader("📥 Upload Grade-Tonnage CSV", type=["csv"])

if uploaded_file is not None:
    user_curve = pd.read_csv(uploaded_file)
    use_curve = True
else:
    use_curve = False

def grade_tonnage_curve(cutoff):
    if use_curve:
        nearest = user_curve.iloc[(user_curve['Cutoff'] - cutoff).abs().argsort()[:1]]
        return float(nearest['Tonnage']), float(nearest['Grade'])
    else:
        a = 500  # adjustable
        b = 0.7  # shape factor
        tonnage = a * (cutoff ** -b)
        grade = np.maximum(1.5 - cutoff * 0.5, 0.2)  # simple inverse relationship
        return tonnage, grade

def calculate_npv(tonnage, grade, price, recovery, opex, capex, discount_rate, production):
    metal_content = tonnage * grade / 100
    revenue = metal_content * recovery / 100 * price
    years = tonnage / production
    annual_cashflow = (revenue - opex * tonnage) / years
    npv = sum([annual_cashflow / ((1 + discount_rate / 100) ** t) for t in range(1, int(np.ceil(years)) + 1)]) - capex
    return npv, years

# --- Scenario Generation ---
cutoff_vals = np.arange(cutoff_range[0], cutoff_range[1] + 0.01, 0.1)
prod_vals = np.arange(prod_range[0], prod_range[1] + 0.01, 0.5)

scenarios = []
for cutoff in cutoff_vals:
    for prod in prod_vals:
        npvs = []
        years_list = []
        for _ in range(250):
            price = np.random.normal(metal_price_mean, metal_price_std)
            recovery = np.random.normal(recovery_mean, recovery_std)
            tonnage, grade = grade_tonnage_curve(cutoff)
            npv, yrs = calculate_npv(tonnage, grade, price, recovery, opex, capex, discount_rate, prod)
            npvs.append(npv)
            years_list.append(yrs)
        avg_npv = np.mean(npvs)
        avg_years = np.mean(years_list)
        scenarios.append({"Cutoff": cutoff, "Production": prod, "Avg NPV": avg_npv, "Avg Life": avg_years})

# --- DataFrame ---
df = pd.DataFrame(scenarios)
st.subheader("📊 Scenario Table")
st.dataframe(df.round(2), use_container_width=True)

# --- 3D Plot ---
fig = go.Figure(data=[
    go.Surface(
        z=df.pivot_table(index='Cutoff', columns='Production', values='Avg NPV').values,
        x=prod_vals,
        y=cutoff_vals,
        colorscale='Viridis'
    )
])
fig.update_layout(
    title="Hill of Value - 3D Surface",
    scene=dict(
        xaxis_title='Production (Mtpa)',
        yaxis_title='Cut-off Grade (%)',
        zaxis_title='Avg NPV ($M)'
    ),
    height=600
)
st.subheader("🗻 3D Hill of Value")
st.plotly_chart(fig, use_container_width=True)

# --- Export ---
st.download_button(
    label="📥 Download Scenario Table (CSV)",
    data=df.to_csv(index=False).encode('utf-8'),
    file_name="hill_of_value_scenarios.csv",
    mime="text/csv"
)

st.markdown("""
### 📄 Grade-Tonnage CSV Format

Upload a CSV file with the following format:

```
Cutoff,Tonnage,Grade
0.2,500,0.85
0.3,420,0.90
0.4,350,0.95
...etc.
```

If no file is uploaded, an automatic curve will be used.
""")
