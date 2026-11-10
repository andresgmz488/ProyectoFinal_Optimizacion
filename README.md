# DataNet Analytics – Optimización multiflujo

Proyecto 3 (Ciencia de Datos) del trabajo final de Técnicas de Optimización.

Modelo de flujo multiproducto que decide cuánto tráfico de cada comunicación viaja por cada enlace de una red de 8 servidores, minimizando el costo total sin superar la capacidad compartida de los enlaces. Implementado en Python con PuLP (solver CBC) y una interfaz en Streamlit.

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Archivos

| Archivo | Contenido |
| --- | --- |
| `app.py` | Interfaz Streamlit: red, datos editables, optimización, resultados y comparación de escenarios |
| `model.py` | Datos, modelo PuLP (variables, objetivo, restricciones), resolución, estados y validación |
| `requirements.txt` | Dependencias |
| `notebooks/DataNet_Modelo.ipynb` | El mismo modelo en formato notebook (Colab) |

## Formulación

- Variables: `x[k,i,j] >= 0`, Gbps de la comunicación k por el enlace (i,j); continuas.
- Objetivo: `min Σ_k Σ_(i,j) c_ij · x[k,i,j]`
- Conservación por comunicación y nodo: salida − entrada = d_k (origen), −d_k (destino), 0 (otros).
- Capacidad compartida: `Σ_k x[k,i,j] <= u_ij` en los enlaces activos.

## Resultados

| Caso | Costo |
| --- | --- |
| Base | 176 |
| 1. Falla 3→6 | 191 |
| 2. F1 = 10 Gbps | 240 |
| 3. Ampliación 3→6 a 14 Gbps | 172 |
| Prueba adicional: 5→8, 6→8 y 7→8 con capacidad 2 | Infactible |

## Despliegue

En https://share.streamlit.io: *Create app* → este repositorio, rama `main`, archivo principal `app.py`.
