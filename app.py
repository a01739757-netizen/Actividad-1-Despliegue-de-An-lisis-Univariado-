#Creamos el archivo de la APP (Dashboard GAC Motor - Etapa I: Extracción de Características)
#####################################################
#Importamos librerias
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import io
import math
import base64
from PIL import Image
######################################################
#Configuración de la página (pantalla ancha)
st.set_page_config(page_title="GAC Motor | Análisis univariado", layout="wide")

#Colores de GAC
ROJO = "#C8102E"   #Color principal
GRIS = "#8C8C8C"   #Color secundario (lo que no necesita atención)
NEGRO = "#1A1A1A"  #Color de apoyo
PLATA = "#D0D0D0"  #Bordes metálicos

LOGO = "logo_gac.png"
FONDO = "auto fondo.jpeg"
DISCO = "disco_freno.png"
CARBONO = "fibra_carbono.png"
BRILLO = "brillo_dona.png"

pio.templates["gac"] = go.layout.Template(layout=dict(
    font=dict(color="#2B2B2B", size=13),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=[ROJO, NEGRO, GRIS, "#E06B7D", "#4D4D4D", "#F2B8C0"],
    xaxis=dict(gridcolor="rgba(0,0,0,0.08)", linecolor="rgba(0,0,0,0.3)", zeroline=False),
    yaxis=dict(gridcolor="rgba(0,0,0,0.08)", linecolor="rgba(0,0,0,0.3)", zeroline=False),
    hoverlabel=dict(bgcolor=NEGRO, font_color="white", bordercolor=ROJO)))
pio.templates.default = "plotly_white+gac"

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

#Etapas del embudo en orden (de la primera a la última)
#Leads generados/efectivos NO se usan: vienen rellenados con la media (83.06 se repite)
ETAPAS = ["Cita programada", "Cita efectiva", "Prueba de manejo",
          "Solicitud de crédito generada", "Solicitud de crédito aprobada",
          "Ventas", "Formalizado"]

#Lista de las 15 variables: nombre en el dashboard -> (base, columna, tipo, medida)
#Medida = columna que se SUMA por categoría. Si es None, se cuentan registros.
VARIABLES = {
    "Canal (Funnel)":            ("Funnel", "Canal", "Categórica", "Real"),
    "Indicador del embudo":      ("Funnel", "Indicador", "Categórica", "Real"),
    "Campaña digital":           ("MKT_Digital", "Campaña", "Categórica", "Leads"),
    "Canal principal":           ("Principales_Canales", "Canal", "Categórica", "Ventas"),
    "Asesor de piso":            ("Analisis_de_Piso", "Asesor", "Categórica", "Ventas"),
    "Vendedor":                  ("Ventas_por_Asesor", "Vendedor", "Categórica", "Ventas"),
    "Ventas por asesor de piso": ("Analisis_de_Piso", "Ventas", "Numérica discreta", None),
    "Ventas por vendedor":       ("Ventas_por_Asesor", "Ventas", "Numérica discreta", None),
    "Bono de marketing":         ("Marketing", "Bono_Marketing", "Numérica discreta", None),
    "Bajas de personal":         ("TOPS_TDH", "Bajas", "Numérica discreta", None),
    "Vacantes":                  ("TOPS_TDH", "Vacantes", "Numérica discreta", None),
    "APVS Oro":                  ("TOPS_TDH", "APVS_Oro", "Numérica discreta", None),
    "APVS Plata":                ("TOPS_TDH", "APVS_Plata", "Numérica discreta", None),
    "APVS Bronce":               ("TOPS_TDH", "APVS_Bronce", "Numérica discreta", None),
    "Clima laboral":             ("TOPS_TDH", "Clima_Laboral", "Numérica discreta", None),
}

######################################################
#Definimos la instancia
@st.cache_resource
######################################################
#Creamos la función de carga de datos
def load_data():
    #Lectura de los archivos csv (una por una). Deben estar en la misma carpeta que app.py
    #No rellenamos nulos con bfill/ffill: un dato faltante no es igual al del mes vecino
    bases = {}
    bases["Analisis_de_Piso"] = pd.read_csv("Analisis_de_Piso_Limpio.csv")
    bases["Funnel"] = pd.read_csv("Funnel_Limpio.csv")
    bases["Leads_Reales"] = pd.read_csv("Leads_Reales_Limpio.csv")
    bases["Marketing"] = pd.read_csv("Marketing_Limpio.csv")
    bases["MKT_Digital"] = pd.read_csv("MKT_Digital_Limpio.csv")
    bases["Principales_Canales"] = pd.read_csv("Principales_Canales_Limpio.csv")
    bases["SDC"] = pd.read_csv("SDC_Limpio.csv")
    bases["TOPS_TDH"] = pd.read_csv("TOPS_TDH_Limpio.csv")
    bases["Ventas"] = pd.read_csv("Ventas_Limpio.csv")
    bases["Ventas_por_Asesor"] = pd.read_csv("Ventas_por_Asesor_Limpio.csv")

    #Unificamos nombres repetidos del mismo canal en Funnel
    bases["Funnel"]["Canal"] = bases["Funnel"]["Canal"].replace({
        "Plaza Ange": "Plaza Angelopólis",
        "Gran Patio": "Gran Patio Tlaxcala",
        "Prospeccion": "Estrategia de Prospeccion",
        "Plaza Pachuca (2)": "Plaza Pachuca",
        "Otros / Cartera / Casa": "Otros",
        "Otros / Custom": "Otros",
    })
    return bases

###############################################################################
#Cargo los datos obtenidos de la función "load_data"
bases = load_data()

###############################################################################
#FUNCIONES DE APOYO
#Escribe las categorías sin decimales de sobra: 2.0 -> "2"
def como_texto(valor):
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)

#Prepara los datos de Funnel para que no se cuente doble
def preparar(df, variable):
    if variable == "Canal (Funnel)":
        #"GAC Angelopolis" es el TOTAL de la agencia (suma de los demás canales): lo quitamos
        #y medimos cada canal por sus ventas reales
        return df[(df["Indicador"] == "Ventas") & (df["Canal"] != "GAC Angelopolis")]
    if variable == "Indicador del embudo":
        #Usamos solo la fila del total para ver el embudo completo de la agencia
        return df[(df["Canal"] == "GAC Angelopolis") & (df["Indicador"].isin(ETAPAS))]
    return df

