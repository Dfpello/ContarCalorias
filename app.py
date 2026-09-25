import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Macros App Online", page_icon="💪", layout="centered")

# Conexión a BBDD (Lee de Secrets en Cloud o .streamlit/secrets.toml en local)
conn = st.connection("postgresql", type="sql")

OBJETIVOS = {
    "Grasas": 70.0,
    "Carbohidratos": 240.0,
    "Proteina": 160.0,
    "Kcal": 2230.0 
}

# --- FUNCIONES DE BBDD ---
def cargar_biblioteca():
    return conn.query("SELECT * FROM biblioteca_alimentos ORDER BY comida ASC;", ttl="10m")

def cargar_log_hoy(fecha):
    query = "SELECT * FROM log_diario WHERE fecha = :f"
    return conn.query(query, params={"f": fecha}, ttl=0)

# --- LÓGICA PRINCIPAL ---
st.title("💪 Mi Diario de Macros")
fecha_hoy = datetime.now().date()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["➕ Registrar", "📊 Hoy", "📜 Historial", "⚙️ BBDD", "📏 Físico", "📅 Buscar"])

# --- TAB 1: REGISTRAR CONSUMO ---
with tab1:
    st.subheader("¿Qué has comido?")
    
    # Selector de fecha (por defecto el día actual)
    fecha_registro = st.date_input("Fecha del registro", value=datetime.now().date())
    
    momento = st.selectbox("Momento del día", ["Desayuno", "Comida", "Merienda", "Cena", "Otro"])
    
    biblioteca = cargar_biblioteca()
    
    if not biblioteca.empty:
        alimento_nombres = biblioteca['comida'].tolist()
        seleccion = st.selectbox("Busca y selecciona el plato", [""] + alimento_nombres)
        
        if seleccion:
            plato = biblioteca[biblioteca['comida'] == seleccion].iloc[0]
            es_medida_100 = "100" in str(plato['porcion'])
            unidad_texto = "gramos/ml" if es_medida_100 else "unidades"
            
            # Modificado para usar solo números enteros
            cantidad = st.number_input(f"Cantidad en {unidad_texto}", min_value=1, value=100 if es_medida_100 else 1, step=1)
            
            if st.button("Añadir al Diario"):
                factor = cantidad / 100.0 if es_medida_100 else cantidad
                
                try:
                    with conn.session as s:
                        s.execute(
                            text("""INSERT INTO log_diario (fecha, momento, comida, grasas, carbohidratos, proteina, kcal) 
                                 VALUES (:f, :m, :c, :g, :ca, :p, :k);"""),
                            params={
                                "f": fecha_registro, "m": momento, "c": plato['comida'],
                                "g": round(float(plato['grasas']) * factor, 2),
                                "ca": round(float(plato['carbohidratos']) * factor, 2),
                                "p": round(float(plato['proteina']) * factor, 2),
                                "k": round(float(plato['calorias']) * factor, 2)
                            }
                        )
                        s.commit()
                    st.toast(f"✅ {plato['comida']} añadido al diario")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hubo un problema al guardar el registro: {e}")
    else:
        st.warning("La biblioteca está vacía. Añade alimentos en la pestaña BBDD.")

