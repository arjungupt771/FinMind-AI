"""
RAG (Retrieval-Augmented Generation) System for FinMind AI
Handles long-term financial memory and context retrieval
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import json
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings

    _persist_dir = os.getenv("CHROMA_DB_PATH", "./chroma_data")
    chroma_client = chromadb.PersistentClient(
        path=_persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )
    logger.info("ChromaDB client initialized successfully")
except Exception as e:
    logger.warning(f"ChromaDB not available: {str(e)}")
    chroma_client = None


def _require_user_id(user_id: Optional[str]) -> str:
    """
    Every RAG read/write must be scoped to a user. Refusing to proceed on an
    empty/None user_id (rather than silently building a filter that might not
    filter anything) is the actual hardening here — a caller bug upstream
    fails loudly instead of leaking cross-user documents.
    """
    if not user_id or not isinstance(user_id, str):
        raise ValueError("user_id is required for all RAG operations")
    return user_id


def _user_where(user_id: Optional[str], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Single source of truth for the user-scoping filter — every collection
    query in this file must go through this function, never build `where`
    inline, so there's exactly one place to audit for correctness."""
    user_id = _require_user_id(user_id)
    base = {"user_id": {"$eq": user_id}}
    if not extra:
        return base
    return {"$and": [base, extra]}


