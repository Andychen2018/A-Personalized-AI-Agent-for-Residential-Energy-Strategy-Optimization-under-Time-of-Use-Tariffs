#!/usr/bin/env python3
"""
Simple Agent Tools - Direct Integration of p042, p043, p044

This module provides a simplified agent interface based on the existing
test_func_5_int.py workflow, keeping the tools unchanged.

Author: Andychen2018
"""

import os
import json
import pandas as pd
from typing import Dict, List, Optional

def process_energy_optimization(
    user_instruction: str = None,
    region: str = "California",
    house_id: str = None
) -> Dict:
    """
    Process energy optimization for household appliances
    
    This function provides a simplified agent interface that integrates:
    1. Default constraint generation (p042)
    2. User instruction parsing via LLM (p042) 
    3. Minimum duration filtering (p043)
    4. TOU optimization and masking (p044)
    
    Args:
        user_instruction (str): Natural language instruction for appliance constraints
        region (str): Target region for tariff optimization ("California", "UK", "Germany")
        house_id (str): Optional house identifier
    
    Returns:
        Dict: Comprehensive optimization results
    """
    
    print(f"🚀 Processing Energy Optimization for {region}")
    print("=" * 60)
    
    # Import the individual tool functions directly
    try:
        from tools.p_042_user_constraints import UserConstraintsParser
        from tools.p_043_min_duration_filter import MinDurationEventFilter
        from tools.p_044_tou_optimization_filter import process_and_mask_events
    except ImportError as e:
        return {
            "status": "failed",
            "error": f"Failed to import tool functions: {e}"
        }
    
    # Set default instruction if none provided
    if user_instruction is None:
        user_instruction = (
            "For Washing Machine, Tumble Dryer, and Dishwasher:\n"
            "- Replace the default forbidden operating time with 23:30 to 06:00 (next day);\n"
            "- Set latest_finish to 14:00 of the next day (i.e., 38:00);\n"
            "- Ignore all events shorter than 5 minutes.\n"
            "Keep all other appliances with default scheduling rules."
        )
    
    try:
        # Execute the complete workflow
        result = execute_optimization_workflow(
            user_instruction=user_instruction,
            region=region,
            house_id=house_id or "house1"
        )
        
        # Add house_id to result if provided
        if house_id:
            result["house_id"] = house_id
        
        # Generate summary statistics
        if result["status"] == "success":
            result["statistics"] = generate_optimization_statistics(result["output_files"])
        
        return result
        
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Optimization failed: {str(e)}",
            "region": region
        }


