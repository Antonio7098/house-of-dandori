"""Neo4j helper for persisting and exploring GraphRAG triples."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Session


class Neo4jGraphStore:
    """Minimal wrapper around the Neo4j driver for GraphRAG data."""

    def __init__(self, uri: str, user: str, password: str, batch_size: int = 500):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self.batch_size = max(1, batch_size)

    def close(self) -> None:
        self._driver.close()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    def replace_graph(self, relationships: List[Dict[str, Any]]) -> None:
        if not relationships:
            return
        with self._driver.session() as session:
            session.execute_write(self._clear_graph)
            for start in range(0, len(relationships), self.batch_size):
                batch = relationships[start : start + self.batch_size]
                session.execute_write(self._write_batch, batch)

    @staticmethod
    def _clear_graph(tx) -> None:  # pragma: no cover - thin wrapper
        tx.run("MATCH (n:Entity) DETACH DELETE n")

    @staticmethod
    def _write_batch(tx, batch: List[Dict[str, Any]]):  # pragma: no cover - thin wrapper
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

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------
    def get_entity(self, value: str) -> Optional[Dict[str, Any]]:
        with self._driver.session() as session:
            record = session.execute_read(self._fetch_entity, value)
            if record:
                return record
            return None

    @staticmethod
    def _fetch_entity(tx: Session, value: str) -> Optional[Dict[str, Any]]:
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
    def _fetch_neighbors(tx: Session, uid: str, direction: str, limit: int):
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
            metadata_json = rel.get("metadata_json")
            metadata: Dict[str, Any]
            if isinstance(metadata_json, str):
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    metadata = {"raw": metadata_json}
            else:
                metadata = {}

            neighbors.append(
                {
                    "neighbor": record["name"],
                    "neighbor_uid": record["uid"],
                    "predicate": rel.get("predicate"),
                    "metadata": metadata,
                    "direction": direction,
                    "text": rel.get("text"),
                }
            )
        return neighbors
