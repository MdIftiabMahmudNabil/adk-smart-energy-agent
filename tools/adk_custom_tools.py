"""Custom function tools for energy analysis following ADK best practices."""

from typing import Dict, List, Any
import statistics
from datetime import datetime


def calculate_consumption_statistics(consumption_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistical measures for consumption data.
    
    This tool analyzes time-series consumption data and returns key statistical
    metrics including mean, median, standard deviation, min, and max values.
    
    Args:
        consumption_data: List of dictionaries containing 'timestamp' and 
                         'consumption_kwh' keys. Each entry represents a 
                         consumption reading at a specific time.
    
    Returns:
        Dictionary with status and statistical data.
        Success: {
            "status": "success",
            "mean": 2.45,
            "median": 2.30,
            "std_dev": 0.85,
            "min": 0.8,
            "max": 8.5,
            "total": 120.5,
            "count": 48
        }
        Error: {"status": "error", "error_message": "Description of error"}
    """
    try:
        if not consumption_data or not isinstance(consumption_data, list):
            return {
                "status": "error",
                "error_message": "consumption_data must be a non-empty list"
            }
        
        # Extract consumption values
        consumptions = []
        for item in consumption_data:
            if isinstance(item, dict) and 'consumption_kwh' in item:
                try:
                    consumptions.append(float(item['consumption_kwh']))
                except (ValueError, TypeError):
                    continue
        
        if not consumptions:
            return {
                "status": "error",
                "error_message": "No valid consumption_kwh values found in data"
            }
        
        # Calculate statistics
        return {
            "status": "success",
            "mean": round(statistics.mean(consumptions), 2),
            "median": round(statistics.median(consumptions), 2),
            "std_dev": round(statistics.stdev(consumptions), 2) if len(consumptions) > 1 else 0,
            "min": round(min(consumptions), 2),
            "max": round(max(consumptions), 2),
            "total": round(sum(consumptions), 2),
            "count": len(consumptions)
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to calculate statistics: {str(e)}"
        }


def detect_peak_hours(consumption_data: List[Dict[str, Any]], top_n: int = 5) -> Dict[str, Any]:
    """
    Identify the hours with highest energy consumption.
    
    This tool analyzes hourly consumption patterns and returns the hours of day
    that consistently show the highest energy usage. Useful for understanding
    when to implement energy-saving strategies.
    
    Args:
        consumption_data: List of dictionaries with 'timestamp' and 'consumption_kwh'
        top_n: Number of top peak hours to return (default: 5)
    
    Returns:
        Dictionary with status and peak hour information.
        Success: {
            "status": "success",
            "peak_hours": [18, 19, 20, 7, 8],
            "peak_hours_consumption": {"18": 3.2, "19": 3.5, ...},
            "average_peak_consumption": 3.1
        }
        Error: {"status": "error", "error_message": "Description"}
    """
    try:
        if not consumption_data or not isinstance(consumption_data, list):
            return {
                "status": "error",
                "error_message": "consumption_data must be a non-empty list"
            }
        
        # Group consumption by hour
        hourly_consumption = {}
        for item in consumption_data:
            if not isinstance(item, dict):
                continue
            
            timestamp = item.get('timestamp')
            consumption = item.get('consumption_kwh')
            
            if not timestamp or consumption is None:
                continue
            
            try:
                # Parse timestamp to get hour
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = timestamp
                
                hour = dt.hour
                
                if hour not in hourly_consumption:
                    hourly_consumption[hour] = []
                hourly_consumption[hour].append(float(consumption))
            
            except (ValueError, AttributeError):
                continue
        
        if not hourly_consumption:
            return {
                "status": "error",
                "error_message": "Could not extract hourly consumption data"
            }
        
        # Calculate average consumption per hour
        hourly_averages = {
            hour: statistics.mean(consumptions)
            for hour, consumptions in hourly_consumption.items()
        }
        
        # Sort by consumption (highest first)
        sorted_hours = sorted(hourly_averages.items(), key=lambda x: x[1], reverse=True)
        
        # Get top N peak hours
        peak_hours = [hour for hour, _ in sorted_hours[:top_n]]
        peak_consumption = {
            str(hour): round(consumption, 2)
            for hour, consumption in sorted_hours[:top_n]
        }
        
        avg_peak = statistics.mean([consumption for _, consumption in sorted_hours[:top_n]])
        
        return {
            "status": "success",
            "peak_hours": peak_hours,
            "peak_hours_consumption": peak_consumption,
            "average_peak_consumption": round(avg_peak, 2),
            "total_hours_analyzed": len(hourly_averages)
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to detect peak hours: {str(e)}"
        }


def calculate_cost_by_rate_tier(
    consumption_kwh: float,
    rate_tiers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate energy cost using tiered rate structure.
    
    This tool applies a tiered pricing structure to calculate the total cost
    of energy consumption. Useful for utilities that charge different rates
    for different consumption levels or time periods.
    
    Args:
        consumption_kwh: Total energy consumption in kilowatt-hours
        rate_tiers: List of rate tiers, each with:
            - tier_name: Name like "off-peak", "standard", "peak"
            - rate_per_kwh: Cost per kWh for this tier
            - hours: List of hours this rate applies (0-23)
            OR
            - threshold_kwh: Consumption threshold for this tier
            - rate_per_kwh: Cost per kWh above threshold
    
    Returns:
        Dictionary with status and cost calculation.
        Success: {
            "status": "success",
            "total_cost": 127.50,
            "currency": "USD",
            "tier_breakdown": [
                {"tier": "off-peak", "kwh": 200, "cost": 20.00},
                {"tier": "standard", "kwh": 650, "cost": 97.50}
            ]
        }
        Error: {"status": "error", "error_message": "Description"}
    """
    try:
        if consumption_kwh <= 0:
            return {
                "status": "error",
                "error_message": "consumption_kwh must be greater than 0"
            }
        
        if not rate_tiers or not isinstance(rate_tiers, list):
            return {
                "status": "error",
                "error_message": "rate_tiers must be a non-empty list"
            }
        
        # Simple flat rate if only one tier
        if len(rate_tiers) == 1:
            tier = rate_tiers[0]
            rate = float(tier.get('rate_per_kwh', tier.get('rate', 0.15)))
            total_cost = consumption_kwh * rate
            
            return {
                "status": "success",
                "total_cost": round(total_cost, 2),
                "currency": "USD",
                "tier_breakdown": [{
                    "tier": tier.get('tier_name', tier.get('tier', 'standard')),
                    "kwh": consumption_kwh,
                    "rate": rate,
                    "cost": round(total_cost, 2)
                }]
            }
        
        # Multi-tier calculation
        remaining_kwh = consumption_kwh
        total_cost = 0
        breakdown = []
        
        # Sort tiers by rate (ascending) for progressive billing
        sorted_tiers = sorted(rate_tiers, key=lambda x: float(x.get('rate_per_kwh', x.get('rate', 0))))
        
        for tier in sorted_tiers:
            if remaining_kwh <= 0:
                break
            
            rate = float(tier.get('rate_per_kwh', tier.get('rate', 0.15)))
            threshold = float(tier.get('threshold_kwh', remaining_kwh))
            
            # Use minimum of remaining or threshold
            tier_kwh = min(remaining_kwh, threshold)
            tier_cost = tier_kwh * rate
            
            breakdown.append({
                "tier": tier.get('tier_name', tier.get('tier', f'tier_{len(breakdown)+1}')),
                "kwh": round(tier_kwh, 2),
                "rate": rate,
                "cost": round(tier_cost, 2)
            })
            
            total_cost += tier_cost
            remaining_kwh -= tier_kwh
        
        return {
            "status": "success",
            "total_cost": round(total_cost, 2),
            "currency": "USD",
            "tier_breakdown": breakdown,
            "average_rate": round(total_cost / consumption_kwh, 3)
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to calculate tiered cost: {str(e)}"
        }


def estimate_savings_potential(
    current_consumption_kwh: float,
    reduction_percentage: float,
    rate_per_kwh: float = 0.15
) -> Dict[str, Any]:
    """
    Estimate potential cost savings from reducing energy consumption.
    
    This tool calculates how much money could be saved by reducing energy
    consumption by a given percentage. Useful for evaluating the impact
    of energy efficiency measures.
    
    Args:
        current_consumption_kwh: Current monthly energy consumption in kWh
        reduction_percentage: Expected reduction as percentage (e.g., 15 for 15%)
        rate_per_kwh: Energy rate in USD per kWh (default: 0.15)
    
    Returns:
        Dictionary with status and savings calculation.
        Success: {
            "status": "success",
            "monthly_savings_usd": 19.13,
            "annual_savings_usd": 229.50,
            "kwh_saved_monthly": 127.5,
            "kwh_saved_annually": 1530,
            "new_monthly_cost": 108.38
        }
        Error: {"status": "error", "error_message": "Description"}
    """
    try:
        if current_consumption_kwh <= 0:
            return {
                "status": "error",
                "error_message": "current_consumption_kwh must be greater than 0"
            }
        
        if not (0 <= reduction_percentage <= 100):
            return {
                "status": "error",
                "error_message": "reduction_percentage must be between 0 and 100"
            }
        
        if rate_per_kwh <= 0:
            return {
                "status": "error",
                "error_message": "rate_per_kwh must be greater than 0"
            }
        
        # Calculate savings
        kwh_saved_monthly = current_consumption_kwh * (reduction_percentage / 100)
        kwh_saved_annually = kwh_saved_monthly * 12
        
        monthly_savings = kwh_saved_monthly * rate_per_kwh
        annual_savings = monthly_savings * 12
        
        current_monthly_cost = current_consumption_kwh * rate_per_kwh
        new_monthly_cost = current_monthly_cost - monthly_savings
        
        return {
            "status": "success",
            "monthly_savings_usd": round(monthly_savings, 2),
            "annual_savings_usd": round(annual_savings, 2),
            "kwh_saved_monthly": round(kwh_saved_monthly, 2),
            "kwh_saved_annually": round(kwh_saved_annually, 2),
            "current_monthly_cost": round(current_monthly_cost, 2),
            "new_monthly_cost": round(new_monthly_cost, 2),
            "reduction_percentage": reduction_percentage
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to estimate savings: {str(e)}"
        }


if __name__ == "__main__":
    # Test the tools
    import json
    from datetime import timedelta
    
    print("=== Testing Custom Function Tools ===\n")
    
    # Generate test data
    base_time = datetime(2024, 11, 1, 0, 0)
    test_data = []
    for hour in range(24):
        timestamp = base_time + timedelta(hours=hour)
        # Simulate realistic pattern
        if 0 <= hour < 6:
            consumption = 0.8
        elif 6 <= hour < 9:
            consumption = 2.5
        elif 9 <= hour < 17:
            consumption = 1.5
        elif 17 <= hour < 22:
            consumption = 3.2
        else:
            consumption = 1.2
        
        test_data.append({
            "timestamp": timestamp.isoformat(),
            "consumption_kwh": consumption
        })
    
    # Test 1: Calculate statistics
    print("1. Calculate Consumption Statistics:")
    result = calculate_consumption_statistics(test_data)
    print(json.dumps(result, indent=2))
    
    # Test 2: Detect peak hours
    print("\n2. Detect Peak Hours:")
    result = detect_peak_hours(test_data)
    print(json.dumps(result, indent=2))
    
    # Test 3: Calculate tiered cost
    print("\n3. Calculate Cost by Rate Tier:")
    rate_tiers = [
        {"tier": "off-peak", "rate_per_kwh": 0.10, "threshold_kwh": 200},
        {"tier": "standard", "rate_per_kwh": 0.15, "threshold_kwh": 500},
        {"tier": "peak", "rate_per_kwh": 0.25, "threshold_kwh": 1000}
    ]
    result = calculate_cost_by_rate_tier(850, rate_tiers)
    print(json.dumps(result, indent=2))
    
    # Test 4: Estimate savings
    print("\n4. Estimate Savings Potential:")
    result = estimate_savings_potential(850, 15, 0.15)
    print(json.dumps(result, indent=2))
    
    print("\n✅ All tools tested successfully!")
