import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit_authenticator as stauth
import os

st.set_page_config(page_title="ERP Gerencial", layout="wide")

# RETOQUE GERENCIAL PREMIUM QUIRÚRGICO (PROTEGE LAS GRÁFICAS DE FORMA INDESTRUCTIBLE)
st.markdown("""
    <style>
    .stApp { background-color: #FAF8F5 !important; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important; }
    section[data-testid="stSidebar"] { background-color: #2B1810 !important; min-width: 270px !important; }
    section[data-testid="stSidebar"] h2 { color: #E6C280 !important; font-family: 'serif', 'Times New Roman' !important; letter-spacing: 2px !important; text-align: center !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label p { color: #F5F0E6 !important; font-size: 0.95rem !important; font-weight: 600 !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] [data-checked="true"] label p { color: #E6C280 !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label { background-color: transparent !important; border: none !important; padding: 12px 15px !important; display: flex !important; width: 100% !important; border-left: 4px solid transparent !important; transition: all 0.2s ease !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover, div[data-testid="stRadio"] div[role="radiogroup"] [data-checked="true"] label { background-color: #3D2419 !important; border-left: 4px solid #E6C280 !important; }
    div[data-testid="stMetric"] { background-color: #FFFFFF !important; border: 1px solid #EAE6DF !important; border-top: 4px solid #C29B68 !important; border-radius: 12px !important; padding: 20px 15px !important; box-shadow: 0 4px 12px rgba(43, 24, 16, 0.03) !important; }
    div[data-testid="stMetricLabel"] p { font-size: 0.75rem !important; text-transform: uppercase !important; color: #8C857B !important; font-weight: 600 !important; letter-spacing: 1px !important; }
    div[data-testid="stMetricValue"] div { font-size: 1.9rem !important; font-weight: 700 !important; color: #1A365D !important; }
    </style>
""", unsafe_allow_html=True)

config = {
    "credentials": {"usernames": {
        "admin": {"name": "Administrador", "password": "Password123"},
        "gerente": {"name": "Gerente", "password": "Ventas2026"}
    }}
}

# Deshabilitamos la expiración automática para que no cause bucles
authenticator = stauth.Authenticate(config['credentials'], "cookie_limpia_2026", "clave_indestructible_sha256_2026", cookie_expiry_days=0)

if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None

# CONDICIONAL MAESTRO: Si NO ha iniciado sesión, muestra estrictamente el Login
if st.session_state["authentication_status"] is not True:
    try:
        authenticator.login(location='main')
    except Exception:
        pass

    if st.session_state["authentication_status"] == False:
        st.error('Usuario o contraseña incorrectos.')
    elif st.session_state["authentication_status"] == None:
        st.warning('Por favor, ingresa tus credenciales para acceder al sistema Bruselas.')

