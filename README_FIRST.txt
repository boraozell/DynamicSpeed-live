DynamicSpeed v43.1 LOW MEMORY - Render Free (512 MB)

Github repo root must have: main.py simulation.py __init__.py simulator.html Dockerfile requirements.txt index.html.
Replace ONLY: main.py simulation.py simulator.html Dockerfile with these files. Do NOT overwrite requirements.txt or index.html.
Initial test: dry, 600 vehicles/hour, 10 minutes, seed 314, Static 100 + Rule-Based.
Changes: 1-minute sample interval, max 400 vehicle drawings per sampled frame (counts still calculated from full frame), two-policy limit, lower traffic & duration caps, SUMO teleport after 300s to bound stuck queue, SUMO_HOME set.
WARNING: The teleport rule changes model semantics, so outcomes must NOT be compared directly with original v12 research results. This package is a capacity-constrained demonstration, not a scientifically equivalent model.
The 512MB free tier may STILL fail under load. If OOM persists, use a service with more RAM or run simulations in Colab/local, not Render free.
No real SUMO end-to-end run was possible in this environment (SUMO executable is not installed), so test with Render logs and results.
