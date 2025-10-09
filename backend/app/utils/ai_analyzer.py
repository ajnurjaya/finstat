import os
from typing import Dict, Optional
import requests

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class AIAnalyzer:
    """AI-powered analysis using Anthropic Claude, OpenAI GPT, or local LLMs via Ollama"""

    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "ollama").lower()

        if self.provider == "anthropic" and Anthropic:
            self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
            if self.anthropic_key:
                self.client = Anthropic(api_key=self.anthropic_key)
        elif self.provider == "openai" and OpenAI:
            self.openai_key = os.getenv("OPENAI_API_KEY")
            self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
            if self.openai_key:
                self.client = OpenAI(api_key=self.openai_key)
        elif self.provider == "ollama":
            # Support both OLLAMA_BASE_URL (Docker) and OLLAMA_URL (legacy)
            self.ollama_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_URL", "http://localhost:11434")
            self.model = os.getenv("OLLAMA_MODEL", "mistral")
            self.client = None

    def _call_ollama(self, prompt: str, system_prompt: str = None) -> str:
        """Call local Ollama API"""
        url = f"{self.ollama_url}/api/generate"

        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False
        }

        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()

        return response.json()["response"]

    def summarize_financial_statement(self, text: str) -> Dict[str, any]:
        """Generate a summary of the financial statement"""

        prompt = f"""You are a financial analyst. Analyze the following financial statement and provide:

1. A concise executive summary (2-3 paragraphs)
2. Key financial metrics and highlights
3. Notable trends or concerns
4. Overall financial health assessment

Financial Statement:
{text[:15000]}  # Limit text to avoid token limits

Please structure your response clearly with headers."""

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                summary = response.content[0].text

            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a financial analyst expert."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000
                )
                summary = response.choices[0].message.content

            elif self.provider == "ollama":
                summary = self._call_ollama(prompt, "You are a financial analyst expert.")

            return {
                "success": True,
                "summary": summary,
                "provider": self.provider,
                "model": self.model
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"AI summarization failed: {str(e)}",
                "provider": self.provider
            }

    def extract_insights(self, text: str) -> Dict[str, any]:
        """Extract key insights and metrics from financial statement"""

        prompt = f"""Analyze this financial statement and extract:

1. **Key Financial Metrics**: Revenue, profit, expenses, assets, liabilities, etc.
2. **Growth Indicators**: Year-over-year changes, trends
3. **Risk Factors**: Any concerning patterns or red flags
4. **Opportunities**: Positive indicators or growth opportunities
5. **Recommendations**: Strategic suggestions based on the data

Financial Statement:
{text[:15000]}

Provide structured insights in a clear, bulleted format."""

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2500,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                insights = response.content[0].text

            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a financial analyst expert specializing in insight extraction."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2500
                )
                insights = response.choices[0].message.content

            elif self.provider == "ollama":
                insights = self._call_ollama(prompt, "You are a financial analyst expert specializing in insight extraction.")

            return {
                "success": True,
                "insights": insights,
                "provider": self.provider,
                "model": self.model
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"AI insights extraction failed: {str(e)}",
                "provider": self.provider
            }

    def comprehensive_analysis(self, text: str) -> Dict[str, any]:
        """Perform comprehensive analysis including both summary and insights"""

        prompt = f"""As a senior financial analyst, provide a comprehensive analysis of this financial statement:

## EXECUTIVE SUMMARY
Provide a 2-3 paragraph overview of the company's financial position.

## KEY METRICS
List and analyze the most important financial metrics found in the document.

## FINANCIAL HIGHLIGHTS
- Revenue and profitability analysis
- Cash flow position
- Asset and liability assessment
- Equity and capital structure

## TRENDS & PATTERNS
Identify any notable trends, patterns, or changes over time.

## RISK ASSESSMENT
Highlight any concerning areas, risks, or red flags.

## OPPORTUNITIES & STRENGTHS
Identify positive indicators and competitive advantages.

## RECOMMENDATIONS
Provide strategic recommendations for stakeholders.

Financial Statement:
{text[:15000]}

Provide a thorough, professional analysis."""

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                analysis = response.content[0].text

            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a senior financial analyst providing comprehensive financial statement analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4000
                )
                analysis = response.choices[0].message.content

            elif self.provider == "ollama":
                analysis = self._call_ollama(prompt, "You are a senior financial analyst providing comprehensive financial statement analysis.")

            # Try to parse sections
            sections = self._parse_analysis_sections(analysis)

            return {
                "success": True,
                "full_analysis": analysis,
                "sections": sections,
                "provider": self.provider,
                "model": self.model
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Comprehensive analysis failed: {str(e)}",
                "provider": self.provider
            }

    def _parse_analysis_sections(self, analysis: str) -> Dict[str, str]:
        """Parse the analysis into sections with flexible header detection"""
        sections = {}

        # Define section markers
        markers = [
            "EXECUTIVE SUMMARY",
            "KEY METRICS",
            "FINANCIAL HIGHLIGHTS",
            "TRENDS & PATTERNS",
            "TRENDS AND PATTERNS",
            "RISK ASSESSMENT",
            "OPPORTUNITIES & STRENGTHS",
            "OPPORTUNITIES AND STRENGTHS",
            "RECOMMENDATIONS"
        ]

        lines = analysis.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            # Check if line is a section header
            is_header = False
            line_upper = line.upper().strip()
            line_clean = line.strip().replace('*', '').replace('#', '').replace(':', '').strip()

            for marker in markers:
                # More flexible matching:
                # - Case insensitive
                # - Accepts markdown (# or ##)
                # - Accepts bold (**text**)
                # - Accepts with colon (Text:)
                # - Accepts mixed case if it's the only significant text on the line
                if marker in line_upper:
                    # Check if this looks like a header (short line, mostly just the marker)
                    word_count = len(line_clean.split())
                    marker_word_count = len(marker.split())

                    # It's a header if:
                    # 1. Line starts with # or ##, OR
                    # 2. Line is all uppercase, OR
                    # 3. Line is short (within 5 words of marker length), OR
                    # 4. Line ends with colon
                    if (line.strip().startswith('#') or
                        line.isupper() or
                        word_count <= marker_word_count + 5 or
                        line.strip().endswith(':')):

                        # Save previous section
                        if current_section and current_content:
                            sections[current_section] = '\n'.join(current_content).strip()

                        current_section = marker.lower().replace(' & ', '_').replace(' ', '_')
                        current_content = []
                        is_header = True
                        break

            if not is_header and current_section:
                current_content.append(line)

        # Add last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        # If no sections were found, try to extract at least summary from beginning
        if not sections and analysis:
            # Take first 3 paragraphs as executive summary
            paragraphs = [p.strip() for p in analysis.split('\n\n') if p.strip()]
            if paragraphs:
                sections['executive_summary'] = '\n\n'.join(paragraphs[:3])

        return sections
