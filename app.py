import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import model as m

st.set_page_config(page_title="DataNet Analytics – Optimización multiflujo", layout="wide")

POS = {1: (0, 1), 2: (1, 2), 3: (1, 0), 4: (2, 1.6), 5: (3, 2), 6: (3, 0), 7: (4, 0.8), 8: (5, 1)}
COLORS = {"Disponible": "#9AA5B1", "Utilizado": "#2E86DE", "Saturado": "#E74C3C", "Inactivo": "#D0D0D0"}


# ---------------------------------------------------------------- estado
def load_into_state(data):
    st.session_state.links_df = pd.DataFrame(
        [{"Enlace": f"{i}→{j}", "Origen": i, "Destino": j, "Costo": v["cost"],
          "Capacidad": v["cap"], "Activo": v["active"]} for (i, j), v in data["links"].items()])
    st.session_state.flows_df = pd.DataFrame(
        [{"Flujo": k, "Origen": v["o"], "Destino": v["t"], "Demanda": v["d"]}
         for k, v in data["flows"].items()])


if "links_df" not in st.session_state:
    load_into_state(m.default_data())
    st.session_state.history = {}


def data_from_state():
    ldf, fdf = st.session_state.links_df, st.session_state.flows_df
    return {
        "links": {(int(r.Origen), int(r.Destino)): {"cost": float(r.Costo), "cap": float(r.Capacidad),
                                                    "active": bool(r.Activo)} for r in ldf.itertuples()},
        "flows": {r.Flujo: {"o": int(r.Origen), "t": int(r.Destino), "d": float(r.Demanda)}
                  for r in fdf.itertuples()},
    }


def link_status(a, link, res):
    if not link["active"]:
        return "Inactivo"
    if res is None or not res["ok"]:
        return "Disponible"
    load = res["load"].get(a, 0)
    if load > 1e-6 and load >= link["cap"] - 1e-6:
        return "Saturado"
    return "Utilizado" if load > 1e-6 else "Disponible"


def draw_network(data, res):
    fig = go.Figure()
    for a, l in data["links"].items():
        (x0, y0), (x1, y1) = POS[a[0]], POS[a[1]]
        s = link_status(a, l, res)
        load = res["load"].get(a, 0) if res and res["ok"] else 0
        width = 2 + (load / max(l["cap"], 1)) * 6 if s in ("Utilizado", "Saturado") else 2
        fig.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines",
                                 line=dict(color=COLORS[s], width=width,
                                           dash="dot" if s == "Inactivo" else "solid"),
                                 hoverinfo="skip", showlegend=False))
        fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowsize=1.2, arrowwidth=1.2,
                           arrowcolor=COLORS[s], standoff=16)
        txt = f"c={l['cost']:g}, u={l['cap']:g}" + (f"<br>carga {load:g}" if res and res["ok"] and load > 1e-6 else "")
        fig.add_trace(go.Scatter(x=[(x0 + x1) / 2], y=[(y0 + y1) / 2], mode="text", text=[txt],
                                 textfont=dict(size=10, color=COLORS[s] if s != "Disponible" else "#555"),
                                 hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=[p[0] for p in POS.values()], y=[p[1] for p in POS.values()],
                             mode="markers+text", text=[str(n) for n in POS], textposition="middle center",
                             marker=dict(size=34, color="#1B2631"), textfont=dict(color="white", size=14),
                             hoverinfo="skip", showlegend=False))
    for nombre, c in COLORS.items():
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=c, width=4), name=nombre))
    fig.update_layout(height=480, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(visible=False),
                      yaxis=dict(visible=False), plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=-0.05))
    return fig


# ---------------------------------------------------------------- UI
st.title("DataNet Analytics – Optimización de transmisión de información")
st.caption("Modelo de flujo multiproducto (multicommodity flow): minimiza el costo total de transmitir "
           "las comunicaciones sin superar la capacidad compartida de cada enlace. Resuelto con PuLP/CBC.")

with st.sidebar:
    st.header("Escenarios")
    esc = st.selectbox("Cargar escenario predefinido", m.SCENARIOS)
    if st.button("Cargar datos del escenario"):
        load_into_state(m.scenario_data(esc))
        st.session_state.pop("res", None)
        st.session_state.loaded = esc
        st.rerun()
    if st.button("Restablecer datos iniciales"):
        load_into_state(m.default_data())
        st.session_state.pop("res", None)
        st.session_state.loaded = "Base"
        st.rerun()
    st.info("Cada escenario se carga siempre desde los datos iniciales. También puedes editar "
            "cualquier valor en las tablas y ejecutar el optimizador.")

tab1, tab2, tab3 = st.tabs(["Datos y optimización", "Resultados", "Comparación de escenarios"])

with tab1:
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Enlaces (costo, capacidad, activo)")
        st.session_state.links_df = st.data_editor(
            st.session_state.links_df, disabled=["Enlace", "Origen", "Destino"], hide_index=True,
            width="stretch", key="ed_links",
            column_config={"Costo": st.column_config.NumberColumn(min_value=0.0, step=1.0),
                           "Capacidad": st.column_config.NumberColumn(min_value=0.0, step=1.0)})
    with c2:
        st.subheader("Comunicaciones")
        st.session_state.flows_df = st.data_editor(
            st.session_state.flows_df, disabled=["Flujo", "Origen", "Destino"], hide_index=True,
            width="stretch", key="ed_flows",
            column_config={"Demanda": st.column_config.NumberColumn(min_value=0.0, step=1.0)})
    label = st.text_input("Nombre para guardar esta ejecución en la comparación",
                          value=st.session_state.get("loaded", "Base"))
    if st.button("Ejecutar optimización", type="primary"):
        data = data_from_state()
        res = m.solve(data)
        res["data"] = data
        st.session_state.res = res
        st.session_state.history[label] = res