# --- TAB 2: HOY ---
with tab2:
    # Mostramos siempre los registros del día actual en esta pestaña
    log_hoy = cargar_log_hoy(fecha_hoy)
    
    if not log_hoy.empty:
        for col in ['grasas', 'carbohidratos', 'proteina', 'kcal']:
            log_hoy[col] = pd.to_numeric(log_hoy[col], errors='coerce').fillna(0)
            
        totales = log_hoy[['grasas', 'carbohidratos', 'proteina', 'kcal']].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Proteína", f"{totales['proteina']:.0f}g", f"{totales['proteina'] - OBJETIVOS['Proteina']:.0f}g")
        c2.metric("Carbs", f"{totales['carbohidratos']:.0f}g", f"{totales['carbohidratos'] - OBJETIVOS['Carbohidratos']:.0f}g")
        c3.metric("Grasas", f"{totales['grasas']:.0f}g", f"{totales['grasas'] - OBJETIVOS['Grasas']:.0f}g")
        
        st.write(f"**Calorías totales: {totales['kcal']:.0f} / {OBJETIVOS['Kcal']} kcal**")
        st.progress(min(float(totales['kcal']) / OBJETIVOS['Kcal'], 1.0))
        
        st.divider()
        
        # --- Distribución por comida con métricas destacadas ---
        st.markdown("### 🍽️ Distribución por comida")
        distribucion = log_hoy.groupby('momento')['kcal'].sum()
        
        if not distribucion.empty:
            # Crea tantas columnas como comidas hayas registrado hoy
            cols_dist = st.columns(len(distribucion))
            for col, (mom, kcal) in zip(cols_dist, distribucion.items()):
                col.metric(mom, f"{kcal:.0f} kcal")
        
        st.divider()
        
        for _, row in log_hoy.iterrows():
            col_info, col_del = st.columns([4, 1])
            col_info.write(f"**{row['momento']}**: {row['comida']} ({row['kcal']:.0f} kcal)")
            if col_del.button("🗑️", key=f"del_{row['id']}"):
                try:
                    with conn.session as s:
                        s.execute(text("DELETE FROM log_diario WHERE id = :id"), params={"id": row['id']})
                        s.commit()
                    st.toast("✅ Registro eliminado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hubo un problema al eliminar: {e}")
    else:
        st.info("Nada registrado hoy.")

# --- TAB 3: HISTORIAL ---
with tab3:
    st.subheader("Evolución de Calorías")
    historial = conn.query("SELECT * FROM log_diario ORDER BY fecha DESC, id DESC;", ttl=0)
    
    if not historial.empty:
        # Gráfica de evolución de kcal diarias
        for col in ['grasas', 'carbohidratos', 'proteina', 'kcal']:
            historial[col] = pd.to_numeric(historial[col], errors='coerce').fillna(0)
            
        tendencia_kcal = historial.groupby('fecha')['kcal'].sum().reset_index()
        tendencia_kcal.set_index('fecha', inplace=True)
        st.bar_chart(tendencia_kcal)
        
        st.subheader("Registros detallados")
        st.dataframe(historial, use_container_width=True)
    else:
        st.info("No hay suficientes datos para mostrar gráficas.")

# --- TAB 4: GESTIONAR BBDD ---
with tab4:
    st.subheader("Biblioteca de alimentos")
    with st.form("form_bbdd"):
        n_nombre = st.text_input("Nombre del alimento")
        col1, col2, col3 = st.columns(3)
        n_g = col1.number_input("Grasas", min_value=0.0, step=0.1)
        n_c = col2.number_input("Carbs", min_value=0.0, step=0.1)
        n_p = col3.number_input("Proteína", min_value=0.0, step=0.1)
        n_uni = st.radio("Porción base", ["100g", "100ml", "1U"], horizontal=True)
        
        if st.form_submit_button("Guardar Alimento"):
            if n_nombre:
                n_kcal = (n_g * 9) + (n_c * 4) + (n_p * 4)
                try:
                    with conn.session as s:
                        s.execute(
                            text("""INSERT INTO biblioteca_alimentos (comida, grasas, carbohidratos, proteina, porcion, calorias) 
                                 VALUES (:n, :g, :c, :p, :por, :k) 
                                 ON CONFLICT (comida) DO UPDATE SET 
                                 grasas=EXCLUDED.grasas, carbohidratos=EXCLUDED.carbohidratos, 
                                 proteina=EXCLUDED.proteina, calorias=EXCLUDED.calorias;"""),
                            params={"n": n_nombre, "g": n_g, "c": n_c, "p": n_p, "por": n_uni, "k": n_kcal}
                        )
                        s.commit()
                    
                    # Limpieza de caché para que aparezca al instante
                    conn.reset() 
                    
                    st.toast(f"✅ {n_nombre} guardado correctamente")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hubo un problema al modificar la biblioteca: {e}")