def execute_optimization_workflow(user_instruction: str, region: str, house_id: str) -> Dict:
    """Execute the complete optimization workflow"""

    print("🔄 Executing optimization workflow...")

    # Import required classes
    from tools.p_042_user_constraints import UserConstraintsParser
    from tools.p_043_min_duration_filter import MinDurationEventFilter
    from tools.p_044_tou_optimization_filter import process_and_mask_events

    try:
        # Step 1: Process user constraints
        print("🔧 Step 1: Processing user constraints...")
        parser = UserConstraintsParser()
        constraint_result = parser.process_single_household(house_id, user_input=user_instruction)

        if not constraint_result:
            return {
                "status": "failed",
                "error": "Failed to process user constraints"
            }

        constraint_file = constraint_result.get('revised_file')
        if not constraint_file or not os.path.exists(constraint_file):
            return {
                "status": "failed",
                "error": "Constraint file not generated"
            }

        # Step 2: Filter by minimum duration
        print("⏱️ Step 2: Filtering by minimum duration...")

        try:
            duration_filter = MinDurationEventFilter()
            print(f"🔍 Debug: Created duration filter, calling process_single_household({house_id})")
            duration_result = duration_filter.process_single_household(house_id)
            print(f"🔍 Debug: duration_result = {duration_result}")
        except Exception as e:
            print(f"🔍 Debug: Exception in duration filtering: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "error": f"Duration filtering exception: {str(e)}"
            }

        if not duration_result:
            return {
                "status": "failed",
                "error": "Duration filtering failed"
            }

        duration_filtered_file = duration_result.get('output_file')
        print(f"🔍 Debug: duration_filtered_file = {duration_filtered_file}")

        if not duration_filtered_file:
            return {
                "status": "failed",
                "error": "Duration filtered file path not returned"
            }

        if not os.path.exists(duration_filtered_file):
            return {
                "status": "failed",
                "error": f"Duration filtered file not found: {duration_filtered_file}"
            }

        # Step 3: Apply TOU optimization
        print("💰 Step 3: Applying TOU optimization...")

        # Determine tariff configurations based on region
        tariff_configs = get_tariff_configs_for_region(region)
        output_files = []

        for tariff_name, config_path in tariff_configs:
            if not os.path.exists(config_path):
                print(f"⚠️ Config file not found: {config_path}, skipping {tariff_name}")
                continue

            print(f"🔄 Processing {tariff_name}...")

            tou_output_dir = f"output/04_TOU_filter/{region}/{tariff_name}/{house_id}"
            os.makedirs(tou_output_dir, exist_ok=True)

            try:
                tou_result_file = process_and_mask_events(
                    event_csv_path=duration_filtered_file,
                    constraint_json_path=constraint_file,
                    tariff_config_path=config_path,
                    tariff_name=tariff_name,
                    output_dir=tou_output_dir
                )

                if tou_result_file and os.path.exists(tou_result_file):
                    output_files.append(tou_result_file)
                    print(f"✅ {tariff_name} optimization completed")
                else:
                    print(f"❌ {tariff_name} optimization failed")

            except Exception as e:
                print(f"❌ Error processing {tariff_name}: {e}")

        if not output_files:
            return {
                "status": "failed",
                "error": "No TOU optimization files generated"
            }

        # Return success result
        return {
            "status": "success",
            "region": region,
            "house_id": house_id,
            "processed_tariffs": [name for name, _ in tariff_configs if any(name in f for f in output_files)],
            "output_files": output_files,
            "llm_parsing_success": constraint_result.get('llm_success', False),
            "user_instruction": user_instruction,
            "file_paths": {
                "constraints": constraint_file,
                "duration_filtered": duration_filtered_file,
                "tou_optimized": output_files
            }
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": f"Workflow execution failed: {str(e)}"
        }


def get_tariff_configs_for_region(region: str) -> List[tuple]:
    """Get tariff configurations for a specific region"""

    if region == "California":
        return [("TOU_D", "config/TOU_D.json")]
    elif region == "UK":
        return [
            ("Economy_7", "config/tariff_config.json"),
            ("Economy_10", "config/tariff_config.json")
        ]
    elif region == "Germany":
        return [("Germany_Variable", "config/Germany_Variable.json")]
    else:
        return [("TOU_D", "config/TOU_D.json")]  # Default fallback


def generate_optimization_statistics(output_files: List[str]) -> Dict:
    """Generate summary statistics from optimization output files"""
    
    stats = {
        "total_files": len(output_files),
        "tariff_results": {},
        "overall_summary": {}
    }
    
    total_events = 0
    total_reschedulable = 0
    
    for file_path in output_files:
        if not os.path.exists(file_path):
            continue
            
        try:
            df = pd.read_csv(file_path)
            
            # Extract tariff name from filename
            filename = os.path.basename(file_path)
            if "TOU_D" in filename:
                tariff_name = "TOU_D"
            elif "Economy_7" in filename:
                tariff_name = "Economy_7"
            elif "Economy_10" in filename:
                tariff_name = "Economy_10"
            elif "Germany_Variable" in filename:
                tariff_name = "Germany_Variable"
            else:
                tariff_name = "Unknown"
            
            events_count = len(df)
            reschedulable_count = len(df[df['is_reschedulable'] == True])
            filter_efficiency = (events_count - reschedulable_count) / events_count * 100 if events_count > 0 else 0
            
            stats["tariff_results"][tariff_name] = {
                "total_events": events_count,
                "reschedulable_events": reschedulable_count,
                "filtered_events": events_count - reschedulable_count,
                "filter_efficiency": round(filter_efficiency, 1),
                "file_path": file_path
            }
            
            total_events += events_count
            total_reschedulable += reschedulable_count
            
        except Exception as e:
            print(f"⚠️ Error processing statistics for {file_path}: {e}")
    
    # Overall summary
    overall_efficiency = (total_events - total_reschedulable) / total_events * 100 if total_events > 0 else 0
    stats["overall_summary"] = {
        "total_events": total_events,
        "total_reschedulable": total_reschedulable,
        "total_filtered": total_events - total_reschedulable,
        "overall_efficiency": round(overall_efficiency, 1)
    }
    
    return stats


