import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit_authenticator as stauth
import os, datetime, io, requests, re
import numpy as np

st.set_page_config(page_title="ERP Gerencial", layout="wide")

# Estilos corporativos de Bruselas para proteger la interfaz visual
st.markdown("""
    <style>
    .stApp { background-color: #FAF8F5 !important; font-family: sans-serif !important; }
    section[data-testid="stSidebar"] { background-color: #2B1810 !important; min-width: 270px !important; }
    section[data-testid="stSidebar"] h2 { color: #E6C280 !important; font-family: serif !important; letter-spacing: 2px !important; text-align: center !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label p { color: #F5F0E6 !important; font-size: 0.95rem !important; font-weight: 600 !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] [data-checked="true"] label p { color: #E6C280 !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label { background-color: transparent !important; border: none !important; padding: 12px 15px !important; display: flex !important; width: 100% !important; border-left: 4px solid transparent !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover, div[data-testid="stRadio"] div[role="radiogroup"] [data-checked="true"] label { background-color: #3D2419 !important; border-left: 4px solid #E6C280 !important; }
    div[data-testid="stMetric"] { background-color: #FFFFFF !important; border: 1px solid #EAE6DF !important; border-top: 4px solid #C29B68 !important; border-radius: 12px !important; padding: 20px 15px !important; }
    div[data-testid="stMetricLabel"] p { font-size: 0.75rem !important; text-transform: uppercase !important; color: #8C857B !important; font-weight: 600 !important; }
    div[data-testid="stMetricValue"] div { font-size: 1.9rem !important; font-weight: 700 !important; color: #1A365D !important; }
    </style>
""", unsafe_allow_html=True)

config = {
    "credentials": {"usernames": {
        "admin": {"name": "Administrador", "password": "Password123"},
        "gerente": {"name": "Gerente", "password": "Ventas2026"}
    }}
}

authenticator = stauth.Authenticate(config['credentials'], "cookie_limpia_2026", "clave_indestructible_sha256_2026", cookie_expiry_days=0)

if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None

#  termuina caja 1 empieza caja 2 botones panel


if st.session_state["authentication_status"] is not True:
    try: authenticator.login(location='main')
    except Exception: pass
    if st.session_state["authentication_status"] == False:
        st.error('Usuario o contraseña incorrectos.')
    elif st.session_state["authentication_status"] == None:
        st.warning('Por favor, ingresa tus credenciales para acceder al sistema Bruselas v 1.21.')

