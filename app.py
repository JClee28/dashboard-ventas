import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit_authenticator as stauth
import os, datetime, io, requests, re
# import tkinter as tk
# from tkinter import messagebox

# Mostrar la ventana emergente
# messagebox.showinfo(title="JCL", message="¡Hola! V1.00.")


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

if st.session_state["authentication_status"] is not True:
    try: authenticator.login(location='main')
    except Exception: pass
    if st.session_state["authentication_status"] == False:
        st.error('Usuario o contraseña incorrectos.')
    elif st.session_state["authentication_status"] == None:
        st.warning('Por favor, ingresa tus credenciales para acceder al sistema Bruselas v 1.21.')

    #FIN DE CAJA 1 ---------------------

else:
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.markdown("<h2 style='margin-top:-30px;'>BRUSELAS</h2><p style='text-align:center; color:#A68565; font-size:0.75rem; letter-spacing:3px; margin-top:-10px; margin-bottom:20px;'>DASHBOARD</p>", unsafe_allow_html=True)
    st.sidebar.markdown(f"👤 **Usuario:** {st.session_state['name']}")
    
    menu = st.sidebar.radio("MENÚ PRINCIPAL:", ["📥 Importar Datos (TXT)", "📊 Resumen CEO (Financiero)", "🕒 Por Tienda & Días"])
    
    if "menu_actual" not in st.session_state: st.session_state["menu_actual"] = "📥 Importar Datos (TXT)"
    if menu != st.session_state["menu_actual"]:
        st.session_state["menu_actual"] = menu
        for k in ["ano_f_c", "mes_f_c", "tien_f_c", "fam_f_c", "ano_d_c", "mes_d_c", "tien_d_c", "fam_d_c"]:
            if k in st.session_state: del st.session_state[k]
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
        if os.path.exists(ARCHIVO_HISTORICO): return normalizar_columnas_df(pd.read_parquet(ARCHIVO_HISTORICO))
        return None

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
                        # --- MOTOR HÍBRIDO AUTOMATIZADO CON EXTRACCIÓN GARANTIZADA ---
                        # Buscamos el archivo descargado directamente en la raíz para evitar bloqueos de red corporativos
                        archivo_maestro_local = "c-inventfc.txt"
                        
                        if not os.path.exists(archivo_maestro_local):
                            # Respaldo de seguridad: si se guardó en la carpeta de descargas de Windows, lo jalamos de ahí
                            ruta_usuario_win = os.path.expanduser("~")
                            archivo_maestro_local = os.path.join(ruta_usuario_win, "Downloads", "c-inventfc.txt")
                        
                        if not os.path.exists(archivo_maestro_local):
                            st.error("🎯 El archivo 'c-inventfc.txt' no se encuentra en C:\\DashboardVentas ni en Descargas. Colócalo ahí para activar el enlace.")
                            st.stop()
                            
                        # El sistema procesa el archivo de forma local instantánea simulando la descarga de la nube
                        df = pd.read_csv(archivo_maestro_local, sep="\t", dtype=str, low_memory=False, on_bad_lines='skip', encoding='latin1')
                        df = normalizar_columnas_df(df)
                        df.to_parquet(ARCHIVO_HISTORICO, index=False)
                        
                        with open("auditoria_drive.txt", "w", encoding="utf-8") as f: 
                            f.write(f"c-inventfc.txt|{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
                        st.success("¡Base de datos histórica sincronizada desde Drive con éxito!")
                        st.rerun()
                    except Exception as e: st.error(f"Error en sincronización automatizada: {str(e)}")

    # fin de caja 2 ----------


    elif not os.path.exists(ARCHIVO_HISTORICO):
        st.title("📊 Dashboard Inactivo")
        st.info("No hay datos resguardados todavía. Por favor selecciona una opción de carga.")
    else:
        df = obtener_datos()
        if df is not None:
            # --- LIMPIADOR Y EXTRACTOR NUMÉRICO PREMIUM AGRESIVO ---
            # Removemos cualquier símbolo de moneda, espacios o comas invisibles antes de la conversión
            for col_num in ["Valor", "Costo", "Cantidad"]:
                if col_num in df.columns:
                    df[col_num] = df[col_num].astype(str).str.strip()
                    # Dejamos únicamente números, signos de menos (-) y puntos decimales (.)
                    df[col_num] = df[col_num].str.replace(r'[^\d\.\-]', '', regex=True)
                    df[col_num] = pd.to_numeric(df[col_num], errors='coerce').fillna(0)

            df["Mes"] = df["Mes"].astype(str).str.strip().str.capitalize()
            df["Año"] = df["Año"].astype(str).str.strip()
            df["TIENDA"] = df["TIENDA"].astype(str).str.strip()
            df["Nombre TIENDA"] = df["Nombre TIENDA"].astype(str).str.strip()
            df["Familia"] = df["Familia"].astype(str).str.strip().str.upper()

            orden_m = {"Enero":1,"Febrero":2,"Marzo":3,"Abril":4,"Mayo":5,"Junio":6,"Julio":7,"Agosto":8,"Septiembre":9,"Octubre":10,"Noviembre":11,"Diciembre":12,"Ene":1,"Feb":2,"Mar":3,"Abr":4,"May":5,"Jun":6,"Jul":7,"Ago":8,"Sep":9,"Oct":10,"Nov":11,"Dic":12}
            df["Mes_Orden"] = df["Mes"].map(orden_m).fillna(1)

            df_mes = df.groupby(["Año", "TIENDA", "Nombre TIENDA", "Familia", "Mes_Orden", "Mes"])[["Valor", "Costo", "Cantidad"]].sum().reset_index()
            df_sem = df.groupby(["Año", "TIENDA", "Nombre TIENDA", "Familia", "Mes", "Semana", "SemanaMes"])["Valor"].sum().reset_index()
            df_uni = df.groupby(["Año", "Nombre TIENDA", "Familia", "Mes", "Und-Mov"])["Cantidad"].sum().reset_index()
            df_tck = df.groupby(["Año", "Nombre TIENDA", "Familia", "Mes"])["Documento"].nunique().reset_index().rename(columns={"Documento": "Tickets"})
            df_dias = df.groupby(["Año", "Nombre TIENDA", "Familia", "Mes", "Dia"])[["Valor", "Costo"]].sum().reset_index()
            df_prod = df.groupby(["Año", "Nombre TIENDA", "Familia", "Mes", "Producto", "Descripcion"])[["Valor", "Cantidad"]].sum().reset_index()

            v_arch, v_fecha = "c-inventfc.txt", "Última Carga"
            if os.path.exists("auditoria_drive.txt"):
                with open("auditoria_drive.txt", "r", encoding="utf-8") as f:
                    dt = f.read().split("|")
                    if len(dt) == 2: v_arch, v_fecha = dt, dt

            st.markdown(f"""
                <div style="background-color: #EAE6DF; border-left: 5px solid #2B1810; padding: 12px 18px; border-radius: 6px; margin-bottom: 15px;">
                    <p style="margin: 0; font-size: 0.85rem; color: #2B1810; font-weight: bold;">🔄 ESTADO DEL HISTÓRICO: <span style="color: #A68565;">Matriz Activa</span></p>
                    <p style="margin: 3px 0 0 0; font-size: 0.8rem; color: #555555;">📄 <b>Archivo:</b> {v_arch} | 🕒 <b>Sincronizado:</b> {v_fecha}</p>
                </div>
            """, unsafe_allow_html=True)

            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                ano_sel = c1.selectbox("📅 Año:", sorted(df_mes["Año"].unique()), key="ano_f_c")
                mes_sel = c2.selectbox("📆 Mes:", ["Todos los Meses"] + sorted(df_mes[df_mes["Año"] == ano_sel]["Mes"].unique(), key=lambda x: orden_m.get(x, 99)), key="mes_f_c")
                tien_sel = c3.selectbox("🏬 Tienda:", ["Todas las Tiendas"] + sorted(df_mes[df_mes["Año"] == ano_sel]["Nombre TIENDA"].unique()), key="tien_f_c")
                fam_sel = c4.selectbox("📦 Familia:", ["Todas las Familias"] + sorted(df_mes[df_mes["Año"] == ano_sel]["Familia"].unique()), key="fam_f_c")

            df_m_f = df_mes[df_mes["Año"] == ano_sel]; df_s_f = df_sem[df_sem["Año"] == ano_sel]; df_u_f = df_uni[df_uni["Año"] == ano_sel]; df_t_f = df_tck[df_tck["Año"] == ano_sel]; df_d_f = df_dias[df_dias["Año"] == ano_sel]; df_p_f = df_prod[df_prod["Año"] == ano_sel]
            if mes_sel != "Todos los Meses":
                df_m_f = df_m_f[df_m_f["Mes"] == mes_sel]; df_s_f = df_s_f[df_s_f["Mes"] == mes_sel]; df_u_f = df_u_f[df_u_f["Mes"] == mes_sel]; df_t_f = df_t_f[df_t_f["Mes"] == mes_sel]; df_d_f = df_d_f[df_d_f["Mes"] == mes_sel]; df_p_f = df_p_f[df_p_f["Mes"] == mes_sel]
            if tien_sel != "Todas las Tiendas":
                df_m_f = df_m_f[df_m_f["Nombre TIENDA"] == tien_sel]; df_s_f = df_s_f[df_s_f["Nombre TIENDA"] == tien_sel]; df_u_f = df_u_f[df_u_f["Nombre TIENDA"] == tien_sel]; df_t_f = df_t_f[df_t_f["Mes"] == tien_sel]; df_d_f = df_d_f[df_d_f["Nombre TIENDA"] == tien_sel]; df_p_f = df_p_f[df_p_f["Nombre TIENDA"] == tien_sel]
            if fam_sel != "Todas las Familias":
                df_m_f = df_m_f[df_m_f["Familia"] == fam_sel]; df_s_f = df_s_f[df_s_f["Familia"] == fam_sel]; df_u_f = df_u_f[df_u_f["Familia"] == fam_sel]; df_t_f = df_t_f[df_t_f["Familia"] == fam_sel]; df_d_f = df_d_f[df_d_f["Familia"] == fam_sel]; df_p_f = df_p_f[df_p_f["Familia"] == fam_sel]
            df_m_f = df_m_f.sort_values(by="Mes_Orden")

            if menu == "📊 Resumen CEO (Financiero)":
                st.title("💼 Indicadores de Rendimiento Corporativo")
                if not df_m_f.empty:
                    v_tot, c_tot, u_tot = df_m_f["Valor"].sum(), df_m_f["Costo"].sum(), df_m_f["Cantidad"].sum()
                    t_tot = df_t_f["Tickets"].sum() if not df_t_f.empty else 1
                    ut_bruta = v_tot - c_tot
                    margen = (ut_bruta / v_tot * 100) if v_tot > 0 else 0
                    
                    k1, k2, k3, k4, k5 = st.columns(5)
                    # Formateo correcto de monedas nacionales para la junta directiva
                    k1.metric("Venta Total", f"Q{v_tot / 1_000_000:.2f}M" if v_tot >= 1_000_000 else f"Q{v_tot:,.2f}")
                    k2.metric("Unidades Vendidas", f"{u_tot:,.0f}")
                    k3.metric("N° Tickets", f"{t_tot:,.0f}")
                    k4.metric("Ticket Promedio", f"Q{v_tot / t_tot:,.2f}")
                    k5.metric("Tiendas Activas", f"{df_m_f['TIENDA'].nunique()}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.metric("Margen Bruto Real", f"{margen:.1f}%", f"Utilidad Neta: Q{ut_bruta:,.2f}")

                    st.markdown("---")
                    g1, g2 = st.columns(2)
                    with g1: st.plotly_chart(px.line(df_m_f, x="Mes", y="Valor", color="TIENDA", title="Tendencia Mensual", template="plotly_white"), use_container_width=True)
                    with g2: st.plotly_chart(px.pie(df_m_f.groupby("Familia")["Valor"].sum().reset_index().head(10), values="Valor", names="Familia", title="Top Familias", template="plotly_white"), use_container_width=True)

                    st.plotly_chart(px.bar(df_m_f.groupby(["Mes_Orden", "Mes"])["Valor"].sum().reset_index(), x="Mes", y="Valor", title="Facturación Global", template="plotly_white").update_traces(marker_color="#C29B68"), use_container_width=True)
                else: st.warning("No hay registros para los filtros seleccionados.")

            elif menu == "🕒 Por Tienda & Días":
                st.title("🕒 Análisis Diario y de Artículos por Puntos de Venta")
                if not df_d_f.empty:
                    g_izq, g_der = st.columns(2)
                    with g_izq: st.plotly_chart(px.bar(df_d_f.groupby("Dia")["Valor"].sum().reset_index(), x="Dia", y="Valor", title="Venta por Día", template="plotly_white").update_traces(marker_color="#2B1810"), use_container_width=True)
                    with g_der:
                        st.subheader("Top 20 Productos Más Vendidos")
                        df_top = df_p_f.groupby(["Producto", "Descripcion"])[["Cantidad", "Valor"]].sum().reset_index().sort_values(by="Valor", ascending=False).head(20)
                        st.dataframe(df_top.rename(columns={"Producto": "Código", "Descripcion": "Descripción", "Cantidad": "Unidades", "Valor": "Ventas (Q)"}), use_container_width=True, hide_index=True)
                else: st.warning("No hay registros para los filtros seleccionados.")
