"""Constraint-aware Dijkstra routing on a fictional campus graph."""
import heapq
import math
from core import APIError, Database, rows

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY,name TEXT NOT NULL,x INTEGER NOT NULL,y INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS edges(id INTEGER PRIMARY KEY,a TEXT REFERENCES nodes(id),b TEXT REFERENCES nodes(id),
 distance INTEGER NOT NULL CHECK(distance>0),slope REAL NOT NULL CHECK(slope>=0),
 width INTEGER NOT NULL CHECK(width>0),stairs INTEGER NOT NULL CHECK(stairs IN(0,1)),
 blocked INTEGER NOT NULL DEFAULT 0 CHECK(blocked IN(0,1)));
"""


def shortest_path(nodes, edges, start, end, step_free=True, max_slope=8, min_width=90):
    """Return the shortest feasible route; O((V+E) log V). Edges are undirected."""
    if start not in nodes or end not in nodes:
        raise APIError("Choose valid start and destination nodes.")
    graph = {node: [] for node in nodes}
    excluded = []
    for edge in edges:
        reasons = []
        if edge["blocked"]:
            reasons.append("closed")
        if step_free and edge["stairs"]:
            reasons.append("stairs")
        if edge["slope"] > max_slope:
            reasons.append("slope exceeds preference")
        if edge["width"] < min_width:
            reasons.append("too narrow")
        if reasons:
            excluded.append({"edge": edge["id"], "reasons": reasons})
            continue
        for a, b in ((edge["a"], edge["b"]), (edge["b"], edge["a"])):
            graph[a].append((b, edge["distance"], edge["id"]))
    distance = {start: 0}
    previous = {}
    queue = [(0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != distance[node]:
            continue
        if node == end:
            break
        for neighbor, weight, edge_id in graph[node]:
            candidate = cost + weight
            if candidate < distance.get(neighbor, math.inf):
                distance[neighbor] = candidate
                previous[neighbor] = (node, edge_id)
                heapq.heappush(queue, (candidate, neighbor))
    if end not in distance:
        return {"found": False, "nodes": [], "edges": [], "distance": None, "excluded": excluded}
    route, route_edges = [end], []
    while route[-1] != start:
        parent, edge_id = previous[route[-1]]
        route.append(parent)
        route_edges.append(edge_id)
    return {"found": True, "nodes": route[::-1], "edges": route_edges[::-1], "distance": distance[end], "excluded": excluded}


class AccessPath:
    def __init__(self, path):
        self.db = Database(path)
        self.db.initialize(SCHEMA, self.seed)

    @staticmethod
    def seed(conn):
        conn.executemany("INSERT INTO nodes VALUES (?,?,?,?)", [
            ("gate", "Main gate", 75, 215), ("quad", "Courtyard", 270, 95),
            ("library", "Library", 470, 95), ("ramp", "Garden ramp", 270, 330),
            ("lab", "Computer lab", 620, 220), ("hall", "Lecture hall", 470, 330)])
        conn.executemany("INSERT INTO edges(a,b,distance,slope,width,stairs) VALUES (?,?,?,?,?,?)", [
            ("gate", "quad", 70, 3, 150, 0), ("quad", "library", 60, 4, 120, 0),
            ("library", "lab", 40, 0, 110, 1), ("gate", "ramp", 85, 2, 140, 0),
            ("ramp", "hall", 70, 5, 100, 0), ("hall", "lab", 65, 4, 120, 0),
            ("quad", "ramp", 60, 12, 80, 0), ("library", "hall", 90, 6, 100, 0)])

    def handle(self, method, path, data, query):
        with self.db.connect() as conn:
            if path == "/map" and method == "GET":
                return {"nodes": rows(conn.execute("SELECT * FROM nodes ORDER BY id")), "edges": rows(conn.execute("SELECT * FROM edges ORDER BY id"))}
            if path.startswith("/edges/") and method == "PATCH":
                try:
                    edge_id = int(path.rsplit("/", 1)[-1])
                except ValueError:
                    raise APIError("Edge ID must be a number.")
                if not isinstance(data.get("blocked"), bool):
                    raise APIError("Blocked must be true or false.")
                if not conn.execute("UPDATE edges SET blocked=? WHERE id=?", (int(data["blocked"]), edge_id)).rowcount:
                    raise APIError("Path segment not found.", 404)
                return {"updated": edge_id}
            if path == "/plan" and method == "POST":
                step_free = data.get("step_free", True)
                slope, width = data.get("max_slope", 8), data.get("min_width", 90)
                if not isinstance(step_free, bool):
                    raise APIError("Step-free must be true or false.")
                for value, label, minimum, maximum in ((slope, "Slope", 0, 20), (width, "Width", 50, 250)):
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
                        raise APIError(f"{label} must be between {minimum} and {maximum}.")
                nodes = {r["id"] for r in conn.execute("SELECT id FROM nodes")}
                start, end = data.get("start"), data.get("end")
                if not isinstance(start, str) or not isinstance(end, str):
                    raise APIError("Start and destination must be node IDs.")
                return shortest_path(nodes, rows(conn.execute("SELECT * FROM edges")), start, end, step_free, slope, width)
        raise APIError("Endpoint not found.", 404)
