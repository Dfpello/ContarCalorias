import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Macros App", page_icon="💪", layout="centered")

# Objetivos fijados por el usuario
OBJETIVOS = {
    "Grasas": 70.0,
    "Carbohidratos": 240.0,
    "Proteina": 160.0,
    "Kcal": 2230.0 # (70*9 + 240*4 + 160*4)
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
st.title("💪 Mi Diario de Macros")
bbdd = cargar_bbdd()
fecha_hoy = datetime.now().strftime('%Y-%m-%d')

# Creamos las pestañas para la navegación móvil
tab1, tab2, tab3, tab4 = st.tabs(["➕ Registrar", "📊 Hoy", "📜 Historial", "⚙️ BBDD"])

# --- TAB 1: REGISTRAR CONSUMO ---
with tab1:
    st.subheader("¿Qué has comido?")
    momento = st.selectbox("Momento del día", ["Desayuno", "Comida", "Merienda", "Cena", "Otro"])
    
    busqueda = st.text_input("🔍 Buscar alimento en BBDD...")
    
    if busqueda:
        coincidencias = bbdd[bbdd['Comida'].str.contains(busqueda, case=False, na=False)]
        
        if not coincidencias.empty:
            seleccion = st.selectbox("Selecciona el plato", coincidencias['Comida'].tolist())
            plato = coincidencias[coincidencias['Comida'] == seleccion].iloc[0]
            
            unidad_texto = "gramos" if "100g" in str(plato['Porcion']) else "unidades"
            cantidad = st.number_input(f"Cantidad en {unidad_texto}", min_value=0.1, value=100.0 if unidad_texto=="gramos" else 1.0)
            
            if st.button("Añadir al Diario"):
                factor = cantidad / 100.0 if "100g" in str(plato['Porcion']) else cantidad
                nuevo_log = {
                    "Fecha": fecha_hoy,
                    "Momento": momento,
                    "Comida": plato['Comida'],
                    "Grasas": round(plato['Grasas'] * factor, 2),
                    "Carbohidratos": round(plato['Carbohidratos'] * factor, 2),
                    "Proteina": round(plato['Proteina'] * factor, 2),
                    "Kcal": round(plato['Calorias'] * factor, 2)
                }
                
                # Guardar
                log_actual = cargar_log()
                log_actual = pd.concat([log_actual, pd.DataFrame([nuevo_log])], ignore_index=True)
                log_actual.to_csv('log_diario.csv', index=False)
                st.success(f"✅ {plato['Comida']} añadido a {momento}")
                st.rerun()
        else:
            st.warning("No se encontró el alimento. Añádelo en la pestaña BBDD.")

# --- TAB 2: RESUMEN DE HOY Y ELIMINAR ---
with tab2:
    st.subheader(f"Resumen: {datetime.now().strftime('%d/%m/%Y')}")
    log = cargar_log()
    hoy_df = log[log['Fecha'] == fecha_hoy].reset_index() # Reset index para poder borrar correctamente
    
    if not hoy_df.empty:
        totales = hoy_df[['Grasas', 'Carbohidratos', 'Proteina', 'Kcal']].sum()
        
        # Métricas de colores
        c1, c2, c3 = st.columns(3)
        c1.metric("Proteína", f"{totales['Proteina']:.1f}g", f"{totales['Proteina'] - OBJETIVOS['Proteina']:.1f}g")
        c2.metric("Carbs", f"{totales['Carbohidratos']:.1f}g", f"{totales['Carbohidratos'] - OBJETIVOS['Carbohidratos']:.1f}g")
        c3.metric("Grasas", f"{totales['Grasas']:.1f}g", f"{totales['Grasas'] - OBJETIVOS['Grasas']:.1f}g")
        
        st.divider()
        st.write(f"**Calorías:** {totales['Kcal']:.0f} / {OBJETIVOS['Kcal']:.0f} kcal")
        st.progress(min(totales['Kcal'] / OBJETIVOS['Kcal'], 1.0))
        
        # Fila de Pendientes
        pend_p = max(0, OBJETIVOS['Proteina'] - totales['Proteina'])
        st.info(f"🚩 Falta para el objetivo: **{pend_p:.1f}g de Proteína**")

        # Lista de comidas con opción de borrar
        st.write("### Desglose y Edición")
        for i, row in hoy_df.iterrows():
            col_info, col_del = st.columns([4, 1])
            col_info.write(f"**{row['Momento']}**: {row['Comida']} ({row['Kcal']:.0f} kcal)")
            # Usamos el índice original del log para borrar
            if col_del.button("🗑️", key=f"btn_{row['index']}"):
                log_completo = cargar_log()
                log_completo = log_completo.drop(row['index'])
                log_completo.to_csv('log_diario.csv', index=False)
                st.rerun()
    else:
        st.info("Todavía no has registrado nada hoy.")

# --- TAB 3: HISTORIAL COMPLETO ---
with tab3:
    st.subheader("Historial de registros")
    log_h = cargar_log()
    if not log_h.empty:
        st.dataframe(log_h.sort_values(by="Fecha", ascending=False), use_container_width=True)
        if st.button("Limpiar todo el historial"):
            if st.confirm("¿Seguro que quieres borrar TODO el historial?"):
                os.remove('log_diario.csv')
                st.rerun()
    else:
        st.write("No hay datos guardados.")

# --- TAB 4: GESTIONAR BBDD ---
with tab4:
    st.subheader("Añadir nuevo alimento a BBDD")
    with st.form("form_bbdd"):
        n_nombre = st.text_input("Nombre del alimento")
        col_a, col_b, col_c = st.columns(3)
        n_g = col_a.number_input("Grasas", min_value=0.0, step=0.1)
        n_c = col_b.number_input("Carbs", min_value=0.0, step=0.1)
        n_p = col_c.number_input("Proteína", min_value=0.0, step=0.1)
        n_uni = st.radio("Porción base", ["100g", "1U"], horizontal=True)
        
        if st.form_submit_button("Guardar Alimento"):
            if n_nombre:
                n_kcal = (n_g * 9) + (n_c * 4) + (n_p * 4)
                nueva_comida = pd.DataFrame([{
                    "Comida": n_nombre, "Grasas": n_g, "Carbohidratos": n_c,
                    "Proteina": n_p, "Porcion": n_uni, "Calorias": n_kcal
                }])
                nueva_comida.to_csv('bbdd_final.csv', mode='a', index=False, header=not os.path.exists('bbdd_final.csv'))
                st.success(f"✅ {n_nombre} guardado.")
                st.rerun()
            else:
                st.error("Ponle un nombre al alimento.")

    st.divider()
    st.write("### Alimentos actuales")
    st.dataframe(bbdd, use_container_width=True)
