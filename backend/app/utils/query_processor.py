"""
Enhanced Query Processor for Financial Documents
- Financial domain-aware keyword extraction
- Intent detection (comparison, extraction, summarization)
- Query expansion with financial synonyms
"""
import re
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass


@dataclass
class QueryAnalysis:
    """Structured query analysis result"""
    original_query: str
    intent: str  # 'compare', 'extract', 'summarize', 'question'
    entities: List[str]  # Financial terms, company names, metrics
    keywords: List[str]  # Domain-specific keywords
    expanded_terms: List[str]  # Synonyms and related terms
    action_verbs: List[str]  # compare, calculate, find, etc.
    is_cross_document: bool  # Requires multiple documents


class FinancialQueryProcessor:
    """
    Production-grade query processor for financial domain
    """

    # Financial metrics and their synonyms
    FINANCIAL_METRICS = {
        'revenue': ['sales', 'income', 'turnover', 'receipts', 'proceeds'],
        'profit': ['earnings', 'net income', 'bottom line', 'margin', 'gains'],
        'loss': ['deficit', 'shortfall', 'negative earnings', 'red ink'],
        'assets': ['holdings', 'resources', 'property', 'investments'],
        'liabilities': ['debts', 'obligations', 'payables', 'borrowings'],
        'equity': ['capital', 'shareholder equity', 'net worth', 'ownership'],
        'cash flow': ['cash generation', 'liquidity', 'operating cash'],
        'ebitda': ['operating profit', 'operating income', 'operational earnings'],
        'expenses': ['costs', 'expenditures', 'outflows', 'spending'],
        'dividend': ['payout', 'distribution', 'shareholder return'],
        'debt': ['borrowing', 'loan', 'bond', 'financing', 'leverage'],
        'growth': ['increase', 'expansion', 'rise', 'improvement'],
        'valuation': ['value', 'worth', 'market cap', 'enterprise value'],
        'margin': ['profitability', 'markup', 'spread', 'profit margin'],
        'ratio': ['metric', 'indicator', 'measurement', 'coefficient']
    }

    # Action verbs indicating intent
    COMPARISON_VERBS = ['compare', 'versus', 'vs', 'between', 'difference', 'contrast', 'rank', 'which']
    EXTRACTION_VERBS = ['what', 'how much', 'show', 'find', 'get', 'extract', 'list']
    SUMMARY_VERBS = ['summarize', 'overview', 'summary', 'explain', 'describe', 'tell me about']
    CALCULATION_VERBS = ['calculate', 'compute', 'determine', 'measure']

    # Entity patterns
    ENTITY_PATTERNS = {
        'year': r'\b(20\d{2}|FY\d{2}|Q[1-4]\s*20\d{2})\b',
        'currency': r'\b(USD|EUR|GBP|JPY|CNY|INR|IDR|Rp|[$€£¥])\b',
        'percentage': r'\b\d+\.?\d*\s*%',
        'amount': r'\b\d+[\d,]*\.?\d*\s*(million|billion|trillion|k|m|b|mn|bn)\b',
    }

    def __init__(self):
        """Initialize query processor with financial domain knowledge"""
        # Build reverse lookup for synonyms
        self.term_to_canonical = {}
        for canonical, synonyms in self.FINANCIAL_METRICS.items():
            self.term_to_canonical[canonical.lower()] = canonical
            for syn in synonyms:
                self.term_to_canonical[syn.lower()] = canonical

    def analyze(self, query: str) -> QueryAnalysis:
        """
        Comprehensive query analysis

        Returns QueryAnalysis with:
        - Intent detection
        - Financial entity extraction
        - Keyword identification
        - Query expansion
        """
        query_lower = query.lower()

        # 1. Detect intent
        intent = self._detect_intent(query_lower)

        # 2. Extract entities (years, amounts, currencies)
        entities = self._extract_entities(query)

        # 3. Extract financial keywords
        keywords = self._extract_financial_keywords(query_lower)

        # 4. Detect action verbs
        action_verbs = self._extract_action_verbs(query_lower)

        # 5. Expand query with synonyms
        expanded_terms = self._expand_query(keywords)

        # 6. Detect cross-document requirement
        is_cross_doc = self._is_cross_document_query(query_lower, action_verbs)

        return QueryAnalysis(
            original_query=query,
            intent=intent,
            entities=entities,
            keywords=keywords,
            expanded_terms=expanded_terms,
            action_verbs=action_verbs,
            is_cross_document=is_cross_doc
        )

    def _detect_intent(self, query_lower: str) -> str:
        """Detect query intent based on action verbs"""
        if any(verb in query_lower for verb in self.COMPARISON_VERBS):
            return 'compare'
        elif any(verb in query_lower for verb in self.CALCULATION_VERBS):
            return 'calculate'
        elif any(verb in query_lower for verb in self.SUMMARY_VERBS):
            return 'summarize'
        elif any(verb in query_lower for verb in self.EXTRACTION_VERBS):
            return 'extract'
        else:
            return 'question'

    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities (years, amounts, currencies)"""
        entities = []

        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities.extend(matches)

        return entities

    def _extract_financial_keywords(self, query_lower: str) -> List[str]:
        """
        Extract financial domain keywords
        Returns canonical form (e.g., 'sales' → 'revenue')
        """
        keywords = []

        # Match against all known financial terms
        for term, canonical in self.term_to_canonical.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, query_lower):
                if canonical not in keywords:
                    keywords.append(canonical)

        return keywords

    def _extract_action_verbs(self, query_lower: str) -> List[str]:
        """Extract action verbs from query"""
        all_verbs = (self.COMPARISON_VERBS + self.EXTRACTION_VERBS +
                     self.SUMMARY_VERBS + self.CALCULATION_VERBS)

        found_verbs = []
        for verb in all_verbs:
            pattern = r'\b' + re.escape(verb) + r'\b'
            if re.search(pattern, query_lower):
                found_verbs.append(verb)

        return found_verbs

    def _expand_query(self, keywords: List[str]) -> List[str]:
        """Expand keywords with synonyms"""
        expanded = []

        for keyword in keywords:
            # Add canonical term
            expanded.append(keyword)

            # Add all synonyms
            if keyword in self.FINANCIAL_METRICS:
                expanded.extend(self.FINANCIAL_METRICS[keyword])

        return list(set(expanded))  # Remove duplicates

    def _is_cross_document_query(self, query_lower: str, action_verbs: List[str]) -> bool:
        """Detect if query requires multiple documents"""
        cross_doc_indicators = [
            'compare', 'versus', 'vs', 'between', 'across documents',
            'all documents', 'which company', 'which document',
            'highest', 'lowest', 'best', 'worst', 'rank'
        ]

        return any(indicator in query_lower for indicator in cross_doc_indicators)

    def get_search_terms(self, analysis: QueryAnalysis, top_k: int = 5) -> List[str]:
        """
        Get prioritized search terms for vector/keyword search

        Priority:
        1. Financial keywords (canonical forms)
        2. Entities (years, amounts)
        3. Top synonyms
        """
        search_terms = []

        # Priority 1: Financial keywords
        search_terms.extend(analysis.keywords)

        # Priority 2: Entities
        search_terms.extend(analysis.entities)

        # Priority 3: Expanded terms (limit to top_k)
        remaining = top_k - len(search_terms)
        if remaining > 0:
            search_terms.extend(analysis.expanded_terms[:remaining])

        return search_terms[:top_k]