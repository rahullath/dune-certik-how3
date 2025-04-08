import logging
import requests
from typing import Dict, Any, Optional
from config import CERTIK_API_KEY, CERTIK_API_BASE_URL

logger = logging.getLogger(__name__)

class CertikAPI:
    """Client for interacting with the Certik Skynet API."""

    def __init__(self, api_key=None):
        self.api_key = api_key or CERTIK_API_KEY
        self.base_url = CERTIK_API_BASE_URL
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def get_project_security_score(self, project_name: str) -> Dict[str, Any]:
        """Get the security score for a project from Certik Skynet.

        Args:
            project_name: The name of the project to get the score for

        Returns:
            Dict containing security score and related information
        """
        if not self.api_key:
            logger.error("Certik API key not provided")
            return {"error": "API key not configured", "security_score": 0}
        
        try:
            # Fetch project information
            url = f"{self.base_url}/projects/{project_name}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            project_data = response.json()
            
            # Extract security score and relevant information
            security_data = {
                "security_score": project_data.get("security_score", 0),
                "audit_status": project_data.get("audit_status", "not_audited"),
                "last_audit_date": project_data.get("last_audit_date", None),
                "total_vulnerabilities": project_data.get("total_vulnerabilities", 0),
                "critical_vulnerabilities": project_data.get("critical_vulnerabilities", 0),
                "high_vulnerabilities": project_data.get("high_vulnerabilities", 0)
            }
            
            return security_data
        
        except requests.RequestException as e:
            logger.error(f"Error getting security score for {project_name}: {e}")
            # Return a default structure with zero score
            return {
                "error": str(e),
                "security_score": 0,
                "audit_status": "not_found",
                "last_audit_date": None,
                "total_vulnerabilities": 0,
                "critical_vulnerabilities": 0,
                "high_vulnerabilities": 0
            }
    
    def normalize_security_score(self, security_data: Dict[str, Any]) -> float:
        """Normalize the security score to a scale of 0-100.

        Args:
            security_data: Security data from the Certik API

        Returns:
            Normalized security score (0-100)
        """
        try:
            # Get the base security score
            base_score = float(security_data.get("security_score", 0))
            
            # Apply penalties for vulnerabilities
            critical_vuln = security_data.get("critical_vulnerabilities", 0)
            high_vuln = security_data.get("high_vulnerabilities", 0)
            
            # Calculate penalty (more severe for critical vulnerabilities)
            vuln_penalty = (critical_vuln * 15) + (high_vuln * 5)
            
            # Ensure score doesn't go below 0
            adjusted_score = max(0, base_score - vuln_penalty)
            
            # Normalize to 0-100 scale (Certik scores are typically 0-100 already)
            normalized_score = min(100, adjusted_score)
            
            return normalized_score
            
        except Exception as e:
            logger.error(f"Error normalizing security score: {e}")
            return 0
