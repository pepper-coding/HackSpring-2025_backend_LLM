from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import random
import math
import uvicorn
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def alive():
    return {"alive": True}

class Position(BaseModel):
    x: float
    y: float
    z: float

class Shelf(BaseModel):
    id: str
    position: Position
    rotation: float
    interactions: int
    discount: Optional[float] = 0

class StoreSize(BaseModel):
    width: float
    length: float
    height: float

class StoreConfig(BaseModel):
    storeSize: StoreSize
    shelves: List[Shelf]
    entrance: Position
    cashDesks: List[Position]
    createdAt: str

class SimRequest(BaseModel):
    config: StoreConfig
    timeOfDay: str
    promotions: Optional[List[str]] = []
    categories: Optional[List[str]] = []
    shelfDiscounts: Optional[Dict[str, float]] = {}
    prefersDiscounts: Optional[bool] = False

def distance(p1: Position, p2: Position) -> float:
    return math.sqrt((p1.x - p2.x)**2 + (p1.z - p2.z)**2)

def rotate_position(position: Position, angle: float) -> Position:
    """Поворот точки с учетом угла"""
    angle_rad = math.radians(angle)
    x_new = position.x * math.cos(angle_rad) - position.z * math.sin(angle_rad)
    z_new = position.x * math.sin(angle_rad) + position.z * math.cos(angle_rad)
    return Position(x=x_new, y=position.y, z=z_new)

def get_visitors_count(time_of_day: str) -> int:
    """Определяет количество посетителей в зависимости от времени суток"""
    try:
        hour = int(time_of_day.split(":")[0])
    except:
        if time_of_day == "morning":
            hour = 9
        elif time_of_day == "afternoon":
            hour = 15
        elif time_of_day == "evening":
            hour = 19
        else:
            hour = 12

    if (12 <= hour < 14) or (17 <= hour < 19):
        return random.randint(40, 50)
    elif (8 <= hour < 10) or (14 <= hour < 17):
        return random.randint(20, 35)
    else:
        return random.randint(5, 15)

def get_shelf_type_and_size(shelf_id: str) -> dict:
    """Возвращает тип и размер полки по ID в формате 'размер-тип-номер'"""
    try:
        parts = shelf_id.split('-')
        if len(parts) < 2:
            return {"type": "unknown", "size": [1.5, 1.5, 0.6]}

        size_map = {
            "small": [1.0, 1.5, 0.6],
            "medium": [1.5, 1.5, 0.6],
            "large": [2.5, 1.5, 0.6]
        }

        shelf_size = size_map.get(parts[0].lower(), [1.5, 1.5, 0.6])
        shelf_type = parts[1].lower()

        type_mapping = {
            "vegetables": "vegetables",
            "bakery": "bakery",
            "dairy": "dairy",
            "electronics": "electronics",
            "produce" : "produce",
            "meat" : "meat",
        }

        shelf_type = type_mapping.get(shelf_type, shelf_type)

        return {"type": shelf_type, "size": shelf_size}
    except:
        return {"type": "unknown", "size": [1.5, 1.5, 0.6]}

def find_nearest_cash_desk(position: Position, cash_desks: List[Position]) -> Position:
    """Находит ближайшую кассу к заданной позиции"""
    if not cash_desks:
        return None

    nearest = cash_desks[0]
    min_dist = distance(position, nearest)

    for desk in cash_desks[1:]:
        dist = distance(position, desk)
        if dist < min_dist:
            min_dist = dist
            nearest = desk

    return nearest

@app.post("/simulate")
async def simulate(sim: SimRequest):
    config = sim.config
    entrance = config.entrance
    shelves = config.shelves
    cash_desks = config.cashDesks

    num_visitors = get_visitors_count(sim.timeOfDay)

    visitors = []
    heatmap = {}
    cash_desk_queues = {f"{desk.x},{desk.z}": 0 for desk in cash_desks}

    grid_size = 1.0
    grid_width = int(config.storeSize.width / grid_size)
    grid_length = int(config.storeSize.length / grid_size)
    heatmap_grid = [[0 for _ in range(grid_width)] for _ in range(grid_length)]

    for i in range(num_visitors):
        visitor_id = i
        preferences = []

        if sim.categories:
            preferences = random.sample(sim.categories, k=random.randint(1, min(3, len(sim.categories))))
        else:
            preferences = random.choices(["bakery", "vegetables", "dairy", "electronics", "produce", "meat"], k=random.randint(1, 3))

        if sim.prefersDiscounts:
            preferences.append("discount_lover")

        visited_shelves = []
        path = [{"x": entrance.x, "z": entrance.z}]

        sorted_shelves = sorted(
            shelves,
            key=lambda s: (
                0 if any(pref.lower() in get_shelf_type_and_size(s.id)["type"].lower() for pref in preferences) or
                   ("discount_lover" in preferences and s.discount and s.discount > 0)
                else 1,
                distance(entrance, s.position)
            )
        )

        last_position = entrance
        for shelf in sorted_shelves:
            shelf_data = get_shelf_type_and_size(shelf.id)
            shelf_type = shelf_data["type"]

            if (any(pref.lower() in shelf_type.lower() for pref in preferences) or
                ("discount_lover" in preferences and shelf.discount and shelf.discount > 0)):

                approach_position = Position(
                    x=shelf.position.x - 0.5 * math.sin(math.radians(shelf.rotation)),
                    y=shelf.position.y,
                    z=shelf.position.z - 0.5 * math.cos(math.radians(shelf.rotation))
                )

                path.append({"x": approach_position.x, "z": approach_position.z})
                visited_shelves.append(shelf.id)
                last_position = approach_position

                # Обновляем тепловую карту
                grid_x = int((approach_position.x + config.storeSize.width/2) / grid_size)
                grid_z = int((approach_position.z + config.storeSize.length/2) / grid_size)

                if 0 <= grid_x < grid_width and 0 <= grid_z < grid_length:
                    heatmap_grid[grid_z][grid_x] += 1

        if cash_desks:
            nearest_cash_desk = find_nearest_cash_desk(last_position, cash_desks)
            if nearest_cash_desk:
                path.append({"x": nearest_cash_desk.x, "z": nearest_cash_desk.z})
                cash_desk_key = f"{nearest_cash_desk.x},{nearest_cash_desk.z}"
                cash_desk_queues[cash_desk_key] += 1

        path.append({"x": entrance.x, "z": entrance.z})

        visitors.append({
            "id": visitor_id,
            "preferences": preferences,
            "path": [[p["x"], p["z"]] for p in path],
            "queue_time": round(random.uniform(0.2, 0.5), 1),
            "visited_shelves": visited_shelves,
            "final_position": [entrance.x, entrance.z]
        })

    return {
        "visitors": visitors,
        "heatmap": heatmap_grid,
        "events": {
            "broken_cash_desk": False,
            "promotions": sim.promotions or []
        },
        "stats": {
            "total_visitors": len(visitors),
            "avg_queue_time": round(sum(v["queue_time"] for v in visitors) / len(visitors), 2) if visitors else 0,
            "max_queue_length": max(max(row) for row in heatmap_grid) if heatmap_grid else 0,
            "time_of_day": sim.timeOfDay,
            "calculated_visitors": num_visitors,
            "cash_desk_queues": cash_desk_queues
        },
        "store_dimensions": {
            "width": config.storeSize.width,
            "length": config.storeSize.length,
            "grid_size": grid_size
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
