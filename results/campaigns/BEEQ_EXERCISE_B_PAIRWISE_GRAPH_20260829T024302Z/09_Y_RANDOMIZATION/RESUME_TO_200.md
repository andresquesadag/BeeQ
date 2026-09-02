# Ampliación de Y-randomization a 200 repeticiones

La campaña actual contiene 5 repeticiones completas, guardadas atómicamente en
`09_Y_RANDOMIZATION/checkpoints/`.

Desde `C:\Github_Repos\BeeQ`, ejecutar:

```powershell
.\.venv\Scripts\python.exe -m src.exercise_b_campaign `
  --campaign-dir "C:\Github_Repos\BeeQ\results\campaigns\BEEQ_EXERCISE_B_PAIRWISE_GRAPH_20260829T024302Z" `
  --resume `
  --y-replicates 200
```

El parámetro `--y-replicates` es el total objetivo, no el número de repeticiones
adicionales. Por tanto, el comando reutiliza las repeticiones 1–5 y calcula solo
las 195 faltantes. Los seeds son deterministas y cada repetición se escribe en un
checkpoint separado antes de actualizar el CSV agregado.

Benchmark local: 394.9768583 segundos por repetición completa. La proyección
lineal para 200 es 21.94 horas en este equipo; por eso la ejecución actual se
limitó a 5 y debe interpretarse exclusivamente como diagnóstico exploratorio.
