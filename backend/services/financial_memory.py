
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from backend.database.repositories import FinancialMemoryRepository


class FinancialMemoryService:


    MEMORY_TYPES = {
        "preference",
        "goal",
        "financial_fact",
        "behavior",
        "constraint",
        "decision",
        "conversation",
    }

    STATUS_PRIORITY = {
        "active": 4,
        "contradicted": 3,
        "superseded": 2,
        "expired": 1,
    }

    TYPE_WEIGHTS = {
        "goal": 1.35,
        "constraint": 1.2,
        "preference": 1.1,
        "decision": 1.1,
        "financial_fact": 0.85,
        "behavior": 0.75,
        "conversation": 0.6,
    }

    INTENT_HINTS = {
        "goal": {"goal", "save", "target", "car", "home", "travel", "emergency", "fund"},
        "budget": {"budget", "spend", "expense", "cut", "reduce", "limit"},
        "subscription": {"subscription", "renew", "membership", "cancel", "plan"},
        "forecast": {"forecast", "future", "project", "next month", "trend"},
        "health": {"health", "income", "savings", "cash", "balance"},
        "anomaly": {"anomaly", "spike", "odd", "unexpected", "outlier"},
        "general": set(),
    }

    STOP_WORDS = {
        "i", "me", "my", "mine", "you", "your", "we", "us", "our", "the", "a", "an",
        "to", "for", "of", "in", "on", "and", "or", "is", "are", "be", "it", "this",
        "that", "with", "from", "at", "by", "as", "am", "do", "does", "did", "have",
        "has", "had", "not", "no", "more", "than", "about", "into", "out", "up", "down",
        "want", "need", "just", "like", "would", "could", "should", "will", "can", "may",
        "often", "always", "usually", "sometimes", "really", "very",
    }

    def __init__(self, db):
        self.repository = FinancialMemoryRepository(db)

    def _status_from_memory(self, memory) -> str:
        metadata = dict(memory.metadata_json or {})
        if metadata.get("status") in self.STATUS_PRIORITY:
            return metadata["status"]
        return "active" if memory.active else "expired"

    def _apply_status(self, memory, status: str, reason: Optional[str] = None):
        if not memory:
            return None
        metadata = dict(memory.metadata_json or {})
        metadata["status"] = status
        if reason:
            metadata["status_reason"] = reason

        update_data = {
            "active": status == "active",
            "metadata_json": metadata,
        }

        if status == "superseded":
            update_data["superseded_by"] = metadata.get("superseded_by")

        return self.repository.update(memory.id, update_data)
    @staticmethod
    def _normalize_datetime(value):
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_concept_tokens(self, text: str) -> Set[str]:
        normalized = self._normalize_text(text)
        if not normalized:
            return set()
        tokens = {
            token for token in re.findall(r"[a-z0-9]+", normalized)
            if token not in self.STOP_WORDS and len(token) > 2
        }
        if not tokens:
            return set(re.findall(r"[a-z0-9]+", normalized))
        return tokens

    def _recency_score(self, created_at) -> float:
        if not created_at:
            return 0.5
        normalized_created_at = self._normalize_datetime(created_at)
        age_days = max(0.0, (datetime.now(timezone.utc) - normalized_created_at).total_seconds() / 86400.0)
        # more recent memories are preferred, but not always dominating older, higher-confidence memories
        return max(0.2, 1.0 - min(age_days / 365.0, 0.8))

    def _intent_match_score(self, memory_type: str, intent: str) -> float:
        if not intent:
            return 0.0
        normalized_intent = intent.lower()
        target_tokens = self.INTENT_HINTS.get(normalized_intent, set())
        if not target_tokens:
            return 0.0
        if memory_type in {"goal", "constraint"} and normalized_intent in {"goal", "budget"}:
            return 0.85
        if memory_type == "goal" and normalized_intent == "goal":
            return 0.9
        if memory_type == "constraint" and normalized_intent == "budget":
            return 0.8
        if memory_type == "behavior" and normalized_intent == "health":
            return 0.5
        return 0.3 if any(token in target_tokens for token in self._extract_concept_tokens(memory_type)) else 0.0

    def _is_contradiction(self, previous_text: str, new_text: str) -> bool:
        prev_text = self._normalize_text(previous_text)
        new_text = self._normalize_text(new_text)
        if not prev_text or not new_text:
            return False

        contradiction_markers = (
            "do not want",
            "don't want",
            "do not need",
            "don't need",
            "no longer",
            "not want",
            "not saving",
            "cancel",
            "stop saving",
            "stop budgeting",
            "cannot spend",
            "no more",
        )
        if not any(marker in new_text for marker in contradiction_markers):
            return False

        prev_tokens = self._extract_concept_tokens(prev_text)
        new_tokens = self._extract_concept_tokens(new_text)
        overlap = prev_tokens & new_tokens
        if not overlap:
            return False
        return bool(overlap & {"save", "budget", "spend", "goal", "car", "travel", "home", "fund", "plan"}) or len(overlap) >= 2

    def _resolve_conflicts(self, user_id: str, memory_type: str, content: str, new_memory_id: Optional[str] = None):
        if memory_type not in {"goal", "preference", "constraint", "decision"}:
            return []

        matches = self.repository.get_user_memories(user_id=user_id, memory_type=memory_type, limit=100)
        superseded = []

        for memory in matches:
            if new_memory_id and memory.id == new_memory_id:
                continue
            if memory.active is False:
                continue
            if self._is_contradiction(memory.content, content):
                metadata = dict(memory.metadata_json or {})
                metadata["superseded_by"] = new_memory_id
                self.repository.update(
                    memory.id,
                    {
                        "active": False,
                        "superseded_by": new_memory_id,
                        "metadata_json": {
                            **metadata,
                            "status": "superseded",
                            "status_reason": "Contradicted by newer user update",
                        },
                    },
                )
                superseded.append(memory.id)

        return superseded

    def create_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str = "financial_fact",
        source: str = "system",
        importance: float = 0.5,
        confidence: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        memory_type = memory_type.lower().strip()

        if memory_type not in self.MEMORY_TYPES:
            raise ValueError(f"Unsupported memory type: {memory_type}")

        content = content.strip()
        if not content:
            raise ValueError("Memory content cannot be empty")

        importance = max(0.0, min(1.0, float(importance)))
        confidence = max(0.0, min(1.0, float(confidence)))

        metadata = dict(metadata or {})
        metadata.setdefault("status", "active")
        metadata.pop("superseded_by", None)

        existing = self.repository.find_duplicate(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
        )

        if existing:
            merged_metadata = dict(existing.metadata_json or {})
            merged_metadata.update(metadata)
            updated = self.repository.update(
                existing.id,
                {
                    "importance": max(existing.importance or 0, importance),
                    "confidence": max(existing.confidence or 0, confidence),
                    "active": True,
                    "superseded_by": None,
                    "metadata_json": merged_metadata,
                },
            )
            return self._serialize(updated)

        memory = self.repository.create(
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "memory_type": memory_type,
                "content": content,
                "source": source,
                "importance": importance,
                "confidence": confidence,
                "active": True,
                "superseded_by": None,
                "metadata_json": metadata,
            }
        )

        self._resolve_conflicts(user_id=user_id, memory_type=memory_type, content=content, new_memory_id=memory.id)
        return self._serialize(memory)

    def extract_memories_from_message(self, message: str) -> List[Dict[str, Any]]:
        """
        Extract durable financial facts from a user message.

        This intentionally uses conservative patterns rather than
        treating every sentence as a memory.
        """

        if not message:
            return []

        text = message.strip()
        lowered = text.lower()

        memories = []

        preference_patterns = [
            (r"\bi prefer ([^.]+)", "preference", 0.8),
            (r"\bi usually ([^.]+)", "behavior", 0.6),
            (r"\bi always ([^.]+)", "behavior", 0.7),
            (r"\bi never ([^.]+)", "constraint", 0.8),
        ]

        for pattern, memory_type, importance in preference_patterns:
            match = re.search(pattern, lowered)
            if match:
                statement = match.group(0).strip()
                memories.append({
                    "content": statement,
                    "memory_type": memory_type,
                    "importance": importance,
                    "confidence": 0.85,
                    "source": "conversation",
                })

        goal_patterns = [
            r"\bi want to save ([^.]+)\.?",
            r"\bi need to save ([^.]+)\.?",
            r"\bmy goal is ([^.]+)\.?",
            r"\bi am saving for ([^.]+)\.?",
            r"\bi do not want to save for ([^.]+)\.?",
        ]

        for pattern in goal_patterns:
            match = re.search(pattern, lowered)
            if match:
                statement = match.group(0).strip()
                memories.append({
                    "content": statement,
                    "memory_type": "goal",
                    "importance": 0.9,
                    "confidence": 0.85,
                    "source": "conversation",
                })

        constraint_patterns = [
            r"\bi cannot spend ([^.]+)",
            r"\bi can't spend ([^.]+)",
            r"\bi have a budget of ([^.]+)",
            r"\bmy budget is ([^.]+)",
        ]

        for pattern in constraint_patterns:
            match = re.search(pattern, lowered)
            if match:
                statement = match.group(0).strip()
                memories.append({
                    "content": statement,
                    "memory_type": "constraint",
                    "importance": 0.9,
                    "confidence": 0.85,
                    "source": "conversation",
                })

        unique = {}
        for memory in memories:
            unique[(memory["memory_type"], memory["content"])] = memory
        return list(unique.values())

    def remember_message(self, user_id: str, message: str) -> List[Dict[str, Any]]:
        extracted = self.extract_memories_from_message(message)
        created = []
        for memory in extracted:
            created.append(
                self.create_memory(
                    user_id=user_id,
                    content=memory["content"],
                    memory_type=memory["memory_type"],
                    source=memory["source"],
                    importance=memory["importance"],
                    confidence=memory["confidence"],
                )
            )
        return created

    def retrieve(
        self,
        user_id: str,
        query: str,
        limit: int = 8,
        intent: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        memories = self.repository.get_user_memories(user_id=user_id, limit=200)
        if not memories:
            return []

        query_tokens = self._extract_concept_tokens(query or "")
        intent_norm = (intent or "general").lower()
        scored = []

        for memory in memories:
            if memory.active is False:
                continue

            semantic_tokens = self._extract_concept_tokens(memory.content)
            keyword_overlap = len(query_tokens & semantic_tokens)
            semantic_overlap = len(self._extract_concept_tokens(query or "") & self._extract_concept_tokens(memory.content))
            importance = memory.importance if memory.importance is not None else 0.5
            confidence = memory.confidence if memory.confidence is not None else 0.5
            recency = self._recency_score(memory.created_at)
            type_weight = self.TYPE_WEIGHTS.get(memory.memory_type, 0.7)
            intent_bonus = self._intent_match_score(memory.memory_type, intent_norm)

            score = (
                keyword_overlap * 2.2
                + semantic_overlap * 1.4
                + importance * 2.0
                + confidence * 1.4
                + recency * 1.0
                + type_weight * 0.9
                + intent_bonus * 1.5
            )

            if memory.memory_type in {"goal", "constraint"}:
                score += 0.8

            if score > 0.4:
                scored.append((score, memory))

        scored.sort(key=lambda item: item[0], reverse=True)

        return [
            {
                **self._serialize(memory),
                "relevance_score": round(score, 4),
                "status": self._status_from_memory(memory),
            }
            for score, memory in scored[:limit]
        ]

    def get_all(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> List[Dict[str, Any]]:
        memories = self.repository.get_user_memories(
            user_id=user_id,
            memory_type=memory_type,
            active_only=not include_inactive,
            limit=limit,
        )

        return [self._serialize(memory) for memory in memories]

    def build_context(self, user_id: str, query: str, limit: int = 8, intent: Optional[str] = None) -> str:
        memories = self.retrieve(user_id=user_id, query=query, limit=limit, intent=intent)
        if not memories:
            return ""

        lines = ["LONG-TERM FINANCIAL MEMORY:"]
        for memory in memories:
            lines.append(f"- [{memory['memory_type']}] {memory['content']}")
        return "\n".join(lines)

    @staticmethod
    def _tokenize(text: str) -> set:
        if not text:
            return set()
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    @staticmethod
    def _serialize(memory) -> Dict[str, Any]:
        metadata = dict(memory.metadata_json or {})
        return {
            "id": memory.id,
            "user_id": memory.user_id,
            "memory_type": memory.memory_type,
            "content": memory.content,
            "source": memory.source,
            "importance": memory.importance,
            "confidence": memory.confidence,
            "active": memory.active,
            "status": metadata.get("status", "active" if memory.active else "expired"),
            "metadata": metadata,
            "created_at": memory.created_at.isoformat() if memory.created_at else None,
            "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
        }

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        memory = self.repository.get_by_id(memory_id)
        if not memory or memory.user_id != user_id:
            return False

        metadata = dict(memory.metadata_json or {})
        metadata["status"] = "expired"
        metadata["status_reason"] = "User removed outdated memory"
        self.repository.update(memory_id, {"active": False, "metadata_json": metadata})
        return True