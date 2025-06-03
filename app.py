import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --- Input Parameters ---
cutoff_range = (0.2, 1.0)
prod_range = (2.0, 6.0)
metal_price_mean = 4000
metal_price_std = 500
recovery_mean = 85
recovery_std = 5
discount_rate = 8.0
opex = 40

def grade_tonnage_curve(cutoff):
    a = 500
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

df.to_csv("hill_of_value_scenarios.csv", index=False)

fig1 = px.scatter(df, x="Production", y="CAPEX", color="Cutoff", size="Avg NPV",
                  labels={"CAPEX": "CAPEX ($M)", "Production": "Production (Mtpa)"})
fig1.write_html("capex_vs_production.html")

fig2 = px.scatter(df, x="Cutoff", y="Avg Life", color="Production", size="Avg NPV",
                  labels={"Avg Life": "Mine Life (Years)"})
fig2.write_html("life_vs_cutoff.html")

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
fig3.write_html("hill_of_value_3d.html")

print("✅ Outputs saved: hill_of_value_scenarios.csv, capex_vs_production.html, life_vs_cutoff.html, hill_of_value_3d.html")
