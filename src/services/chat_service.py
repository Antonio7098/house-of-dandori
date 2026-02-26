from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, time
from time import monotonic
from typing import Any, Dict, Generator, List, Optional, Tuple
import requests

from src.core.utils import parse_json_fields
from src.models.database import get_db_connection
from src.services.safety_service import safety_service

DISPLAY_PATTERN = re.compile(r"display\((\d+)\)")
ALLOWED_FILTER_COLUMNS = {
    "id",
    "class_id",
    "title",
    "instructor",
    "location",
    "course_type",
    "cost",
    "learning_objectives",
    "provided_materials",
    "skills",
    "description",
    "filename",
    "pdf_url",
    "created_at",
    "updated_at",
}


class ChatService:
    def __init__(self):
        self._rag_service = None
        self._graph_rag_service = None
        self._semantic_cache: Dict[
            Tuple[str, int, Optional[str]], Tuple[float, Dict[str, Any]]
        ] = {}

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: self._json_safe(val) for key, val in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._json_safe(item) for item in value]
        if isinstance(value, set):
            return [self._json_safe(item) for item in value]
        return value

    def _placeholder(self) -> str:
        return "%s" if bool(os.environ.get("DATABASE_URL")) else "?"

    def _search_courses(
        self,
        *,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0,
        order_by: str = "id",
        order_dir: str = "asc",
    ) -> Dict[str, Any]:
        filters = filters or {}
        limit = max(1, min(int(limit), 100))
        offset = max(0, int(offset))
        order_by = order_by if order_by in ALLOWED_FILTER_COLUMNS else "id"
        order_dir = "desc" if str(order_dir).lower() == "desc" else "asc"

        placeholder = self._placeholder()
        where_parts = ["1=1"]
        params: List[Any] = []

        if query:
            q = f"%{query}%"
            if placeholder == "%s":
                where_parts.append(
                    "("
                    + " OR ".join(
                        [
                            "title ILIKE %s",
                            "class_id ILIKE %s",
                            "description ILIKE %s",
                            "instructor ILIKE %s",
                            "location ILIKE %s",
                            "course_type ILIKE %s",
                        ]
                    )
                    + ")"
                )
            else:
                where_parts.append(
                    "("
                    + " OR ".join(
                        [
                            "title LIKE ?",
                            "class_id LIKE ?",
                            "description LIKE ?",
                            "instructor LIKE ?",
                            "location LIKE ?",
                            "course_type LIKE ?",
                        ]
                    )
                    + ")"
                )
            params.extend([q, q, q, q, q, q])

        for key, raw_value in filters.items():
            if key not in ALLOWED_FILTER_COLUMNS:
                continue
            if raw_value is None or raw_value == "":
                continue
            if isinstance(raw_value, list) and raw_value:
                placeholders = ",".join([placeholder] * len(raw_value))
                where_parts.append(f"{key} IN ({placeholders})")
                params.extend(raw_value)
            elif isinstance(raw_value, (int, float)):
                where_parts.append(f"{key} = {placeholder}")
                params.append(raw_value)
            else:
                where_parts.append(f"{key} LIKE {placeholder}")
                params.append(f"%{raw_value}%")

        where_sql = " AND ".join(where_parts)
        sql = f"SELECT * FROM courses WHERE {where_sql} ORDER BY {order_by} {order_dir} LIMIT {placeholder} OFFSET {placeholder}"
        count_sql = f"SELECT COUNT(*) as count FROM courses WHERE {where_sql}"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(count_sql, params)
        count_row = cursor.fetchone()
        total = (
            count_row.get("count", 0)
            if hasattr(count_row, "get")
            else count_row[0]
            if count_row
            else 0
        )

        cursor.execute(sql, [*params, limit, offset])
        rows = [parse_json_fields(row) for row in cursor.fetchall()]
        conn.close()
        return {"courses": rows, "count": total, "limit": limit, "offset": offset}

    def _semantic_search(
        self, query: str, limit: int = 5, provider: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            normalized_limit = max(1, min(int(limit), 20))
            cache_key = (query.strip().lower(), normalized_limit, provider)
            cached = self._semantic_cache.get(cache_key)
            now = monotonic()
            if cached and now - cached[0] < 30:
                return cached[1]

            if self._rag_service is None or (
                provider
                and provider != getattr(self._rag_service, "provider_name", None)
            ):
                from src.services.rag_service import get_rag_service

                self._rag_service = get_rag_service(provider)

            results = self._rag_service.search(query, n_results=normalized_limit)
            self._semantic_cache[cache_key] = (now, results)
            return results
        except Exception as exc:
            return {"error": f"semantic_search unavailable: {exc}"}

    def _graph_neighbors(
        self, value: str, limit: int = 25, provider: Optional[str] = None
    ) -> Dict[str, Any]:
        if self._graph_rag_service is None:
            from src.services.graph_rag_service import get_graph_rag_service

            self._graph_rag_service = get_graph_rag_service(
                provider or os.environ.get("GRAPH_RAG_VECTOR_PROVIDER", "chroma")
            )

        if not getattr(self._graph_rag_service, "neo4j_enabled", False):
            return {"error": "Neo4j neighbors are disabled"}
        return self._graph_rag_service.graph_neighbors(
            value=value, limit=max(1, min(int(limit), 100))
        )

    def _initial_context(self, query: str, mode: str) -> str:
        snippets: List[str] = []
        if query:
            try:
                quick = self._search_courses(query=query, limit=3)
                for course in quick.get("courses", [])[:3]:
                    snippets.append(
                        "SQL | "
                        + f"{course.get('title') or 'Course'} — {course.get('course_type') or 'Type'} in {course.get('location') or 'Unknown'}"
                    )
            except Exception:
                pass
            if mode == "graphrag":
                try:
                    graph = self._graph_neighbors(value=query, limit=3)
                    for node in (graph.get("neighbors") or [])[:3]:
                        label = node.get("label") or node.get("name") or "Node"
                        snippets.append(f"Graph | {label} — score {node.get('score')}")
                except Exception:
                    pass
        return "\n".join(snippets)

    @staticmethod
    def _display_artifacts(text: str) -> List[Dict[str, Any]]:
        seen = set()
        ids: List[int] = []
        for match in DISPLAY_PATTERN.findall(text or ""):
            cid = int(match)
            if cid in seen:
                continue
            seen.add(cid)
            ids.append(cid)

        if not ids:
            return []

        placeholder = "%s" if bool(os.environ.get("DATABASE_URL")) else "?"
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = ",".join([placeholder] * len(ids))
        cursor.execute(f"SELECT * FROM courses WHERE id IN ({ph})", ids)
        courses = [parse_json_fields(c) for c in cursor.fetchall()]
        conn.close()
        cmap = {c["id"]: c for c in courses if "id" in c}
        return [
            {
                "type": "course",
                "course_id": cid,
                "display": f"display({cid})",
                "course": cmap.get(cid),
            }
            for cid in ids
        ]

    @staticmethod
    def _format_course_results(payload: Dict[str, Any]) -> str:
        courses = payload.get("courses") or []
        if not courses:
            return "No courses were found for that query."
        lines: List[str] = ["Course search results:"]
        for idx, course in enumerate(courses[:10], start=1):
            title = course.get("title") or "Course"
            instructor = course.get("instructor") or "Unknown"
            location = course.get("location") or "Unknown"
            cost = course.get("cost") or "N/A"
            course_type = course.get("course_type") or "General"
            lines.append(
                f"{idx}. {title} — type: {course_type}, instructor: {instructor}, location: {location}, cost: {cost}"
            )
            if course.get("skills"):
                lines.append(f"   Skills: {course['skills']}")
            if course.get("learning_objectives"):
                los = course["learning_objectives"]
                snippet = "; ".join(los[:3]) if isinstance(los, list) else str(los)
                lines.append(f"   Learning objectives: {snippet}")
            if course.get("description"):
                desc = str(course.get("description"))
                lines.append(
                    f"   Description: {desc[:240]}" + ("…" if len(desc) > 240 else "")
                )
        lines.append(
            "Use the specific details above to answer the user's request; focus only on the course(s) they asked about."
        )
        return "\n".join(lines)

    @staticmethod
    def _format_semantic_results(payload: Dict[str, Any]) -> str:
        metadatas = payload.get("metadatas") or []
        if not metadatas:
            return "Semantic search returned no matches."
        lines = ["Semantic matches:"]
        for idx, meta in enumerate(metadatas[:5], start=1):
            title = meta.get("title") or meta.get("class_id") or "Document"
            course_type = meta.get("course_type") or ""
            location = meta.get("location") or ""
            instructor = meta.get("instructor") or ""
            lines.append(
                f"{idx}. {title} — {course_type} in {location} (Instructor: {instructor})"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_graph_results(payload: Dict[str, Any]) -> str:
        neighbors = payload.get("neighbors") or []
        if not neighbors:
            return "Graph neighbors lookup returned no entities."
        lines = ["Graph context:"]
        for idx, node in enumerate(neighbors[:5], start=1):
            label = node.get("label") or node.get("name") or "Node"
            score = node.get("score")
            lines.append(f"{idx}. {label} (score: {score})")
        return "\n".join(lines)

    def _tool_schemas(self, enable_graph_neighbors: bool) -> List[Dict[str, Any]]:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_courses",
                    "description": "Search courses in the SQL database using free text and flexible filters.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "filters": {"type": "object", "additionalProperties": True},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                            "offset": {"type": "integer", "minimum": 0},
                            "order_by": {"type": "string"},
                            "order_dir": {"type": "string", "enum": ["asc", "desc"]},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "semantic_search",
                    "description": "Run semantic vector search over course content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                            "provider": {"type": "string"},
                        },
                        "required": ["query"],
                    },
                },
            },
        ]
        if enable_graph_neighbors:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "graph_neighbors",
                        "description": "Fetch nearby entities for a graph node from Neo4j-backed GraphRAG store.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string"},
                                "limit": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 100,
                                },
                                "provider": {"type": "string"},
                            },
                            "required": ["value"],
                        },
                    },
                }
            )
        return tools

    def _run_tool(self, name: str, args: Dict[str, Any], mode: str) -> Dict[str, Any]:
        if name == "search_courses":
            return self._search_courses(
                query=args.get("query", ""),
                filters=args.get("filters") or {},
                limit=args.get("limit", 10),
                offset=args.get("offset", 0),
                order_by=args.get("order_by", "id"),
                order_dir=args.get("order_dir", "asc"),
            )
        if name == "semantic_search":
            return self._semantic_search(
                query=args.get("query", ""),
                limit=args.get("limit", 5),
                provider=args.get("provider"),
            )
        if name == "graph_neighbors":
            if mode != "graphrag":
                return {"error": "graph_neighbors is available only in graphrag mode"}
            return self._graph_neighbors(
                value=args.get("value", ""),
                limit=args.get("limit", 25),
                provider=args.get("provider"),
            )
        return {"error": f"Unknown tool: {name}"}

    def stream_chat(
        self, payload: Dict[str, Any]
    ) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
        mode = "graphrag" if payload.get("mode") == "graphrag" else "standard"
        model = payload.get("model") or os.environ.get(
            "CHAT_MODEL", "openai/gpt-4o-mini"
        )
        user_message = (payload.get("message") or "").strip()
        history = payload.get("history") or []

        if not user_message:
            yield "error", {"error": "message is required"}
            return

        prompt_safety = safety_service.check_prompt(user_message)
        if not prompt_safety.safe:
            safety_service.log_block(
                stage="prompt", text=user_message, result=prompt_safety
            )
            block_message = prompt_safety.message or "Prompt blocked by safety filters."
            yield "text_delta", {"delta": block_message}
            yield (
                "message_end",
                {
                    "message": block_message,
                    "artifacts": [],
                    "mode": mode,
                    "model": None,
                },
            )
            return

        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get(
            "OPENAI_API_KEY"
        )
        if not api_key:
            # Graceful fallback to deterministic DB search if API key is missing.
            quick = self._search_courses(
                query=user_message, filters=payload.get("filters") or {}, limit=5
            )
            courses = quick.get("courses", [])
            if not courses:
                text = "I can still run a local search, but no matching courses were found."
            else:
                bullet_lines = [
                    f"- {c.get('title') or 'Course'} (Instructor: {c.get('instructor') or 'TBD'})"
                    for c in courses
                ]
                text = (
                    "I can still search courses locally. Here are a few options:\n"
                    + "\n".join(bullet_lines)
                )
            yield "text_delta", {"delta": text}
            yield (
                "message_end",
                {"message": text, "artifacts": [], "mode": mode, "model": None},
            )
            return

        try:
            from openai import OpenAI
        except ModuleNotFoundError:
            quick = self._search_courses(
                query=user_message, filters=payload.get("filters") or {}, limit=5
            )
            ids = [
                c.get("id") for c in quick.get("courses", []) if c.get("id") is not None
            ]
            text = (
                "The OpenAI SDK is not installed; using local search only. "
                + " ".join([f"display({cid})" for cid in ids])
            )
            yield "text_delta", {"delta": text}
            artifacts = self._display_artifacts(text)
            yield (
                "message_end",
                {
                    "message": text,
                    "artifacts": artifacts,
                    "mode": mode,
                    "model": None,
                },
            )
            return

        base_url = os.environ.get(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ).rstrip("/")
        chat_url = f"{base_url}/chat/completions"
        timeout = int(os.environ.get("OPENROUTER_TIMEOUT_SECONDS", "60"))

        system_prompt = (
            "You are the School of Dandori assistant, a whimsical moonlit concierge who speaks with gentle wonder while staying factual. "
            "For every user query about courses, use BOTH search_courses (normal search) AND semantic_search to get the best results. "
            "Combine insights from both searches before answering. "
            "When replying, ground every recommendation in the retrieved evidence, weave concise markdown bullets with playful verbs, "
            "and close with an inviting next step (e.g., suggest another vibe, budget, or instructor to explore)."
        )
        if mode == "graphrag":
            system_prompt += " Use graph_neighbors when node-level context from Neo4j can improve the answer."

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        context_blob = self._initial_context(user_message, mode)
        if context_blob:
            messages.append(
                {
                    "role": "system",
                    "content": "Initial Dandori context:\n" + context_blob,
                }
            )
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant", "system"} and isinstance(content, str):
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        max_rounds = 5
        tools = self._tool_schemas(enable_graph_neighbors=(mode == "graphrag"))
        missed_tool_attempts = 0
        has_called_tool = False

        for _ in range(max_rounds):
            payload_body = {
                "model": model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.2,
            }
            try:
                completion = requests.post(
                    chat_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload_body,
                    timeout=timeout,
                )
                completion.raise_for_status()
                completion_data = completion.json()
                message = (
                    (completion_data.get("choices") or [{}])[0].get("message")
                ) or {}
            except Exception as exc:
                yield "error", {"message": f"Chat completion failed: {exc}"}
                return

            tool_calls = message.get("tool_calls") or []
            message_content = message.get("content") or ""

            if not tool_calls:
                if not has_called_tool and missed_tool_attempts < 2:
                    missed_tool_attempts += 1
                    messages.append({"role": "assistant", "content": message_content})
                    reminder = (
                        "You must call BOTH search_courses (normal search) AND semantic_search for every course question. "
                        "Combine results from both before answering. Return the tool call JSON arguments only."
                    )
                    messages.append({"role": "system", "content": reminder})
                    continue
                final_text = message_content.strip()
                output_safety = safety_service.check_output(final_text)
                if not output_safety.safe:
                    safety_service.log_block(
                        stage="output", text=final_text, result=output_safety
                    )
                    block_message = (
                        output_safety.message
                        or "Model output blocked by safety filters."
                    )
                    yield "text_delta", {"delta": block_message}
                    yield (
                        "message_end",
                        {
                            "message": block_message,
                            "artifacts": [],
                            "mode": mode,
                            "model": model,
                        },
                    )
                    return

                if final_text:
                    yield "text_delta", {"delta": final_text}
                artifacts = self._display_artifacts(final_text)
                safe_artifacts = self._json_safe(artifacts)
                yield (
                    "message_end",
                    {
                        "message": final_text,
                        "artifacts": safe_artifacts,
                        "mode": mode,
                        "model": model,
                    },
                )
                return

            messages.append(
                {
                    "role": "assistant",
                    "content": message_content,
                    "tool_calls": tool_calls,
                }
            )

            has_called_tool = True

            for tool_call in tool_calls:
                function_payload = tool_call.get("function") or {}
                name = function_payload.get("name") or ""
                raw_args = function_payload.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except Exception:
                    args = {}
                yield (
                    "tool_call",
                    {
                        "id": tool_call.get("id"),
                        "name": name,
                        "arguments": args,
                        "status": "running",
                    },
                )
                try:
                    result = self._run_tool(name, args, mode)
                except Exception as exc:
                    result = {"error": f"{name} failed: {exc}"}
                safe_result = self._json_safe(result)
                yield (
                    "tool_result",
                    {
                        "id": tool_call.get("id"),
                        "name": name,
                        "arguments": args,
                        "status": "completed"
                        if not safe_result.get("error")
                        else "error",
                        "result": safe_result,
                    },
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "name": name,
                        "content": json.dumps(safe_result),
                    }
                )
        fallback = self._search_courses(
            query=user_message, filters=payload.get("filters") or {}, limit=5
        )
        courses = fallback.get("courses", [])
        if courses:
            lines = [
                f"- {course.get('title') or 'Course'} (Instructor: {course.get('instructor') or 'TBD'})"
                for course in courses
            ]
            text = (
                "I wasn't able to finish that reasoning loop, but here are a few locally searched ideas:\n"
                + "\n".join(lines)
            )
        else:
            text = "I wasn't able to finish that reasoning loop, and no local results were found. Please try again with more detail."
        yield "text_delta", {"delta": text}
        yield (
            "message_end",
            {
                "message": text,
                "artifacts": [],
                "mode": mode,
                "model": model,
            },
        )


chat_service = ChatService()
