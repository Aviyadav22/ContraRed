"""
Smriti MCP Client.

Provides a client for interacting with the Smriti MCP server
for legal research: case law, statute text, judicial interpretations.

Gracefully degrades when Smriti is unavailable — returns empty results
and logs a warning, never blocks the pipeline.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SMRITI_MCP_URL = os.getenv("SMRITI_MCP_URL", "")
SMRITI_TIMEOUT = float(os.getenv("SMRITI_TIMEOUT", "10"))


class SmritiClient:
    """Client for Smriti MCP server.

    All methods return empty/default results when Smriti is unavailable.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = SMRITI_TIMEOUT):
        self.base_url = (base_url or SMRITI_MCP_URL).rstrip("/")
        self.timeout = timeout
        self._available: Optional[bool] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a Smriti MCP tool. Returns empty dict on failure."""
        if not self.is_configured:
            return {}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/tools/{tool_name}",
                    json=params,
                )
                resp.raise_for_status()
                self._available = True
                return resp.json()
        except httpx.TimeoutException:
            logger.warning("Smriti MCP timeout calling %s", tool_name)
            self._available = False
            return {}
        except httpx.HTTPStatusError as e:
            logger.warning("Smriti MCP HTTP error calling %s: %s", tool_name, e.response.status_code)
            self._available = False
            return {}
        except Exception as e:
            logger.warning("Smriti MCP error calling %s: %s", tool_name, e)
            self._available = False
            return {}

    async def search_case_law(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        max_results: int = 3,
    ) -> List[Dict[str, Any]]:
        """Search for relevant case law.

        Returns list of cases with citation, summary, relevance_score.
        """
        result = await self._call_tool("search_case_law", {
            "query": query,
            "jurisdiction": jurisdiction,
            "max_results": max_results,
        })
        return result.get("cases", [])

    async def get_statute_text(
        self,
        statute_reference: str,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get full text of a statute section.

        Returns dict with section_text, statute_name, last_amended.
        """
        return await self._call_tool("get_statute_text", {
            "statute_reference": statute_reference,
            "jurisdiction": jurisdiction,
        })

    async def find_judicial_interpretation(
        self,
        clause_type: str,
        jurisdiction: Optional[str] = None,
        max_results: int = 2,
    ) -> List[Dict[str, Any]]:
        """Find judicial interpretations for a clause type.

        Returns list of interpretations with case, principle, relevance.
        """
        result = await self._call_tool("find_judicial_interpretation", {
            "clause_type": clause_type,
            "jurisdiction": jurisdiction,
            "max_results": max_results,
        })
        return result.get("interpretations", [])

    async def get_legal_principle(
        self,
        principle_name: str,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a legal principle with supporting case law.

        Returns dict with principle, description, supporting_cases.
        """
        return await self._call_tool("get_legal_principle", {
            "principle_name": principle_name,
            "jurisdiction": jurisdiction,
        })

    async def check_statute_compliance(
        self,
        clause_text: str,
        statute_reference: str,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check if a clause complies with a specific statute.

        Returns dict with compliant (bool), issues, recommendations.
        """
        return await self._call_tool("check_statute_compliance", {
            "clause_text": clause_text,
            "statute_reference": statute_reference,
            "jurisdiction": jurisdiction,
        })


# Module-level singleton (lazy — only connects when called)
smriti_client = SmritiClient()