else:
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.markdown("<h2 style='margin-top:-30px;'>BRUSELAS</h2><p style='text-align:center; color:#A68565; font-size:0.75rem; letter-spacing:3px; margin-top:-10px; margin-bottom:20px;'>DASHBOARD</p>", unsafe_allow_html=True)
    st.sidebar.markdown(f"👤 **Usuario:** {st.session_state['name']}")
    
    # --- INYECCIÓN DE LA QUINTA OPCIÓN COMPLETA EN LA BARRA LATERAL ---
    menu = st.sidebar.radio("MENÚ PRINCIPAL:", [
        "📥 Importar Datos (TXT)", 
        "📊 Resumen CEO & Proyecciones", 
        "🏬 Comparativa Frente a Frente", 
        "📦 Top Margen Real (Quetzales)",
        "🕒 Por Tienda & Días"
    ])
    
    if "menu_actual" not in st.session_state: st.session_state["menu_actual"] = "📥 Importar Datos (TXT)"
    if menu != st.session_state["menu_actual"]:
        st.session_state["menu_actual"] = menu
        st.rerun()

    ARCHIVO_HISTORICO = "ventas_historico.parquet"

    def normalizar_columnas_df(df_crudo):
        df_crudo.columns = df_crudo.columns.astype(str).str.strip().str.replace('"', '').str.replace("'", "")
        m_caps = {c.upper(): c for c in df_crudo.columns}
        
        df_limpio = df_crudo.rename(columns={
            m_caps.get("MES", "Mes"): "Mes", m_caps.get("FECHA", "Fecha"): "Fecha",
            m_caps.get("AÑO", "Año"): "Año", m_caps.get("NOMBRE TIENDA", "Nombre TIENDA"): "Nombre TIENDA",
            m_caps.get("TIENDA", "TIENDA"): "TIENDA", m_caps.get("FAMILIA", "Familia"): "Familia", 
            m_caps.get("DIA", "Dia"): "Dia", m_caps.get("DÍA", "Dia"): "Dia", 
            m_caps.get("DOCUMENTO", "Documento"): "Documento", m_caps.get("PRODUCTO", "Producto"): "Producto", 
            m_caps.get("DESCRIPCION", "Descripcion"): "Descripcion", m_caps.get("DESCRIPCIÓN", "Descripcion"): "Descripcion"
        })
        df_limpio = df_limpio.loc[:, ~df_limpio.columns.duplicated()]
        
        if "Fecha" in df_limpio.columns:
            if isinstance(df_limpio["Fecha"], pd.DataFrame): df_limpio["Fecha"] = df_limpio["Fecha"].iloc[:, 0]
            df_limpio["Año"] = df_limpio["Fecha"].astype(str).str.extract(r'(\d{4})').fillna("2026")
            
        for c in ["Mes", "Año", "TIENDA", "Nombre TIENDA", "Familia", "Dia", "Documento", "Producto", "Descripcion", "Costo", "Valor", "Cantidad", "Semana", "SemanaMes", "Und-Mov"]:
            if c not in df_limpio.columns:
                df_limpio[c] = "0" if c in ["Costo", "Valor", "Cantidad", "Semana", "SemanaMes"] else "Desconocido"
            else:
                if isinstance(df_limpio[c], pd.DataFrame): df_limpio[c] = df_limpio[c].iloc[:, 0]
                df_limpio[c] = df_limpio[c].astype(str).str.strip()
        return df_limpio

    def obtener_datos():
        if os.path.exists(ARCHIVO_HISTORICO): 
            df = pd.read_parquet(ARCHIVO_HISTORICO)
            for col in ["Valor", "Costo", "Cantidad"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(r'[^0-9.-]', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            return df
        return None

    COLOR_PRIMARIO = "#2B1810" 
    COLOR_ACENTO = "#C29B68"   
    COLOR_FONDO = "#FAF8F5"  


    # ==========================================
    # MÓDULO 1: IMPORTAR DATOS
    # ==========================================
    if menu == "📥 Importar Datos (TXT)":
        st.title("📥 Panel de Control de Carga Híbrido")
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            st.markdown("### 💻 Carga manual desde PC")
            arch_local = st.file_uploader("Selecciona el archivo TXT local", type=["txt", "tsv"])
            if arch_local is not None and st.button("📥 Cargar desde Computadora", use_container_width=True):
                with st.spinner("Procesando matriz..."):
                    try:
                        df = pd.read_csv(arch_local, sep="\t", dtype=str, low_memory=False, on_bad_lines='skip', encoding='latin1')
                        df = normalizar_columnas_df(df)
                        df.to_parquet(ARCHIVO_HISTORICO, index=False)
                        with open("auditoria_drive.txt", "w", encoding="utf-8") as f: f.write(f"{arch_local.name}|{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
                        st.success("¡Sincronizado localmente con éxito!")
                        st.rerun()
                    except Exception as e: st.error(f"Error local: {str(e)}")
                    
        with btn_col2:
            st.markdown("### ☁️ Opción B: Sincronizar desde la Nube")
            if st.button("🔄 Ejecutar Descarga desde Drive", type="primary", use_container_width=True):
                with st.spinner("Sincronizando matriz de datos interna de forma automática..."):
                    try:
                        archivo_maestro_local = "c-inventfc.txt"
                        if not os.path.exists(archivo_maestro_local):
                            ruta_usuario_win = os.path.expanduser("~")
                            archivo_maestro_local = os.path.join(ruta_usuario_win, "Downloads", "c-inventfc.txt")
                        
                        if os.path.exists(archivo_maestro_local):
                            df = pd.read_csv(archivo_maestro_local, sep="\t", dtype=str, low_memory=False, on_bad_lines='skip', encoding='latin1')
                            df = normalizar_columnas_df(df)
                            df.to_parquet(ARCHIVO_HISTORICO, index=False)
                            with open("auditoria_drive.txt", "w", encoding="utf-8") as f: f.write(f"c-inventfc.txt|{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
                            st.success("¡Sincronizado desde sistema con éxito!")
                            st.rerun()
                        else:
                            st.error("No se detectó el archivo 'c-inventfc.txt' en rutas del sistema.")
                    except Exception as e: st.error(f"Error: {str(e)}")

    
     # ==========================================
    # MÓDULO 2: RESUMEN CEO & PROYECCIONES
    # ==========================================
    elif menu == "📊 Resumen CEO & Proyecciones":
        st.title("📊 Resumen Ejecutivo & Proyección de Demanda")
        df = obtener_datos()
        
        if df is not None:
            # --- PANEL DE FILTROS EN COLUMNAS CON EXTRACCIÓN PROTEGIDA ---
            f_col1, f_col2, f_col3 = st.columns(3)
            
            with f_col1:
                # Filtrar valores nulos o flotantes erróneos en la columna Año
                anios_limpios = df["Año"].dropna().astype(str).unique()
                años_disponibles = sorted([a for a in anios_limpios if a.strip() != ""])
                ano_sel = st.selectbox("📅 Año de Análisis", años_disponibles, index=len(años_disponibles)-1)
            
            with f_col2:
                # Convertir a texto estricto y eliminar nulos antes de ordenar alfabéticamente
                tiendas_limpias = df["Nombre TIENDA"].dropna().astype(str).unique()
                tiendas_filtradas = sorted([t for t in tiendas_limpias if t.strip() != ""])
                tiendas_disp = ["TODAS"] + tiendas_filtradas
                tienda_sel = st.selectbox("🏬 Filtrar por Sucursal", tiendas_disp)
                
            with f_col3:
                # Convertir a texto estricto y eliminar nulos antes de ordenar la familia
                familias_limpias = df["Familia"].dropna().astype(str).unique()
                familias_filtradas = sorted([f for f in familias_limpias if f.strip() != ""])
                familias_disp = ["TODAS"] + familias_filtradas
                familia_sel = st.selectbox("📦 Filtrar por Familia", familias_disp)

            # --- MAPEO CRONOLÓGICO SEGURO ---
            meses_map = {
                "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
                "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
            }
            
            df_time = df.copy()
            df_time["Mes_Limpio"] = df_time["Mes"].astype(str).str.strip().str.capitalize()
            df_time["Mes_Num"] = df_time["Mes_Limpio"].map(meses_map).fillna(1).astype(int)
            
            # --- APLICACIÓN DE FILTROS CRUZADOS EN DATA GENERAL ---
            if tienda_sel != "TODAS":
                df_time = df_time[df_time["Nombre TIENDA"].astype(str) == tienda_sel]
            if familia_sel != "TODAS":
                df_time = df_time[df_time["Familia"].astype(str) == familia_sel]
                
            # Data filtrada específica para las tarjetas KPI de un año particular
            df_ano = df_time[df_time["Año"].astype(str) == str(ano_sel)]

            # Consolidación cronológica para la tendencia
            df_cronologico = df_time.groupby(["Año", "Mes_Limpio", "Mes_Num"]).agg({"Valor": "sum"}).reset_index()
            df_cronologico = df_cronologico.rename(columns={"Mes_Limpio": "Mes"})
            
            df_cronologico["Mes_Str"] = df_cronologico["Mes_Num"].astype(str).str.zfill(2)
            df_cronologico["Eje_X_Texto"] = df_cronologico["Año"].astype(str) + "-" + df_cronologico["Mes_Str"] + "-" + df_cronologico["Mes"]
            df_cronologico = df_cronologico.sort_values(by=["Año", "Mes_Num"]).reset_index(drop=True)
            df_cronologico["Eje_X_Num"] = df_cronologico["Año"].astype(int) * 12 + df_cronologico["Mes_Num"]
            
            # --- CÁLCULO DE PROYECCIÓN AL SIGUIENTE MES ---
            if len(df_cronologico) > 1:
                x = df_cronologico["Eje_X_Num"].values
                y = df_cronologico["Valor"].values
                slope, intercept = np.polyfit(x, y, 1)
                
                prox_x = x[-1] + 1
                prediccion_proximo_mes = slope * prox_x + intercept
                if prediccion_proximo_mes < 0: prediccion_proximo_mes = y[-1] * 1.02
                
                ultimo_mes_num = df_cronologico["Mes_Num"].iloc[-1]
                ultimo_ano_num = int(df_cronologico["Año"].iloc[-1])
                
                if ultimo_mes_num == 12:
                    prox_mes_num = 1
                    prox_ano_num = ultimo_ano_num + 1
                else:
                    prox_mes_num = ultimo_mes_num + 1
                    prox_ano_num = ultimo_ano_num
                    
                nombres_meses = {v: k for k, v in meses_map.items()}
                nombre_prox_mes_etiqueta = nombres_meses[prox_mes_num]
                
                prox_mes_str = str(prox_mes_num).zfill(2)
                eje_x_proyeccion = f"{prox_ano_num}-{prox_mes_str}-{nombre_prox_mes_etiqueta}"
                nombre_prox_mes_kpi = f"{nombre_prox_mes_etiqueta} {prox_ano_num}"
            else:
                prediccion_proximo_mes = df_time["Valor"].sum() * 0.08
                eje_x_proyeccion = "2026-06-Junio"
                nombre_prox_mes_kpi = "Junio 2026"

            # Construcción de capas de graficación
            df_plot_historico = df_cronologico[["Eje_X_Texto", "Valor"]].copy()
            df_plot_historico["Tipo"] = "Ventas Reales Históricas"
            
            df_plot_proyeccion = pd.DataFrame([
                {"Eje_X_Texto": df_cronologico["Eje_X_Texto"].iloc[-1], "Valor": df_cronologico["Valor"].iloc[-1], "Tipo": "Proyección de Tendencia"},
                {"Eje_X_Texto": eje_x_proyeccion, "Valor": prediccion_proximo_mes, "Tipo": "Proyección de Tendencia"}
            ])
            
            df_grafico_completo = pd.concat([df_plot_historico, df_plot_proyeccion]).reset_index(drop=True)
            lista_orden_secuencial = list(df_cronologico["Eje_X_Texto"].unique()) + [eje_x_proyeccion]

            # KPIs Superiores adaptados a los filtros aplicados
            v_totales = df_ano["Valor"].sum()
            c_totales = df_ano["Costo"].sum()
            m_total_q = v_totales - c_totales
            
            m1, m2, m3 = st.columns(3)
            m1.metric("VENTAS NETAS TOTALES", f"Q {v_totales / 1e6:,.2f}M")
            m2.metric("MARGEN DE UTILIDAD BRUTA", f"Q {m_total_q / 1e6:,.2f}M")
            m3.metric(f"PROYECCIÓN ALGORÍTMICA ({nombre_prox_mes_kpi.upper()})", f"Q {prediccion_proximo_mes / 1e6:,.2f}M")
            
            st.markdown("---")
            st.subheader("📉 Análisis de Tendencia Histórica y Línea de Predicción Financiera")
            
            fig = px.line(
                df_grafico_completo, x="Eje_X_Texto", y="Valor", color="Tipo",
                category_orders={"Eje_X_Texto": lista_orden_secuencial},
                color_discrete_sequence=[COLOR_PRIMARIO, COLOR_ACENTO], markers=True
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='white', margin=dict(l=20, r=20, t=30, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
                yaxis=dict(showgrid=True, gridcolor='#EAE6DF', title="Montos de Venta (Q)", tickformat=",.2s"),
                xaxis=dict(showgrid=True, gridcolor='#EAE6DF', tickangle=-30, title=None, type='category')
            )
            fig.for_each_trace(lambda t: t.update(line=dict(dash='dash', width=3)) if t.name == "Proyección de Tendencia" else t.update(line=dict(width=3)))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay matriz de datos históricos activa. Cargue un archivo en la primera pestaña.")



    # ==========================================
    # MÓDULO 3: COMPARATIVA FRENTE A FRENTE
    # ==========================================
    elif menu == "🏬 Comparativa Frente a Frente":
        st.title("🏬 Comparador de Rendimiento Comercial Frente a Frente")
        df = obtener_datos()
        
        if df is not None:
            # --- PANEL DE FILTROS SUPERIORES CRUZADOS PROTEGIDOS ---
            f_col1, f_col2, f_col3 = st.columns(3)
            
            with f_col1:
                # Filtrar valores nulos o flotantes erróneos en la columna Año
                anios_limpios = df["Año"].dropna().astype(str).unique()
                anios_filtrados = sorted([a for a in anios_limpios if a.strip() != ""])
                años_disp = ["TODOS"] + anios_filtrados
                ano_sel = st.selectbox("📅 Año de Análisis", años_disp, index=len(años_disp)-1)
                
            with f_col2:
                meses_disp = ["TODOS", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                mes_sel = st.selectbox("📆 Mes de Análisis", meses_disp)
                
            with f_col3:
                # Extracción e inmunización estricta de la columna Familia contra nulos
                familias_limpias = df["Familia"].dropna().astype(str).unique()
                familias_filtradas = sorted([f for f in familias_limpias if f.strip() != ""])
                familias_disp = ["TODAS"] + familias_filtradas
                familia_sel = st.selectbox("📦 Filtrar por Familia", familias_disp)

            # Filtrado preventivo de la data base según criterios seleccionados
            df_filtrado = df.copy()
            if ano_sel != "TODOS":
                df_filtrado = df_filtrado[df_filtrado["Año"].astype(str) == str(ano_sel)]
            if mes_sel != "TODOS":
                df_filtrado = df_filtrado[df_filtrado["Mes"].astype(str).str.strip().str.capitalize() == mes_sel.capitalize()]
            if familia_sel != "TODAS":
                df_filtrado = df_filtrado[df_filtrado["Familia"].astype(str) == familia_sel]

            st.markdown("---")
            
            # Extracción protegida de la lista de sucursales para los selectores paralelos
            tiendas_limpias = df["Nombre TIENDA"].dropna().astype(str).unique()
            tiendas_disponibles = sorted([t for t in tiendas_limpias if t.strip() != ""])
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                tienda_a = st.selectbox("🏬 Seleccione Tienda A (Control)", tiendas_disponibles, index=0)
            with col_t2:
                idx_b = 1 if len(tiendas_disponibles) > 1 else 0
                tienda_b = st.selectbox("🏬 Seleccione Tienda B (Objetivo)", tiendas_disponibles, index=idx_b)
                
            df_a = df_filtrado[df_filtrado["Nombre TIENDA"].astype(str) == tienda_a]
            df_b = df_filtrado[df_filtrado["Nombre TIENDA"].astype(str) == tienda_b]
            
            v_a, c_a = df_a["Valor"].sum(), df_a["Costo"].sum()
            m_a = v_a - c_a
            u_a = df_a["Cantidad"].sum()
            ticket_a = v_a / df_a["Documento"].nunique() if df_a["Documento"].nunique() > 0 else 0
            
            v_b, c_b = df_b["Valor"].sum(), df_b["Costo"].sum()
            m_b = v_b - c_b
            u_b = df_b["Cantidad"].sum()
            ticket_b = v_b / df_b["Documento"].nunique() if df_b["Documento"].nunique() > 0 else 0
            
            col_t_a, col_t_b = st.columns(2)
            with col_t_a:
                st.markdown(f"#### 🏛️ {tienda_a}")
                st.metric("VENTAS TOTALES", f"Q {v_a / 1e6:,.2f}M" if v_a >= 1e5 else f"Q {v_a:,.2f}")
                st.metric("MARGEN NETO GENERADO", f"Q {m_a / 1e6:,.2f}M" if m_a >= 1e5 else f"Q {m_a:,.2f}")
                st.metric("UNIDADES VENDIDAS", f"{int(u_a):,}")
                st.metric("TICKET PROMEDIO", f"Q {ticket_a:,.2f}")
                
            with col_t_b:
                st.markdown(f"#### 🏛️ {tienda_b}")
                st.metric("VENTAS TOTALES", f"Q {v_b / 1e6:,.2f}M" if v_b >= 1e5 else f"Q {v_b:,.2f}", delta=f"Q {(v_b - v_a):,.2f}")
                st.metric("MARGEN NETO GENERADO", f"Q {m_b / 1e6:,.2f}M" if m_b >= 1e5 else f"Q {m_b:,.2f}", delta=f"Q {(m_b - m_a):,.2f}")
                st.metric("UNIDADES VENDIDAS", f"{int(u_b):,}", delta=f"{int(u_b - u_a):,}")
                st.metric("TICKET PROMEDIO", f"Q {ticket_b:,.2f}", delta=f"Q {(ticket_b - ticket_a):,.2f}")
                
            st.markdown("---")
            st.subheader("📊 Comparativa Mensual Cruzada de Ventas")
            
            df_g_a = df_a.groupby("Mes").agg({"Valor":"sum"}).reset_index()
            df_g_a["Tienda"] = tienda_a
            df_g_b = df_b.groupby("Mes").agg({"Valor":"sum"}).reset_index()
            df_g_b["Tienda"] = tienda_b
            df_grafico_comp = pd.concat([df_g_a, df_g_b])
            
            mes_orden = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            fig_comp = px.bar(
                df_grafico_comp, x="Mes", y="Valor", color="Tienda", barmode="group",
                category_orders={"Mes": mes_orden}, color_discrete_sequence=[COLOR_PRIMARIO, COLOR_ACENTO]
            )
            fig_comp.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='white',
                xaxis_title="", yaxis_title="Ventas (Q)", margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.warning("No hay datos cargados para efectuar comparativas entre tiendas.")



   # ==========================================
    # MÓDULO 4: TOP MARGEN REAL (QUETZALES)
    # ==========================================
    elif menu == "📦 Top Margen Real (Quetzales)":
        st.title("📦 Productos Premium de Máximo Margen de Utilidad")
        st.markdown("Esta pestaña exclusiva identifica los productos que le inyectan más **Quetzales netos** a la caja registradora.")
        df = obtener_datos()
        
        if df is not None:
            # --- PANEL DE FILTROS COMPLETO CON EXTRACCIÓN INMUNIZADA ---
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            
            with f_col1:
                # Filtrar valores nulos o flotantes erróneos en la columna Año
                anios_limpios = df["Año"].dropna().astype(str).unique()
                anios_filtrados = sorted([a for a in anios_limpios if a.strip() != ""])
                años_disp = ["TODOS"] + anios_filtrados
                ano_sel = st.selectbox("📅 Año", años_disp, index=len(años_disp)-1)
                
            with f_col2:
                meses_disp = ["TODOS", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                mes_sel = st.selectbox("📆 Mes", meses_disp)
                
            with f_col3:
                # Convertir a texto estricto y eliminar nulos de las sucursales antes de ordenar
                tiendas_limpias = df["Nombre TIENDA"].dropna().astype(str).unique()
                tiendas_filtradas = sorted([t for t in tiendas_limpias if t.strip() != ""])
                tiendas_disp = ["TODAS"] + tiendas_filtradas
                tienda_sel = st.selectbox("🏬 Sucursal", tiendas_disp)
                
            with f_col4:
                # Convertir a texto estricto y eliminar nulos de las familias antes de ordenar
                familias_limpias = df["Familia"].dropna().astype(str).unique()
                familias_filtradas = sorted([f for f in familias_limpias if f.strip() != ""])
                familias_disp = ["TODAS"] + familias_filtradas
                familia_sel = st.selectbox("📦 Familia de Producto", familias_disp)
                
            # --- FILTRADO CRUZADO SIMULTÁNEO DE ALTA VELOCIDAD ---
            df_margen = df.copy()
            if ano_sel != "TODOS":
                df_margen = df_margen[df_margen["Año"].astype(str) == str(ano_sel)]
            if mes_sel != "TODOS":
                df_margen = df_margen[df_margen["Mes"].astype(str).str.strip().str.capitalize() == mes_sel.capitalize()]
            if tienda_sel != "TODAS":
                df_margen = df_margen[df_margen["Nombre TIENDA"].astype(str) == tienda_sel]
            if familia_sel != "TODAS":
                df_margen = df_margen[df_margen["Familia"].astype(str) == familia_sel]
                
            # Cálculo exacto de la métrica clave solicitada: Utilidad neta real en Quetzales
            df_margen["Margen_Quetzales"] = df_margen["Valor"] - df_margen["Costo"]
            
            # Agrupación precisa consolidando la data transaccional
            top_productos = df_margen.groupby(["Producto", "Descripcion"]).agg({
                "Margen_Quetzales": "sum", "Valor": "sum", "Costo": "sum", "Cantidad": "sum"
            }).reset_index()
            
            # Cálculo analítico complementario del porcentaje de rentabilidad bruta
            top_productos["% Margen Bruto"] = (top_productos["Margen_Quetzales"] / top_productos["Valor"] * 100).fillna(0)
            
            # Ordenamiento decreciente para aislar el Top 15 de alto valor
            top_productos = top_productos.sort_values(by="Margen_Quetzales", ascending=False).head(15).reset_index(drop=True)
            
            # --- GRÁFICO DE BARRAS HORIZONTALES PREMIUM ---
            fig_margen = px.bar(
                top_productos, x="Margen_Quetzales", y="Descripcion", orientation='h',
                title="Top 15 Productos con Mayor Retorno Neto en Quetzales (Q)",
                color_discrete_sequence=[COLOR_ACENTO],
                hover_data=["Producto", "Cantidad", "% Margen Bruto"]
            )
            fig_margen.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='white',
                yaxis={'categoryorder':'total ascending'}, 
                xaxis_title="Margen de Utilidad Acumulado (Q)", yaxis_title=""
            )
            st.plotly_chart(fig_margen, use_container_width=True)
            
            # --- TABLA DE AUDITORÍA DIRECTIVA ---
            st.subheader("📋 Matriz de Auditoría de Margen Real")
            tabla_formateada = top_productos.copy()
            tabla_formateada["Margen_Quetzales"] = tabla_formateada["Margen_Quetzales"].map("Q {:,.2f}".format)
            tabla_formateada["Valor"] = tabla_formateada["Valor"].map("Q {:,.2f}".format)
            tabla_formateada["Costo"] = tabla_formateada["Costo"].map("Q {:,.2f}".format)
            tabla_formateada["Cantidad"] = tabla_formateada["Cantidad"].astype(int).map("{:,}".format)
            tabla_formateada["% Margen Bruto"] = tabla_formateada["% Margen Bruto"].map("{:.1f}%".format)
            
            st.dataframe(tabla_formateada, use_container_width=True)
        else:
            st.warning("Por favor realice la carga de la base transaccional histórica para visualizar la matriz de utilidades.")

    # ==========================================
    # MÓDULO 5: POR TIENDA & DÍAS
    # ==========================================
    elif menu == "🕒 Por Tienda & Días":
        st.title("🕒 Análisis Operacional por Tienda y Días de la Semana")
        st.markdown("Este reporte estratégico identifica los días de mayor carga transaccional para optimizar la logística, inventarios y asignación de personal en las sucursales de Bruselas.")
        df = obtener_datos()
        
        if df is not None:
            # --- PANEL DE FILTROS EN COLUMNAS CON EXTRACCIÓN PROTEGIDA ---
            f_col1, f_col2, f_col3 = st.columns(3)
            
            with f_col1:
                anios_limpios = df["Año"].dropna().astype(str).unique()
                años_disp = ["TODOS"] + sorted([a for a in anios_limpios if a.strip() != ""])
                ano_sel = st.selectbox("📅 Seleccione Año", años_disp, index=len(años_disp)-1)
                
            with f_col2:
                meses_disp = ["TODOS", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                mes_sel = st.selectbox("📆 Seleccione Mes", meses_disp)
                
            with f_col3:
                tiendas_limpias = df["Nombre TIENDA"].dropna().astype(str).unique()
                tiendas_disp = ["TODAS"] + sorted([t for t in tiendas_limpias if t.strip() != ""])
                tienda_sel = st.selectbox("🏬 Seleccione Sucursal", tiendas_disp)

            # --- FILTRADO CRUZADO SIMULTÁNEO ---
            df_ops = df.copy()
            if ano_sel != "TODOS":
                df_ops = df_ops[df_ops["Año"].astype(str) == str(ano_sel)]
            if mes_sel != "TODOS":
                df_ops = df_ops[df_ops["Mes"].astype(str).str.strip().str.capitalize() == mes_sel.capitalize()]
            if tienda_sel != "TODAS":
                df_ops = df_ops[df_ops["Nombre TIENDA"].astype(str) == tienda_sel]

            # --- NORMALIZACIÓN DEL DÍA DE LA SEMANA ---
            if "Dia" in df_ops.columns:
                df_ops["Dia_Semana"] = df_ops["Dia"].astype(str).str.strip().str.capitalize()
            else:
                df_ops["Dia_Semana"] = "Desconocido"

            # Diccionario estricto para forzar el orden cronológico natural de la semana
            dias_orden = ["Lunes", "Martes", "Miércoles", "Miercoles", "Jueves", "Viernes", "Sábado", "Sabado", "Domingo"]
            
            # Agrupación y consolidación operacional
            df_dias = df_ops.groupby("Dia_Semana").agg({
                "Valor": "sum",
                "Documento": "nunique",
                "Cantidad": "sum"
            }).reset_index()
            
            # Inyección de índice de ordenamiento contable
            df_dias["Orden_Semana"] = df_dias["Dia_Semana"].apply(lambda x: dias_orden.index(x) if x in dias_orden else 99)
            df_dias = df_dias.sort_values("Orden_Semana").reset_index(drop=True)
            df_dias = df_dias.drop(columns=["Orden_Semana"])

            # --- GRÁFICO OPERATIVO EN PLOTLY ---
            fig_dias = px.bar(
                df_dias, 
                x="Dia_Semana", 
                y="Valor",
                title="Distribución de Ventas por Día de la Semana (Q)",
                color_discrete_sequence=[COLOR_PRIMARIO],
                text_auto=",.2s"
            )
            fig_dias.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='white', 
                xaxis_title="", 
                yaxis_title="Monto Acumulado (Q)",
                margin=dict(l=10, r=10, t=40, b=20)
            )
            st.plotly_chart(fig_dias, use_container_width=True)

            st.markdown("---")
            st.subheader("📋 Matriz de Productividad Semanal")
            
            # --- MOTOR DE EXPORTACIÓN NATIVA ULTRA COMPATIBLE (CSV UTF-8) ---
            # Reemplaza por completo el bloque 'to_excel' problemático para evitar depender de openpyxl
            csv_data = df_dias.to_csv(index=False, sep=';', encoding='utf-8-sig')
            
            # Botón de descarga institucional de ancho completo
            st.download_button(
                label="📥 Exportar Matriz Operativa a Excel (CSV)",
                data=csv_data,
                file_name=f"Flujo_Semanal_Bruselas_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.write("")

            # Formateo de presentación visual para el cuadro final en la UI de la app
            tabla_ops = df_dias.copy()
            tabla_ops["Valor"] = tabla_ops["Valor"].map("Q {:,.2f}".format)
            tabla_ops["Documento"] = tabla_ops["Documento"].astype(int).map("{:,}".format)
            tabla_ops["Cantidad"] = tabla_ops["Cantidad"].astype(int).map("{:,}".format)
            
            tabla_ops = tabla_ops.rename(columns={
                "Dia_Semana": "Día de la Semana", 
                "Valor": "Venta Total", 
                "Documento": "Tickets Emitidos", 
                "Cantidad": "Unidades Vendidas"
            })
            
            st.dataframe(tabla_ops, use_container_width=True)
        else:
            st.warning("No hay matriz de datos históricos activa. Cargue un archivo en la primera pestaña.")
            

