"""
Decision Logger Service
Logs all discount decisions for audit and analysis
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)


class DecisionLogger:
    """
    📊 DECISION LOGGER - Logs all discount decisions
    
    Provides audit trail and analytics for discount decisions
    """
    
    def __init__(self):
        self.logger = logging.getLogger("discount_decisions")
        
        # Configure JSON formatted logging
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_decision(self, decision_data: Dict[str, Any]) -> None:
        """Log a discount decision with all relevant data"""
        try:
            # Ensure all data is JSON serializable
            log_entry = {
                "timestamp": decision_data.get("timestamp", datetime.now().isoformat()),
                "request_id": decision_data.get("request_id", "unknown"),
                "user_email": decision_data.get("user_email"),
                "show_description": decision_data.get("show_description"),
                "decision_method": decision_data.get("decision_method", "unknown"),
                "final_decision": decision_data.get("final_decision"),
                "reasoning": decision_data.get("rejection_reason") or decision_data.get("llm_reasoning", ""),
                "processing_time_seconds": decision_data.get("processing_time_seconds", 0),
                "llm_used": decision_data.get("llm_used", False),
                "candidate_shows_found": decision_data.get("candidate_shows_found", 0),
                "confidence_score": decision_data.get("confidence_score"),
                "show_matched": decision_data.get("show_matched"),
                "error_message": decision_data.get("error_message")
            }
            
            # Log as structured JSON
            self.logger.info(f"DECISION_LOG: {json.dumps(log_entry, ensure_ascii=False)}")
            
        except Exception as e:
            # Fallback logging if JSON serialization fails
            self.logger.error(f"Error logging decision: {str(e)} - Data: {decision_data}")
    
    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log performance metrics"""
        try:
            self.logger.info(f"PERFORMANCE_METRICS: {json.dumps(metrics, ensure_ascii=False)}")
        except Exception as e:
            self.logger.error(f"Error logging performance metrics: {str(e)}")
    
    def log_system_health(self, health_data: Dict[str, Any]) -> None:
        """Log system health status"""
        try:
            self.logger.info(f"SYSTEM_HEALTH: {json.dumps(health_data, ensure_ascii=False)}")
        except Exception as e:
            self.logger.error(f"Error logging system health: {str(e)}") 