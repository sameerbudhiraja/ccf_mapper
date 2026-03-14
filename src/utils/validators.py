"""
Validation utilities for data quality checks.
"""
from typing import List, Dict, Any
from src.models.control import Control, Requirement


class ControlValidator:
    """Validates control objects."""
    
    @staticmethod
    def validate(control: Control) -> bool:
        """
        Validate a control object.
        
        Args:
            control: Control to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not control.control_id:
            return False
        if not control.control_title:
            return False
        if not control.control_description:
            return False
        return True


class RequirementValidator:
    """Validates requirement objects."""
    
    @staticmethod
    def validate(requirement: Requirement) -> bool:
        """
        Validate a requirement object.
        
        Args:
            requirement: Requirement to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not requirement.requirement_id:
            return False
        if not requirement.requirement_title:
            return False
        if not requirement.requirement_description:
            return False
        if not requirement.framework_name:
            return False
        return True
