import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Mi Contador de Macros", page_icon="💪", layout="centered")

# Objetivos fijos
OBJETIVOS = {"Grasas": 70.0, "Carbohidratos": 240.0, "Proteina": 160.0, "Kcal": 2230}

# --- FUNCIONES DE DATOS ---
def cargar_datos():
    if os.path.exists('bbdd_final.csv'):
        return pd.read_csv('bbdd_final.csv')
    return pd.DataFrame(columns=['Comida', 'Grasas', 'Carbohidratos', 'Proteina', 'Porcion', 'Calorias'])

def guardar_registro(nueva_fila):
    archivo = 'log_diario.csv'
    df = pd.DataFrame([nueva_fila])
    if not os.path.exists(archivo):
        df.to_csv(archivo, index=False)
    else:
        df.to_csv(archivo, mode='a', index=False, header=False)

# --- INTERFAZ ---
st.title("💪 Mi Diario de Macros")

bbdd = cargar_datos()
fecha_hoy = datetime.now().strftime('%Y-%m-%d')

# Pestañas para organizar la App
tab1, tab2, tab3 = st.tabs(["➕ Registrar", "📊 Hoy", "📜 Historial"])

with tab1:
    st.subheader("Registrar Alimento")
    
    momento = st.selectbox("Momento del día", ["Desayuno", "Comida", "Merienda", "Cena", "Otro"])
    
    busqueda = st.text_input("🔍 Buscar alimento...")
    if busqueda:
        coincidencias = bbdd[bbdd['Comida'].str.contains(busqueda, case=False, na=False)]
        
        if not coincidencias.empty:
            seleccion = st.selectbox("Selecciona el plato exacto", coincidencias['Comida'].tolist())
            plato = coincidencias[coincidencias['Comida'] == seleccion].iloc[0]
            
            unidad_texto = "Gramos" if "100g" in str(plato['Porcion']) else "Unidades"
            cantidad = st.number_input(f"Cantidad en {unidad_texto}", min_value=0.1, value=100.0 if unidad_texto=="Gramos" else 1.0)
            
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
                guardar_registro(nuevo_log)
                st.success(f"¡{plato['Comida']} añadido!")
        else:
            st.warning("No se encontró el alimento.")

with tab2:
    st.subheader(f"Resumen de Hoy ({datetime.now().strftime('%d/%m/%Y')})")
    
    if os.path.exists('log_diario.csv'):
        log = pd.read_csv('log_diario.csv')
        hoy_df = log[log['Fecha'] == fecha_hoy]
        
        if not hoy_df.empty:
            # Totales
            totales = hoy_df[['Grasas', 'Carbohidratos', 'Proteina', 'Kcal']].sum()
            
            # Mostrar métricas visuales
            col1, col2, col3 = st.columns(3)
            col1.metric("Proteína", f"{totales['Proteina']:.1f}g", f"{totales['Proteina'] - OBJETIVOS['Proteina']:.1f}g")
            col2.metric("Carbs", f"{totales['Carbohidratos']:.1f}g", f"{totales['Carbohidratos'] - OBJETIVOS['Carbohidratos']:.1f}g")
            col3.metric("Grasas", f"{totales['Grasas']:.1f}g", f"{totales['Grasas'] - OBJETIVOS['Grasas']:.1f}g")
            
            st.divider()
            
            # Barras de progreso
            st.write(f"**Calorías Totales:** {totales['Kcal']:.0f} / {OBJETIVOS['Kcal']}")
            progreso_kcal = min(totales['Kcal'] / OBJETIVOS['Kcal'], 1.0)
            st.progress(progreso_kcal)
            
            # Tabla detallada
            st.write("### Detalle de hoy")
            st.dataframe(hoy_df[['Momento', 'Comida', 'Kcal', 'Proteina']], use_container_width=True)
            
            # Lo que falta
            st.info(f"💡 Te faltan **{max(0, OBJETIVOS['Proteina'] - totales['Proteina']):.1f}g de proteína** para tu objetivo.")
        else:
            st.info("No has registrado nada hoy.")
    else:
        st.info("No hay historial disponible.")

with tab3:
    st.subheader("Historial Completo")
    if os.path.exists('log_diario.csv'):
        st.dataframe(pd.read_csv('log_diario.csv'), use_container_width=True)
    else:
        st.write("Archivo de historial no encontrado.")