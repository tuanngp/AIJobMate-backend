from typing import Dict, Any, List, Optional
import re
from datetime import datetime
import pandas as pd
import numpy as np
from cerberus import Validator
from loguru import logger

class DataValidator:
    def __init__(self):
        """Initialize data validator"""
        self.validator = Validator(allow_unknown=True)
        self.custom_types = {
            "email": self._validate_email,
            "url": self._validate_url,
            "date": self._validate_date,
            "number_range": self._validate_number_range,
            "enum": self._validate_enum,
            "nested_object": self._validate_nested_object
        }

    def validate_data_quality(
        self,
        data: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate data against defined rules"""
        try:
            # Add custom validation types
            for type_name, validator_func in self.custom_types.items():
                self.validator.types_mapping[type_name] = validator_func

            # Validate data
            is_valid = self.validator.validate(data, rules)
            
            return {
                "valid": is_valid,
                "errors": self.validator.errors if not is_valid else None,
                "normalized_data": self.validator.document if is_valid else None
            }

        except Exception as e:
            logger.error(f"Error validating data: {str(e)}")
            return {
                "valid": False,
                "errors": {"validation_error": str(e)},
                "normalized_data": None
            }

    def _validate_email(self, field: str, value: Any) -> bool:
        """Validate email format"""
        if not isinstance(value, str):
            return False
            
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, value))

    def _validate_url(self, field: str, value: Any) -> bool:
        """Validate URL format"""
        if not isinstance(value, str):
            return False
            
        pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        return bool(re.match(pattern, value))

    def _validate_date(self, field: str, value: Any) -> bool:
        """Validate date format"""
        if isinstance(value, datetime):
            return True
            
        if not isinstance(value, str):
            return False
            
        try:
            datetime.fromisoformat(value)
            return True
        except ValueError:
            return False

    def _validate_number_range(
        self,
        field: str,
        value: Any,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None
    ) -> bool:
        """Validate number within range"""
        if not isinstance(value, (int, float)):
            return False
            
        if min_val is not None and value < min_val:
            return False
            
        if max_val is not None and value > max_val:
            return False
            
        return True

    def _validate_enum(
        self,
        field: str,
        value: Any,
        allowed_values: List[Any]
    ) -> bool:
        """Validate value from enumerated list"""
        return value in allowed_values

    def _validate_nested_object(
        self,
        field: str,
        value: Any,
        schema: Dict[str, Any]
    ) -> bool:
        """Validate nested object structure"""
        if not isinstance(value, dict):
            return False
            
        nested_validator = Validator(schema, allow_unknown=True)
        return nested_validator.validate(value)

def validate_data_structure(
    data: Dict[str, Any],
    expected_schema: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate data structure against expected schema"""
    validator = DataValidator()
    return validator.validate_data_quality(data, expected_schema)

def validate_data_completeness(
    data: Dict[str, Any],
    required_fields: List[str]
) -> Dict[str, Any]:
    """Check if all required fields are present and non-null"""
    missing_fields = []
    null_fields = []
    
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
        elif data[field] is None:
            null_fields.append(field)
            
    is_valid = not (missing_fields or null_fields)
    
    return {
        "valid": is_valid,
        "missing_fields": missing_fields,
        "null_fields": null_fields
    }

def validate_data_consistency(
    data: Dict[str, Any],
    consistency_rules: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Check data consistency based on rules"""
    violations = []
    
    for rule in consistency_rules:
        rule_type = rule["type"]
        
        if rule_type == "dependency":
            # Check field dependencies
            if rule["if_field"] in data and data[rule["if_field"]] == rule["if_value"]:
                if rule["then_field"] not in data:
                    violations.append({
                        "rule": rule,
                        "message": f"Missing dependent field {rule['then_field']}"
                    })
                    
        elif rule_type == "mutual_exclusion":
            # Check mutually exclusive fields
            fields = rule["fields"]
            present_fields = [f for f in fields if f in data and data[f] is not None]
            if len(present_fields) > 1:
                violations.append({
                    "rule": rule,
                    "message": f"Fields {fields} are mutually exclusive"
                })
                
        elif rule_type == "correlation":
            # Check correlated fields
            fields = rule["fields"]
            if all(f in data for f in fields):
                values = [data[f] for f in fields]
                if not rule["validator"](values):
                    violations.append({
                        "rule": rule,
                        "message": f"Correlation rule violated for fields {fields}"
                    })
    
    return {
        "valid": not violations,
        "violations": violations
    }

def validate_numeric_bounds(
    value: float,
    bounds: Dict[str, float]
) -> Dict[str, Any]:
    """Validate numeric value within bounds"""
    min_val = bounds.get("min")
    max_val = bounds.get("max")
    
    violations = []
    
    if min_val is not None and value < min_val:
        violations.append(f"Value {value} is below minimum {min_val}")
        
    if max_val is not None and value > max_val:
        violations.append(f"Value {value} is above maximum {max_val}")
    
    return {
        "valid": not violations,
        "violations": violations,
        "value": value
    }

def validate_statistical_rules(
    data: List[Dict[str, Any]],
    rules: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate data using statistical rules"""
    try:
        df = pd.DataFrame(data)
        violations = []
        
        for field, field_rules in rules.items():
            if field not in df.columns:
                continue
                
            values = df[field].dropna()
            
            if "outlier_std" in field_rules:
                # Check for outliers using standard deviation
                std_limit = field_rules["outlier_std"]
                mean = values.mean()
                std = values.std()
                outliers = values[abs(values - mean) > std_limit * std]
                
                if not outliers.empty:
                    violations.append({
                        "field": field,
                        "rule": "outlier_std",
                        "outliers": outliers.tolist()
                    })
                    
            if "outlier_iqr" in field_rules:
                # Check for outliers using IQR
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                outliers = values[
                    (values < Q1 - 1.5 * IQR) |
                    (values > Q3 + 1.5 * IQR)
                ]
                
                if not outliers.empty:
                    violations.append({
                        "field": field,
                        "rule": "outlier_iqr",
                        "outliers": outliers.tolist()
                    })
                    
            if "distribution" in field_rules:
                # Check value distribution
                expected_dist = field_rules["distribution"]
                current_dist = values.value_counts(normalize=True).to_dict()
                
                for value, expected_prob in expected_dist.items():
                    current_prob = current_dist.get(value, 0)
                    if abs(current_prob - expected_prob) > field_rules.get("tolerance", 0.1):
                        violations.append({
                            "field": field,
                            "rule": "distribution",
                            "value": value,
                            "expected": expected_prob,
                            "actual": current_prob
                        })
    
        return {
            "valid": not violations,
            "violations": violations
        }

    except Exception as e:
        logger.error(f"Error in statistical validation: {str(e)}")
        return {
            "valid": False,
            "error": str(e)
        }

def validate_time_series(
    data: List[Dict[str, Any]],
    rules: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate time series data"""
    try:
        df = pd.DataFrame(data)
        violations = []
        
        for field, field_rules in rules.items():
            if field not in df.columns:
                continue
                
            values = pd.to_numeric(df[field], errors='coerce')
            timestamps = pd.to_datetime(df[field_rules["timestamp_field"]])
            
            if "missing_threshold" in field_rules:
                # Check for gaps in time series
                time_diff = timestamps.diff()
                max_gap = pd.Timedelta(field_rules["missing_threshold"])
                gaps = time_diff[time_diff > max_gap]
                
                if not gaps.empty:
                    violations.append({
                        "field": field,
                        "rule": "missing_threshold",
                        "gaps": gaps.to_dict()
                    })
                    
            if "change_threshold" in field_rules:
                # Check for sudden changes
                changes = values.diff().abs()
                threshold = field_rules["change_threshold"]
                spikes = changes[changes > threshold]
                
                if not spikes.empty:
                    violations.append({
                        "field": field,
                        "rule": "change_threshold",
                        "spikes": spikes.to_dict()
                    })
                    
            if "trend_threshold" in field_rules:
                # Check for trend violations
                window = field_rules.get("trend_window", 5)
                trend = values.rolling(window=window).mean()
                threshold = field_rules["trend_threshold"]
                
                trend_violations = trend[abs(trend - values) > threshold]
                if not trend_violations.empty:
                    violations.append({
                        "field": field,
                        "rule": "trend_threshold",
                        "violations": trend_violations.to_dict()
                    })
    
        return {
            "valid": not violations,
            "violations": violations
        }

    except Exception as e:
        logger.error(f"Error in time series validation: {str(e)}")
        return {
            "valid": False,
            "error": str(e)
        }

def validate_uniqueness(
    data: List[Dict[str, Any]],
    unique_fields: List[str]
) -> Dict[str, Any]:
    """Check uniqueness constraints"""
    try:
        df = pd.DataFrame(data)
        duplicates = {}
        
        for field in unique_fields:
            if field in df.columns:
                dups = df[df[field].duplicated()][field]
                if not dups.empty:
                    duplicates[field] = dups.tolist()
    
        return {
            "valid": not duplicates,
            "duplicates": duplicates
        }

    except Exception as e:
        logger.error(f"Error checking uniqueness: {str(e)}")
        return {
            "valid": False,
            "error": str(e)
        }

def validate_referential_integrity(
    data: List[Dict[str, Any]],
    reference_data: Dict[str, List[Any]],
    reference_rules: List[Dict[str, str]]
) -> Dict[str, Any]:
    """Check referential integrity"""
    violations = []
    
    for rule in reference_rules:
        field = rule["field"]
        reference = rule["reference"]
        
        if reference not in reference_data:
            violations.append({
                "field": field,
                "error": f"Reference data not found for {reference}"
            })
            continue
            
        valid_values = set(reference_data[reference])
        
        for record in data:
            if field in record:
                value = record[field]
                if value not in valid_values:
                    violations.append({
                        "field": field,
                        "value": value,
                        "error": f"Invalid reference value"
                    })
    
    return {
        "valid": not violations,
        "violations": violations
    }

def validate_data_quality(
    data: Dict[str, Any],
    rules: Dict[str, Any]
) -> Dict[str, Any]:
    """Main entry point for data quality validation"""
    try:
        results = {}
        
        # Validate structure
        if "schema" in rules:
            results["structure"] = validate_data_structure(
                data,
                rules["schema"]
            )
            
        # Validate completeness
        if "required_fields" in rules:
            results["completeness"] = validate_data_completeness(
                data,
                rules["required_fields"]
            )
            
        # Validate consistency
        if "consistency_rules" in rules:
            results["consistency"] = validate_data_consistency(
                data,
                rules["consistency_rules"]
            )
            
        # Validate numeric bounds
        if "numeric_bounds" in rules:
            numeric_results = {}
            for field, bounds in rules["numeric_bounds"].items():
                if field in data:
                    numeric_results[field] = validate_numeric_bounds(
                        data[field],
                        bounds
                    )
            results["numeric_bounds"] = numeric_results
            
        # Validate statistical rules
        if "statistical_rules" in rules and isinstance(data, list):
            results["statistical"] = validate_statistical_rules(
                data,
                rules["statistical_rules"]
            )
            
        # Validate time series
        if "time_series_rules" in rules and isinstance(data, list):
            results["time_series"] = validate_time_series(
                data,
                rules["time_series_rules"]
            )
            
        # Validate uniqueness
        if "unique_fields" in rules and isinstance(data, list):
            results["uniqueness"] = validate_uniqueness(
                data,
                rules["unique_fields"]
            )
            
        # Validate referential integrity
        if all(key in rules for key in ["reference_data", "reference_rules"]) and isinstance(data, list):
            results["referential_integrity"] = validate_referential_integrity(
                data,
                rules["reference_data"],
                rules["reference_rules"]
            )
            
        # Calculate overall validity
        is_valid = all(
            result.get("valid", False)
            for result in results.values()
            if isinstance(result, dict)
        )
        
        return {
            "valid": is_valid,
            "results": results
        }

    except Exception as e:
        logger.error(f"Error in data quality validation: {str(e)}")
        return {
            "valid": False,
            "error": str(e)
        }
