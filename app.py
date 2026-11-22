import os
from datetime import datetime, timedelta, timezone
import requests
from flask import abort, render_template, request
from common import create_base, text


def create_app(config=None):
    app = create_base(config)
    app.config.setdefault("OPENWEATHER_API_KEY", os.environ.get("OPENWEATHER_API_KEY", ""))
    app.config.setdefault("WEATHER_DEMO", os.environ.get("WEATHER_DEMO", "false").lower() == "true")

    @app.get("/")
    def index():
        return render_template("index.html")

    def upstream(path, params):
        try:
            response = requests.get("https://api.openweathermap.org/"+path,params={**params,"appid":app.config["OPENWEATHER_API_KEY"]},timeout=(3,8))
            if response.status_code == 404:
                abort(404,"City not found. Check the spelling or add a country code.")
            if response.status_code in (401,403):
                abort(503,"Weather service credentials are unavailable or inactive.")
            if response.status_code == 429:
                abort(503,"Weather service limit reached. Try again later.")
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            abort(504,"Weather service timed out. Try again.")
        except (requests.RequestException,ValueError):
            abort(502,"Weather service is unavailable. Try again later.")

    def normalize(item):
        return {"time":item["dt"],"temperature":item["main"]["temp"],"feels_like":item["main"]["feels_like"],"humidity":item["main"]["humidity"],"wind_speed":item["wind"]["speed"],"description":item["weather"][0]["description"]}

    @app.get("/api/weather")
    def weather():
        city = text(request.args.get("city"),"City",100)
        units = request.args.get("units","metric")
        if units not in {"metric","imperial"}:
            abort(400,"Units must be metric or imperial.")
        now = datetime.now(timezone.utc)
        if app.config["WEATHER_DEMO"]:
            temp = 27 if units == "metric" else 80.6
            current = {"time":int(now.timestamp()),"temperature":temp,"feels_like":temp+1,"humidity":62,"wind_speed":3.2 if units == "metric" else 7.2,"description":"sample scattered clouds"}
            forecast = [dict(current,time=int((now+timedelta(days=i)).timestamp()),temperature=round(temp+i*.4,1)) for i in range(1,6)]
            return {"city":city+" (sample)","country":"Demo","units":units,"timezone":0,"demo":True,"current":current,"forecast":forecast,"updated_at":now.isoformat()}
        if not app.config["OPENWEATHER_API_KEY"]:
            abort(503,"Set OPENWEATHER_API_KEY for live weather, or WEATHER_DEMO=true for sample data.")
        places = upstream("geo/1.0/direct",{"q":city,"limit":1})
        if not isinstance(places,list) or not places:
            abort(404,"City not found. Try City,CountryCode.")
        try:
            place = places[0]
            params = {"lat":place["lat"],"lon":place["lon"],"units":units}
            current = upstream("data/2.5/weather",params)
            forecast = upstream("data/2.5/forecast",params)
            offset = current.get("timezone",0)
            days = {}
            for item in forecast["list"]:
                local = datetime.fromtimestamp(item["dt"]+offset,timezone.utc)
                key = local.date().isoformat()
                if key == datetime.fromtimestamp(current["dt"]+offset,timezone.utc).date().isoformat():
                    continue
                candidate = (abs(local.hour-12),item)
                if key not in days or candidate[0] < days[key][0]:
                    days[key] = candidate
            return {"city":place["name"],"country":place.get("country",""),"units":units,"timezone":offset,"demo":False,"current":normalize(current),"forecast":[normalize(v[1]) for _,v in sorted(days.items())][:5],"updated_at":now.isoformat()}
        except (KeyError,TypeError,IndexError,ValueError):
            abort(502,"Weather service returned incomplete data. Try again later.")

    return app
