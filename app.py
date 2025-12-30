import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Macros App", page_icon="💪", layout="centered")

# Objetivos definidos: Perder grasa y ganar músculo
OBJETIVOS = {
    "Grasas": 70.0,
    "Carbohidratos": 240.0,
    "Proteina": 160.0,
    "Kcal": 2230.0  # Calculado como (70*9) + (240*4) + (160*4)
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

def guardar_comida_en_csv(nueva_entrada):
    archivo_log = 'log_diario.csv'
    df_nueva = pd.DataFrame([nueva_entrada])
    # Guardado incremental: añade cada comida como una fila nueva
    if not os.path.exists(archivo_log):
        df_nueva.to_csv(archivo_log, index=False, encoding='utf-8')
    else:
        df_nueva.to_csv(archivo_log, mode='a', index=False, header=False, encoding='utf-8')

# --- LÓGICA DE INICIO ---
bbdd = cargar_bbdd()
log_completo = cargar_log()
fecha_hoy = datetime.now().strftime('%Y-%m-%d')

st.title("💪 Mi Diario de Macros")

# Pestañas de navegación táctil para móvil
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
            
            # Identificar unidad (g, ml o unidad)
            p_base = str(plato['Porcion']).lower()
            if "100g" in p_base:
                u_medida = "gramos"
                es_prop = True
            elif "100ml" in p_base:
                u_medida = "ml"
                es_prop = True
            else:
                u_medida = "unidades"
                es_prop = False

            cantidad = st.number_input(f"Cantidad en {u_medida}", min_value=0.1, value=100.0 if es_prop else 1.0)
            
            if st.button("🚀 Registrar Comida"):
                factor = cantidad / 100.0 if es_prop else cantidad
                
                datos_registro = {
                    "Fecha": fecha_hoy,
                    "Momento": momento,
                    "Comida": plato['Comida'],
                    "Grasas": round(plato['Grasas'] * factor, 2),
                    "Carbohidratos": round(plato['Carbohidratos'] * factor, 2),
                    "Proteina": round(plato['Proteina'] * factor, 2),
                    "Kcal": round(plato['Calorias'] * factor, 2)
                }
                
                guardar_comida_en_csv(datos_registro)
                st.success(f"✅ {plato['Comida']} guardado correctamente")
                st.rerun()
        else:
            st.warning("Alimento no encontrado en la base de datos.")

# --- TAB 2: RESUMEN DE HOY Y BORRAR ---
with tab2:
    st.subheader(f"Estado: {datetime.now().strftime('%d/%m/%Y')}")
    # Recargar log para ver cambios inmediatos
    log_actualizado = cargar_log()
    hoy_df = log_actualizado[log_actualizado['Fecha'] == fecha_hoy].reset_index()
    
    if not hoy_df.empty:
        totales = hoy_df[['Grasas', 'Carbohidratos', 'Proteina', 'Kcal']].sum()
        
        # Indicadores de Macros
        c1, c2, c3 = st.columns(3)
        c1.metric("Proteína", f"{totales['Proteina']:.1f}g", f"{totales['Proteina'] - OBJETIVOS['Proteina']:.1f}g")
        c2.metric("Carbs", f"{totales['Carbohidratos']:.1f}g", f"{totales['Carbohidratos'] - OBJETIVOS['Carbohidratos']:.1f}g")
        c3.metric("Grasas", f"{totales['Grasas']:.1f}g", f"{totales['Grasas'] - OBJETIVOS['Grasas']:.1f}g")
        
        # Barra de progreso calórico
        st.write(f"**Calorías:** {totales['Kcal']:.0f} / {OBJETIVOS['Kcal']:.0f} kcal")
        st.progress(min(totales['Kcal'] / OBJETIVOS['Kcal'], 1.0))
        
        # Cálculo de lo que falta
        falta_p = max(0, OBJETIVOS['Proteina'] - totales['Proteina'])
        st.info(f"🚩 Pendiente para el objetivo: **{falta_p:.1f}g de Proteína**")

        st.divider()
        st.write("### Comidas de hoy")
        for i, row in hoy_df.iterrows():
            col_info, col_del = st.columns([4, 1])
            col_info.write(f"**{row['Momento']}**: {row['Comida']} ({row['Kcal']:.0f} kcal)")
            if col_del.button("🗑️", key=f"del_{row['index']}"):
                # Al borrar, cargamos el log completo, eliminamos la fila original y guardamos
                full_log = cargar_log()
                full_log = full_log.drop(row['index'])
                full_log.to_csv('log_diario.csv', index=False)
                st.rerun()
    else:
        st.info("No has registrado ninguna comida hoy.")

# --- TAB 3: HISTORIAL COMPLETO ---
with tab3:
    st.subheader("Historial Total")
    if os.path.exists('log_diario.csv'):
        st.dataframe(pd.read_csv('log_diario.csv').sort_values(by="Fecha", ascending=False), use_container_width=True)
    else:
        st.write("No hay registros en el historial.")

# --- TAB 4: GESTIÓN DE BBDD ---
with tab4:
    st.subheader("Añadir Alimento a BBDD")
    with st.form("nuevo_alimento"):
        nombre = st.text_input("Nombre del plato")
        col_g, col_c, col_p = st.columns(3)
        g = col_g.number_input("Grasas", min_value=0.0, step=0.1)
        c = col_c.number_input("Carbs", min_value=0.0, step=0.1)
        p = col_p.number_input("Proteína", min_value=0.0, step=0.1)
        uni = st.radio("Porción base", ["100g", "100ml", "1 U"], horizontal=True)
        
        if st.form_submit_button("Guardar en BBDD"):
            if nombre:
                kcal = (g * 9) + (c * 4) + (p * 4)
                nueva_entrada = pd.DataFrame([{
                    "Comida": nombre, "Grasas": g, "Carbohidratos": c,
                    "Proteina": p, "Porcion": uni, "Calorias": round(kcal, 2)
                }])
                nueva_entrada.to_csv('bbdd_final.csv', mode='a', index=False, header=not os.path.exists('bbdd_final.csv'))
                st.success(f"✅ {nombre} añadido correctamente.")
                st.rerun()
            else:
                st.error("El nombre del alimento es obligatorio.")

    st.divider()
    st.write("### Base de Datos Actual")
    st.dataframe(bbdd, use_container_width=True)