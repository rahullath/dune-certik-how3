import requests
import logging
import os
from config import get_config

logger = logging.getLogger(__name__)

class CertikClient:
    """Client for interacting with Certik Skynet API"""
    
    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.CERTIK_API_KEY
        self.base_url = self.config.CERTIK_API_BASE_URL
        
        # Mapping of how3.io protocol names to Certik project identifiers
        # This would need to be maintained as protocols are added
        self.protocol_mapping = {
            "chainlink": "chainlink",
            "uniswap": "uniswap",
            "aave": "aave",
            # Add more mappings as needed
        }
    
    def get_security_score(self, protocol_name):
        """Get security score for a protocol from Certik Skynet"""
        if not self.api_key:
            logger.warning("Certik API key not found. Please provide a valid API key in environment variables to get real security data.")
            return self._get_test_security_score(protocol_name)
        
        certik_id = self.protocol_mapping.get(protocol_name.lower())
        if not certik_id:
            logger.warning(f"No Certik mapping found for {protocol_name}. Using test data (API key: {self.api_key}).")
            return self._get_test_security_score(protocol_name)
        
        try:
            # Endpoint for getting project security score
            url = f"{self.base_url}/projects/{certik_id}/security-score"
            headers = {
                "X-API-KEY": self.api_key,
                "Accept": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract the security score from the response
            security_score = data.get("data", {}).get("score")
            
            if security_score is not None:
                logger.info(f"Successfully retrieved security score for {protocol_name} from Certik API")
                return float(security_score)
            else:
                logger.warning(f"No security score found for {protocol_name} in Certik API response. Using test data.")
                return self._get_test_security_score(protocol_name)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Certik data for {protocol_name}: {str(e)}")
            return self._get_test_security_score(protocol_name)
    
    def _get_test_security_score(self, protocol_name):
        """Provide test security scores for development and testing
        
        Note: These are NOT real security scores. In production, 
        always use the Certik API with a valid API key.
        """
        logger.info(f"Using test security score for {protocol_name} - this is NOT real data")
        test_scores = {
            "chainlink": 85,
            "uniswap": 80,
            "aave": 82,
            "compound": 81,
            "maker": 83,
            "curve": 79,
            "synthetix": 75,
            "yearn": 76,
            # Add more as needed
        }
        
        return test_scores.get(protocol_name.lower(), 50)  # Default to 50 if unknown
