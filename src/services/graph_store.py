"""Graph store abstraction and registry for graph backends."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

try:  # Optional dependency for graph persistence
    from neo4j import GraphDatabase

    HAVE_NEO4J = True
except ModuleNotFoundError:  # pragma: no cover - exercised when driver missing
    GraphDatabase = None  # type: ignore[assignment]
    HAVE_NEO4J = False

GraphBackendFactory = Callable[..., Optional["GraphStore"]]


class GraphStore(ABC):
    """Abstract interface for graph database operations."""

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def replace_graph(self, relationships: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_entity(self, value: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def neighbors(self, value: str, limit: int = 25) -> Dict[str, Any]:
        raise NotImplementedError


class Neo4jGraphStore(GraphStore):
    """Neo4j implementation of GraphStore."""

    def __init__(self, uri: str, user: str, password: str, batch_size: int = 500):
        if not HAVE_NEO4J or GraphDatabase is None:
            raise RuntimeError("neo4j driver is not installed")
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self.batch_size = max(1, batch_size)

    def close(self) -> None:
        self._driver.close()

    def replace_graph(self, relationships: List[Dict[str, Any]]) -> None:
        if not relationships:
            return
        with self._driver.session() as session:
            session.execute_write(self._clear_graph)
            for start in range(0, len(relationships), self.batch_size):
                batch = relationships[start : start + self.batch_size]
                session.execute_write(self._write_batch, batch)

    @staticmethod
    def _clear_graph(tx) -> None:
        tx.run("MATCH (n:Entity) DETACH DELETE n")

    @staticmethod
    def _write_batch(tx, batch: List[Dict[str, Any]]):
        tx.run(
            """
            UNWIND $batch AS triple
            MERGE (s:Entity {uid: triple.subject_id})
            SET s += triple.subject_props
            MERGE (o:Entity {uid: triple.object_id})
            SET o += triple.object_props
            MERGE (s)-[r:RELATED {rid: triple.rel_id}]->(o)
            SET r += triple.rel_props
            """,
            batch=batch,
        )

    def get_entity(self, value: str) -> Optional[Dict[str, Any]]:
        with self._driver.session() as session:
            record = session.execute_read(self._fetch_entity, value)
            if record:
                return record
            return None

    @staticmethod
    def _fetch_entity(tx, value: str) -> Optional[Dict[str, Any]]:
        result = tx.run(
            """
            MATCH (n:Entity)
            WHERE n.uid = $slug OR toLower(n.name) = toLower($value)
            RETURN n.uid AS uid, n.name AS name, n AS node
            LIMIT 1
            """,
            slug=value,
            value=value,
        )
        data = result.single()
        if not data:
            result = tx.run(
                """
                MATCH (n:Entity)
                WHERE toLower(n.name) CONTAINS toLower($value)
                   OR toLower(n.uid) CONTAINS toLower($value)
                RETURN n.uid AS uid, n.name AS name, n AS node
                LIMIT 1
                """,
                value=value,
            )
            data = result.single()
            if not data:
                return None
        node = data["node"]
        return {
            "uid": data["uid"],
            "name": data["name"],
            "properties": dict(node),
        }

    def neighbors(self, value: str, limit: int = 25) -> Dict[str, Any]:
        entity = self.get_entity(value)
        if not entity:
            return {"found": False, "entity": value, "neighbors": []}
        uid = entity["uid"]
        with self._driver.session() as session:
            outgoing = session.execute_read(self._fetch_neighbors, uid, "out", limit)
            incoming = session.execute_read(self._fetch_neighbors, uid, "in", limit)
        neighbors = outgoing + incoming
        return {
            "found": True,
            "entity": entity["name"],
            "uid": uid,
            "properties": entity["properties"],
            "neighbors": neighbors,
        }

    @staticmethod
    def _fetch_neighbors(tx, uid: str, direction: str, limit: int):
        if direction == "out":
            query = (
                "MATCH (n:Entity {uid: $uid})-[r:RELATED]->(m:Entity) "
                "RETURN m.uid AS uid, m.name AS name, r AS rel "
                "LIMIT $limit"
            )
        else:
            query = (
                "MATCH (m:Entity)-[r:RELATED]->(n:Entity {uid: $uid}) "
                "RETURN m.uid AS uid, m.name AS name, r AS rel "
                "LIMIT $limit"
            )
        result = tx.run(query, uid=uid, limit=limit)
        neighbors: List[Dict[str, Any]] = []
        for record in result:
            rel = record["rel"]
            neighbors.append(
                {
                    "neighbor": record["name"],
                    "neighbor_uid": record["uid"],
                    "predicate": rel.get("predicate"),
                    "metadata": dict(rel.get("metadata") or {}),
                    "direction": direction,
                    "text": rel.get("text"),
                }
            )
        return neighbors


_GRAPH_BACKENDS: Dict[str, GraphBackendFactory] = {}


def register_graph_backend(name: str, factory: GraphBackendFactory) -> None:
    _GRAPH_BACKENDS[name] = factory


def _ensure_default_backends() -> None:
    if "neo4j" in _GRAPH_BACKENDS:
        return

    def _neo4j_factory(**kwargs) -> Optional[GraphStore]:
        if not HAVE_NEO4J:
            return None
        uri = kwargs.get("uri") or "bolt://localhost:7687"
        user = kwargs.get("user") or "neo4j"
        password = kwargs.get("password")
        if not password:
            return None
        batch_size = kwargs.get("batch_size", 500)
        return Neo4jGraphStore(
            uri=uri, user=user, password=password, batch_size=batch_size
        )

    register_graph_backend("neo4j", _neo4j_factory)


def create_graph_store(
    backend: str = "neo4j",
    **kwargs,
) -> Optional[GraphStore]:
    _ensure_default_backends()
    factory = _GRAPH_BACKENDS.get(backend)
    if not factory:
        return None
    return factory(**kwargs)
