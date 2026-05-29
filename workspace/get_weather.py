import urllib.request
import json

# Guangzhou coordinates
url = "https://api.open-meteo.com/v1/forecast?latitude=23.13&longitude=113.26&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=Asia%2FShanghai"

r = urllib.request.urlopen(url, timeout=15)
data = json.loads(r.read().decode())

current = data["current"]
weather_codes = {
    0: "晴天", 1: "大部晴朗", 2: "局部多云", 3: "多云",
    45: "有雾", 48: "雾凇",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹"
}

weather = weather_codes.get(current["weather_code"], f"未知({current['weather_code']})")
temp = current["temperature_2m"]
feels_like = current["apparent_temperature"]
humidity = current["relative_humidity_2m"]
wind = current["wind_speed_10m"]

print(f"广州天气 ({current['time']})")
print(f"天气：{weather}")
print(f"温度：{temp}°C（体感 {feels_like}°C）")
print(f"湿度：{humidity}%")
print(f"风速：{wind} km/h")
