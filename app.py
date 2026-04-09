import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Macros App Online", page_icon="💪", layout="centered")

# Configuración de conexión a BBDD (Se configura en .streamlit/secrets.toml)
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
    query = f"SELECT * FROM log_diario WHERE fecha = '{fecha}';"
    return conn.query(query, ttl=0) # ttl=0 para ver cambios inmediatos

# --- LÓGICA PRINCIPAL ---
st.title("💪 Mi Diario de Macros (Cloud)")
fecha_hoy = datetime.now().date()

tab1, tab2, tab3, tab4 = st.tabs(["➕ Registrar", "📊 Hoy", "📜 Historial", "⚙️ BBDD"])

# --- TAB 1: REGISTRAR CONSUMO ---
with tab1:
    st.subheader("¿Qué has comido?")
    momento = st.selectbox("Momento del día", ["Desayuno", "Comida", "Merienda", "Cena", "Otro"])
    
    # Obtenemos la biblioteca de la BBDD
    biblioteca = cargar_biblioteca()
    
    if not biblioteca.empty:
        alimento_nombres = biblioteca['comida'].tolist()
        seleccion = st.selectbox("Busca y selecciona el plato", [""] + alimento_nombres)
        
        if seleccion:
            plato = biblioteca[biblioteca['comida'] == seleccion].iloc[0]
            es_medida_100 = "100" in str(plato['porcion'])
            unidad_texto = "gramos/ml" if es_medida_100 else "unidades"
            
            cantidad = st.number_input(f"Cantidad en {unidad_texto}", min_value=0.1, value=100.0 if es_medida_100 else 1.0)
            
            if st.button("Añadir al Diario"):
                factor = cantidad / 100.0 if es_medida_100 else cantidad
                
                with conn.session as s:
                    s.execute(
                        "INSERT INTO log_diario (fecha, momento, comida, grasas, carbohidratos, proteina, kcal) "
                        "VALUES (:f, :m, :c, :g, :ca, :p, :k);",
                        params={
                            "f": fecha_hoy, "m": momento, "c": plato['comida'],
                            "g": round(plato['grasas'] * factor, 2),
                            "ca": round(plato['carbohidratos'] * factor, 2),
                            "p": round(plato['proteina'] * factor, 2),
                            "k": round(plato['calorias'] * factor, 2)
                        }
                    )
                    s.commit()
                st.success(f"✅ {plato['comida']} añadido")
                st.rerun()
    else:
        st.warning("La biblioteca está vacía. Añade alimentos en la pestaña BBDD.")

# --- TAB 2: HOY ---
with tab2:
    log_hoy = cargar_log_hoy(fecha_hoy)
    
    if not log_hoy.empty:
        totales = log_hoy[['grasas', 'carbohidratos', 'proteina', 'kcal']].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Proteína", f"{totales['proteina']:.1f}g", f"{totales['proteina'] - OBJETIVOS['Proteina']:.1f}g")
        c2.metric("Carbs", f"{totales['carbohidratos']:.1f}g", f"{totales['carbohidratos'] - OBJETIVOS['Carbohidratos']:.1f}g")
        c3.metric("Grasas", f"{totales['grasas']:.1f}g", f"{totales['grasas'] - OBJETIVOS['Grasas']:.1f}g")
        
        st.progress(min(totales['kcal'] / OBJETIVOS['Kcal'], 1.0))
        
        for _, row in log_hoy.iterrows():
            col_info, col_del = st.columns([4, 1])
            col_info.write(f"**{row['momento']}**: {row['comida']} ({row['kcal']:.0f} kcal)")
            if col_del.button("🗑️", key=f"del_{row['id']}"):
                with conn.session as s:
                    s.execute("DELETE FROM log_diario WHERE id = :id", params={"id": row['id']})
                    s.commit()
                st.rerun()
    else:
        st.info("Nada registrado hoy.")

# --- TAB 3: HISTORIAL ---
with tab3:
    historial = conn.query("SELECT * FROM log_diario ORDER BY fecha DESC, id DESC;", ttl=0)
    st.dataframe(historial, use_container_width=True)

# --- TAB 4: GESTIONAR BBDD ---
with tab4:
    with st.form("form_bbdd"):
        n_nombre = st.text_input("Nombre del alimento")
        col1, col2, col3 = st.columns(3)
        n_g = col1.number_input("Grasas", min_value=0.0)
        n_c = col2.number_input("Carbs", min_value=0.0)
        n_p = col3.number_input("Proteína", min_value=0.0)
        n_uni = st.radio("Porción base", ["100g", "100ml", "1U"], horizontal=True)
        
        if st.form_submit_button("Guardar en BBDD"):
            if n_nombre:
                n_kcal = (n_g * 9) + (n_c * 4) + (n_p * 4)
                with conn.session as s:
                    s.execute(
                        "INSERT INTO biblioteca_alimentos (comida, grasas, carbohidratos, proteina, porcion, calorias) "
                        "VALUES (:n, :g, :c, :p, :por, :k) ON CONFLICT (comida) DO NOTHING;",
                        params={"n": n_nombre, "g": n_g, "c": n_c, "p": n_p, "por": n_uni, "k": n_kcal}
                    )
                    s.commit()
                st.success("Alimento guardado.")
                st.rerun()