import math

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import current_user
from ..models import User

router = APIRouter(prefix="/api/v1/food", tags=["food"])
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = "https://overpass-api.de/api/interpreter"


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371
    first, second = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    value = math.sin(delta_lat / 2) ** 2 + math.cos(first) * math.cos(second) * math.sin(delta_lon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


@router.get("/search")
async def search_nearby_food(
    location: str = Query(min_length=2, max_length=150),
    meal: str = Query(default="不限"),
    _: User = Depends(current_user),
):
    headers = {"User-Agent": "ZhenzhiAgent/1.0"}
    try:
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            geocode = await client.get(NOMINATIM, params={"q": location, "format": "jsonv2", "limit": 1})
            geocode.raise_for_status()
            places = geocode.json()
            if not places:
                raise HTTPException(status_code=404, detail="未找到该位置，请输入更具体的地址")
            lat, lon = float(places[0]["lat"]), float(places[0]["lon"])
            query = f'[out:json][timeout:15];(node["amenity"~"restaurant|cafe|fast_food"](around:4000,{lat},{lon});way["amenity"~"restaurant|cafe|fast_food"](around:4000,{lat},{lon}););out center tags 30;'
            response = await client.post(OVERPASS, data={"data": query})
            response.raise_for_status()
            elements = response.json().get("elements", [])
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="附近餐馆检索超时，请稍后重试") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"地图/餐馆服务暂不可用：{exc}") from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=502, detail="地图服务返回数据格式无效") from exc

    results = []
    for element in elements:
        tags = element.get("tags", {})
        coords = element.get("center", element)
        if not tags.get("name") or "lat" not in coords or "lon" not in coords:
            continue
        distance = _distance_km(lat, lon, float(coords["lat"]), float(coords["lon"]))
        price = tags.get("price_range") or tags.get("price_level")
        results.append({
            "name": tags["name"],
            "type": tags.get("cuisine", tags.get("amenity", "餐饮")),
            "distance_km": round(distance, 2),
            "price": price,
            "address": tags.get("addr:street", ""),
            "open_hours": tags.get("opening_hours", ""),
            "map_url": f"https://www.openstreetmap.org/?mlat={coords['lat']}&mlon={coords['lon']}#map=17/{coords['lat']}/{coords['lon']}",
        })
    results.sort(key=lambda item: (item["price"] is None, item["distance_km"]))
    return {
        "location": places[0].get("display_name", location),
        "meal": meal,
        "results": results,
        "notice": "结果来自 OpenStreetMap 实时数据；仅按已提供的价位标签与距离排序。缺价位信息的店铺不代表低价，也不含虚构评分。",
    }
