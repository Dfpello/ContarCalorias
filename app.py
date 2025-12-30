import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Macros App", page_icon="💪", layout="centered")

OBJETIVOS = {
    "Grasas": 70.0,
    "Carbohidratos": 240.0,
    "Proteina": 160.0,
    "Kcal": 2230.0
}

# --- FUNCIONES DE PERSISTENCIA ---
def cargar_bbdd():
    if os.path.exists('bbdd_final.csv'):
        return pd.read_csv('bbdd_final.csv')
    return pd.DataFrame(columns=['Comida', 'Grasas', 'Carbohidratos', 'Proteina', 'Porcion', 'Calorias'])

def cargar_log():
    if os.path.exists('log_diario.csv'):
        return pd.read_csv('log_diario.csv')
    return pd.DataFrame(columns=["Fecha", "Momento", "Comida", "Grasas", "Carbohidratos", "Proteina", "Kcal"])

# --- LÓGICA PRINCIPAL ---
bbdd = cargar_bbdd()
log_completo = cargar_log()
fecha_hoy = datetime.now().strftime('%Y-%m-%d')

st.title("💪 Mi Diario de Macros")

# Pestañas de navegación
tab1, tab2, tab3, tab4 = st.tabs(["➕ Registrar", "📊 Hoy", "📜 Historial", "⚙️ BBDD"])

# --- TAB 1: REGISTRAR CONSUMO ---
with tab1:
    st.subheader("Registrar Alimento")
    momento = st.selectbox("Momento del día", ["Desayuno", "Comida", "Merienda", "Cena", "Otro"])
    
    busqueda = st.text_input("🔍 Buscar alimento...")
    
    if busqueda:
        coincidencias = bbdd[bbdd['Comida'].str.contains(busqueda, case=False, na=False)]
        
        if not coincidencias.empty:
            seleccion = st.selectbox("Selecciona el plato", coincidencias['Comida'].tolist())
            plato = coincidencias[coincidencias['Comida'] == seleccion].iloc[0]
            
            # Identificar unidad según BBDD
            p_base = str(plato['Porcion']).lower()
            if "100g" in p_base:
                u_medida = "gramos"
                es_proporcional = True
            elif "100ml" in p_base:
                u_medida = "ml"
                es_proporcional = True
            else:
                u_medida = "unidades"
                es_proporcional = False

            cantidad = st.number_input(f"Cantidad en {u_medida}", min_value=0.1, value=100.0 if es_proporcional else 1.0)
            
            if st.button("Añadir al Diario"):
                factor = cantidad / 100.0 if es_proporcional else cantidad
                
                nuevo_registro = {
                    "Fecha": fecha_hoy,
                    "Momento": momento,
                    "Comida": plato['Comida'],
                    "Grasas": round(plato['Grasas'] * factor, 2),
                    "Carbohidratos": round(plato['Carbohidratos'] * factor, 2),
                    "Proteina": round(plato['Proteina'] * factor, 2),
                    "Kcal": round(plato['Calorias'] * factor, 2)
                }
                
                # Actualizar y guardar
                log_final = pd.concat([log_completo, pd.DataFrame([nuevo_registro])], ignore_index=True)
                log_final.to_csv('log_diario.csv', index=False)
                st.success(f"✅ {plato['Comida']} guardado")
                st.rerun()
        else:
            st.warning("Alimento no encontrado.")

# --- TAB 2: RESUMEN DE HOY Y BORRADO ---
with tab2:
    st.subheader(f"Estado: {datetime.now().strftime('%d/%m/%Y')}")
    hoy_df = log_completo[log_completo['Fecha'] == fecha_hoy].copy()
    
    if not hoy_df.empty:
        totales = hoy_df[['Grasas', 'Carbohidratos', 'Proteina', 'Kcal']].sum()
        
        # Métricas visuales
        m1, m2, m3 = st.columns(3)
        m1.metric("Prot", f"{totales['Proteina']:.1f}g", f"{totales['Proteina'] - OBJETIVOS['Proteina']:.1f}g")
        m2.metric("Carbs", f"{totales['Carbohidratos']:.1f}g", f"{totales['Carbohidratos'] - OBJETIVOS['Carbohidratos']:.1f}g")
        m3.metric("Grasas", f"{totales['Grasas']:.1f}g", f"{totales['Grasas'] - OBJETIVOS['Grasas']:.1f}g")
        
        # Barra de calorías
        st.write(f"**Calorías:** {totales['Kcal']:.0f} / {OBJETIVOS['Kcal']:.0f} kcal")
        st.progress(min(totales['Kcal'] / OBJETIVOS['Kcal'], 1.0))
        
        # Fila de pendientes
        falta_p = max(0, OBJETIVOS['Proteina'] - totales['Proteina'])
        st.info(f"🚩 Pendiente: **{falta_p:.1f}g de Proteína** para el objetivo.")

        st.divider()
        st.write("### Registros de hoy")
        # Mostrar cada fila con botón de eliminar
        for i, row in hoy_df.iterrows():
            c_txt, c_btn = st.columns([4, 1])
            c_txt.write(f"**{row['Momento']}**: {row['Comida']} ({row['Kcal']:.0f} kcal)")
            if c_btn.button("🗑️", key=f"del_{i}"):
                log_completo = log_completo.drop(i)
                log_completo.to_csv('log_diario.csv', index=False)
                st.rerun()
    else:
        st.info("No hay registros para el día de hoy.")

# --- TAB 3: HISTORIAL COMPLETO ---
with tab3:
    st.subheader("Historial Total")
    if not log_completo.empty:
        st.dataframe(log_completo.sort_values(by="Fecha", ascending=False), use_container_width=True)
        if st.button("Eliminar TODO el historial"):
            if st.checkbox("Confirmar borrado total"):
                os.remove('log_diario.csv')
                st.rerun()
    else:
        st.write("Historial vacío.")

# --- TAB 4: GESTIÓN DE BBDD ---
with tab4:
    st.subheader("Añadir Alimento a BBDD")
    with st.form("nuevo_alimento"):
        nombre = st.text_input("Nombre")
        c1, c2, c3 = st.columns(3)
        g = c1.number_input("Grasas", min_value=0.0, format="%.2f")
        c = c2.number_input("Carbs", min_value=0.0, format="%.2f")
        p = c3.number_input("Proteína", min_value=0.0, format="%.2f")
        porcion = st.radio("Porción base", ["100g", "100ml", "1 U"], horizontal=True)
        
        if st.form_submit_button("Guardar en BBDD"):
            if nombre:
                cals = (g * 9) + (c * 4) + (p * 4)
                nueva_fila = pd.DataFrame([{
                    "Comida": nombre, "Grasas": g, "Carbohidratos": c,
                    "Proteina": p, "Porcion": porcion, "Calorias": round(cals, 2)
                }])
                bbdd_actualizada = pd.concat([bbdd, nueva_fila], ignore_index=True)
                bbdd_actualizada.to_csv('bbdd_final.csv', index=False)
                st.success(f"✅ {nombre} añadido a la base de datos.")
                st.rerun()
            else:
                st.error("El nombre es obligatorio.")

    st.divider()
    st.write("### Base de Datos Actual")
    st.dataframe(bbdd, use_container_width=True)