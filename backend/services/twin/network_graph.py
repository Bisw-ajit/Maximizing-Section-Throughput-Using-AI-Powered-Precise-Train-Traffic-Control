import json
import networkx as nx
from pathlib import Path


class RailNetwork:
    """NetworkX-backed railway graph for RAILOPTIX."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: dict[str, dict] = {}
        self.sections: dict[str, dict] = {}
        self.routes: dict[str, dict] = {}
        self._loaded = False

    def load_from_json(self, path: str) -> None:
        data = json.loads(Path(path).read_text())

        for node in data["nodes"]:
            self.nodes[node["node_id"]] = node
            self.graph.add_node(node["node_id"], **node)

        self.raw_sections = list(data["sections"])
        for section in data["sections"]:
            self.sections[section["section_id"]] = section
            fwd_id = section["section_id"]
            rev_id = f"{section['to_node']}-{section['from_node']}"
            # Forward edge
            self.graph.add_edge(
                section["from_node"], section["to_node"],
                section_id=fwd_id, length_km=section["length_km"],
                capacity=section["capacity"]
            )
            # Reverse edge (bidirectional track)
            if section.get("is_bidirectional", True):
                rev_section = {**section, "section_id": rev_id,
                               "from_node": section["to_node"],
                               "to_node": section["from_node"]}
                self.sections[rev_id] = rev_section
                self.graph.add_edge(
                    section["to_node"], section["from_node"],
                    section_id=rev_id, length_km=section["length_km"],
                    capacity=section["capacity"]
                )

        for route in data["routes"]:
            self.routes[route["route_id"]] = route

        self._loaded = True

    def get_section_between(self, from_node: str, to_node: str) -> dict | None:
        section_id = self.get_section_id(from_node, to_node)
        return self.sections.get(section_id) if section_id else None

    def get_section_id(self, from_node: str, to_node: str) -> str | None:
        if self.graph.has_edge(from_node, to_node):
            return self.graph[from_node][to_node].get("section_id")
        return None

    def get_route(self, route_id: str) -> dict | None:
        return self.routes.get(route_id)

    def get_route_sections(self, route_id: str) -> list[dict]:
        route = self.routes.get(route_id)
        if not route:
            return []
        nodes = route["node_sequence"]
        sections = []
        for i in range(len(nodes) - 1):
            section = self.get_section_between(nodes[i], nodes[i + 1])
            if section:
                sections.append(section)
        return sections

    def get_neighbors(self, node_id: str) -> list[str]:
        return list(self.graph.successors(node_id))

    def is_section_available(self, section_id: str, current_occupants: list[str],
                              requesting_train: str) -> bool:
        section = self.sections.get(section_id)
        if not section:
            return False
        capacity = section.get("capacity", 1)
        occupants_excluding_requester = [t for t in current_occupants if t != requesting_train]
        return len(occupants_excluding_requester) < capacity

    def get_all_paths(self, from_node: str, to_node: str) -> list[list[str]]:
        try:
            return list(nx.all_simple_paths(self.graph, from_node, to_node, cutoff=6))
        except nx.NetworkXError:
            return []

    def get_node(self, node_id: str) -> dict | None:
        return self.nodes.get(node_id)

    def get_all_nodes(self) -> list[dict]:
        return list(self.nodes.values())

    def get_all_sections(self) -> list[dict]:
        return getattr(self, "raw_sections", list(self.sections.values()))

    def get_all_routes(self) -> list[dict]:
        return list(self.routes.values())

    def is_loaded(self) -> bool:
        return self._loaded


# Singleton — loaded once at app startup
rail_network = RailNetwork()
