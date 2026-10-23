# Borrador de post para LinkedIn

**Imagen para adjuntar:** `notebook/figures/fig4_anomaly_mexico_fashion.png`
(el gráfico de la caída — es el más visual e "intrigante" para parar el scroll;
el segundo mejor candidato es `fig5_cancellation_rate.png` como segunda imagen
del carrusel, para mostrar la confirmación de causa raíz en la misma publicación).

**Link:** https://github.com/lucasagustinpiccoli/marketpulse-ecommerce-analytics

---

## Versión en español (sugerida como principal)

¿Cómo distinguís una caída real de ventas de un simple ruido estacional?

Armé un caso de análisis end-to-end (datos 100% sintéticos, ninguna empresa real) para mostrar el flujo completo que uso en mi trabajo de Data/BI Analyst:

🔎 Un detector de anomalías en SQL (CTEs + funciones de ventana) marca 14 semanas "raras" en el dataset.
📅 13 de esas 14 son la misma semana del año — pura estacionalidad post-diciembre, no un problema real.
🚨 Pero 1 se destaca sola: una categoría en una región específica cae 75% por debajo de su base, y la tasa de cancelación del mismo segmento se duplica en simultáneo.

Esa combinación (volumen abajo + cancelaciones arriba, aislado a un solo segmento) es la firma de una falla operativa real, no de menor demanda — y es exactamente el tipo de diagnóstico que hice de forma recurrente en mi rol en PedidosYa (Rider Care), ahora reconstruido acá con datos ficticios para poder compartirlo libremente.

El repo incluye:
🐍 Python + pandas + gráficos (notebook completo)
🗃️ SQL con CTEs, funciones de ventana y detección de anomalías
🤖 Un agente de IA (Claude) que convierte las métricas en un resumen de incidente redactado para negocio
📄 Case study completo en el README

Repo: https://github.com/lucasagustinpiccoli/marketpulse-ecommerce-analytics

#DataAnalytics #BusinessIntelligence #SQL #Python #AI #Analytics

---

## English version (alternative, for international recruiters)

How do you tell a real demand drop apart from ordinary seasonal noise?

I built an end-to-end analysis case (100% synthetic data, no real company) to show the workflow I use as a Data/BI Analyst:

🔎 A SQL anomaly detector (CTEs + window functions) flags 14 "odd" weeks in the dataset.
📅 13 of them are the same calendar week — pure post-holiday seasonality, not a real issue.
🚨 But 1 stands alone: one category in one region drops 75% below its baseline, and that segment's cancellation rate doubles at the same time.

That combination — volume down, cancellations up, isolated to a single segment — is the signature of a real operational failure, not softer demand. It's the same kind of diagnosis I did regularly in my Rider Care role at PedidosYa, rebuilt here on fictional data so I can actually share it.

What's in the repo:
🐍 Python + pandas + charts (full notebook)
🗃️ SQL with CTEs, window functions, and anomaly detection
🤖 An AI agent (Claude) that turns the metrics into a business-ready incident summary
📄 Full case study in the README

Repo: https://github.com/lucasagustinpiccoli/marketpulse-ecommerce-analytics

#DataAnalytics #BusinessIntelligence #SQL #Python #AI #Analytics

---

## Notas
- Si querés, puedo armar un segundo post (parte 2) más adelante mostrando
  específicamente el agente de IA (`ai_agent/insight_agent.py`) con su output
  real — buena forma de tener contenido recurrente sin tener que armar un
  proyecto nuevo cada vez.
- Considerá fijar (pin) el post en tu perfil mientras estás buscando trabajo.