#Arma las frecuencias (o sumas) de cada categoría con su porcentaje
def frecuencias(df, columna, medida, tipo, variable=""):
    if medida:
        Datos = df.groupby(columna)[medida].sum().reset_index()
        if variable == "Canal (Funnel)":
            nombre = "Ventas"
        elif variable == "Indicador del embudo":
            nombre = "Clientes"
        else:
            nombre = medida
    else:
        Datos = df[columna].value_counts().reset_index()
        nombre = "Registros"
    Datos.columns = ["Categoría", nombre]
    #Las numéricas se ordenan 0, 1, 2...; las de texto de mayor a menor
    if tipo == "Numérica discreta":
        Datos = Datos.sort_values("Categoría")
    else:
        Datos = Datos.sort_values(nombre, ascending=False)
    Datos["Categoría"] = Datos["Categoría"].apply(como_texto)
    Datos[nombre] = Datos[nombre].round(0).astype(int)
    Datos["Porcentaje"] = (Datos[nombre] / max(Datos[nombre].sum(), 1) * 100).round(1)
    return Datos.reset_index(drop=True), nombre

#Datos del embudo (etapas en orden, real vs objetivo)
def datos_embudo(df):
    Embudo = (df.groupby("Indicador")[["Real", "Objetivo"]].sum()
              .reindex(ETAPAS).fillna(0).reset_index())
    Embudo["Real"] = Embudo["Real"].round(0).astype(int)
    Embudo["Cumplimiento"] = (Embudo["Real"] / Embudo["Objetivo"].replace(0, 1) * 100).round(0)
    Embudo["Pasa"] = (Embudo["Real"] / Embudo["Real"].shift(1) * 100).round(0)
    return Embudo

@st.cache_data
def imagen_b64(ruta, ancho=None):
    if not os.path.exists(ruta):
        return None
    imagen = Image.open(ruta)
    if ancho:
        imagen.thumbnail((ancho, ancho))
    buffer = io.BytesIO()
    formato = "JPEG" if imagen.mode == "RGB" else "PNG"
    imagen.save(buffer, format=formato, quality=88)
    return f"data:image/{formato.lower()};base64," + base64.b64encode(buffer.getvalue()).decode()

def aplicar_estilos():
    fondo, carbono = imagen_b64(FONDO, 1600), imagen_b64(CARBONO)
    icono = imagen_b64(DISCO, 64)
    capa_fondo = f", url('{fondo}')" if fondo else ""
    capa_carbono = f", url('{carbono}')" if carbono else ""
    vineta = f"background: url('{icono}') no-repeat 0 0.2em / 1.05em;" if icono else ""
    st.markdown(f"""<style>
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(rgba(240,241,243,0.45), rgba(240,241,243,0.45)){capa_fondo};
        background-size: cover; background-position: right bottom; background-attachment: fixed;
        background-color: #EEEFF1;
    }}
    [data-testid="stHeader"] {{ background: transparent; }}

    [data-testid="stSidebar"] {{
        background: radial-gradient(ellipse at 30% 0%, rgba(255,255,255,0.10), rgba(0,0,0,0.35) 80%){capa_carbono};
        background-color: #1E1E1E;
        border-right: 3px solid {ROJO};
        border-radius: 0 26px 26px 0;
        box-shadow: 4px 0 22px rgba(200,16,46,0.45), inset -6px 0 10px rgba(0,0,0,0.5);
    }}
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: #E4E4E4 !important; }}

    [data-testid="stSidebar"] :is([data-testid="stSelectbox"], [data-testid="stMultiSelect"]) > div:last-child > div {{
        background: linear-gradient(180deg, #F7F7F7 0%, #CFCFCF 48%, #B9B9B9 52%, #E2E2E2 100%);
        border: 1px solid #8A8A8A; border-radius: 6px;
        box-shadow: inset 0 1px 0 #FFFFFF, 0 2px 6px rgba(0,0,0,0.5);
    }}
    [data-testid="stSidebar"] :is([data-testid="stSelectbox"], [data-testid="stMultiSelect"]) > div:last-child * {{ color: {NEGRO} !important; }}
    [data-testid="stSidebar"] [data-testid="stMultiSelectTagsContainer"] [role="group"] > span {{
        background: linear-gradient(180deg, #E0213F, {ROJO} 55%, #9E0C24) !important;
        border: 1px solid #7A0A1C;
    }}
    [data-testid="stSidebar"] [data-testid="stMultiSelectTagsContainer"] [role="group"] > span,
    [data-testid="stSidebar"] [data-testid="stMultiSelectTagsContainer"] [role="group"] > span * {{ color: #FFFFFF !important; }}

    .stMain h1 {{
        font-weight: 800; letter-spacing: 0.5px;
        background: linear-gradient(180deg, #8A8A8A 0%, #3A3A3A 45%, #1E1E1E 55%, #5A5A5A 100%);
        -webkit-background-clip: text; background-clip: text; color: transparent;
        filter: drop-shadow(0 2px 1px rgba(0,0,0,0.25));
    }}
    .stMain h3 {{ color: {NEGRO}; font-weight: 700; }}
    .stMain hr {{ border-color: rgba(0,0,0,0.12); }}

    .stMain [data-testid="stMarkdownContainer"] ul {{ list-style: none; padding-left: 0; }}
    .stMain [data-testid="stMarkdownContainer"] li {{ padding-left: 1.6em; margin-bottom: 0.45em; {vineta} }}
    .puntos-titulo {{ font-weight: 700; color: {NEGRO}; margin-bottom: 0.4em;
                      border-bottom: 2px solid {ROJO}; display: inline-block; padding-bottom: 2px; }}

    [data-testid="stMetric"] {{
        background: rgba(255,255,255,0.78); backdrop-filter: blur(4px);
        border-left: 4px solid {ROJO}; border-radius: 10px; padding: 12px 18px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.12);
    }}
    </style>""", unsafe_allow_html=True)

