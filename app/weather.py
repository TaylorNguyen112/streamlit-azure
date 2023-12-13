import datetime as dt
import requests

BASE_URL = 'http://api.openweathermap.org/data/2.5/weather?'
API_KEY = 'dbaecf4fed2aa7d835d57610058b46e8'
CITY = "Philippines"

def kelvin_to_celsius_fahrenheit(kelvin):
    celsius = kelvin - 273.15
    fahrenheit = celsius * (9/5) + 32
    return celsius, fahrenheit

def weather_report():
    url = BASE_URL + "appid=" + API_KEY + "&q=" + CITY
    response = requests.get(url).json()

    temp_kelvin = response['main']['temp']
    temp_celsius, temp_fahrenheit = kelvin_to_celsius_fahrenheit(temp_kelvin)
    feels_like_kelvin = response['main']['feels_like']
    feels_like_celsius, feels_like_fahrenheit = kelvin_to_celsius_fahrenheit(feels_like_kelvin)
    humidity = response['main']['humidity']
    wind_speed = response['wind']['speed']
    description = response['weather'][0]['description']

    weather_description = f"Weather Report in {CITY}:\nTemperature: {temp_celsius:.2f} Celsius or {temp_fahrenheit:.2f} Fahrenheit\nTemperature feels like: {feels_like_celsius:.2f} Celsius or {feels_like_fahrenheit:.2f} Fahrenheit\nHumidity: {humidity}%\nWind Speed: {wind_speed}m/s\nDescription: {description}"

    return weather_description