# --- TAB 5: MEDICIONES FÍSICAS ---
with tab5:
    st.subheader("Control de Medidas y Recomposición")
    with st.form("form_mediciones"):
        col_p, col_c = st.columns(2)
        peso = col_p.number_input("Peso (kg)", min_value=40.0, value=75.2, step=0.1)
        cintura = col_c.number_input("Cintura (cm)", min_value=40.0, value=80.0, step=0.5)
        
        col_cue, col_h = st.columns(2)
        cuello = col_cue.number_input("Cuello (cm)", min_value=20.0, value=38.0, step=0.5)
        hombros = col_h.number_input("Hombros (cm)", min_value=80.0, value=115.0, step=0.5)
        
        col_b, col_g = st.columns(2)
        brazo = col_b.number_input("Brazo (cm)", min_value=20.0, value=35.0, step=0.5)
        gemelo = col_g.number_input("Gemelo (cm)", min_value=20.0, value=38.0, step=0.5)
        
        if st.form_submit_button("Guardar Medidas"):
            try:
                with conn.session as s:
                    # Crea la tabla automáticamente la primera vez que se usa
                    s.execute(text("""CREATE TABLE IF NOT EXISTS registro_fisico (
                                        fecha DATE PRIMARY KEY, 
                                        peso REAL, cintura REAL, cuello REAL, 
                                        hombros REAL, brazo REAL, gemelo REAL
                                     );"""))
                    s.execute(
                        text("""INSERT INTO registro_fisico (fecha, peso, cintura, cuello, hombros, brazo, gemelo) 
                             VALUES (:f, :p, :cin, :cue, :h, :b, :g)
                             ON CONFLICT (fecha) DO UPDATE SET 
                             peso=EXCLUDED.peso, cintura=EXCLUDED.cintura, cuello=EXCLUDED.cuello,
                             hombros=EXCLUDED.hombros, brazo=EXCLUDED.brazo, gemelo=EXCLUDED.gemelo;"""),
                        params={"f": fecha_hoy, "p": peso, "cin": cintura, "cue": cuello, "h": hombros, "b": brazo, "g": gemelo}
                    )
                    s.commit()
                st.toast("✅ Mediciones registradas con éxito")
            except Exception as e:
                st.error(f"Error al guardar las mediciones: {e}")

                # --- TAB 6: BUSCAR FECHA ---
with tab6:
    st.subheader("Consultar días anteriores")
    
    # Selector de fecha independiente
    fecha_busqueda = st.date_input("Selecciona el día que quieres ver", value=fecha_hoy, key="fecha_buscar")
    
    log_busqueda = cargar_log_hoy(fecha_busqueda)
    
    if not log_busqueda.empty:
        for col in ['grasas', 'carbohidratos', 'proteina', 'kcal']:
            log_busqueda[col] = pd.to_numeric(log_busqueda[col], errors='coerce').fillna(0)
            
        totales_busq = log_busqueda[['grasas', 'carbohidratos', 'proteina', 'kcal']].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Proteína", f"{totales_busq['proteina']:.0f}g", f"{totales_busq['proteina'] - OBJETIVOS['Proteina']:.0f}g")
        c2.metric("Carbs", f"{totales_busq['carbohidratos']:.0f}g", f"{totales_busq['carbohidratos'] - OBJETIVOS['Carbohidratos']:.0f}g")
        c3.metric("Grasas", f"{totales_busq['grasas']:.0f}g", f"{totales_busq['grasas'] - OBJETIVOS['Grasas']:.0f}g")
        
        st.write(f"**Calorías totales: {totales_busq['kcal']:.0f} / {OBJETIVOS['Kcal']} kcal**")
        st.progress(min(float(totales_busq['kcal']) / OBJETIVOS['Kcal'], 1.0))
        
        st.divider()
        
        # --- Distribución por comida con métricas destacadas ---
        st.markdown("### 🍽️ Distribución por comida")
        distribucion_busq = log_busqueda.groupby('momento')['kcal'].sum()
        
        if not distribucion_busq.empty:
            cols_dist = st.columns(len(distribucion_busq))
            for col, (mom, kcal) in zip(cols_dist, distribucion_busq.items()):
                col.metric(mom, f"{kcal:.0f} kcal")
        
        st.divider()
        
        for _, row in log_busqueda.iterrows():
            col_info, col_del = st.columns([4, 1])
            col_info.write(f"**{row['momento']}**: {row['comida']} ({row['kcal']:.0f} kcal)")
            
            # Usamos una key distinta (del_busq_...) para evitar conflictos con el tab "Hoy"
            if col_del.button("🗑️", key=f"del_busq_{row['id']}"):
                try:
                    with conn.session as s:
                        s.execute(text("DELETE FROM log_diario WHERE id = :id"), params={"id": row['id']})
                        s.commit()
                    st.toast("✅ Registro eliminado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hubo un problema al eliminar: {e}")
    else:
        st.info("Nada registrado en esta fecha.")