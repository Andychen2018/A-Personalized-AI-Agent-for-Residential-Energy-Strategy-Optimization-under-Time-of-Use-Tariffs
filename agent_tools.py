#!/usr/bin/env python3
"""
Agent Tools - Simplified Interface for Energy Optimization

This module provides simplified, agent-friendly functions that integrate
the p042, p043, and p044 tools into easy-to-use interfaces.

Author: Andychen2018
"""

import os
import json
from typing import Dict, List, Optional
from agent_energy_optimizer import optimize_household_energy

def process_energy_constraints(
    user_instruction: str,
    region: str = "California",
    house_id: str = None
) -> Dict:
    """
    Process energy constraints and optimize household appliance scheduling
    
    This function integrates the complete workflow:
    1. Generate default appliance constraints
    2. Parse user natural language instructions using LLM
    3. Filter events by minimum duration requirements
    4. Apply TOU (Time-of-Use) optimization based on regional tariffs
    
    Args:
        user_instruction (str): Natural language instruction for appliance constraints
            Example: "Washing machine cannot run between 11 PM and 6 AM, 
                     must finish by 2 PM next day, ignore events under 5 minutes"
        
        region (str): Target region for tariff optimization
            Options: "California", "UK", "Germany"
            Default: "California"
        
        house_id (str): Optional house identifier for file organization
            If provided, will look for house-specific data files
    
    Returns:
        Dict: Comprehensive optimization results
        {
            "status": "success" | "failed",
            "region": str,
            "processed_tariffs": List[str],
            "output_files": List[str],
            "llm_parsing_success": bool,
            "user_instruction": str,
            "file_paths": Dict[str, str],
            "statistics": Dict,
            "error": str (if failed)
        }
    
    Example:
        >>> result = process_energy_constraints(
        ...     user_instruction="Dishwasher should not run during peak hours 5-8 PM",
        ...     region="California"
        ... )
        >>> print(f"Status: {result['status']}")
        >>> print(f"Optimized files: {result['output_files']}")
    """
    
    # Determine tariff names based on region
    tariff_mapping = {
        "California": ["TOU_D"],
        "UK": ["Economy_7", "Economy_10"], 
        "Germany": ["Germany_Variable"]
    }
    
    tariff_names = tariff_mapping.get(region, ["TOU_D"])
    
    # Set base directory (adjust if house_id is provided)
    base_dir = "."
    if house_id:
        # Could be extended to handle house-specific directories
        print(f"🏠 Processing for house: {house_id}")
    
    # Call the main optimization function
    result = optimize_household_energy(
        user_instruction=user_instruction,
        tariff_names=tariff_names,
        region=region,
        base_dir=base_dir
    )
    
    return result


def quick_tou_optimization(
    region: str = "California",
    use_default_constraints: bool = True
) -> Dict:
    """
    Quick TOU optimization with default settings
    
    This is a simplified version that uses default constraints and
    focuses on TOU optimization without custom user instructions.
    
    Args:
        region (str): Target region for optimization
        use_default_constraints (bool): Whether to use default constraints
    
    Returns:
        Dict: Optimization results
    """
    
    default_instruction = (
        "Use default scheduling constraints for all appliances. "
        "Apply standard time-of-use optimization to minimize electricity costs."
    )
    
    if not use_default_constraints:
        default_instruction = (
            "For major appliances (Washing Machine, Tumble Dryer, Dishwasher):\n"
            "- Avoid operation during peak price periods\n"
            "- Prefer off-peak hours for energy savings\n"
            "- Maintain reasonable completion times\n"
            "Apply cost optimization for all shiftable appliances."
        )
    
    return process_energy_constraints(
        user_instruction=default_instruction,
        region=region
    )