res = st.session_state.get("res")
data_now = data_from_state()

with tab1:
    st.subheader("Red de servidores")
    st.plotly_chart(draw_network(data_now, res), width="stretch", key="net_edit")

with tab2:
    if res is None:
        st.info("Ejecuta la optimización en la primera pestaña.")
    elif not res["ok"]:
        st.error(f"Estado del solucionador: **{res['status']}**. "
                 + ("El problema es INFACTIBLE: con los enlaces activos y sus capacidades no es posible "
                    "transmitir todas las demandas. No se muestra ninguna solución."
                    if res["status"] == "Infeasible" else
                    "No se obtuvo una solución óptima; no se muestran resultados."))
    else:
        v = m.validate(res)
        st.success("Estado del solucionador: **Óptimo**")
        k1, k2, k3 = st.columns(3)
        k1.metric("Costo total", f"{res['cost']:,.2f}")
        k2.metric("Tráfico total demandado (Gbps)", f"{sum(f['d'] for f in res['flows'].values()):g}")
        k3.metric("Validación de restricciones", "Correcta" if v["valido"] else "Con errores")
        st.caption(f"Costo recalculado con la solución reportada: {v['costo_recalculado']:,.2f}")

        rows = []
        for a, l in res["links"].items():
            row = {"Enlace": f"{a[0]}→{a[1]}", "Costo": l["cost"], "Capacidad": l["cap"]}
            for k in res["flows"]:
                row[k] = round(res["flow"][k, a[0], a[1]], 3)
            row["Carga total"] = round(res["load"][a], 3)
            row["Utilización %"] = round(res["util"][a], 1)
            row["Estado"] = link_status(a, l, res)
            rows.append(row)
        st.subheader("Flujo de cada comunicación por enlace")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

        st.subheader("Red con enlaces disponibles, utilizados y saturados")
        st.plotly_chart(draw_network(res["data"], res), width="stretch", key="net_res")

        st.subheader("Utilización de capacidad por enlace")
        u = pd.DataFrame(rows)
        fig = go.Figure(go.Bar(x=u["Enlace"], y=u["Utilización %"],
                               marker_color=[COLORS[s] for s in u["Estado"]]))
        fig.update_layout(yaxis_title="% de capacidad", height=350, margin=dict(t=10))
        st.plotly_chart(fig, width="stretch", key="bar_util")

        st.subheader("Rutas utilizadas por comunicación")
        for k, f in res["flows"].items():
            usados = [f"{a[0]}→{a[1]}: {res['flow'][k, a[0], a[1]]:g}" for a in res["links"]
                      if res["flow"][k, a[0], a[1]] > 1e-6]
            st.write(f"**{k}** ({f['o']}→{f['t']}, {f['d']:g} Gbps): " + ", ".join(usados))

with tab3:
    hist = {k: r for k, r in st.session_state.history.items()}
    if st.button("Resolver base y los 3 escenarios obligatorios"):
        for s in m.SCENARIOS:
            d = m.scenario_data(s)
            r = m.solve(d)
            r["data"] = d
            st.session_state.history[s] = r
        st.rerun()
    if not hist:
        st.info("Ejecuta escenarios para compararlos.")
    else:
        base = hist.get("Base")
        tabla = []
        for nombre, r in hist.items():
            fila = {"Escenario": nombre, "Estado": r["status"]}
            if r["ok"]:
                fila["Costo total"] = round(r["cost"], 2)
                if base and base["ok"]:
                    fila["Δ vs base"] = round(r["cost"] - base["cost"], 2)
                fila["Enlaces usados"] = sum(1 for x in r["load"].values() if x > 1e-6)
                fila["Enlaces saturados"] = sum(
                    1 for a, x in r["load"].items() if x > 1e-6 and x >= r["links"][a]["cap"] - 1e-6)
                fila["Utilización media %"] = round(sum(r["util"].values()) / len(r["util"]), 1)
            tabla.append(fila)
        st.dataframe(pd.DataFrame(tabla), hide_index=True, width="stretch")

        oks = {n: r for n, r in hist.items() if r["ok"]}
        if oks:
            fig = go.Figure(go.Bar(x=list(oks), y=[r["cost"] for r in oks.values()], marker_color="#2E86DE"))
            fig.update_layout(yaxis_title="Costo total", height=320, margin=dict(t=10))
            st.plotly_chart(fig, width="stretch", key="bar_cost")

            allarcs = sorted({a for r in oks.values() for a in r["links"]} | set(m.LINKS))
            fig2 = go.Figure()
            for n, r in oks.items():
                fig2.add_trace(go.Bar(name=n, x=[f"{a[0]}→{a[1]}" for a in allarcs],
                                      y=[r["util"].get(a, 0) for a in allarcs]))
            fig2.update_layout(barmode="group", yaxis_title="% de utilización", height=400,
                               margin=dict(t=10), legend=dict(orientation="h", y=-0.25))
            st.subheader("Porcentaje de utilización de capacidad por enlace")
            st.plotly_chart(fig2, width="stretch", key="bar_cmp")
        if st.button("Limpiar comparación"):
            st.session_state.history = {}
            st.rerun()
