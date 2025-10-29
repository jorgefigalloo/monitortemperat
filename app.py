import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import re

st.set_page_config(page_title="Monitor de Temperatura", layout="wide")

st.title("📈 Análisis de Temperatura - Estación Clinica carita feliz")

archivo = st.file_uploader("Sube el archivo CSV de temperatura", type=["csv"])

if archivo is not None:
    # Leer todo el contenido del archivo
    contenido = archivo.read().decode('utf-8', errors='ignore')
    lineas = contenido.splitlines()

    # Buscar automáticamente el inicio de los datos reales
    indice_inicio = None
    for i, linea in enumerate(lineas):
        if re.match(r"MM\.DD\.YYYY", linea.strip()):
            indice_inicio = i + 1  # la siguiente línea es donde empiezan los datos
            break

    if indice_inicio is None:
        st.error("No se encontró el encabezado de datos 'MM.DD.YYYY  HH:MM:SS   T' en el archivo.")
    else:
        # Solo tomar las líneas con datos
        datos = "\n".join(lineas[indice_inicio:])
        data = io.StringIO(datos)

        # Leer el bloque de datos
        df = pd.read_csv(
            data,
            delim_whitespace=True,
            names=["Fecha", "Hora", "Temperatura"],
            comment='#',
            skip_blank_lines=True,
            on_bad_lines='skip',
            engine='python'
        )

        # Asegurar que la columna de temperatura sea numérica
        df["Temperatura"] = pd.to_numeric(df["Temperatura"], errors='coerce')

        # Convertir a datetime y separar día y hora
        df["Datetime"] = pd.to_datetime(df["Fecha"] + " " + df["Hora"], format="%m.%d.%Y %H:%M:%S", errors='coerce')
        df = df.dropna(subset=["Datetime", "Temperatura"])
        df["Día"] = df["Datetime"].dt.date
        df["HoraSolo"] = df["Datetime"].dt.hour + df["Datetime"].dt.minute / 60.0

        st.success("✅ Archivo cargado correctamente y datos procesados.")
        st.dataframe(df.head())

        # ============================
        # 🔍 Filtro de rango de fechas
        # ============================
        fecha_min = df["Día"].min()
        fecha_max = df["Día"].max()

        st.subheader("📅 Filtro de rango de fechas")
        rango_fechas = st.date_input(
            "Selecciona una fecha o rango de fechas a visualizar:",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max
        )

        # ✅ Soporta una sola fecha o un rango
        if isinstance(rango_fechas, (tuple, list)):
            if len(rango_fechas) == 2:
                fecha_inicio, fecha_fin = rango_fechas
            else:
                fecha_inicio = fecha_fin = rango_fechas[0]
        else:
            fecha_inicio = fecha_fin = rango_fechas

        # Filtrar datos por rango de fechas
        df_filtrado = df[(df["Día"] >= fecha_inicio) & (df["Día"] <= fecha_fin)]

        st.write(f"Mostrando datos desde **{fecha_inicio}** hasta **{fecha_fin}**.")
        st.write(f"Total de registros en el rango: **{len(df_filtrado)}**")

        # Selección de tipo de gráfico
        opcion = st.selectbox(
            "Selecciona el tipo de gráfico",
            ("Por día", "Por hora y temperatura", "Promedio diario")
        )

        # ===================================================
        # 📊 Gráfico por día — con mejora si es un solo día
        # ===================================================
        if opcion == "Por día":
            fig, ax = plt.subplots(figsize=(10, 4))

            dias_unicos = df_filtrado["Día"].unique()

            # Si el rango es un solo día → gráfico detallado por hora
            if len(dias_unicos) == 1:
                dia = dias_unicos[0]
                datos_dia = df_filtrado[df_filtrado["Día"] == dia]
                ax.plot(
                    datos_dia["HoraSolo"],
                    datos_dia["Temperatura"],
                    marker="o",
                    color="orange",
                    linewidth=1.5,
                    markersize=4
                )
                ax.set_xlabel("Hora del día")
                ax.set_ylabel("Temperatura (°C)")
                ax.set_title(f"Temperatura detallada por hora ({dia})")
                ax.grid(True, linestyle='--', alpha=0.5)
                plt.xticks(range(0, 25, 1))
            else:
                # Varios días → traza cada día como línea separada
                for dia, datos_dia in df_filtrado.groupby("Día"):
                    ax.plot(datos_dia["Datetime"], datos_dia["Temperatura"], label=str(dia))
                ax.set_xlabel("Fecha y hora")
                ax.set_ylabel("Temperatura (°C)")
                ax.set_title("Evolución de la temperatura (Día y Hora)")
                ax.legend(title="Fecha", fontsize=8)
                plt.xticks(rotation=45)

            st.pyplot(fig)

        # ===================================================
        # 📈 Gráfico continuo en el tiempo
        # ===================================================
        elif opcion == "Por hora y temperatura":
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(df_filtrado["Datetime"], df_filtrado["Temperatura"], color="blue", linewidth=1)
            ax.set_xlabel("Fecha y hora")
            ax.set_ylabel("Temperatura (°C)")
            ax.set_title("Temperatura continua en el tiempo")
            plt.xticks(rotation=45)
            st.pyplot(fig)

        # ===================================================
        # 📊 Promedio diario
        # ===================================================
        elif opcion == "Promedio diario":
            promedio = df_filtrado.groupby("Día")["Temperatura"].mean().dropna()
            fig, ax = plt.subplots(figsize=(10, 4))
            promedio.plot(kind="bar", ax=ax)
            ax.set_xlabel("Día")
            ax.set_ylabel("Temperatura promedio (°C)")
            ax.set_title("Promedio diario de temperatura")
            st.pyplot(fig)

        # ===================================================
        # 📈 Análisis automático
        # ===================================================
        temp_max = df_filtrado["Temperatura"].max()
        temp_min = df_filtrado["Temperatura"].min()
        temp_mean = df_filtrado["Temperatura"].mean()
        variacion = temp_max - temp_min

        st.subheader("📊 Análisis de Temperatura (rango seleccionado)")
        st.write(f"🌡️ **Temperatura máxima:** {temp_max:.2f} °C")
        st.write(f"🥶 **Temperatura mínima:** {temp_min:.2f} °C")
        st.write(f"📉 **Temperatura promedio:** {temp_mean:.2f} °C")

        if variacion > 5:
            st.warning("⚠️ Se detectaron **grandes variaciones** de temperatura en el periodo analizado.")
        else:
            st.info("✅ Las variaciones de temperatura se mantuvieron dentro de un rango estable.")
else:
    st.info("Por favor, sube un archivo CSV para comenzar.")
