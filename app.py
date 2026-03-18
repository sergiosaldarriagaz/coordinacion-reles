import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Coordinación 50/51", layout="centered")
st.title("Estudio de Coordinación de Protecciones")
st.markdown("Herramienta de simulación de curvas de sobrecorriente y daño de transformadores.")

# --- 1. FUNCIONES MATEMÁTICAS ---
def curva_rele(I, I_p, dial, curva, I_tdef, T_def):
    if I_p <= 0: return np.full_like(I, np.inf)
    constantes = {
        'IEC Normal Inversa': (0.14, 0.02, 0.0),
        'IEC Muy Inversa': (13.5, 1.0, 0.0),
        'IEC Extremadamente Inversa': (80.0, 2.0, 0.0),
        'ANSI Moderadamente Inversa': (0.0515, 0.02, 0.114),
        'ANSI Muy Inversa': (19.61, 2.0, 0.491),
        'ANSI Extremadamente Inversa': (28.2, 2.0, 0.1217)
    }
    K, alpha, B = constantes[curva]
    PSM = np.clip(I / I_p, 0, 20) # Límite de 20 veces el pickup
    with np.errstate(divide='ignore', invalid='ignore'):
        t_curva = dial * (K / (PSM**alpha - 1) + B)
        t_curva = np.where(PSM >= 1.03, t_curva, np.inf)
    t_definido = np.where(I >= I_tdef, T_def, np.inf)
    return np.minimum(t_curva, t_definido)

def dano_transformador(I_pu, P_mva, Z_cc):
    if P_mva <= 0 or Z_cc <= 0 or I_pu < 2 or I_pu > (1/Z_cc): return np.inf
    if P_mva <= 0.5 or Z_cc <= 0.04:
        return 19500 / (I_pu**3.8) if I_pu < 4.6 else 1250 / (I_pu**2)
    elif P_mva <= 5:
        return 19500 / (I_pu**3.8) if I_pu < 4.6 else 1250 / (I_pu**2) if (Z_cc * I_pu) <= 0.7 else 2 / ((I_pu**2) * (Z_cc**2))
    else:
        return 19500 / (I_pu**3.8) if I_pu < 4.6 else 1250 / (I_pu**2) if (Z_cc * I_pu) <= 0.5 else 2 / ((I_pu**2) * (Z_cc**2))

# --- 2. INTERFAZ MÓVIL (GUI) ---
tab1, tab2, tab3 = st.tabs(["Relés", "Trafos", "Análisis Icc"])

reles_data = []
with tab1:
    st.markdown("### Configuración de Relés (50/51)")
    st.caption("Pon Ip=0 para desactivar un relé de la gráfica.")
    # Generamos los 5 relés
    for i in range(5): 
        with st.expander(f"Relé {i+1}", expanded=(i==0)): # Solo el primero se muestra desplegado por defecto
            curva = st.selectbox(f"Curva R{i+1}", ['IEC Normal Inversa', 'IEC Muy Inversa', 'IEC Extremadamente Inversa', 'ANSI Moderadamente Inversa', 'ANSI Muy Inversa', 'ANSI Extremadamente Inversa'], key=f"c_{i}")
            ip = st.number_input(f"Ip (A) R{i+1}", value=100.0 if i==0 else 0.0, step=10.0, key=f"ip_{i}")
            dial = st.number_input(f"Dial R{i+1}", value=1.0, step=0.1, key=f"d_{i}")
            itdef = st.number_input(f"I Tiempo Def (A) R{i+1}", value=1000.0, step=100.0, key=f"it_{i}")
            tdef = st.number_input(f"T Def (s) R{i+1}", value=0.1, step=0.05, key=f"td_{i}")
            reles_data.append({'curva': curva, 'ip': ip, 'dial': dial, 'itdef': itdef, 'tdef': tdef})

trafos_data = []
with tab2:
    st.markdown("### Curvas de Daño Térmico y Mecánico")
    st.caption("Pon Potencia=0 para desactivar un transformador.")
    # Generamos los 2 transformadores
    for i in range(2):
        with st.expander(f"Transformador {i+1}", expanded=(i==0)):
            mva = st.number_input(f"Potencia (MVA) T{i+1}", value=2.0 if i==0 else 0.0, step=0.5, key=f"mva_{i}")
            zcc = st.number_input(f"Impedancia Zcc (pu) T{i+1}", value=0.05, step=0.01, key=f"zcc_{i}")
            inom = st.number_input(f"Corriente Nominal (A) T{i+1}", value=100.0, step=10.0, key=f"inom_{i}")
            trafos_data.append({'mva': mva, 'zcc': zcc, 'inom': inom})

with tab3:
    st.markdown("### Simulación de Falla")
    st.caption("Intersección de operación para análisis selectivo.")
    icc_val = st.number_input("Corriente de Cortocircuito (A)", value=1500.0, step=100.0)

# --- 3. GENERACIÓN DE GRÁFICA ---
if st.button("Generar Gráfica", type="primary", use_container_width=True):
    fig, ax = plt.subplots(figsize=(10, 6)) # Tamaño adaptado para mostrar todo bien
    corrientes = np.logspace(1, 4, 1000)
    colores = ['#003f5c', '#bc5090', '#ff6361', '#ffa600', '#2f4b7c'] # Paleta de colores profesionales
    
    # 1. Graficar Relés
    for i, r in enumerate(reles_data):
        if r['ip'] > 0:
            t = curva_rele(corrientes, r['ip'], r['dial'], r['curva'], r['itdef'], r['tdef'])
            ax.plot(corrientes, t, label=f'Relé {i+1}: {r["curva"]}', color=colores[i], linewidth=2.5)
            
            # Etiqueta de tiempo exacto en la Icc
            if icc_val > 0:
                t_op = curva_rele(np.array([icc_val]), r['ip'], r['dial'], r['curva'], r['itdef'], r['tdef'])[0]
                if t_op != np.inf and not np.isnan(t_op):
                    ax.scatter([icc_val], [t_op], color=colores[i], s=80, zorder=5)
                    ax.annotate(f' {t_op:.3f} s', xy=(icc_val, t_op), xytext=(8, 0), textcoords='offset points', color=colores[i], fontweight='bold', va='center')

    # 2. Graficar Transformadores
    for i, t in enumerate(trafos_data):
        if t['mva'] > 0 and t['inom'] > 0:
            c_pu = corrientes / t['inom']
            t_trafo = [dano_transformador(ipu, t['mva'], t['zcc']) for ipu in c_pu]
            ax.plot(corrientes, t_trafo, label=f'Límite Daño Trafo {i+1}', linestyle='-.', color='gray', linewidth=2)

    # 3. Marcar la corriente de falla global
    if icc_val > 0:
        ax.axvline(x=icc_val, color='black', linestyle='--', alpha=0.5, label=f'Icc = {icc_val} A')

    # Configuración del plano logarítmico
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(10, 10000)
    ax.set_ylim(0.01, 1000)
    ax.grid(True, which="both", ls="--", alpha=0.5)
    ax.set_title('Curvas de Coordinación de Protecciones', fontweight='bold')
    ax.set_xlabel('Corriente (Amperios)')
    ax.set_ylabel('Tiempo (Segundos)')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small') # Leyenda por fuera de la gráfica
    
    plt.tight_layout()
    st.pyplot(fig) # Muestra la gráfica en la interfaz web