def decorar_dona(fig):
    traza = fig.data[0]
    etiquetas, valores = list(traza.labels), list(traza.values)
    colores = list(traza.marker.colors or fig.layout.piecolorway or [ROJO, NEGRO, GRIS])
    total = max(sum(valores), 1)
    fig.update_layout(height=400, margin=dict(t=50, b=50, l=20, r=20))
    radio = 150
    fig.update_traces(sort=False, direction="clockwise", rotation=0, textinfo="label+percent",
                      textfont=dict(size=14, color="white"),
                      marker=dict(colors=colores, line=dict(color="#2A2A2A", width=2)))
    if os.path.exists(BRILLO):
        fig.add_layout_image(source=Image.open(BRILLO), xref="paper", yref="paper", x=0.5, y=0.5,
                             sizex=1, sizey=1, xanchor="center", yanchor="middle", layer="above")
    if os.path.exists(DISCO):
        fig.add_layout_image(source=Image.open(DISCO), xref="paper", yref="paper", x=0.5, y=0.5,
                             sizex=0.5, sizey=0.5, xanchor="center", yanchor="middle", layer="above")
    acumulado = 0
    for i, (etiqueta, valor) in enumerate(zip(etiquetas, valores)):
        angulo = math.radians(90 - (acumulado + valor / 2) / total * 360)
        acumulado += valor
        color = colores[i % len(colores)]
        fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper",
                           xshift=radio * 0.92 * math.cos(angulo), yshift=radio * 0.92 * math.sin(angulo),
                           ax=95 * math.cos(angulo), ay=-45 * math.sin(angulo),
                           text=f"{etiqueta} ({valor / total * 100:.1f}%)", showarrow=True,
                           arrowhead=0, arrowwidth=1.5, arrowcolor="#555555",
                           bgcolor=color, bordercolor=PLATA, borderwidth=2, borderpad=6,
                           font=dict(color="white", size=13))
    return fig