def get_optimization_summary(result: Dict) -> str:
    """
    Generate a human-readable summary of optimization results
    
    Args:
        result (Dict): Result from process_energy_constraints()
    
    Returns:
        str: Formatted summary text
    """
    
    if result["status"] != "success":
        return f"❌ Optimization failed: {result.get('error', 'Unknown error')}"
    
    summary_lines = [
        "✅ Energy Optimization Summary",
        "=" * 40,
        f"Region: {result['region']}",
        f"Processed Tariffs: {', '.join(result['processed_tariffs'])}",
        f"LLM Parsing: {'✅ Success' if result['llm_parsing_success'] else '⚠️ Used defaults'}",
        f"Output Files Generated: {len(result['output_files'])}",
        ""
    ]
    
    # Add statistics if available
    if "statistics" in result and "tariff_results" in result["statistics"]:
        summary_lines.append("📊 Tariff Results:")
        for tariff, stats in result["statistics"]["tariff_results"].items():
            summary_lines.extend([
                f"  {tariff}:",
                f"    Total Events: {stats['total_events']}",
                f"    Reschedulable: {stats['reschedulable_events']}",
                f"    Filter Efficiency: {stats['filter_efficiency']:.1f}%"
            ])
        summary_lines.append("")
    
    # Add file paths
    if "file_paths" in result:
        summary_lines.extend([
            "📁 Generated Files:",
            f"  Constraints: {os.path.basename(result['file_paths']['constraints'])}",
            f"  Duration Filtered: {os.path.basename(result['file_paths']['duration_filtered'])}",
            f"  TOU Optimized: {len(result['file_paths']['tou_optimized'])} files"
        ])
    
    return "\n".join(summary_lines)


def validate_user_instruction(instruction: str) -> Dict[str, bool]:
    """
    Validate user instruction format and content
    
    Args:
        instruction (str): User instruction to validate
    
    Returns:
        Dict: Validation results
        {
            "is_valid": bool,
            "has_appliance_names": bool,
            "has_time_constraints": bool,
            "has_duration_constraints": bool,
            "suggestions": List[str]
        }
    """
    
    instruction_lower = instruction.lower()
    
    # Check for appliance names
    appliance_keywords = ['washing machine', 'tumble dryer', 'dishwasher', 'dryer', 'washer']
    has_appliances = any(keyword in instruction_lower for keyword in appliance_keywords)
    
    # Check for time constraints
    time_keywords = ['between', 'from', 'to', 'during', 'before', 'after', 'pm', 'am', ':']
    has_time = any(keyword in instruction_lower for keyword in time_keywords)
    
    # Check for duration constraints
    duration_keywords = ['minutes', 'min', 'hours', 'hour', 'shorter than', 'longer than', 'duration']
    has_duration = any(keyword in instruction_lower for keyword in duration_keywords)
    
    suggestions = []
    if not has_appliances:
        suggestions.append("Consider specifying appliance names (e.g., 'Washing Machine', 'Dishwasher')")
    
    if not has_time:
        suggestions.append("Consider adding time constraints (e.g., 'between 11 PM and 6 AM')")
    
    if not has_duration:
        suggestions.append("Consider adding duration filters (e.g., 'ignore events shorter than 5 minutes')")
    
    is_valid = len(instruction.strip()) > 10  # Basic length check
    
    return {
        "is_valid": is_valid,
        "has_appliance_names": has_appliances,
        "has_time_constraints": has_time,
        "has_duration_constraints": has_duration,
        "suggestions": suggestions
    }


# Example usage and testing
if __name__ == "__main__":
    print("🧪 Testing Agent Tools")
    print("=" * 50)
    
    # Test 1: Basic optimization
    print("\n🔧 Test 1: Basic Energy Optimization")
    user_instruction = (
        "For Washing Machine and Dishwasher:\n"
        "- Do not operate between 5 PM and 8 PM (peak hours)\n"
        "- Must complete by 10 AM next day\n"
        "- Ignore events shorter than 10 minutes"
    )
    
    result = process_energy_constraints(
        user_instruction=user_instruction,
        region="California"
    )
    
    print(get_optimization_summary(result))
    
    # Test 2: Instruction validation
    print("\n🔍 Test 2: Instruction Validation")
    validation = validate_user_instruction(user_instruction)
    print(f"Validation: {validation}")
    
    # Test 3: Quick optimization
    print("\n⚡ Test 3: Quick TOU Optimization")
    quick_result = quick_tou_optimization(region="California")
    print(f"Quick optimization status: {quick_result['status']}")
    print(f"Files generated: {len(quick_result.get('output_files', []))}")