def get_optimization_summary(result: Dict) -> str:
    """Generate a human-readable summary of optimization results"""
    
    if result["status"] != "success":
        return f"❌ Optimization failed: {result.get('error', 'Unknown error')}"
    
    lines = [
        "✅ Energy Optimization Summary",
        "=" * 50,
        f"🌍 Region: {result['region']}",
        f"📋 Processed Tariffs: {', '.join(result['processed_tariffs'])}",
        f"🧠 LLM Parsing: {'✅ Success' if result.get('llm_parsing_success', False) else '⚠️ Used defaults'}",
        f"📁 Output Files: {len(result['output_files'])}",
        ""
    ]
    
    # Add detailed statistics
    if "statistics" in result:
        stats = result["statistics"]
        lines.extend([
            "📊 Overall Statistics:",
            f"  Total Events: {stats['overall_summary']['total_events']}",
            f"  Reschedulable Events: {stats['overall_summary']['total_reschedulable']}",
            f"  Filter Efficiency: {stats['overall_summary']['overall_efficiency']}%",
            ""
        ])
        
        if stats["tariff_results"]:
            lines.append("🔍 Tariff Details:")
            for tariff, data in stats["tariff_results"].items():
                lines.extend([
                    f"  {tariff}:",
                    f"    Events: {data['total_events']} → {data['reschedulable_events']} reschedulable",
                    f"    Efficiency: {data['filter_efficiency']}%"
                ])
            lines.append("")
    
    # Add file information
    lines.extend([
        "📂 Generated Files:",
        *[f"  • {os.path.basename(f)}" for f in result["output_files"][:3]],  # Show first 3 files
    ])
    
    if len(result["output_files"]) > 3:
        lines.append(f"  ... and {len(result['output_files']) - 3} more files")
    
    return "\n".join(lines)


def validate_user_instruction(instruction: str) -> Dict:
    """Validate user instruction format and provide suggestions"""
    
    if not instruction or len(instruction.strip()) < 10:
        return {
            "is_valid": False,
            "issues": ["Instruction too short"],
            "suggestions": ["Provide more detailed constraints for appliances"]
        }
    
    instruction_lower = instruction.lower()
    
    # Check for key components
    has_appliances = any(app in instruction_lower for app in 
                        ['washing machine', 'dishwasher', 'tumble dryer', 'dryer'])
    has_time_constraints = any(word in instruction_lower for word in 
                              ['between', 'from', 'to', 'before', 'after', 'pm', 'am'])
    has_duration = any(word in instruction_lower for word in 
                      ['minutes', 'min', 'shorter', 'longer', 'duration'])
    
    issues = []
    suggestions = []
    
    if not has_appliances:
        issues.append("No specific appliances mentioned")
        suggestions.append("Specify appliances like 'Washing Machine', 'Dishwasher'")
    
    if not has_time_constraints:
        issues.append("No time constraints specified")
        suggestions.append("Add time restrictions like 'between 11 PM and 6 AM'")
    
    if not has_duration:
        suggestions.append("Consider adding duration filters like 'ignore events shorter than 5 minutes'")
    
    return {
        "is_valid": len(issues) == 0,
        "has_appliances": has_appliances,
        "has_time_constraints": has_time_constraints,
        "has_duration_constraints": has_duration,
        "issues": issues,
        "suggestions": suggestions
    }


# Example usage and testing
if __name__ == "__main__":
    print("🧪 Testing Simple Agent Tools")
    print("=" * 60)
    
    # Test instruction validation first
    user_instruction = (
        "For Washing Machine and Dishwasher:\n"
        "- Do not operate between 5 PM and 8 PM (peak hours)\n"
        "- Must complete by 10 AM next day\n"
        "- Ignore events shorter than 10 minutes"
    )
    
    print("🔍 Testing instruction validation...")
    validation = validate_user_instruction(user_instruction)
    print(f"Validation result: {validation}")
    
    print("\n🔧 Testing California TOU_D optimization...")
    result = process_energy_optimization(
        user_instruction=user_instruction,
        region="California"
    )
    
    print(get_optimization_summary(result))
