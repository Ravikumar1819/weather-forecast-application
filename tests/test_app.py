from datetime import datetime,timezone
from unittest.mock import Mock,patch
import pytest
import requests
from app import create_app


@pytest.fixture
def client():
    return create_app({"TESTING":True,"WEATHER_DEMO":False,"OPENWEATHER_API_KEY":"test-only"}).test_client()


def reply(payload,status=200):
    r=Mock(status_code=status)
    r.json.return_value=payload
    if status >= 400:
        r.raise_for_status.side_effect=requests.HTTPError()
    return r


def reading(dt=1795348800):
    return {"dt":dt,"main":{"temp":25,"feels_like":26,"humidity":60},"wind":{"speed":4},"weather":[{"description":"clear sky"}],"timezone":19800}


def test_demo_is_explicit_and_units():
    c=create_app({"TESTING":True,"WEATHER_DEMO":True}).test_client()
    r=c.get("/api/weather?city=Hyderabad&units=imperial")
    assert r.status_code == 200 and r.json["demo"] is True
    assert r.json["current"]["temperature"] == 80.6 and len(r.json["forecast"]) == 5
    assert c.get("/api/weather?city=Hyderabad&units=bad").status_code == 400
    assert c.get("/api/weather?city=").status_code == 400


def test_live_normalization_and_forecast(client):
    now=int(datetime(2026,11,22,6,tzinfo=timezone.utc).timestamp())
    with patch("app.requests.get",side_effect=[reply([{"lat":17.3,"lon":78.4,"name":"Hyderabad","country":"IN"}]),reply(reading(now)),reply({"list":[reading(now+86400),reading(now+2*86400)]})]) as get:
        r=client.get("/api/weather?city=Hyderabad,IN")
    assert r.status_code == 200 and r.json["demo"] is False
    assert r.json["city"] == "Hyderabad" and len(r.json["forecast"]) == 2
    assert get.call_count == 3 and get.call_args.kwargs["timeout"] == (3,8)
    assert get.call_args.kwargs["params"]["lat"] == 17.3


@pytest.mark.parametrize("response,status",[(reply([],200),404),(reply({},401),503),(reply({},429),503),(reply({},500),502)])
def test_provider_failures(client,response,status):
    with patch("app.requests.get",return_value=response):
        assert client.get("/api/weather?city=Unknown").status_code == status


def test_timeout_bad_payload_and_no_key(client):
    with patch("app.requests.get",side_effect=requests.Timeout):
        assert client.get("/api/weather?city=London").status_code == 504
    with patch("app.requests.get",return_value=reply([{}])):
        assert client.get("/api/weather?city=London").status_code == 502
    c=create_app({"TESTING":True,"WEATHER_DEMO":False,"OPENWEATHER_API_KEY":""}).test_client()
    assert c.get("/api/weather?city=London").status_code == 503
