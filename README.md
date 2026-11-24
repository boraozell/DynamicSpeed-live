# DynamicSpeed v43 — Customer-Controlled SUMO Simulator

**What changed:** The visitor can now choose demand, synthetic weather, duration, seed, and 2–3 controllers. This is not a prerecorded replay: the backend builds the same synthetic road and executes fresh SUMO/TraCI experiments. Results are returned as objective J, completed/unfinished vehicles, control limits, and 30-second actual simulated vehicle snapshots. The previous presentation/portfolio pages remain available at `/`.

## Important: GitHub Pages alone cannot run this

`index.html` is the front end; `app/main.py` + `app/simulation.py` are the **Python backend**. Do **not** upload this ZIP to the old GitHub Pages repository expecting the Start Simulation button to work. You need a host that supports Docker and a running Python server. Your current GitHub Pages portfolio remains accessible without changes.

## Quick start — local Docker (recommended for testing)

1. Install Docker Desktop on your computer (or Docker Engine on Linux).
2. Open a terminal **inside this extracted project folder**.
3. Run:

```bash
docker build -t dynamicspeed-live .
docker run --rm -p 8000:8000 dynamicspeed-live
```

4. Open <http://localhost:8000/> and select **Kendi simülasyonunu oluştur** or go to <http://localhost:8000/simulator>.
5. Choose, e.g. **2,600 cars/h, dry, 30 min, Static + Rule-Based**. The browser creates a job, periodically polls status, and displays fresh SUMO runs.

Note: Docker runs SUMO **on the machine running Docker**; Docker Desktop may consume considerable CPU/RAM. Your existing laptop may be slow. No GPU is necessary. SUMO uses TraCI, not libsumo.

## Cloud publishing — Docker web service

1. Push the **entire unzipped project folder** to a new GitHub repository, e.g. `DynamicSpeed-live` (not your old static site repo). Keep `Dockerfile`, `requirements.txt`, `app/`, and `index.html` at the repository root.
2. On a Docker-compatible host (for example Render Web Service, a VPS, or a platform supporting Docker), connect that repository and choose **Docker** as runtime. It will use the included `Dockerfile` and `${PORT}` provided by the host.
3. Use a **paid always-on service with enough CPU/RAM** for prolonged SUMO workloads; background simulation jobs are in-memory and will be lost if the service sleeps/restarts or its request worker is recycled. Confirm the host's job execution and resource limits. Multi-worker is not supported with the current in-process job queue.
4. Check `https://YOUR-SERVICE/api/health`. It should report `"sumo":true` and `"netconvert":true`.
5. Use `https://YOUR-SERVICE/` as the full live version, including old pages and new customer simulation. Once it works, you can put a link to the new URL on the existing GitHub Pages site or use your own domain. **Do not replace your existing GitHub Pages index with this one expecting SUMO to run there.**

## API

- `POST /api/simulations` with JSON `{ "demand": 2600, "weather": "dry", "duration_minutes": 30, "seed": 314, "policies": ["static", "rule"] }`
- `GET /api/simulations/{id}` to poll the state
- `GET /api/simulations/{id}/result` when complete
- `GET /api/health` for service check

### Limits and assumptions

- Synthetic **6 km, 3→1→3 lane** corridor. Controlled edges e1/e2, sensor e3. Cars enter during first two thirds of the simulation. All policies use same route, demand, and seed.
- 30/60/90 min and 1200–4200 cars/hour are permitted via API. Browser UI provides discrete presets. Up to three control policies per job.
- Policies: static 100 km/h, baseline Rule-Based thresholds 40/65 km/h, 5-minute simplified two-reservoir MPC (not calibrated), and synthetic weather-aware rule. Maximum 10 km/h adjustment per minute.
- Objective: `J = H + 0.25 * unfinished_vehicles + 0.03 * ten_km_limit_changes`; H vehicle-hours from SUMO `running + waiting` snapshots per second. **Not** a directly measured travel time reduction.
- Weather changes following-distance, accel/decel and preferred speed: **not measured precipitation or validated weather driving behavior**.
- 30-second traffic replay snapshots are simulated SUMO road/lane positions; road/vehicles rendered schematically. No real GPS, live weather, public road deployment or real crash predictions.
- One experiment uses one random seed. Use several separate seeds to check variability; changing total duration/injection time changes the experiment, so v43 results should **not** be compared directly to the original 90-min archived results unless conditions match.

### Prototype vs production

This is a working research prototype, **not a public SaaS-ready backend**. It uses a single process, in-memory job queue, ephemeral results, basic per-IP rate limits and one simulation worker. Before opening publicly to unknown users add authentication, shared persistent job state/storage, absolute job execution limits/worker monitoring, managed queue and per-user quotas. Simulation can be CPU-intensive and hosting may cost money.

Config environment variables: `DS_OUTPUT_DIR`, `DS_MAX_QUEUED` (default 3), `DS_MAX_HISTORY` (default 12), `DS_MAX_REQUESTS_PER_HOUR` (default 3). The Docker service should run with **one** uvicorn worker. Test with `PYTHONPATH=. pytest -q` (pytest is a test-only dependency).

### Technical attribution

Core network, route generation, weather assumptions, control rules, simplified MPC forecast and J metric are adapted from the user's own `DynamicSpeed_12_WeatherAware_Full.ipynb` study. Changes include user-selected experiment duration and updated demand-injection schedule, new position recording, API queue and client-side visualizations.

### Final SUMO runtime verification (must run where SUMO is installed)

After Docker build, run:

```bash
docker run --rm dynamicspeed-live python -m app.smoke
```

This executes two new 5-minute SUMO runs and checks that each produces both real trajectory frames and nonnegative objective J. It is a smoke test, **not** evidence of traffic optimization performance.
