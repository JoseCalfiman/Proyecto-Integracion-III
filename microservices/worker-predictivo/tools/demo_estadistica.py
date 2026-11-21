import json
import sys
import argparse
import tempfile
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from predictor import calcular_pendiente, evaluar_riesgo
from descriptive_stats import FACTOR_IQR, calcular_estadisticas


def formato(valor):
    if valor is None:
        return "No calculable"
    return f"{valor:.3f}".rstrip("0").rstrip(".")


def generar_informe(escenarios, destino):
    secciones = []
    for nombre, temperaturas, esperado in escenarios:
        ventana = [
            {"timestamp": i * 60, "temperature": temperatura}
            for i, temperatura in enumerate(temperaturas)
        ]
        resultado = evaluar_riesgo(ventana, absolute_max_temp=-10)
        estadisticas = calcular_estadisticas(temperaturas)
        diagnostico = resultado["diagnostico"]
        pendiente_original = calcular_pendiente(
            [lectura["timestamp"] for lectura in ventana], temperaturas,
        )
        filas = "".join(
            f"<tr><th>{etiqueta}</th><td>{formato(estadisticas[clave])}</td></tr>"
            for clave, etiqueta in [
                ("sample_count", "Muestras"), ("media", "Media (°C)"),
                ("mediana", "Mediana (°C)"), ("std", "Desviación muestral (°C)"),
                ("min", "Mínimo (°C)"), ("max", "Máximo (°C)"),
                ("q1", "Q1 (°C)"), ("q3", "Q3 (°C)"), ("iqr", "IQR (°C)"),
            ]
        )
        atipicos = "".join(
            f"<li>Lectura {lectura['index'] + 1}, segundo {lectura['timestamp']}: "
            f"{formato(lectura['temperature'])} °C</li>"
            for lectura in diagnostico["outliers"]
        ) or "<li>Ninguna lectura marcada.</li>"
        interpretaciones = {
            "VENTANA_INSUFICIENTE": "Evidencia insuficiente para estimar una tendencia.",
            "DATOS_VARIABLES": "La ventana original tiene dispersión elevada según el umbral de 0,5 °C.",
            "CON_ATIPICOS": "Hay lecturas fuera de los límites IQR que requieren revisión.",
        }
        calidad = " ".join(
            interpretaciones[condicion] for condicion in diagnostico["condiciones"]
        ) or "Ventana suficiente, con baja dispersión y sin atípicos detectados."
        riesgo = (
            "Evaluación pendiente por falta de datos utilizables."
            if "VENTANA_INSUFICIENTE" in diagnostico["condiciones"]
            else f"Nivel predictivo {resultado['nivel_riesgo']}. "
                 f"Alerta predictiva: {'sí' if resultado['hay_riesgo'] else 'no'}."
        )
        limites = "No calculables"
        if estadisticas["iqr"] is not None:
            margen = FACTOR_IQR * estadisticas["iqr"]
            limites = (
                f"{formato(estadisticas['q1'] - margen)} a "
                f"{formato(estadisticas['q3'] + margen)} °C"
            )
        detalles = escape(json.dumps(resultado, indent=2, ensure_ascii=False))
        secciones.append(f"""
        <section>
          <h2>{escape(nombre)}</h2>
          <p class="lecturas">Lecturas (°C): {escape(str(temperaturas))}</p>
          <p>{escape(esperado)}</p>
          <div class="grid">
            <article><h3>M1 · Describir</h3><table>{filas}</table></article>
            <article><h3>M2 · Identificar atípicos</h3>
              <p>Límites de aceptación IQR: {limites}</p>
              <p><strong>{diagnostico["outlier_count"]} lecturas atípicas</strong></p>
              <ul>{atipicos}</ul>
              <p>Las lecturas originales se conservan.</p></article>
            <article><h3>M3 · Proteger la predicción</h3>
              <p>Pendiente original: <strong>{formato(pendiente_original)} °C/min</strong></p>
              <p>Pendiente con lecturas aceptadas:
                <strong>{formato(resultado["pendiente_por_minuto"])} °C/min</strong></p>
              <p>Tiempo restante: {formato(resultado["tiempo_restante_min"])} min</p>
              <p>{escape(riesgo)}</p></article>
            <article><h3>M4 · Diagnosticar calidad</h3>
              <p><strong>{escape(calidad)}</strong></p>
              <p>{diagnostico["sample_count"]} muestras recibidas ·
                {diagnostico["usable_sample_count"]} aceptadas ·
                {formato(diagnostico["span_minutes"])} minutos de ventana</p>
              <p>El diagnóstico describe los datos. El nivel predictivo describe
                el tiempo estimado hasta el límite de temperatura.</p></article>
          </div>
          <details><summary>Ver resultado técnico completo</summary><pre>{detalles}</pre></details>
        </section>""")
    contenido = """<!doctype html>
<html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CryoMetric · Avances M1–M4</title>
<style>
body{font:16px/1.6 system-ui,sans-serif;background:#f3f6fa;color:#162b40;margin:0}
main{max-width:1150px;margin:auto;padding:32px 20px}
h1{font-size:32px;margin-bottom:4px}h2{margin-top:0}h3{color:#185c79}
section{background:white;border:1px solid #d8e1ea;border-radius:14px;padding:24px;margin:26px 0}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}
article{min-width:0}table{border-collapse:collapse;width:100%}
th,td{text-align:left;border-bottom:1px solid #e2e8ef;padding:6px}
td{font-variant-numeric:tabular-nums}th{font-weight:500}
.lecturas{font-family:monospace;font-size:16px;overflow-wrap:anywhere}
details{margin-top:20px}summary{cursor:pointer;color:#185c79}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6fa;padding:16px}
footer{color:#41566b}@media(max-width:700px){.grid{grid-template-columns:1fr}}
@media print{body{background:white}section{break-inside:avoid}details{display:none}}
</style><main>
<h1>CryoMetric · Avances M1–M4</h1>
<p>Demostración con cálculos del Predictor y cuatro series controladas.</p>
<p>Una muestra cada minuto · Límite de temperatura −10 °C ·
Alerta predictiva al llegar al límite en 40 minutos o menos.</p>
""" + "".join(secciones) + """
<footer>Datos simulados. Umbral descriptivo de variabilidad inicial de 0,5 °C,
pendiente de validación por el equipo. Un atípico estadístico requiere revisión.
Si el último dato es atípico, el tiempo restante corresponde al instante de
la última lectura aceptada. La detección de límites absolutos corresponde a HACCP.
Los resultados se calculan al generar este informe.</footer></main></html>"""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Genera un informe visual de M1 a M4.")
    parser.add_argument(
        "--output", type=Path,
        default=Path(tempfile.gettempdir()) / "cryometric-demo-m1-m4.html",
        help="Ubicación del informe HTML.",
    )
    args = parser.parse_args()
    escenarios = [
        ("Ventana insuficiente", [-18],
         "Una lectura no permite calcular una tendencia."),
        ("Temperatura estable", [-18, -18, -18, -18, -18],
         "Pendiente y desviación cero; ninguna lectura atípica."),
        ("Pico aislado de temperatura", [-18, -18.1, -17.9, -18, 20],
         "El valor 20 queda auditable; la pendiente pasa de 7.61 a 0.02 grados/min."),
        ("Aumento real de temperatura", [-18, -17, -16],
         "Se conserva la pendiente de 1 grado/min; faltan 6 min hasta -10 grados."),
    ]

    generar_informe(escenarios, args.output)
    print(f"Informe generado: {args.output.resolve()}")
    print("Abre el archivo HTML en tu navegador para presentar los cuatro avances.")


if __name__ == "__main__":
    main()