#Muestra una sección: pregunta arriba, gráfica a la izquierda y puntos clave a la derecha
def seccion(pregunta, figura, puntos):
    st.subheader(pregunta)
    Contenedor_Graf, Contenedor_Texto = st.columns([2, 1], gap="large")
    with Contenedor_Graf:
        figura.update_layout(height=400, margin=dict(t=20, b=20), title=None,
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        figura.update_traces(marker_line_color="#7A0A1C", marker_line_width=1,
                             selector=lambda t: t.type in ("bar", "funnel"))
        if figura.data and figura.data[0].type == "pie":
            decorar_dona(figura)
        st.plotly_chart(figura, width="stretch", key=pregunta, theme=None)
    with Contenedor_Texto:
        st.markdown('<div class="puntos-titulo">Puntos clave</div>', unsafe_allow_html=True)
        st.markdown("\n".join(f"- {p}" for p in puntos))
    st.divider()

#Suma (o valor) de la variable en cada mes, ordenado en el tiempo
def serie_mensual(df, columna, medida):
    numero_mes = {m: f"{i:02d}" for i, m in enumerate(MESES, 1)}
    datos = df.copy()
    datos["Mes del año"] = datos["Año"].astype(str) + "-" + datos["Mes"].map(numero_mes)
    datos["Valor"] = datos[medida] if medida else datos[columna]
    return datos.groupby("Mes del año", as_index=False)["Valor"].sum().sort_values("Mes del año")

###############################################################################
#CATÁLOGO DE GRÁFICAS DEL ANÁLISIS UNIVARIADO
#Cada función regresa: (figura, pregunta, puntos clave)

#BARRAS HORIZONTALES: las 10 categorías más grandes
def g_barras(df, Datos, nombre, columna, medida, variable):
    d = Datos.head(10)
    fig = px.bar(d.iloc[::-1], x=nombre, y="Categoría", orientation="h", text="Porcentaje",
                 color_discrete_sequence=[ROJO])
    fig.update_traces(texttemplate="%{text}%", textposition="outside", cliponaxis=False)
    fig.update_yaxes(type="category", title="")
    fig.update_xaxes(range=[0, d[nombre].max() * 1.2])
    top3 = Datos["Porcentaje"].head(3).sum()
    return fig, "¿Cuáles son las más grandes?", [
        f"**{Datos['Categoría'].iloc[0]}** es la primera con **{Datos['Porcentaje'].iloc[0]}%**.",
        f"Las 3 primeras juntan **{top3:.0f}%** del total.",
        f"Hay **{len(Datos)}** categorías en total."]

#LOLLIPOP (paleta): como barras pero más limpio para nombres de personas
def g_lollipop(df, Datos, nombre, columna, medida, variable):
    d = Datos.head(10).iloc[::-1]
    fig = px.scatter(d, x=nombre, y="Categoría", text=nombre, color_discrete_sequence=[ROJO])
    for _, fila in d.iterrows():
        fig.add_shape(type="line", x0=0, x1=fila[nombre], y0=fila["Categoría"], y1=fila["Categoría"],
                      line=dict(color=ROJO, width=3))
    fig.update_traces(marker_size=16, textposition="middle right")
    fig.update_yaxes(type="category", title="")
    fig.update_xaxes(range=[0, d[nombre].max() * 1.2])
    lider, segundo = Datos.iloc[0], Datos.iloc[1]
    quienes = "personas" if variable in ("Asesor de piso", "Vendedor") else "canales"
    puntos = [f"**{lider['Categoría']}** lidera con **{lider[nombre]}** ventas ({lider['Porcentaje']}%).",
              f"Le sigue **{segundo['Categoría']}** con **{segundo[nombre]}**."]
    if len(Datos) > 10 and Datos["Porcentaje"].head(10).sum() < 99.5:
        puntos.append(f"El top 10 junta **{Datos['Porcentaje'].head(10).sum():.0f}%** de las ventas "
                      f"de {len(Datos)} {quienes}.")
    else:
        ceros = (Datos[nombre] == 0).sum()
        if ceros:
            puntos.append(f"**{ceros}** {quienes} no tuvieron ninguna venta.")
    pregunta = "¿Quiénes venden más?" if quienes == "personas" else "¿Qué canales venden más?"
    return fig, pregunta, puntos

#TREEMAP: cada cuadro es una categoría; su tamaño es lo que aporta
def g_treemap(df, Datos, nombre, columna, medida, variable):
    d = Datos.head(15)
    fig = px.treemap(d, path=[px.Constant("Total"), "Categoría"], values=nombre,
                     color=nombre, color_continuous_scale="Reds")
    fig.update_traces(texttemplate="%{label}<br>%{value}", root_color="white")
    fig.update_layout(coloraxis_showscale=False)
    return fig, "¿Cuánto aporta cada uno?", [
        f"El cuadro más grande es **{Datos['Categoría'].iloc[0]}**: **{Datos['Porcentaje'].iloc[0]}%** del total.",
        f"Los 3 cuadros más grandes juntan **{Datos['Porcentaje'].head(3).sum():.0f}%**.",
        "Mientras más grande y oscuro el cuadro, más aporta."]

#DONA: pocas categorías
def g_dona(df, Datos, nombre, columna, medida, variable):
    Datos = Datos.copy()
    if variable == "Bono de marketing":
        Datos["Categoría"] = Datos["Categoría"].replace({"0": "Sin bono", "50000": "Con bono de $50,000"})
    fig = px.pie(Datos, names="Categoría", values=nombre, hole=0.5,
                 color_discrete_sequence=[ROJO, "#1A1A1A", GRIS, "#E06B7D", "#4D4D4D", "#F2B8C0"])
    fig.update_traces(textinfo="label+percent", textfont_size=14, sort=False)
    fig.update_layout(showlegend=False)
    p = Datos.sort_values(nombre, ascending=False)
    if VARIABLES[variable][2] == "Numérica discreta":
        #Variables numéricas: hablamos de "registros" (meses), no de "parte del total"
        donde = "de los meses" if VARIABLES[variable][0] in ("TOPS_TDH", "Marketing") else "de los registros"
        puntos = [f"**{p['Categoría'].iloc[0]}** aparece en **{p['Porcentaje'].iloc[0]:.0f}%** {donde}."]
        if len(p) > 1:
            puntos.append(f"**{p['Categoría'].iloc[1]}** aparece en **{p['Porcentaje'].iloc[1]:.0f}%**.")
        pregunta = "¿Qué tan seguido aparece cada valor?"
    else:
        puntos = [f"**{p['Categoría'].iloc[0]}** ocupa **{p['Porcentaje'].iloc[0]}%** del total."]
        if len(p) > 1:
            puntos.append(f"Le sigue **{p['Categoría'].iloc[1]}** con **{p['Porcentaje'].iloc[1]}%**.")
        pregunta = "¿Qué parte del total es cada una?"
    return fig, pregunta, puntos

#DONA TOP 5 VS EL RESTO: muchas categorías
def g_top5(df, Datos, nombre, columna, medida, variable):
    resto = f"Las otras {len(Datos) - 5}"
    d = pd.DataFrame({"Grupo": ["Las 5 más grandes", resto],
                      "Valor": [Datos[nombre].head(5).sum(), Datos[nombre].iloc[5:].sum()]})
    fig = px.pie(d, names="Grupo", values="Valor", hole=0.5, color="Grupo",
                 color_discrete_map={"Las 5 más grandes": ROJO, resto: GRIS})
    fig.update_traces(textinfo="label+percent", textfont_size=14)
    fig.update_layout(showlegend=False)
    pct5 = Datos["Porcentaje"].head(5).sum()
    return fig, "¿Se concentra en pocas?", [
        f"Solo **5 de {len(Datos)}** juntan **{pct5:.0f}%** del total.",
        "Está **muy concentrado** en pocas." if pct5 >= 50 else "Está **repartido** entre muchas."]

#BARRA AL 100%: "de cada 100..."
def g_barra100(df, Datos, nombre, columna, medida, variable):
    d = Datos.copy()
    d["Total"] = "Ventas"
    fig = px.bar(d, x="Porcentaje", y="Total", color="Categoría", orientation="h", text="Categoría",
                 color_discrete_sequence=[ROJO, "#1A1A1A", GRIS])
    fig.update_traces(texttemplate="%{text}<br>%{x:.0f}%", textposition="inside",
                      insidetextanchor="middle", textfont_size=16)
    fig.update_layout(showlegend=False, barmode="stack")
    fig.update_yaxes(visible=False)
    fig.update_xaxes(title="% de las ventas", range=[0, 100])
    partes = ", ".join(f"**{r['Porcentaje']:.0f}** de {r['Categoría']}" for _, r in d.iterrows())
    return fig, "De cada 100 ventas, ¿de dónde vienen?", [
        f"De cada 100 ventas: {partes}.",
        f"**{d['Categoría'].iloc[0]}** es el canal más fuerte, pero ninguno pasa de la mitad."]

#HISTOGRAMA: cuántas personas venden poco, regular o mucho
def g_histograma(df, Datos, nombre, columna, medida, variable):
    fig = px.histogram(Datos, x=nombre, nbins=10, color_discrete_sequence=[ROJO])
    fig.update_traces(marker_line_color="white", marker_line_width=2)
    fig.update_xaxes(title="Ventas totales por vendedor")
    fig.update_yaxes(title="Número de vendedores")
    mediana = Datos[nombre].median()
    altos = (Datos[nombre] >= 20).sum()
    return fig, "¿Cuántos vendedores venden poco y cuántos mucho?", [
        f"La mitad de los vendedores tiene **{mediana:.0f} ventas o menos** en total.",
        f"Solo **{altos} de {len(Datos)}** llegan a 20 ventas o más.",
        "Cada barra agrupa vendedores con ventas parecidas; la barra más alta es lo más común."]

#BARRAS VERTICALES: valores numéricos en orden 0, 1, 2...
def g_barras_v(df, Datos, nombre, columna, medida, variable):
    fig = px.bar(Datos, x="Categoría", y=nombre, text="Porcentaje", color_discrete_sequence=[ROJO])
    fig.update_traces(texttemplate="%{text}%", textposition="outside", cliponaxis=False)
    fig.update_xaxes(type="category", title=variable)
    fig.update_yaxes(range=[0, Datos[nombre].max() * 1.2])
    p = Datos.sort_values(nombre, ascending=False).iloc[0]
    return fig, "¿Qué valor se repite más?", [
        f"El valor más común es **{p['Categoría']}** (**{p['Porcentaje']}%** de los registros).",
        f"Los valores van de **{Datos['Categoría'].iloc[0]}** a **{Datos['Categoría'].iloc[-1]}**."]

#DONA VENDIÓ / NO VENDIÓ
def g_vendio(df, Datos, nombre, columna, medida, variable):
    d = df[columna].apply(lambda v: "Vendió" if v > 0 else "No vendió").value_counts().reset_index()
    d.columns = ["Resultado", "Registros"]
    fig = px.pie(d, names="Resultado", values="Registros", hole=0.5, color="Resultado",
                 color_discrete_map={"Vendió": ROJO, "No vendió": GRIS})
    fig.update_traces(textinfo="label+percent", textfont_size=15)
    fig.update_layout(showlegend=False)
    sin = (df[columna] <= 0).mean() * 100
    return fig, "¿En cuántos meses hubo venta?", [
        f"En **{sin:.0f}%** de los registros no hubo ninguna venta.",
        f"Solo **{100 - sin:.0f} de cada 100** registros tienen al menos una venta."]

#VELOCÍMETRO: % de meses con al menos una venta
def g_gauge_venta(df, Datos, nombre, columna, medida, variable):
    pct = (df[columna] > 0).mean() * 100
    fig = go.Figure(go.Indicator(mode="gauge+number", value=pct, number={"suffix": "%"},
                                 gauge={"axis": {"range": [0, 100]}, "bar": {"color": ROJO},
                                        "steps": [{"range": [0, 100], "color": "#F2F2F2"}]}))
    return fig, "¿Qué tan seguido vende un vendedor?", [
        f"Un vendedor cierra al menos una venta en **{pct:.0f}%** de sus meses.",
        f"En **{100 - pct:.0f}%** de los meses no vende nada.",
        "La aguja llena significaría que todos venden todos los meses."]

#VELOCÍMETRO DEL CLIMA LABORAL (escala de 1 a 5)
def g_gauge_clima(df, Datos, nombre, columna, medida, variable):
    prom = df[columna].mean()
    fig = go.Figure(go.Indicator(mode="gauge+number", value=prom, number={"valueformat": ".2f"},
                                 gauge={"axis": {"range": [0, 5]}, "bar": {"color": ROJO},
                                        "steps": [{"range": [0, 3], "color": "#F2F2F2"},
                                                  {"range": [3, 4], "color": "#E5E5E5"},
                                                  {"range": [4, 5], "color": "#D9D9D9"}]}))
    return fig, "¿Cómo está el clima laboral?", [
        f"El promedio es **{prom:.2f} de 5**: el equipo califica bien su ambiente de trabajo.",
        f"La calificación más baja fue **{df[columna].min()}** y la más alta **{df[columna].max()}**."]

#BOXPLOT: rango de un mes normal
def g_box(df, Datos, nombre, columna, medida, variable):
    fig = px.box(df, x=columna, points="all", hover_data=["Año", "Mes"], color_discrete_sequence=[ROJO])
    fig.update_xaxes(title=variable)
    q1, med, q3 = df[columna].quantile([0.25, 0.5, 0.75])
    peor = df.loc[df[columna].idxmax()]
    return fig, "¿Cuántos hay en un mes normal?", [
        f"En un mes normal hay **entre {como_texto(float(q1))} y {como_texto(float(q3))}** (la caja).",
        f"El valor de en medio es **{como_texto(float(med))}**.",
        f"El mes más alto fue **{peor['Mes']} {peor['Año']}** con **{como_texto(float(peor[columna]))}**."]

#VIOLÍN: forma de la distribución
def g_violin(df, Datos, nombre, columna, medida, variable):
    fig = px.violin(df, x=columna, box=True, points="all", hover_data=["Año", "Mes"],
                    color_discrete_sequence=[ROJO])
    fig.update_xaxes(title=variable)
    med = df[columna].median()
    return fig, "¿Dónde se concentran los meses?", [
        f"La mayoría de los meses tiene alrededor de **{como_texto(float(med))}**.",
        f"Va de **{como_texto(float(df[columna].min()))}** a **{como_texto(float(df[columna].max()))}** por mes.",
        "La parte más ancha de la figura es donde caen más meses."]

#LÍNEA MES A MES
def g_linea(df, Datos, nombre, columna, medida, variable):
    s = serie_mensual(df, columna, medida)
    fig = px.line(s, x="Mes del año", y="Valor", markers=True, color_discrete_sequence=[ROJO],
                  labels={"Valor": variable})
    fig.update_xaxes(type="category", title="")
    alto, bajo = s.loc[s["Valor"].idxmax()], s.loc[s["Valor"].idxmin()]
    return fig, "¿Cómo se movió mes a mes?", [
        f"El punto más alto fue **{alto['Mes del año']}** con **{como_texto(float(alto['Valor']))}**.",
        f"El más bajo fue **{bajo['Mes del año']}** con **{como_texto(float(bajo['Valor']))}**.",
        f"Empezó en **{como_texto(float(s['Valor'].iloc[0]))}** y terminó en "
        f"**{como_texto(float(s['Valor'].iloc[-1]))}**."]

#BARRAS POR MES: en qué meses hubo bono
def g_bono_mes(df, Datos, nombre, columna, medida, variable):
    s = serie_mensual(df, columna, None)
    s["Bono"] = s["Valor"].apply(lambda v: "Con bono" if v > 0 else "Sin bono")
    s["Altura"] = 1
    fig = px.bar(s, x="Mes del año", y="Altura", color="Bono",
                 color_discrete_map={"Con bono": ROJO, "Sin bono": "#E5E5E5"})
    fig.update_xaxes(type="category", title="")
    fig.update_yaxes(visible=False)
    fig.update_layout(legend_title="", legend=dict(orientation="h", y=-0.3, x=0), bargap=0.1)
    con = s[s["Bono"] == "Con bono"]
    puntos = [f"Hubo bono en **{len(con)} de {len(s)}** meses."]
    if len(con):
        puntos.append(f"El primer bono llegó en **{con['Mes del año'].iloc[0]}**; antes nunca hubo.")
    return fig, "¿En qué meses hubo bono?", puntos

#Qué dos gráficas lleva cada variable
GRAFICAS = {
    "Canal (Funnel)":            [g_treemap, g_lollipop],
    "Campaña digital":           [g_barras, g_top5],
    "Canal principal":           [g_barra100, g_dona],
    "Asesor de piso":            [g_lollipop, g_top5],
    "Vendedor":                  [g_treemap, g_histograma],
    "Ventas por asesor de piso": [g_barras_v, g_vendio],
    "Ventas por vendedor":       [g_barras_v, g_gauge_venta],
    "Bono de marketing":         [g_dona, g_bono_mes],
    "Bajas de personal":         [g_barras_v, g_linea],
    "Vacantes":                  [g_box, g_linea],
    "APVS Oro":                  [g_dona, g_linea],
    "APVS Plata":                [g_barras_v, g_box],
    "APVS Bronce":               [g_violin, g_linea],
    "Clima laboral":             [g_gauge_clima, g_dona],
}

###############################################################################
#CREACIÓN DEL DASHBOARD
#Generamos los encabezados para la barra lateral (sidebar)
aplicar_estilos()
#Si el equipo guarda el logo como logo_gac.png junto a app.py, aparece aquí
if os.path.exists(LOGO):
    st.sidebar.image(LOGO, width=200)
else:
    st.sidebar.title("GAC MOTOR")
st.sidebar.caption("Etapa I · Extracción de características")

#Widget 1: Selectbox
#Menu desplegable de las vistas del dashboard
View = st.sidebar.selectbox(label="Vista", options=["Hallazgos principales",
                                                    "Análisis univariado",
                                                    "Comparación por periodo"])

###############################################################################
# CONTENIDO DE LA VISTA 1: HALLAZGOS PRINCIPALES
if View == "Hallazgos principales":
    st.title("Hallazgos principales")
    st.write("Las cinco respuestas más importantes que salen de las 15 variables. "
             "Para ver cualquier variable a detalle, elige **Análisis univariado** en el menú.")
    st.divider()

    #HALLAZGO 1: ventas por canal principal
    Canales, _ = frecuencias(bases["Principales_Canales"], "Canal", "Ventas", "Categórica")
    figure1 = px.pie(Canales, names="Categoría", values="Ventas", hole=0.5,
                     color_discrete_sequence=[ROJO, "#1A1A1A", GRIS])
    figure1.update_traces(textinfo="label+percent", textfont_size=15, sort=False)
    figure1.update_layout(showlegend=False)
    seccion("1. ¿Por dónde llegan las ventas?", figure1, [
        f"**{Canales['Categoría'].iloc[0]}** es el canal que más vende: "
        f"**{Canales['Porcentaje'].iloc[0]:.0f}%** de {Canales['Ventas'].sum():,} ventas.",
        f"**{Canales['Categoría'].iloc[1]}** sigue con **{Canales['Porcentaje'].iloc[1]:.0f}%**.",
        "Ningún canal pasa de la mitad: las ventas están repartidas."])

    #HALLAZGO 2: embudo de venta
    Embudo = datos_embudo(preparar(bases["Funnel"], "Indicador del embudo"))
    figure2 = px.funnel(Embudo, x="Real", y="Indicador", color_discrete_sequence=[ROJO])
    figure2.update_traces(textinfo="value")
    figure2.update_yaxes(title="")
    citas = Embudo["Real"].iloc[0]
    ventas = Embudo.loc[Embudo["Indicador"] == "Ventas", "Real"].iloc[0]
    fuga = Embudo.iloc[1:].sort_values("Pasa").iloc[0]
    seccion("2. ¿Cuántos clientes llegan hasta la venta?", figure2, [
        f"De **{citas:,}** citas se cierran **{ventas:,}** ventas.",
        f"**{ventas / citas * 100:.0f} de cada 100** citas terminan en venta.",
        f"La mayor pérdida es al llegar a **{fuga['Indicador']}**: solo pasa el **{fuga['Pasa']:.0f}%**."])

    #HALLAZGO 3: campañas que traen más leads
    Campanas, _ = frecuencias(bases["MKT_Digital"], "Campaña", "Leads", "Categórica")
    Top5 = Campanas.head(5)
    figure3 = px.bar(Top5.iloc[::-1], x="Leads", y="Categoría", orientation="h",
                     text="Leads", color_discrete_sequence=[ROJO])
    figure3.update_traces(textposition="outside", cliponaxis=False)
    figure3.update_yaxes(title="")
    figure3.update_xaxes(range=[0, Top5["Leads"].max() * 1.2])
    seccion("3. ¿Qué campañas digitales traen más leads?", figure3, [
        f"Las 5 campañas juntan **{Top5['Porcentaje'].sum():.0f}%** de los leads.",
        f"**{Top5['Categoría'].iloc[0]}** trae sola el **{Top5['Porcentaje'].iloc[0]:.0f}%**.",
        "Las campañas de WhatsApp dominan el top."])

    #HALLAZGO 4: vendedores con y sin venta en el mes
    Vendedores = bases["Ventas_por_Asesor"]
    figure4, _, _ = g_vendio(Vendedores, None, None, "Ventas", None, "")
    sin_venta = (Vendedores["Ventas"] <= 0).mean() * 100
    seccion("4. ¿Los vendedores venden cada mes?", figure4, [
        f"En **{sin_venta:.0f}%** de los meses el vendedor no cerró ninguna venta.",
        "Las ventas dependen de pocos vendedores."])

    #HALLAZGO 5: nivel de los asesores (personal)
    Niveles = pd.DataFrame({
        "Nivel": ["Oro", "Plata", "Bronce"],
        "Asesores al mes": [bases["TOPS_TDH"]["APVS_Oro"].mean(),
                            bases["TOPS_TDH"]["APVS_Plata"].mean(),
                            bases["TOPS_TDH"]["APVS_Bronce"].mean()]}).round(1)
    figure5 = px.bar(Niveles, x="Nivel", y="Asesores al mes", text="Asesores al mes",
                     color="Nivel", color_discrete_map={"Oro": ROJO, "Plata": "#1A1A1A", "Bronce": GRIS})
    figure5.update_traces(textposition="outside", cliponaxis=False)
    figure5.update_layout(showlegend=False)
    figure5.update_yaxes(range=[0, Niveles["Asesores al mes"].max() * 1.25])
    seccion("5. ¿Qué nivel tienen los asesores?", figure5, [
        f"En un mes promedio hay **{Niveles['Asesores al mes'].iloc[2]:.0f} Bronce** y solo "
        f"**{Niveles['Asesores al mes'].iloc[0]:.0f} Oro**.",
        "La mayoría del equipo está en el nivel más bajo."])

    st.caption("El conjunto incluye 6 variables categóricas y 9 numéricas discretas. "
               "Confirmen con el profesor si las 15 deben ser estrictamente categóricas.")

###############################################################################
# FILTROS DE LAS VISTAS 2 Y 3 (en la barra lateral)
else:
    #Widget 2: Selectbox de base de datos
    Base = st.sidebar.selectbox(label="Base de datos",
                                options=sorted({b for b, _, _, _ in VARIABLES.values()}))
    #Widget 3: Selectbox de variable (solo las de la base elegida)
    Variable_Cat = st.sidebar.selectbox(label="Variable",
                                        options=[v for v, d in VARIABLES.items() if d[0] == Base])
    _, columna, tipo, medida = VARIABLES[Variable_Cat]

    #Widget 4 y 5: años y meses (solo los que existen en la base elegida)
    df = bases[Base]
    anios = sorted(df["Año"].unique())
    Anio_sel = st.sidebar.multiselect("Año", options=anios, default=anios)
    meses = [m for m in MESES if m in df.loc[df["Año"].isin(Anio_sel), "Mes"].unique()]
    Mes_sel = st.sidebar.multiselect("Mes", options=meses, default=meses)
    df = df[df["Año"].isin(Anio_sel) & df["Mes"].isin(Mes_sel)]
    df = preparar(df, Variable_Cat)

    if df.empty:
        st.warning("No hay datos con esos filtros. Elige al menos un año y un mes.")
        st.stop()

    #Frecuencias de la variable seleccionada (se usan en las gráficas)
    Datos, nombre = frecuencias(df, columna, medida, tipo, Variable_Cat)
    Principal = Datos.sort_values(nombre, ascending=False).iloc[0]

    ###########################################################################
    # CONTENIDO DE LA VISTA 2: ANÁLISIS UNIVARIADO
    if View == "Análisis univariado":
        st.title(Variable_Cat)

        #-------------------------------------------------------------------
        #CASO ESPECIAL: INDICADOR DEL EMBUDO
        if Variable_Cat == "Indicador del embudo":
            st.write("Cuántos clientes avanzan en cada paso del proceso de venta, "
                     "desde que agendan una cita hasta que se formaliza la compra.")
            st.divider()
            Embudo = datos_embudo(df)
            fuga = Embudo.iloc[1:].sort_values("Pasa").iloc[0]
            anterior = ETAPAS[ETAPAS.index(fuga["Indicador"]) - 1]
            citas = Embudo["Real"].iloc[0]
            ventas = Embudo.loc[Embudo["Indicador"] == "Ventas", "Real"].iloc[0]

            #GRAPH 1: EMBUDO (FUNNEL)
            figure1 = px.funnel(Embudo, x="Real", y="Indicador", color_discrete_sequence=[ROJO])
            figure1.update_traces(textinfo="value+percent previous")
            figure1.update_yaxes(title="")
            seccion("¿Cuántos clientes llegan a cada paso?", figure1, [
                f"De **{citas:,}** citas se cierran **{ventas:,}** ventas "
                f"(**{ventas / max(citas, 1) * 100:.0f} de cada 100**).",
                f"La mayor pérdida: de **{anterior}** a **{fuga['Indicador']}** solo pasa el "
                f"**{fuga['Pasa']:.0f}%**.",
                "El % de cada barra es cuántos avanzaron desde el paso anterior."])

            #GRAPH 2: CUMPLIMIENTO DEL OBJETIVO POR ETAPA
            Embudo["Estado"] = Embudo["Cumplimiento"].apply(
                lambda c: "Cumple la meta" if c >= 100 else "No cumple la meta")
            figure2 = px.bar(Embudo.iloc[::-1], x="Cumplimiento", y="Indicador", orientation="h",
                             text="Cumplimiento", color="Estado",
                             color_discrete_map={"Cumple la meta": GRIS, "No cumple la meta": ROJO})
            figure2.update_traces(texttemplate="%{text:.0f}%", textposition="outside", cliponaxis=False)
            figure2.add_vline(x=100, line_dash="dash", line_color="black")  #Meta = 100%
            figure2.update_yaxes(title="")
            figure2.update_xaxes(title="Cumplimiento (%)",
                                 range=[0, max(Embudo["Cumplimiento"].max(), 100) * 1.2])
            figure2.update_layout(legend_title="", legend=dict(orientation="h", y=-0.2, x=0))
            peor = Embudo.sort_values("Cumplimiento").iloc[0]
            cumplen = (Embudo["Cumplimiento"] >= 100).sum()
            seccion("¿Qué pasos alcanzan su meta?", figure2, [
                f"Solo **{cumplen} de {len(Embudo)}** pasos llegan a su meta (línea punteada).",
                f"El más lejos es **{peor['Indicador']}**, con **{peor['Cumplimiento']:.0f}%**.",
                "Los primeros pasos cumplen; el problema está al final del proceso."])

            st.caption("Nota: no se incluyen Leads generados ni Leads efectivos porque vienen rellenados "
                       "con la media (83.06 se repite en varios meses), ni Cerrador (solo aparece un mes).")

        #-------------------------------------------------------------------
        #RESTO DE LAS VARIABLES: cada una con sus dos gráficas del catálogo
        else:
            if Variable_Cat == "Canal (Funnel)":
                st.write("Ventas de cada canal. Se quitó GAC Angelopolis porque es el total de la agencia.")
            elif tipo == "Numérica discreta":
                st.write(f"Cómo se reparten los valores de **{Variable_Cat}** en la base {Base}.")
            else:
                st.write(f"Cuánto aporta cada categoría al total de **{nombre.lower()}** en la base {Base}.")

            #Fila de tarjetas (solo 3)
            Contenedor_A, Contenedor_B, Contenedor_C = st.columns(3)
            Contenedor_A.metric("Número de categorías", len(Datos))
            Contenedor_B.metric("Valor más común" if tipo == "Numérica discreta" else "La más grande",
                                Principal["Categoría"])
            Contenedor_C.metric("Su parte del total", f"{Principal['Porcentaje']}%")
            st.divider()

            #GRAPH 1 y GRAPH 2: las que le tocan a esta variable
            usadas = []
            for grafica in GRAFICAS[Variable_Cat]:
                #Si una gráfica necesita más categorías de las que dejan los filtros, usamos barras
                if grafica in (g_top5, g_lollipop) and len(Datos) <= 5:
                    grafica = g_barras
                if grafica in (g_box, g_violin, g_linea) and len(df) < 3:
                    grafica = g_barras_v
                if grafica in usadas:  #No repetir la misma gráfica dos veces
                    continue
                usadas.append(grafica)
                figura, pregunta, puntos = grafica(df, Datos, nombre, columna, medida, Variable_Cat)
                seccion(pregunta, figura, puntos)

            #Notas que solo aparecen cuando aplican
            if columna == "Ventas" and not medida:
                st.caption("Nota: los valores con decimales (0.18 y 0.53) vienen así en la base limpia; "
                           "son promedios usados para rellenar datos faltantes, no ventas reales.")
            if Base == "TOPS_TDH":
                st.caption("Nota: TOPS_TDH tiene un registro por mes (19 en total); tómalo como referencia, "
                           "no como tendencia firme.")

    ###########################################################################
    # CONTENIDO DE LA VISTA 3: COMPARACIÓN POR PERIODO
    elif View == "Comparación por periodo":
        st.title(f"{Variable_Cat}: cambio en el tiempo")
        st.write("Compara cómo cambia la variable de un periodo a otro.")

        #Widget 6: Radio para comparar por año o por mes
        Periodo = st.radio("Comparar por", ["Año", "Mes"], horizontal=True)
        st.divider()
        datos = df.copy()
        #Año-mes para no juntar, por ejemplo, febrero 2024 con febrero 2025
        numero_mes = {m: f"{i:02d}" for i, m in enumerate(MESES, 1)}
        datos["AñoMes"] = datos["Año"].astype(str) + "-" + datos["Mes"].map(numero_mes)
        datos["Categoría"] = datos[columna].apply(como_texto)
        datos["Valor"] = datos[medida] if medida else 1
        #Primero sumamos cada categoría por mes (un renglón por categoría y mes)
        datos = datos.groupby(["Año", "AñoMes", "Categoría"], as_index=False)["Valor"].sum()
        if Periodo == "Año":
            #Los años no tienen los mismos meses (2026 llega solo a medio año), así que
            #comparamos el PROMEDIO POR MES de cada año y no el total
            meses_por_anio = datos.groupby("Año")["AñoMes"].nunique()
            datos = datos.groupby(["Año", "Categoría"], as_index=False)["Valor"].sum()
            datos["Valor"] = (datos["Valor"] / datos["Año"].map(meses_por_anio)).round(1)
            datos["Periodo"] = datos["Año"].astype(str)
            etiqueta = f"{nombre} (promedio por mes)"
            st.caption("Por año se compara el promedio por mes, porque no todos los años tienen "
                       "los mismos meses: " + ", ".join(f"{a} tiene {n} meses"
                                                       for a, n in meses_por_anio.items()) + ".")
        else:
            datos["Periodo"] = datos["AñoMes"]
            etiqueta = nombre
        #Formato de los números: con un decimal si son promedios
        fmt = ",.1f" if Periodo == "Año" else ",.0f"

        #Categorías a mostrar: etapas en orden para el embudo; las 8 más grandes para lo demás
        if Variable_Cat == "Indicador del embudo":
            top8 = [e for e in ETAPAS if e in set(datos["Categoría"])]
        else:
            top8 = list(Datos.sort_values(nombre, ascending=False).head(8)["Categoría"])

        #GRAPH 3: BARRAS de una categoría en cada periodo
        #Widget 7: elegir una categoría para ver cómo cambia
        Categoria_sel = st.selectbox("Elige una categoría", options=top8)
        Serie = (datos[datos["Categoría"] == Categoria_sel]
                 .groupby("Periodo")["Valor"].sum().reset_index())
        figure3 = px.bar(Serie, x="Periodo", y="Valor", text="Valor",
                         color_discrete_sequence=[ROJO], labels={"Valor": etiqueta})
        figure3.update_traces(texttemplate="%{text:" + fmt + "}", textposition="outside", cliponaxis=False)
        figure3.update_xaxes(type="category")
        figure3.update_yaxes(range=[0, max(Serie["Valor"].max(), 1) * 1.2])
        puntos = []
        if len(Serie) > 1 and Serie["Valor"].iloc[0] > 0:
            cambio = (Serie["Valor"].iloc[-1] / Serie["Valor"].iloc[0] - 1) * 100
            puntos.append(f"De {Serie['Periodo'].iloc[0]} a {Serie['Periodo'].iloc[-1]} "
                          f"{'subió' if cambio >= 0 else 'bajó'} **{abs(cambio):.0f}%**.")
        alto = Serie.loc[Serie["Valor"].idxmax()]
        puntos.append(f"El periodo más alto fue **{alto['Periodo']}** con **{alto['Valor']:{fmt}}**.")
        if len(Serie) > 2:
            bajo = Serie.loc[Serie["Valor"].idxmin()]
            puntos.append(f"El más bajo fue **{bajo['Periodo']}** con **{bajo['Valor']:{fmt}}**.")
        seccion(f"¿Cómo cambió {Categoria_sel}?", figure3, puntos)

        #GRAPH 4: HEATMAP (categorías principales x periodo)
        Heat = datos.pivot_table(index="Categoría", columns="Periodo", values="Valor",
                                 aggfunc="sum", fill_value=0)
        Heat = Heat.reindex(top8, fill_value=0)
        figure4 = px.imshow(Heat, text_auto=fmt.replace(",", ""), aspect="auto", color_continuous_scale="Reds",
                            labels={"color": etiqueta, "x": "Periodo", "y": ""})
        figure4.update_xaxes(type="category")
        mejor = Heat.stack().idxmax()
        #Categoría que más creció entre el primer y el último periodo
        puntos = [f"El cuadro más oscuro es **{mejor[0]}** en **{mejor[1]}**."]
        if Heat.shape[1] > 1:
            crecimiento = (Heat.iloc[:, -1] - Heat.iloc[:, 0])
            puntos.append(f"La que más creció fue **{crecimiento.idxmax()}** y la que más bajó "
                          f"**{crecimiento.idxmin()}**.")
        puntos.append("Lee cada fila de izquierda a derecha: si se oscurece, va subiendo.")
        seccion("Mapa de calor: todas las categorías a la vez", figure4, puntos)
