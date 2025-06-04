import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

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
    npv = sum([(cashflows[t] - capex_schedule[t]) / ((1 + discount_rate / 100) ** (t + 1)) for t in range(len(cashflows))])
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
        scenarios.append({"Cutoff": cutoff, "Production": prod, "Avg NPV": np.mean(npvs), "Avg Life": np.mean(years_list), "CAPEX": np.mean(capex_list)})

df = pd.DataFrame(scenarios)

# Clean data for plotting
try:
    df_plot = df.dropna()
    df_plot = df_plot[df_plot["Avg NPV"] > 0]
    df_plot = df_plot[df_plot["CAPEX"] > 0]
    df_plot = df_plot.astype({
        "Cutoff": float,
        "Production": float,
        "Avg NPV": float,
        "CAPEX": float,
        "Avg Life": float
    })
except Exception as e:
    st.error(f"Data cleaning error: {e}")

st.subheader("📊 Scenario Table")
st.dataframe(df_plot.round(2), use_container_width=True)

st.subheader("📈 Interactive CAPEX vs Production")
try:
    fig1 = px.scatter(df_plot, x="Production", y="CAPEX", color="Cutoff", size="Avg NPV",
                     labels={"CAPEX": "CAPEX ($M)", "Production": "Production (Mtpa)"})
    st.plotly_chart(fig1, use_container_width=True)
except Exception as e:
    st.error(f"Ошибка при построении fig1: {e}")

st.subheader("📉 Project Life vs Cut-off")
try:
    fig2 = px.scatter(df_plot, x="Cutoff", y="Avg Life", color="Production", size="Avg NPV",
                     labels={"Avg Life": "Mine Life (Years)"})
    st.plotly_chart(fig2, use_container_width=True)
except Exception as e:
    st.error(f"Ошибка при построении fig2: {e}")

try:
    z_data = df_plot.pivot_table(index='Cutoff', columns='Production', values='Avg NPV').values
    fig = go.Figure(data=[
        go.Surface(
            z=z_data,
            x=prod_vals,
            y=cutoff_vals,
            colorscale='Viridis',
            hovertemplate="<b>Cutoff</b>: %{y}<br><b>Production</b>: %{x}<br><b>NPV</b>: %{z:.2f}M",
            showscale=True
        )
    ])
    fig.update_layout(
        title="Hill of Value - 3D Surface",
        scene=dict(
            xaxis_title='Production (Mtpa)',
            yaxis_title='Cut-off Grade (%)',
            zaxis_title='Avg NPV ($M)'
        ),
        margin=dict(l=20, r=20, t=50, b=20),
        autosize=True,
        height=800
    )
    st.subheader("🗻 3D Hill of Value")
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Ошибка при построении 3D-графика: {e}")

st.download_button(
    label="📥 Download Scenario Table (CSV)",
    data=df_plot.to_csv(index=False).encode('utf-8'),
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
