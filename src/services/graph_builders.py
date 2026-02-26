"""Graph-specific builders for knowledge graph construction."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:  # Optional dependency for advanced analytics
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

    HAVE_SKLEARN = True
except ModuleNotFoundError:  # pragma: no cover - exercised when sklearn absent
    ENGLISH_STOP_WORDS = frozenset()
    KMeans = None  # type: ignore[assignment]
    TfidfVectorizer = None  # type: ignore[assignment]
    HAVE_SKLEARN = False

from src.core.utils import parse_json_fields
from src.services.base_rag_service import sanitize_metadata
from src.services.chunk_builder import CourseChunkBuilder

Predicate = Dict[str, str]

BASE_PREDICATES: List[Predicate] = [
    {"field": "instructor", "name": "has_instructor"},
    {"field": "course_type", "name": "is_of_type"},
    {"field": "location", "name": "taught_at"},
]

TEACHES_CONCEPT = "teaches_concept"
DEVELOPS_PROFICIENCY_IN = "develops_proficiency_in"
PROVIDES_MATERIAL = "provides_material"
BELONGS_TO_THEME = "belongs_to_theme"

NOISE_TOKENS = {"skill", "skills"}
TOKEN_FREQ_THRESHOLD = 40
TOKEN_COVERAGE_THRESHOLD = 20
FLEXIBLE_WINDOW = 3
MAX_FLEXIBLE_PHRASES = 25
MAX_CANDIDATE_TERMS = 60
MAX_CHUNK_CHARS = 2000

DEFAULT_THEME_NAMES = [
    "Creative Arts and Design Cluster",
    "Culinary Arts and Food Cluster",
    "Textile and Fiber Crafts Cluster",
    "Nature and Wildlife Cluster",
    "Historical and General Skills Cluster",
]

COURSE_TYPE_THEME_MAP = {
    "Culinary Arts": DEFAULT_THEME_NAMES[1],
    "Fiber Arts": DEFAULT_THEME_NAMES[2],
    "Nature Crafts": DEFAULT_THEME_NAMES[3],
    "Traditional Skills": DEFAULT_THEME_NAMES[4],
}

DEFAULT_CANDIDATE_PHRASES = {
    "Creative Cooking",
    "Food Presentation",
    "Flavour Pairing",
    "Creative Writing",
    "Cultural History",
    "Wildlife Conservation",
    "Design Skills",
    "Fiber Arts",
    "Creative Design",
    "Mindfulness Crafting",
    "Stress Relief",
    "Storytelling",
    "Animal Care",
}

TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z'\-]+")

GRAPH_OBJECT_TYPES = {
    "has_instructor": "instructor",
    "is_of_type": "course_type",
    "taught_at": "location",
    TEACHES_CONCEPT: "concept",
    DEVELOPS_PROFICIENCY_IN: "skill",
    PROVIDES_MATERIAL: "material",
    BELONGS_TO_THEME: "theme",
}

GRAPH_RESERVED_METADATA_KEYS = {"subject", "object", "predicate"}


def _course_identifier(course: dict) -> str:
    course_id = course.get("id") or course.get("class_id")
    if course_id:
        return str(course_id)
    title = course.get("title") or "untitled"
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _triple_payload(
    subject: str,
    predicate: str,
    obj: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> dict:
    triple_id = f"kg::{_slugify(subject)}::{_slugify(predicate)}::{_slugify(obj)}"
    text = f"{subject} {predicate.replace('_', ' ')} {obj}"
    base_metadata = {"subject": subject, "predicate": predicate, "object": obj}
    if metadata:
        base_metadata.update(metadata)
    sanitized_metadata = sanitize_metadata(base_metadata)
    return {"id": triple_id, "text": text, "metadata": sanitized_metadata}


def _node_uid(name: str, suffix: Optional[Any] = None) -> str:
    base = _slugify(name) if name else "node"
    if suffix:
        suffix_slug = _slugify(str(suffix))
        if suffix_slug:
            base = f"{base}_{suffix_slug}"
    return base or "node"


def _graph_node_props(
    name: str,
    metadata: Dict[str, Any],
    entity_type: str,
    suffix: Optional[Any] = None,
) -> tuple[str, Dict[str, Any]]:
    uid = _node_uid(name, suffix)
    props = {
        "uid": uid,
        "name": name or entity_type.title(),
        "entity_type": entity_type,
    }
    for key, value in metadata.items():
        if key in GRAPH_RESERVED_METADATA_KEYS:
            continue
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            props[key] = value
        else:
            props[key] = str(value)
    return uid, props


def _subject_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    fields = {
        "course_id": metadata.get("course_id"),
        "class_id": metadata.get("class_id"),
        "title": metadata.get("title"),
    }
    return {k: v for k, v in fields.items() if v is not None}


def _object_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    obj_meta: Dict[str, Any] = {}
    if "term" in metadata:
        obj_meta["term"] = metadata["term"]
    return obj_meta


def build_graph_relationships(triples: List[dict]) -> List[Dict[str, Any]]:
    relationships: List[Dict[str, Any]] = []
    for triple in triples:
        metadata = triple.get("metadata", {})
        subject = metadata.get("subject")
        obj = metadata.get("object")
        predicate = metadata.get("predicate")
        if not subject or not obj or not predicate:
            continue

        subject_meta = _subject_metadata(metadata)
        object_meta = _object_metadata(metadata)

        subject_uid, subject_props = _graph_node_props(
            subject,
            subject_meta,
            entity_type="course",
            suffix=subject_meta.get("course_id") or subject_meta.get("class_id"),
        )

        object_type = GRAPH_OBJECT_TYPES.get(predicate, "entity")
        object_uid, object_props = _graph_node_props(
            obj,
            object_meta,
            entity_type=object_type,
            suffix=object_meta.get("term") or obj,
        )

        rel_props = {
            "predicate": predicate,
            "text": triple.get("text"),
        }

        for key in ("course_id", "class_id", "title"):
            value = subject_meta.get(key)
            if value is not None:
                rel_props[key] = value

        object_term = object_meta.get("term")
        if object_term is not None:
            rel_props["object_term"] = object_term

        relationships.append(
            {
                "subject_id": subject_uid,
                "subject_props": subject_props,
                "object_id": object_uid,
                "object_props": object_props,
                "rel_id": triple["id"],
                "rel_props": rel_props,
            }
        )

    return relationships


def build_kg_triples(courses: List[dict]) -> List[dict]:
    triples: List[dict] = []
    seen: set[str] = set()
    for course in courses:
        course = parse_json_fields(course)
        title = course.get("title")
        if not title:
            continue

        metadata_base = {
            "course_id": course.get("id"),
            "class_id": course.get("class_id"),
            "title": title,
        }
        for predicate in BASE_PREDICATES:
            value = course.get(predicate["field"])
            if not value:
                continue
            payload = _triple_payload(
                subject=title,
                predicate=predicate["name"],
                obj=value,
                metadata=metadata_base,
            )
            if payload["id"] in seen:
                continue
            seen.add(payload["id"])
            triples.append(payload)

    triples.extend(build_enriched_triples(courses))
    return triples


def build_course_chunks(courses: List[dict]) -> List[dict]:
    builder = CourseChunkBuilder(mode="narrative", max_chars=MAX_CHUNK_CHARS)
    return builder.build(courses)


class CourseTextAnalytics:
    """Derive tokens, phrases, and thematic clusters from course metadata."""

    def __init__(self, courses: List[dict]):
        self.courses = [parse_json_fields(course) for course in courses]
        self.stopwords = set(ENGLISH_STOP_WORDS) | NOISE_TOKENS
        self.records = self._build_records()

    def _build_records(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for course in self.courses:
            title = course.get("title")
            if not title:
                continue

            course_id = course.get("id") or course.get("class_id")
            text_blob = self._combine_course_text(course)
            tokens = self._tokenize(text_blob)
            records.append(
                {
                    "course": course,
                    "course_id": course_id,
                    "title": title,
                    "text": text_blob.lower(),
                    "tokens": tokens,
                }
            )
        return records

    def _combine_course_text(self, course: dict) -> str:
        parts: List[str] = []
        for field in (
            "skills",
            "learning_objectives",
            "provided_materials",
            "description",
        ):
            value = course.get(field)
            if not value:
                continue
            if isinstance(value, list):
                parts.extend(value)
            elif isinstance(value, str):
                parts.append(value)
        return " ".join(part for part in parts if part)

    def _tokenize(self, text: str) -> List[str]:
        tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
        return [self._lemmatize(token) for token in tokens if token not in self.stopwords]

    @staticmethod
    def _lemmatize(token: str) -> str:
        if token.endswith("ies") and len(token) > 3:
            return token[:-3] + "y"
        if token.endswith("ing") and len(token) > 4:
            return token[:-3]
        if token.endswith("ed") and len(token) > 3:
            return token[:-2]
        if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
            return token[:-1]
        return token

    def build(self) -> Dict[str, Any]:
        if not HAVE_SKLEARN:
            return {
                "records": self.records,
                "top_tokens": [],
                "candidate_phrases": [],
                "term_clusters": {},
            }

        token_stats = self._token_statistics()
        top_tokens = self._select_top_tokens(token_stats)
        flexible_phrases = self._extract_flexible_phrases()
        candidate_phrases = sorted(
            (DEFAULT_CANDIDATE_PHRASES | set(flexible_phrases))
            if flexible_phrases
            else DEFAULT_CANDIDATE_PHRASES
        )

        candidate_terms = list(dict.fromkeys(list(top_tokens) + candidate_phrases))
        candidate_terms = candidate_terms[:MAX_CANDIDATE_TERMS]
        term_clusters = self._cluster_terms(candidate_terms)

        return {
            "records": self.records,
            "top_tokens": top_tokens,
            "candidate_phrases": candidate_phrases,
            "term_clusters": term_clusters,
        }

    def _token_statistics(self) -> Dict[str, Dict[str, Any]]:
        token_counter: Counter[str] = Counter()
        course_presence: Dict[str, set] = defaultdict(set)
        for record in self.records:
            tokens = record["tokens"]
            token_counter.update(tokens)
            for token in set(tokens):
                course_presence[token].add(record["course_id"])
        return {
            token: {"frequency": freq, "course_count": len(course_presence[token])}
            for token, freq in token_counter.items()
        }

    def _select_top_tokens(self, stats: Dict[str, Dict[str, Any]]) -> List[str]:
        filtered = [
            token
            for token, data in stats.items()
            if data["frequency"] >= TOKEN_FREQ_THRESHOLD
            and data["course_count"] >= TOKEN_COVERAGE_THRESHOLD
        ]
        filtered.sort()
        return filtered

    def _extract_flexible_phrases(self) -> List[str]:
        ngram_counter: Counter[Tuple[str, ...]] = Counter()
        for record in self.records:
            tokens = [token for token in record["tokens"] if token not in NOISE_TOKENS]
            length = len(tokens)
            for idx in range(length):
                start = max(0, idx - FLEXIBLE_WINDOW)
                end = min(length, idx + FLEXIBLE_WINDOW + 1)
                window = tokens[start:end]
                for size in (2, 3):
                    for combo in combinations(window, size):
                        normalized = tuple(sorted(combo))
                        ngram_counter[normalized] += 1

        most_common = [
            " ".join(ngram)
            for ngram, _ in ngram_counter.most_common(MAX_FLEXIBLE_PHRASES)
            if all(token not in NOISE_TOKENS for token in ngram)
        ]
        return most_common

    def _cluster_terms(self, terms: Sequence[str]) -> Dict[str, int]:
        if not HAVE_SKLEARN or len(terms) < 2:
            return {}
        n_clusters = min(len(DEFAULT_THEME_NAMES), len(terms))
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
        matrix = vectorizer.fit_transform(terms).toarray()
        if matrix.shape[0] < n_clusters:
            n_clusters = matrix.shape[0]
        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = model.fit_predict(matrix)
        return {term: int(label) for term, label in zip(terms, labels)}


def build_enriched_triples(courses: List[dict]) -> List[dict]:
    analytics = CourseTextAnalytics(courses).build()
    records = analytics["records"]
    top_tokens = analytics["top_tokens"]
    candidate_phrases = analytics["candidate_phrases"]
    term_clusters = analytics["term_clusters"]

    triples: List[dict] = []
    seen_ids: set[str] = set()

    def append_triple(
        subject: str, predicate: str, obj: str, metadata: Optional[dict] = None
    ) -> None:
        if not subject or not obj:
            return
        payload = _triple_payload(subject, predicate, obj, metadata)
        triple_id = payload["id"]
        if triple_id in seen_ids:
            return
        seen_ids.add(triple_id)
        triples.append(payload)

    for record in records:
        course = record["course"]
        metadata = {
            "course_id": course.get("id"),
            "class_id": course.get("class_id"),
            "title": record["title"],
        }
        token_set = set(record["tokens"])

        for token in top_tokens:
            if token in token_set:
                append_triple(record["title"], TEACHES_CONCEPT, token, metadata)

        course_text = record["text"]
        for phrase in candidate_phrases:
            phrase_lower = phrase.lower()
            if phrase_lower and phrase_lower in course_text:
                append_triple(
                    record["title"], DEVELOPS_PROFICIENCY_IN, phrase, metadata
                )

        materials = course.get("provided_materials") or []
        if isinstance(materials, list):
            for material in materials:
                append_triple(record["title"], PROVIDES_MATERIAL, material, metadata)

        theme = COURSE_TYPE_THEME_MAP.get(
            course.get("course_type"), DEFAULT_THEME_NAMES[0]
        )
        append_triple(record["title"], BELONGS_TO_THEME, theme, metadata)

    cluster_names = {
        idx: DEFAULT_THEME_NAMES[idx % len(DEFAULT_THEME_NAMES)]
        for idx in range(len(DEFAULT_THEME_NAMES))
    }
    for term, cluster_id in term_clusters.items():
        cluster_name = cluster_names.get(cluster_id, DEFAULT_THEME_NAMES[0])
        append_triple(term.title(), BELONGS_TO_THEME, cluster_name, {"term": term})

    return triples