class FinancialMemory:
    """Manages financial document storage and retrieval"""

    COLLECTION_NAMES = {
        'transactions': 'financial_transactions',
        'statements': 'financial_statements',
        'reports': 'financial_reports',
        'insights': 'financial_insights',
        'goals': 'financial_goals',
    }

    def __init__(self):
        if not chroma_client:
            raise RuntimeError("ChromaDB is not initialized")
        self.client = chroma_client
        self._initialize_collections()

    def _initialize_collections(self):
        try:
            for collection_type, collection_name in self.COLLECTION_NAMES.items():
                self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            logger.info("Collections initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing collections: {str(e)}")

    def store_transactions(
        self,
        user_id: str,
        transactions: List[Dict[str, Any]],
        period: str = None
    ) -> Dict[str, Any]:
        """Store transaction summaries in vector database"""
        try:
            user_id = _require_user_id(user_id)
            if not transactions:
                return {'stored': 0, 'message': 'No transactions to store'}

            collection = self.client.get_collection(name=self.COLLECTION_NAMES['transactions'])

            docs, metadatas, ids = [], [], []
            for tx in transactions:
                docs.append(self._format_transaction_text(tx))
                metadatas.append({
                    'user_id': user_id,
                    'date': tx.get('date', ''),
                    'category': tx.get('category', 'Unknown'),
                    'amount': str(tx.get('amount', 0)),
                    'period': period or datetime.now().strftime('%Y-%m'),
                })
                ids.append(f"{user_id}_tx_{tx.get('id', str(hash(str(tx))))}")

            collection.add(documents=docs, metadatas=metadatas, ids=ids)
            logger.info(f"Stored {len(transactions)} transactions for user {user_id}")
            return {'stored': len(transactions), 'collection': 'transactions'}

        except Exception as e:
            logger.error(f"Error storing transactions: {str(e)}")
            return {'stored': 0, 'error': str(e)}

    def store_statement(
        self,
        user_id: str,
        statement_text: str,
        statement_type: str,
        source: str,
        period: str = None
    ) -> Dict[str, Any]:
        """Store financial statement/document"""
        try:
            user_id = _require_user_id(user_id)
            collection = self.client.get_collection(name=self.COLLECTION_NAMES['statements'])
            doc_id = f"{user_id}_stmt_{datetime.now().timestamp()}"

            collection.add(
                documents=[statement_text],
                metadatas=[{
                    'user_id': user_id,
                    'type': statement_type,
                    'source': source,
                    'period': period or datetime.now().strftime('%Y-%m'),
                    'stored_at': datetime.now().isoformat(),
                }],
                ids=[doc_id]
            )
            logger.info(f"Stored {statement_type} statement for user {user_id}")
            return {'stored': 1, 'id': doc_id, 'collection': 'statements'}

        except Exception as e:
            logger.error(f"Error storing statement: {str(e)}")
            return {'stored': 0, 'error': str(e)}

    def store_report(
        self,
        user_id: str,
        report_content: Dict[str, Any],
        report_type: str,
        period: str
    ) -> Dict[str, Any]:
        """Store AI-generated financial report"""
        try:
            user_id = _require_user_id(user_id)
            collection = self.client.get_collection(name=self.COLLECTION_NAMES['reports'])
            report_text = self._format_report_text(report_content)
            doc_id = f"{user_id}_report_{report_type}_{period}"

            collection.add(
                documents=[report_text],
                metadatas=[{
                    'user_id': user_id,
                    'type': report_type,
                    'period': period,
                    'created_at': datetime.now().isoformat(),
                }],
                ids=[doc_id]
            )
            logger.info(f"Stored {report_type} report for user {user_id}")
            return {'stored': 1, 'id': doc_id, 'collection': 'reports'}

        except Exception as e:
            logger.error(f"Error storing report: {str(e)}")
            return {'stored': 0, 'error': str(e)}

    def store_insight(
        self,
        user_id: str,
        insight_text: str,
        insight_type: str,
        confidence: float = 0.8
    ) -> Dict[str, Any]:
        """Store AI-generated financial insight"""
        try:
            user_id = _require_user_id(user_id)
            collection = self.client.get_collection(name=self.COLLECTION_NAMES['insights'])
            doc_id = f"{user_id}_insight_{datetime.now().timestamp()}"

            collection.add(
                documents=[insight_text],
                metadatas=[{
                    'user_id': user_id,
                    'type': insight_type,
                    'confidence': str(confidence),
                    'created_at': datetime.now().isoformat(),
                }],
                ids=[doc_id]
            )
            return {'stored': 1, 'id': doc_id, 'collection': 'insights'}

        except Exception as e:
            logger.error(f"Error storing insight: {str(e)}")
            return {'stored': 0, 'error': str(e)}

    def retrieve_context(
        self,
        user_id: str,
        query: str,
        collection_types: List[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Retrieve relevant financial context for a query, always scoped to user_id."""
        try:
            user_id = _require_user_id(user_id)
            if not collection_types:
                collection_types = list(self.COLLECTION_NAMES.keys())

            all_results = []
            for collection_type in collection_types:
                collection_name = self.COLLECTION_NAMES.get(collection_type)
                if not collection_name:
                    continue

                collection = self.client.get_collection(name=collection_name)
                results = collection.query(
                    query_texts=[query],
                    where=_user_where(user_id),
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )

                if results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        all_results.append({
                            'type': collection_type,
                            'content': doc,
                            'metadata': results['metadatas'][0][i] if results['metadatas'][0] else {},
                            'relevance_score': 1 - results['distances'][0][i],
                        })

            all_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            logger.info(f"Retrieved {len(all_results)} relevant documents for user {user_id}")
            return {'query': query, 'results': all_results[:limit], 'total_results': len(all_results)}

        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return {'error': str(e), 'results': []}

    def retrieve_similar_patterns(
        self,
        user_id: str,
        period: str,
        num_periods: int = 6
    ) -> Dict[str, Any]:
        """Retrieve similar financial patterns from historical data"""
        try:
            user_id = _require_user_id(user_id)
            collection = self.client.get_collection(name=self.COLLECTION_NAMES['transactions'])

            results = collection.query(
                query_texts=[f"transactions in {period}"],
                where=_user_where(user_id),
                n_results=num_periods * 50,
            )

            return {
                'period': period,
                'similar_patterns': results,
                'count': len(results['documents'][0]) if results['documents'] else 0
            }

        except Exception as e:
            logger.error(f"Error retrieving patterns: {str(e)}")
            return {'error': str(e)}

    def build_context_injection(
        self,
        user_id: str,
        question: str,
        context_types: List[str] = None
    ) -> str:
        """Build context injection string for LLM prompts"""
        try:
            if not context_types:
                context_types = ['reports', 'insights', 'transactions']

            context_data = self.retrieve_context(
                user_id=user_id, query=question, collection_types=context_types, limit=5
            )
            if context_data.get('error'):
                return ""

            injection = "## Financial Memory Context\n\n"
            for i, result in enumerate(context_data.get('results', [])[:5], 1):
                relevance = result.get('relevance_score', 0)
                injection += f"### Document {i} ({result['type']}) - Relevance: {relevance:.1%}\n"
                injection += f"{result['content'][:300]}...\n\n"

            return injection

        except Exception as e:
            logger.error(f"Error building context injection: {str(e)}")
            return ""

    @staticmethod
    def _format_transaction_text(transaction: Dict) -> str:
        return (
            f"Transaction: {transaction.get('merchant', 'Unknown')} "
            f"on {transaction.get('date', 'Unknown')} "
            f"for ₹{transaction.get('amount', 0)} "
            f"in category {transaction.get('category', 'Other')}"
        )

    @staticmethod
    def _format_report_text(report: Dict) -> str:
        text = f"Financial Report: {json.dumps(report, indent=2, ensure_ascii=False)}"
        return text[:2000]


try:
    financial_memory = FinancialMemory()
except Exception as e:
    logger.warning(f"FinancialMemory not available: {str(e)}")
    financial_memory = None


async def retrieve_and_inject_context(
    user_id: str,
    question: str,
    context_types: List[str] = None
) -> str:
    """Async wrapper for retrieving and injecting context into prompts (text only, no citations)."""
    if not financial_memory:
        logger.warning("Financial memory system not available")
        return ""

    return financial_memory.build_context_injection(
        user_id=user_id, question=question, context_types=context_types
    )


async def retrieve_context_with_citations(
    user_id: str,
    question: str,
    context_types: List[str] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Like retrieve_and_inject_context, but also returns a structured, deterministic
    citation list (source type + relevance score + snippet) — so a caller can show
    "this answer drew on: 2 past reports, 1 insight" with real numbers, instead of
    an opaque block of injected text with no attribution. Citations come straight
    from the retrieval results, never from the LLM's own output, so they can't be
    hallucinated.
    """
    if not financial_memory:
        return "", []

    context_types = context_types or ['reports', 'insights', 'transactions']
    context_data = financial_memory.retrieve_context(
        user_id=user_id, query=question, collection_types=context_types, limit=5
    )
    if context_data.get('error'):
        return "", []

    results = context_data.get('results', [])[:5]
    injection = "## Financial Memory Context\n\n"
    citations = []
    for i, result in enumerate(results, 1):
        relevance = result.get('relevance_score', 0)
        injection += f"### Document {i} ({result['type']}) - Relevance: {relevance:.1%}\n"
        injection += f"{result['content'][:300]}...\n\n"
        citations.append({
            'source_type': result['type'],
            'relevance_score': round(float(relevance), 4),
            'snippet': result['content'][:200],
        })

    return injection, citations