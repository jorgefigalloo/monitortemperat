import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import tempfile
import base64

st.set_page_config(page_title="Monitor de Temperatura", layout="wide")

st.title("📈 Análisis de Temperatura - Estación Clínica Carita Feliz")

archivo = st.file_uploader("Sube el archivo CSV de temperatura", type=["csv"])

if archivo is not None:
    # Leer contenido del archivo
    contenido = archivo.read().decode('utf-8', errors='ignore')
    lineas = contenido.splitlines()

    # Detectar encabezado
    indice_inicio = None
    for i, linea in enumerate(lineas):
        if re.match(r"MM\.DD\.YYYY", linea.strip()):
            indice_inicio = i + 1
            break

    if indice_inicio is None:
        st.error("No se encontró el encabezado de datos 'MM.DD.YYYY  HH:MM:SS   T' en el archivo.")
    else:
        datos = "\n".join(lineas[indice_inicio:])
        data = io.StringIO(datos)

        # Leer datos
        df = pd.read_csv(
            data,
            delim_whitespace=True,
            names=["Fecha", "Hora", "Temperatura"],
            comment='#',
            skip_blank_lines=True,
            on_bad_lines='skip',
            engine='python'
        )

        # Convertir temperatura a numérico
        df["Temperatura"] = pd.to_numeric(df["Temperatura"], errors='coerce')

        # Convertir a datetime
        df["Datetime"] = pd.to_datetime(df["Fecha"] + " " + df["Hora"], format="%m.%d.%Y %H:%M:%S", errors='coerce')
        df = df.dropna(subset=["Datetime", "Temperatura"])
        df["Día"] = df["Datetime"].dt.date
        df["HoraSolo"] = df["Datetime"].dt.hour + df["Datetime"].dt.minute / 60.0

        st.success("✅ Archivo cargado correctamente y datos procesados.")
        st.dataframe(df.head())

        # ============================
        # 📅 Filtro de rango de fechas
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

        # Soporta un solo día o rango
        if isinstance(rango_fechas, (tuple, list)):
            if len(rango_fechas) == 2:
                fecha_inicio, fecha_fin = rango_fechas
            else:
                fecha_inicio = fecha_fin = rango_fechas[0]
        else:
            fecha_inicio = fecha_fin = rango_fechas

        df_filtrado = df[(df["Día"] >= fecha_inicio) & (df["Día"] <= fecha_fin)]

        st.write(f"Mostrando datos desde **{fecha_inicio}** hasta **{fecha_fin}**.")
        st.write(f"Total de registros en el rango: **{len(df_filtrado)}**")

        # Selección de gráfico
        opcion = st.selectbox(
            "Selecciona el tipo de gráfico",
            ("Por día", "Por hora y temperatura", "Promedio diario")
        )

        # ===================================
        # 📊 Gráficos
        # ===================================
        fig, ax = plt.subplots(figsize=(10, 4))

        if opcion == "Por día":
            dias_unicos = df_filtrado["Día"].unique()
            if len(dias_unicos) == 1:
                dia = dias_unicos[0]
                datos_dia = df_filtrado[df_filtrado["Día"] == dia]
                ax.plot(datos_dia["HoraSolo"], datos_dia["Temperatura"], marker="o", color="orange")
                ax.set_title(f"Temperatura detallada por hora ({dia})")
                ax.set_xlabel("Hora del día")
            else:
                for dia, datos_dia in df_filtrado.groupby("Día"):
                    ax.plot(datos_dia["Datetime"], datos_dia["Temperatura"], label=str(dia))
                ax.legend(title="Fecha", fontsize=8)
                ax.set_title("Evolución de la temperatura (por día)")
            ax.set_ylabel("Temperatura (°C)")
            ax.grid(True, linestyle='--', alpha=0.5)

        elif opcion == "Por hora y temperatura":
            ax.plot(df_filtrado["Datetime"], df_filtrado["Temperatura"], color="blue", linewidth=1)
            ax.set_title("Temperatura continua en el tiempo")
            ax.set_xlabel("Fecha y hora")
            ax.set_ylabel("Temperatura (°C)")
            plt.xticks(rotation=45)

        elif opcion == "Promedio diario":
            promedio = df_filtrado.groupby("Día")["Temperatura"].mean().dropna()
            promedio.plot(kind="bar", ax=ax, color="green")
            ax.set_xlabel("Día")
            ax.set_ylabel("Temperatura promedio (°C)")
            ax.set_title("Promedio diario de temperatura")

        st.pyplot(fig)

        # ===================================
        # 📋 Resumen de temperaturas
        # ===================================
        st.subheader("📋 Resumen de temperaturas extremas")

        temp_max = df_filtrado.loc[df_filtrado["Temperatura"].idxmax()]
        temp_min = df_filtrado.loc[df_filtrado["Temperatura"].idxmin()]
        temp_mean = df_filtrado["Temperatura"].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("🌡️ Máxima", f"{temp_max['Temperatura']:.2f} °C", f"{temp_max['Día']} {temp_max['Hora']}")
        col2.metric("🥶 Mínima", f"{temp_min['Temperatura']:.2f} °C", f"{temp_min['Día']} {temp_min['Hora']}")
        col3.metric("📉 Promedio", f"{temp_mean:.2f} °C")

        # ===================================
        # 🧾 Exportar a PDF
        # ===================================
        st.subheader("📄 Exportar reporte a PDF")

        if st.button("📥 Generar reporte PDF"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
                c = canvas.Canvas(tmpfile.name, pagesize=A4)
                width, height = A4

                # Encabezado
                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, height - 50, "Reporte de Temperatura - Clínica Carita Feliz")
                c.setFont("Helvetica", 11)
                c.drawString(50, height - 70, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")

                # Info del rango
                c.setFont("Helvetica", 12)
                c.drawString(50, height - 110, f"Rango analizado: {fecha_inicio} a {fecha_fin}")
                c.drawString(50, height - 130, f"Tipo de gráfico: {opcion}")

                # Datos de resumen
                c.drawString(50, height - 160, f"Temperatura máxima: {temp_max['Temperatura']:.2f} °C ({temp_max['Día']} {temp_max['Hora']})")
                c.drawString(50, height - 175, f"Temperatura mínima: {temp_min['Temperatura']:.2f} °C ({temp_min['Día']} {temp_min['Hora']})")
                c.drawString(50, height - 190, f"Temperatura promedio: {temp_mean:.2f} °C")

                # Insertar gráfico
                img_buffer = io.BytesIO()
                fig.savefig(img_buffer, format='PNG', bbox_inches='tight')
                img_buffer.seek(0)
                c.drawImage(ImageReader(img_buffer), 40, 250, width=500, height=300, mask='auto')

                # Pie
                c.setFont("Helvetica-Oblique", 10)
                c.drawString(200, 40, "Generado automáticamente con Monitor de Temperatura")

                c.showPage()
                c.save()

                # Descargar PDF
                with open(tmpfile.name, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()
                    b64 = base64.b64encode(pdf_bytes).decode()
                    href = f'<a href="data:application/octet-stream;base64,{b64}" download="Reporte_Temperatura.pdf">📄 Descargar PDF</a>'
                    st.markdown(href, unsafe_allow_html=True)

            st.success("✅ Reporte PDF generado correctamente.")

else:
    st.info("Por favor, sube un archivo CSV para comenzar.")
