# Weather Forecast Application

Current conditions and five-day forecasts from OpenWeather, with an explicit offline demo.

This is a fresh implementation based on the project description in Ravi Kumar's resume. It does not claim to recover an earlier codebase or demonstrate past production usage.

## Run locally

Requires Python 3.11+. From this repository:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m flask --app app run --port 5000
```

Open http://localhost:5000. Set configuration as environment variables; `.env.example` documents the available values. Flask does not automatically load `.env` unless python-dotenv is installed. For persistent sessions set SECRET_KEY to a random secret. SQLite data is created automatically in `instance/app.db`. To reset local data, stop the server and remove that database.

## Verify

```sh
python -m pytest -q
python -m ruff check .
```

## Docker

```sh
docker build -t weather-forecast-application .
docker run --rm -p 5000:5000 -e SECRET_KEY=your-random-secret -v weather-forecast-application-data:/app/instance weather-forecast-application
```

The image serves with Waitress as a non-root user. Check volume ownership if using a host directory. `/api/health` returns a health check. Never commit `.env`, database files or credentials.

## Deployment boundaries

This is a portfolio application. Before public deployment, use HTTPS, set COOKIE_SECURE=true for cookie apps, configure a persistent database and SECRET_KEY, add authentication rate limiting, monitoring and backups, and review access rules. No default account or password is shipped. CI is configured to run lint and tests on pushes and pull requests.

## Live and demo modes

Get an OpenWeather API key with access to current weather and the 5 day / 3 hour forecast. The server uses the Direct Geocoding API to resolve a city to latitude and longitude. Keys stay on the server.

PowerShell demo:
```powershell
$env:WEATHER_DEMO='true'
python -m flask --app app run
```

PowerShell live mode:
```powershell
$env:WEATHER_DEMO='false'
$env:OPENWEATHER_API_KEY='your-key'
python -m flask --app app run
```

GET /api/weather?city=Hyderabad,IN&units=metric returns normalized current conditions and one forecast reading nearest noon for each upcoming local date, up to five dates. Available dates depend on the provider forecast window. Supported units are metric (Celsius, m/s) and imperial (Fahrenheit, mph). No key means an actionable 503 response; demo mode is opt-in and visibly labeled. Timeouts, missing cities, malformed provider responses and provider rate limits have distinct error handling. Tests mock provider requests; no paid API calls run in CI. Add request rate limiting and caching before exposing a live key through a public deployment.

Provider docs: https://openweathermap.org/current and https://openweathermap.org/forecast5 and https://openweathermap.org/api/geocoding-api