# SI YA INICIÓ SESIÓN con éxito, el Login se oculta permanentemente y arranca la App
else:
    authenticator.logout('Cerrar Sesión', 'sidebar')
    
    st.sidebar.markdown("<h2 style='margin-top:-30px;'>BRUSELAS</h2><p style='text-align:center; color:#A68565; font-size:0.75rem; letter-spacing:3px; margin-top:-10px; margin-bottom:20px;'>DASHBOARD</p>", unsafe_allow_html=True)
    st.sidebar.markdown(f"👤 **Usuario:** {st.session_state['name']}")
    
    menu = st.sidebar.radio("MENÚ PRINCIPAL:", ["📥 Importar Datos (TXT)", "📊 Resumen CEO (Financiero)", "🕒 Por Tienda & Días"])
    
    if "menu_actual" not in st.session_state: st.session_state["menu_actual"] = "📥 Importar Datos (TXT)"
    if menu != st.session_state["menu_actual"]:
        st.session_state["menu_actual"] = menu
        for llave in ["ano_f_c", "mes_f_c", "tien_f_c", "fam_f_c", "ano_d_c", "mes_d_c", "tien_d_c", "fam_d_c"]:
            if llave in st.session_state: del st.session_state[llave]
        st.rerun()

    ARCHIVO_HISTORICO = "ventas_historico.parquet"

    def obtener_datos():
        if os.path.exists(ARCHIVO_HISTORICO): return pd.read_parquet(ARCHIVO_HISTORICO)
        return None
    if menu == "📥 Importar Datos (TXT)":
        st.title("📥 Carga de Reportes Transaccionales")
        st.markdown("Sube tu archivo de 120 MB aquí para procesar y actualizar el histórico permanente.")
        archivo_subido = st.file_uploader("Selecciona el archivo TXT o TSV", type=["txt", "tsv"])
        
        if archivo_subido is not None:
            with st.spinner("Consolidando y resguardando matriz de datos..."):
                df_temp = pd.read_csv(archivo_subido, sep="\t", nrows=5, encoding='latin1')
                df_temp.columns = df_temp.columns.astype(str).str.strip()
                col_dia = "Día" if "Día" in df_temp.columns else ("Dia" if "Dia" in df_temp.columns else df_temp.columns)
                cols_cargar = ["TIENDA", "Nombre TIENDA", "Familia", "Valor", "Costo", "Mes", "Fecha", "Semana", "SemanaMes", "Und-Mov", "Cantidad", "Documento", "Producto", "Descripcion", col_dia]
                
                archivo_subido.seek(0)
                df = pd.read_csv(archivo_subido, sep="\t", engine='c', usecols=cols_cargar, encoding='latin1')
                df.columns = df.columns.astype(str).str.strip()
                df = df.rename(columns={col_dia: "Dia"})
                
                for c in ["TIENDA", "Nombre TIENDA", "Und-Mov", "Documento", "Dia", "Producto", "Descripcion"]: df[c] = df[c].astype(str).str.strip()
                df["Familia"] = df["Familia"].astype(str).str.strip().str.upper()
                df["Mes"] = df["Mes"].astype(str).str.strip().str.capitalize()
                
                df["Fecha_Str"] = df["Fecha"].astype(str)
                df["Año"] = df["Fecha_Str"].str.extract(r'(\d{4})')
                df["Año"] = df["Año"].fillna("Año 1").astype(str).str.strip()
                df.drop(columns=["Fecha_Str"], inplace=True)

                df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0)
                df["Costo"] = pd.to_numeric(df["Costo"], errors='coerce').fillna(0)
                df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors='coerce').fillna(0)
                df["Semana"] = pd.to_numeric(df["Semana"], errors='coerce').fillna(0).astype(int)       
                df["SemanaMes"] = pd.to_numeric(df["SemanaMes"], errors='coerce').fillna(0).astype(int)

                df.to_parquet(ARCHIVO_HISTORICO, index=False)
                st.success("¡Base de datos histórica sincronizada con éxito! Selecciona otra pestaña.")
    elif not os.path.exists(ARCHIVO_HISTORICO):
        st.title("📊 Dashboard Inactivo")
        st.info("No hay datos resguardados todavía. Por favor sube tu reporte inicial en la pestaña de Carga.")

    if menu == "📥 Importar Datos (TXT)":
        st.title("📥 Carga de Reportes Transaccionales")
        st.markdown("Puedes subir el archivo manualmente o sincronizar la carpeta de Google Drive.")
        
        # ID de la carpeta compartida (Reemplaza con tu ID real del Paso 2)
        DRIVE_FOLDER_ID = "1XEv1zhCgj1iCXEQbhH5Ve2v5TG9qVf8m"
        ARCHIVOS_CREDENCIAIS = "ventas_historico.json"
        
        # Botón Gerencial de Sincronización Automática
        if st.button("🔄 Sincronizar desde Google Drive", type="primary"):
            if not os.path.exists(ARCHIVOS_CREDENCIAIS):
                st.error("Falta el archivo de credenciales 'ventas_historico.json' en la carpeta del proyecto.")
            else:
                with st.spinner("Conectando con Google Drive y escaneando archivos transaccionales..."):
                    try:
                        from google.oauth2 import service_account
                        import googleapiclient.discovery
                        import io
                        
                        # 1. Definimos los alcances correctos
                        scopes = ['https://www.googleapis.com/auth/drive']
                        
                        # 2. CARGA CORRECTA: Forzamos la creación del objeto con permisos explícitos para Drive
                        creds = service_account.Credentials.from_service_account_file(
                            ARCHIVOS_CREDENCIAIS, 
                            scopes=scopes
                        )
                        
                        # 3. Construcción del servicio de manera indestructible
                        servicio = googleapiclient.discovery.build('drive', 'v3', credentials=creds)
                        
                        # Buscar archivos TXT o TSV en la carpeta de Drive
                        query = f"'{DRIVE_FOLDER_ID}' in parents and (mimeType = 'text/plain' or name contains '.txt' or name contains '.tsv')"
                        resultados = servicio.files().list(q=query, fields="files(id, name)").execute()
                        archivos = resultados.get('files', [])
                        
                        if not archivos:
                            st.warning("No se encontraron archivos TXT o TSV en la carpeta de Google Drive 'Bruselas_Ventas'.")
                        else:
                            # Tomamos el archivo más reciente detectado
                            archivo_target = archivos[0]
                            st.info(f"📂 Archivo detectado: {archivo_target['name']}. Procesando matriz de datos...")
                            
                            # Descargar archivo directamente a la memoria
                            request = servicio.files().get_media(fileId=archivo_target['id'])
                            file_stream = io.BytesIO(request.execute())
                            
                            # --- PROCESAMIENTO QUIRÚRGICO DE DATOS (Igual al proceso manual) ---
                            df_temp = pd.read_csv(file_stream, sep="\t", nrows=5, encoding='latin1')
                            df_temp.columns = df_temp.columns.astype(str).str.strip()
                            col_dia = "Día" if "Día" in df_temp.columns else ("Dia" if "Dia" in df_temp.columns else df_temp.columns)
                            cols_cargar = ["TIENDA", "Nombre TIENDA", "Familia", "Valor", "Costo", "Mes", "Fecha", "Semana", "SemanaMes", "Und-Mov", "Cantidad", "Documento", "Producto", "Descripcion", col_dia]
                            
                            file_stream.seek(0)
                            df = pd.read_csv(file_stream, sep="\t", engine='c', usecols=cols_cargar, encoding='latin1')
                            df.columns = df.columns.astype(str).str.strip()
                            df = df.rename(columns={col_dia: "Dia"})
                            
                            for c in ["TIENDA", "Nombre TIENDA", "Und-Mov", "Documento", "Dia", "Producto", "Descripcion"]: 
                                df[c] = df[c].astype(str).str.strip()
                            df["Familia"] = df["Familia"].astype(str).str.strip().str.upper()
                            df["Mes"] = df["Mes"].astype(str).str.strip().str.capitalize()
                            
                            df["Fecha_Str"] = df["Fecha"].astype(str)
                            df["Año"] = df["Fecha_Str"].str.extract(r'(\d{4})')
                            df["Año"] = df["Año"].fillna("Año 1").astype(str).str.strip()
                            df.drop(columns=["Fecha_Str"], inplace=True)

                            df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0)
                            df["Costo"] = pd.to_numeric(df["Costo"], errors='coerce').fillna(0)
                            df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors='coerce').fillna(0)
                            df["Semana"] = pd.to_numeric(df["Semana"], errors='coerce').fillna(0).astype(int)       
                            df["SemanaMes"] = pd.to_numeric(df["SemanaMes"], errors='coerce').fillna(0).astype(int)

                            # Guardar localmente el Parquet consolidado
                            #df.to_parquet(ARCHIVO_HISTORICO, index=False)
                            # NUEVO: Guardamos una nota de auditoría con la fecha de la sincronización
                            import datetime
                            ahora = datetime.datetime.now()
                            # Formateamos la fecha al estilo latino: DD/MM/AAAA HH:MM
                            fecha_formateada = ahora.strftime("%d/%m/%Y %H:%M")
                            
                            # Guardamos en la sesión para uso inmediato
                            st.session_state["ultimo_archivo"] = archivo_target['name']
                            st.session_state["ultima_fecha"] = fecha_formateada
                            
                            # Guardamos un archivito de texto para que el servidor lo recuerde siempre
                            with open("auditoria_drive.txt", "w", encoding="utf-8") as f:
                                f.write(f"{archivo_target['name']}|{fecha_formateada}")
                            
                            st.success("¡Base de datos sincronizada desde Google Drive con éxito! Ya puedes revisar las gráficas.")
                            st.rerun()
                            
                            #st.success("¡Base de datos sincronizada desde Google Drive con éxito! Ya puedes revisar las gráficas.")
                            #st.rerun()
                    except Exception as e:
                        st.error(f"Error en la conexión o lectura de Google Drive: {str(e)}")

    else:
        df = obtener_datos()
        if df is not None:
            orden_m = {"Enero":1,"Febrero":2,"Marzo":3,"Abril":4,"Mayo":5,"Junio":6,"Julio":7,"Agosto":8,"Septiembre":9,"Octubre":10,"Noviembre":11,"Diciembre":12,"Ene":1,"Feb":2,"Mar":3,"Abr fail":4,"May":5,"Jun":6,"Jul":7,"Ago":8,"Sep":9,"Oct":10,"Nov":11,"Dic":12}
            df["Mes_Orden"] = df["Mes"].map(orden_m).fillna(1)

            df_mes = df.groupby(["Año", "TIENDA", "Nombre TIENDA", "Familia", "Mes_Orden", "Mes"])[["Valor", "Costo", "Cantidad"]].sum().reset_index()
            df_sem = df.groupby(["Año", "TIENDA", "Nombre TIENDA", "Familia", "Mes", "Semana", "SemanaMes"])["Valor"].sum().reset_index()
            df_uni = df.groupby(["Año", "Nombre TIENDA", "Familia", "Mes", "Und-Mov"])["Cantidad"].sum().reset_index()
            df_tck = df.groupby(["Año", "Nombre TIENDA", "Familia", "Mes"])["Documento"].nunique().reset_index().rename(columns={"Documento": "Tickets"})
            df_dias = df.groupby(["Año", "Nombre TIENDA", "Familia", "Mes", "Dia"])[["Valor", "Costo"]].sum().reset_index()
            
            # REPARACIÓN INTEGRAL: Agregamos el parámetro 'Cantidad' para alimentar la pestaña final
            df_prod = df.groupby(["Año", "Nombre TIENDA", "Familia", "Mes", "Producto", "Descripcion"])[["Valor", "Cantidad"]].sum().reset_index()

            # --- NUEVO: LECTOR Y ALERTA VISUAL DE ÚLTIMA SINCRONIZACIÓN ---
            # Si no está en memoria, intentamos leer el archivito de texto
            if "ultimo_archivo" not in st.session_state:
                if os.path.exists("auditoria_drive.txt"):
                    with open("auditoria_drive.txt", "r", encoding="utf-8") as f:
                        datos_auditoria = f.read().split("|")
                        if len(datos_auditoria) == 2:
                            st.session_state["ultimo_archivo"] = datos_auditoria[0]
                            st.session_state["ultima_fecha"] = datos_auditoria[1]
                else:
                    st.session_state["ultimo_archivo"] = "Ninguno (Carga Manual)"
                    st.session_state["ultima_fecha"] = "Desconocida"

            # Desplegamos la alerta estilizada estilo cintillo gerencial
            st.markdown(f"""
                <div style="background-color: #EAE6DF; border-left: 5px solid #2B1810; padding: 12px 18px; border-radius: 6px; margin-bottom: 15px;">
                    <p style="margin: 0; font-size: 0.85rem; color: #2B1810; font-weight: bold; letter-spacing: 0.5px;">
                        🔄 ESTADO DEL HISTÓRICO: <span style="color: #A68565;">Conectado a Google Drive</span>
                    </p>
                    <p style="margin: 3px 0 0 0; font-size: 0.8rem; color: #555555;">
                        📄 <b>Archivo activo:</b> {st.session_state['ultimo_archivo']} | 🕒 <b>Sincronizado el:</b> {st.session_state['ultima_fecha']}
                    </p>
                </div>
            """, unsafe_allow_html=True)

            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                ano_sel = c1.selectbox("📅 Año Fiscal:", sorted(df_mes["Año"].unique()), key="ano_f_c")
                mes_sel = c2.selectbox("📆 Selección de Mes:", ["Todos los Meses"] + sorted(df_mes[df_mes["Año"] == ano_sel]["Mes"].unique(), key=lambda x: orden_m.get(x, 99)), key="mes_f_c")
                tien_sel = c3.selectbox("🏬 Filtrar Tienda:", ["Todas las Tiendas"] + sorted(df_mes[df_mes["Año"] == ano_sel]["Nombre TIENDA"].unique()), key="tien_f_c")
                fam_sel = c4.selectbox("📦 Filtrar Familia:", ["Todas las Familias"] + sorted(df_mes[df_mes["Año"] == ano_sel]["Familia"].unique()), key="fam_f_c")

            df_m_f = df_mes[df_mes["Año"] == ano_sel]; df_s_f = df_sem[df_sem["Año"] == ano_sel]; df_u_f = df_uni[df_uni["Año"] == ano_sel]; df_t_f = df_tck[df_tck["Año"] == ano_sel]; df_d_f = df_dias[df_dias["Año"] == ano_sel]; df_p_f = df_prod[df_prod["Año"] == ano_sel]
            
            if mes_sel != "Todos los Meses":
                df_m_f = df_m_f[df_m_f["Mes"] == mes_sel]; df_s_f = df_s_f[df_s_f["Mes"] == mes_sel]; df_u_f = df_u_f[df_u_f["Mes"] == mes_sel]; df_t_f = df_t_f[df_t_f["Mes"] == mes_sel]; df_d_f = df_d_f[df_d_f["Mes"] == mes_sel]; df_p_f = df_p_f[df_p_f["Mes"] == mes_sel]
            if tien_sel != "Todas las Tiendas":
                df_m_f = df_m_f[df_m_f["Nombre TIENDA"] == tien_sel]; df_s_f = df_s_f[df_s_f["Nombre TIENDA"] == tien_sel]; df_u_f = df_u_f[df_u_f["Nombre TIENDA"] == tien_sel]; df_t_f = df_t_f[df_t_f["Nombre TIENDA"] == tien_sel]; df_d_f = df_d_f[df_d_f["Nombre TIENDA"] == tien_sel]; df_p_f = df_p_f[df_p_f["Nombre TIENDA"] == tien_sel]
            if fam_sel != "Todas las Familias":
                df_m_f = df_m_f[df_m_f["Familia"] == fam_sel]; df_s_f = df_s_f[df_s_f["Familia"] == fam_sel]; 
                df_u_f = df_u_f[df_u_f["Familia"] == fam_sel]
                df_t_f = df_t_f[df_t_f["Familia"] == fam_sel]; df_d_f = df_d_f[df_d_f["Familia"] == fam_sel]; df_p_f = df_p_f[df_p_f["Familia"] == fam_sel]

            df_m_f = df_m_f.sort_values(by="Mes_Orden")
            if menu == "📊 Resumen CEO (Financiero)":
                st.title("💼 Indicadores de Rendimiento Corporativo")
                if not df_m_f.empty:
                    v_tot, c_tot, u_tot = df_m_f["Valor"].sum(), df_m_f["Costo"].sum(), df_m_f["Cantidad"].sum()
                    t_tot = df_t_f["Tickets"].sum() if not df_t_f.empty else 1
                    ut_bruta = v_tot - c_tot
                    margen = (ut_bruta / v_tot * 100) if v_tot > 0 else 0
                    
                    k1, k2, k3, k4, k5 = st.columns(5)
                    k1.metric("Venta Total", f"Q{v_tot / 1_000_000:.1f}M" if v_tot >= 1_000_000 else f"Q{v_tot:,.2f}", f"Q{v_tot:,.2f}")
                    k2.metric("Unidades Vendidas", f"{u_tot:,.0f}")
                    k3.metric("N° Tickets", f"{t_tot:,.0f}")
                    k4.metric("Ticket Promedio", f"Q{v_tot / t_tot:,.0f}")
                    k5.metric("Tiendas Activas", f"{df_m_f['TIENDA'].nunique()}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.metric("Margen Bruto Real", f"{margen:.0f}%", f"Utilidad Neta: Q{ut_bruta / 1_000_000:.1f}M")
                    if margen >= 40: st.markdown('<span style="background-color:#D4EDDA; color:#155724; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold;">🟢 Óptimo</span>', unsafe_allow_html=True)

                    st.markdown("---")
                    g1, g2 = st.columns(2)
                    with g1:
                        colores_fijos = ["#1A365D", "#C29B68", "#2E5B88", "#5B84B1", "#A1BACB"]
                        st.plotly_chart(px.line(df_m_f, x="Mes", y="Valor", color="TIENDA", color_discrete_sequence=colores_fijos, hover_data=["Nombre TIENDA"], title="Tendencia Mensual de Puntos de Venta", labels={"Valor": "Ventas (Q)"}, template="plotly_white"), use_container_width=True)
                    with g2:
                        df_rk = df_m_f.groupby("Familia")["Valor"].sum().reset_index().sort_values(by="Valor", ascending=False)
                        colores_pastel = ["#2B1810", "#C29B68", "#E6C280", "#8C857B", "#A68565", "#EAE6DF"]
                        fig_p = px.pie(df_rk.head(10), values="Valor", names="Familia", color_discrete_sequence=colores_pastel, title="Top 10 Familias (% Participación)", template="plotly_white")
                        fig_p.update_traces(textinfo='label+percent', textposition='inside')
                        st.plotly_chart(fig_p, use_container_width=True)

                    tot_m = df_m_f.groupby(["Mes_Orden", "Mes"])[["Valor"]].sum().reset_index()
                    st.plotly_chart(px.bar(tot_m, x="Mes", y="Valor", title="Consolidado de Facturación Global del Periodo", template="plotly_white").update_traces(marker_color="#C29B68"), use_container_width=True)

                    st.markdown("---")
                    st.subheader("⚙️ Análisis de Tendencia Semanal")
                    t_sem = st.radio("📐 Eje Cronológico Semanal:", ["Ver por Semana Calendario (1 al 52)", "Ver por Semana del Mes (1 al 5)"], horizontal=True)

                    g3, g4 = st.columns(2)
                    with g3:
                        if "Calendario" in t_sem: st.plotly_chart(px.line(df_s_f.sort_values("Semana"), x="Semana", y="Valor", color="TIENDA", color_discrete_sequence=colores_fijos, title="Venta por Semana Calendario", template="plotly_white").update_xaxes(tickmode="linear", dtick=5), use_container_width=True)
                        else: st.plotly_chart(px.line(df_s_f.sort_values("SemanaMes"), x="SemanaMes", y="Valor", color="TIENDA", color_discrete_sequence=colores_fijos, title="Venta Promedio por Semana del Mes", template="plotly_white").update_xaxes(tickmode="linear", dtick=1), use_container_width=True)
                    with g4:
                        st.markdown("**Volumen Físico por Formato de Despacho:**")
                        st.dataframe(df_u_f.groupby("Und-Mov")["Cantidad"].sum().reset_index().rename(columns={"Und-Mov":"Unidad","Cantidad":"Total"}), use_container_width=True, hide_index=True)
                else: st.warning("No hay registros para los filtros seleccionados.")

            # CORRECCIÓN DE AGREGACIÓN: Totalización absoluta por artículo de venta
            elif menu == "🕒 Por Tienda & Días":
                st.title("🕒 Análisis Diario y de Artículos por Puntos de Venta")
                
                if not df_d_f.empty:
                    g_izq, g_der = st.columns(2)
                    
                    with g_izq:
                        st.subheader("Volumen de Facturación por Día")
                        df_dias_vista = df_d_f.groupby("Dia")["Valor"].sum().reset_index()
                        
                        fig_bar_dias = px.bar(
                            df_dias_vista, x="Dia", y="Valor", 
                            color_discrete_sequence=['#2B1810'], template="plotly_white"
                        )
                        fig_bar_dias.update_layout(xaxis_title="Día", yaxis_title="Ventas (Q)")
                        st.plotly_chart(fig_bar_dias, use_container_width=True)
                    
                    with g_der:
                        st.subheader("Top 20 Productos Más Vendidos del Periodo Seleccionado")
                        
                        # Agrupación y totalización por Código y Descripción (Evita filas duplicadas)
                        df_top_prod = df_p_f.groupby(["Producto", "Descripcion"])[["Cantidad", "Valor"]].sum().reset_index()
                        df_top_prod = df_top_prod.sort_values(by="Valor", ascending=False).head(20)
                        
                        df_top_prod_vista = df_top_prod.rename(columns={
                            "Producto": "Código",
                            "Descripcion": "Descripción",
                            "Cantidad": "Unidades",
                            "Valor": "Ventas (Q)"
                        })
                        
                        st.dataframe(
                            df_top_prod_vista[["Código", "Descripción", "Unidades", "Ventas (Q)"]].style.format({
                                "Unidades": "{:,.0f}", 
                                "Ventas (Q)": "Q {:,.2f}"
                            }), 
                            use_container_width=True,
                            hide_index=True
                        )
                else:
                    st.warning("No hay registros diarios para los filtros seleccionados en la parte superior.")
                    