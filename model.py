"""Modelo de optimización multiflujo – DataNet Analytics (Proyecto 3).

Formulación
-----------
Conjuntos:   N nodos, A enlaces dirigidos (i,j), K comunicaciones (flujos).
Parámetros:  c_ij costo unitario, u_ij capacidad (Gbps), a_ij in {0,1} enlace activo,
             o_k origen, t_k destino, d_k demanda (Gbps).
Variables:   x_kij >= 0 (continua): tráfico de la comunicación k por el enlace (i,j).
Objetivo:    min  sum_k sum_(i,j) c_ij * x_kij
Restricciones:
  (1) Conservación por flujo y nodo:
      sum_j x_kij - sum_j x_kji = d_k si i = o_k ; -d_k si i = t_k ; 0 en otro caso
  (2) Capacidad compartida:  sum_k x_kij <= u_ij * a_ij
  (3) Solo existen los enlaces dados (variables definidas únicamente sobre A)
  (4) No negatividad: x_kij >= 0
"""
import pulp

NODES = [1, 2, 3, 4, 5, 6, 7, 8]

# (origen, destino): (costo unitario, capacidad Gbps)
LINKS = {
    (1, 2): (4, 12), (1, 3): (6, 10), (2, 3): (2, 8), (2, 4): (5, 10),
    (2, 5): (7, 8), (3, 4): (3, 12), (3, 6): (5, 10), (4, 5): (2, 10),
    (4, 7): (6, 12), (5, 6): (3, 8), (5, 8): (5, 10), (6, 7): (2, 10),
    (6, 8): (4, 12), (7, 8): (3, 14),
}

# nombre: (origen, destino, demanda Gbps)
FLOWS = {"F1": (1, 8, 6), "F2": (2, 7, 5), "F3": (3, 8, 4)}

TOL = 1e-6


def default_data():
    return {
        "links": {k: {"cost": v[0], "cap": v[1], "active": True} for k, v in LINKS.items()},
        "flows": {k: {"o": v[0], "t": v[1], "d": v[2]} for k, v in FLOWS.items()},
    }


def scenario_data(name):
    """Devuelve los datos de un escenario, partiendo siempre de los datos iniciales."""
    d = default_data()
    if name == "Escenario 1 – Falla 3→6":
        d["links"][(3, 6)]["active"] = False
    elif name == "Escenario 2 – Tráfico F1=10":
        d["flows"]["F1"]["d"] = 10
    elif name == "Escenario 3 – Ampliación 3→6=14":
        d["links"][(3, 6)]["cap"] = 14
    elif name != "Base":
        raise ValueError(name)
    return d


SCENARIOS = ["Base", "Escenario 1 – Falla 3→6", "Escenario 2 – Tráfico F1=10",
             "Escenario 3 – Ampliación 3→6=14"]


def solve(data, nodes=NODES):
    """Construye y resuelve el modelo. Devuelve un dict con estado y resultados."""
    links = {a: v for a, v in data["links"].items() if v["active"]}
    flows = data["flows"]

    prob = pulp.LpProblem("Multiflujo_DataNet", pulp.LpMinimize)

    # Variables de decisión x[k, i, j] >= 0
    x = {(k, i, j): pulp.LpVariable(f"x_{k}_{i}_{j}", lowBound=0)
         for k in flows for (i, j) in links}

    # Función objetivo
    prob += pulp.lpSum(links[(i, j)]["cost"] * x[k, i, j] for (k, i, j) in x), "CostoTotal"

    # (1) Conservación de flujo por comunicación y nodo
    for k, f in flows.items():
        for n in nodes:
            salida = pulp.lpSum(x[k, i, j] for (i, j) in links if i == n)
            entrada = pulp.lpSum(x[k, i, j] for (i, j) in links if j == n)
            rhs = f["d"] if n == f["o"] else (-f["d"] if n == f["t"] else 0)
            prob += salida - entrada == rhs, f"Cons_{k}_{n}"

    # (2) Capacidad compartida por enlace
    for (i, j), l in links.items():
        prob += pulp.lpSum(x[k, i, j] for k in flows) <= l["cap"], f"Cap_{i}_{j}"

    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[prob.status]

    res = {"status": status, "ok": status == "Optimal", "model": prob}
    if res["ok"]:
        flow = {(k, i, j): max(0.0, x[k, i, j].value() or 0.0) for (k, i, j) in x}
        load = {a: sum(flow[k, a[0], a[1]] for k in flows) for a in links}
        res.update(
            flow=flow, load=load, links=links, flows=flows,
            cost=pulp.value(prob.objective),
            util={a: (load[a] / links[a]["cap"] * 100 if links[a]["cap"] > 0 else 0.0) for a in links},
        )
    return res


def validate(res, nodes=NODES, tol=1e-5):
    """Comprueba restricciones y recalcula el objetivo con la solución reportada."""
    if not res["ok"]:
        return {"valido": False, "detalle": "Sin solución óptima"}
    flow, links, flows = res["flow"], res["links"], res["flows"]
    problemas = []
    for k, f in flows.items():
        for n in nodes:
            s = sum(flow[k, i, j] for (i, j) in links if i == n)
            e = sum(flow[k, i, j] for (i, j) in links if j == n)
            rhs = f["d"] if n == f["o"] else (-f["d"] if n == f["t"] else 0)
            if abs(s - e - rhs) > tol:
                problemas.append(f"Conservación {k} nodo {n}")
    for a, l in links.items():
        if res["load"][a] > l["cap"] + tol:
            problemas.append(f"Capacidad {a}")
    if any(v < -tol for v in flow.values()):
        problemas.append("No negatividad")
    costo = sum(links[(i, j)]["cost"] * v for (k, i, j), v in flow.items())
    if abs(costo - res["cost"]) > 1e-4:
        problemas.append("Objetivo no coincide")
    return {"valido": not problemas, "detalle": problemas or "Todas las restricciones se cumplen",
            "costo_recalculado": costo}
