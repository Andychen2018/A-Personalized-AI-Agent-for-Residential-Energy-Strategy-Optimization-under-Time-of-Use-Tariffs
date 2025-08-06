#!/usr/bin/env python3
"""
Agent Energy Optimizer - Integrated Tool for Household Energy Management

This tool integrates p042, p043, and p044 functionalities into a single
agent-callable interface for complete constraint analysis and event filtering.

Author: Andychen2018
"""

import os
import json
import pandas as pd
from typing import Dict, List, Optional, Union

# Import individual tool functions (keeping tools unchanged)
from tools.p_042_user_constraints import UserConstraintsParser, process_single_household_constraints
from tools.p_043_min_duration_filter import process_min_duration_filter
from tools.p_044_tou_optimization_filter import process_and_mask_events

class EnergyOptimizer:
    """
    Integrated Energy Optimization Tool for Agent
    
    Combines constraint generation, duration filtering, and TOU optimization
    into a single cohesive workflow.
    """
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize the Energy Optimizer
        
        Args:
            base_dir: Base directory for file operations
        """
        self.base_dir = base_dir
        self.setup_paths()
    
    def setup_paths(self):
        """Setup file paths for the optimization workflow"""
        self.paths = {
            # Input files
            "events": os.path.join(self.base_dir, "output/02_event_segments/02_appliance_event_segments_id.csv"),
            "appliance_summary": os.path.join(self.base_dir, "output/01_appliance_summary/appliance_summary.json"),
            
            # Constraint files
            "default_constraints": os.path.join(self.base_dir, "output/04_user_constraints/appliance_constraints.json"),
            "revised_constraints": os.path.join(self.base_dir, "output/04_user_constraints/appliance_constraints_revise_by_llm.json"),
            
            # Intermediate files
            "duration_filtered": os.path.join(self.base_dir, "output/04_min_duration_filter/min_duration_filtered_events.csv"),
            
            # Configuration files
            "tariff_config": os.path.join(self.base_dir, "config/tariff_config.json"),
            "tou_d_config": os.path.join(self.base_dir, "config/TOU_D.json"),
            "germany_config": os.path.join(self.base_dir, "config/Germany_Variable.json"),
            
            # Output directories
            "output_constraints": os.path.join(self.base_dir, "output/04_user_constraints"),
            "output_duration": os.path.join(self.base_dir, "output/04_min_duration_filter"),
            "output_tou": os.path.join(self.base_dir, "output/04_TOU_filter")
        }
    
    def validate_inputs(self) -> Dict[str, bool]:
        """
        Validate required input files exist
        
        Returns:
            Dict mapping file types to existence status
        """
        validation = {}
        required_files = ["events", "appliance_summary"]
        
        for file_type in required_files:
            path = self.paths[file_type]
            validation[file_type] = os.path.exists(path)
            if not validation[file_type]:
                print(f"⚠️ Required file missing: {path}")
        
        return validation
    
    def step1_generate_constraints(self, house_id: str = "house1") -> bool:
        """
        Step 1: Generate default appliance constraints

        Args:
            house_id: House identifier for constraint generation

        Returns:
            Success status
        """
        print("🔧 Step 1: Generating default appliance constraints...")

        # Ensure output directory exists
        os.makedirs(self.paths["output_constraints"], exist_ok=True)

        if os.path.exists(self.paths["default_constraints"]):
            print("📋 Default constraints already exist, skipping generation")
            return True

        try:
            # Use the UserConstraintsParser class
            parser = UserConstraintsParser()
            result = parser.process_single_household(house_id, user_input="")

            if result and result.get('success', False):
                print("✅ Default constraints generated successfully")
                return True
            else:
                print("❌ Failed to generate default constraints")
                return False
        except Exception as e:
            print(f"❌ Error generating constraints: {e}")
            return False
    
    def step2_revise_constraints(self, user_instruction: str, house_id: str = "house1") -> bool:
        """
        Step 2: Revise constraints based on user instruction

        Args:
            user_instruction: Natural language instruction from user
            house_id: House identifier for constraint revision

        Returns:
            Success status of LLM parsing
        """
        print("🧠 Step 2: Revising constraints based on user instruction...")
        print(f"User instruction: {user_instruction}")

        try:
            # Use the UserConstraintsParser class with user instruction
            parser = UserConstraintsParser()
            result = parser.process_single_household(house_id, user_input=user_instruction)

            if result and result.get('llm_success', False):
                print("✅ Constraints revised successfully by LLM")
                return True
            else:
                print("⚠️ LLM parsing failed, using default constraints as fallback")
                # The parser should have already created fallback constraints
                print("✅ Fallback to default constraints completed")
                return False
        except Exception as e:
            print(f"❌ Error in constraint revision: {e}")
            return False
    
    def step3_filter_by_duration(self) -> bool:
        """
        Step 3: Filter events by minimum duration
        
        Returns:
            Success status
        """
        print("⏱️ Step 3: Filtering events by minimum duration...")
        
        # Ensure output directory exists
        os.makedirs(self.paths["output_duration"], exist_ok=True)
        
        try:
            result_path = process_min_duration_filter(
                event_csv_path=self.paths["events"],
                constraint_json_path=self.paths["revised_constraints"],
                output_dir=self.paths["output_duration"]
            )
            
            if result_path and os.path.exists(result_path):
                # Update path for next step
                self.paths["duration_filtered"] = result_path
                
                # Print statistics
                df = pd.read_csv(result_path)
                total_events = len(df)
                reschedulable_events = len(df[df['is_reschedulable'] == True])
                
                print(f"✅ Duration filtering completed:")
                print(f"   Total events: {total_events}")
                print(f"   Reschedulable events: {reschedulable_events}")
                print(f"   Filter efficiency: {(total_events - reschedulable_events) / total_events * 100:.1f}%")
                
                return True
            else:
                print("❌ Duration filtering failed")
                return False
                
        except Exception as e:
            print(f"❌ Error in duration filtering: {e}")
            return False

    def step4_apply_tou_optimization(self, tariff_configs: List[Dict[str, str]]) -> List[str]:
        """
        Step 4: Apply TOU optimization for specified tariffs

        Args:
            tariff_configs: List of tariff configurations
                Format: [{"name": "TOU_D", "config_path": "./config/TOU_D.json"}, ...]

        Returns:
            List of output file paths
        """
        print("💰 Step 4: Applying TOU optimization...")

        output_files = []

        for tariff_config in tariff_configs:
            tariff_name = tariff_config["name"]
            config_path = tariff_config["config_path"]

            if not os.path.exists(config_path):
                print(f"⚠️ Config file not found: {config_path}, skipping {tariff_name}")
                continue

            print(f"\n🔄 Processing {tariff_name} tariff...")

            try:
                # Create output directory for this tariff
                output_dir = os.path.join(self.paths["output_tou"], "California" if "TOU" in tariff_name else "UK", tariff_name)
                os.makedirs(output_dir, exist_ok=True)

                # Process TOU optimization
                result_path = process_and_mask_events(
                    event_csv_path=self.paths["duration_filtered"],
                    constraint_json_path=self.paths["revised_constraints"],
                    tariff_config_path=config_path,
                    tariff_name=tariff_name,
                    output_dir=output_dir
                )

                if result_path and os.path.exists(result_path):
                    output_files.append(result_path)

                    # Print statistics
                    df = pd.read_csv(result_path)
                    total_events = len(df)
                    reschedulable_events = len(df[df['is_reschedulable'] == True])
                    filter_efficiency = (total_events - reschedulable_events) / total_events * 100 if total_events > 0 else 0

                    print(f"✅ {tariff_name} optimization completed:")
                    print(f"   Total events: {total_events}")
                    print(f"   Reschedulable events: {reschedulable_events}")
                    print(f"   Filter efficiency: {filter_efficiency:.1f}%")

                    # Calculate average optimization potential
                    reschedulable_df = df[df['is_reschedulable'] == True]
                    if len(reschedulable_df) > 0 and 'optimization_potential' in reschedulable_df.columns:
                        avg_potential = reschedulable_df['optimization_potential'].mean()
                        print(f"   Average optimization potential: {avg_potential:.2f}")
                else:
                    print(f"❌ {tariff_name} optimization failed")

            except Exception as e:
                print(f"❌ Error processing {tariff_name}: {e}")

        print(f"\n✅ TOU optimization completed for {len(output_files)} tariffs")
        return output_files

    def optimize_energy_consumption(
        self,
        user_instruction: str,
        tariff_names: List[str] = None,
        region: str = "California"
    ) -> Dict[str, Union[str, bool, List[str], Dict]]:
        """
        Main optimization function for Agent calls

        Args:
            user_instruction: Natural language constraint instruction
            tariff_names: List of tariff names to process (default: ["TOU_D"])
            region: Region for tariff selection ("California", "UK", "Germany")

        Returns:
            Comprehensive result dictionary with status, files, and statistics
        """
        print("🚀 Starting Energy Consumption Optimization...")
        print("=" * 80)

        # Set default tariffs based on region
        if tariff_names is None:
            if region == "California":
                tariff_names = ["TOU_D"]
            elif region == "UK":
                tariff_names = ["Economy_7", "Economy_10"]
            elif region == "Germany":
                tariff_names = ["Germany_Variable"]
            else:
                tariff_names = ["TOU_D"]  # Default fallback

        # Validate inputs
        validation = self.validate_inputs()
        if not all(validation.values()):
            return {
                "status": "failed",
                "error": "Required input files missing",
                "validation": validation
            }

        try:
            # Step 1: Generate default constraints
            house_id = "house1"  # Default house for single-house processing
            if not self.step1_generate_constraints(house_id):
                return {"status": "failed", "error": "Failed to generate default constraints"}

            # Step 2: Revise constraints based on user instruction
            llm_success = self.step2_revise_constraints(user_instruction, house_id)

            # Step 3: Filter by minimum duration
            if not self.step3_filter_by_duration():
                return {"status": "failed", "error": "Failed to filter events by duration"}

            # Step 4: Apply TOU optimization
            tariff_configs = self._get_tariff_configs(tariff_names, region)
            output_files = self.step4_apply_tou_optimization(tariff_configs)

            # Compile results
            result = {
                "status": "success",
                "region": region,
                "processed_tariffs": tariff_names,
                "output_files": output_files,
                "llm_parsing_success": llm_success,
                "user_instruction": user_instruction,
                "file_paths": {
                    "constraints": self.paths["revised_constraints"],
                    "duration_filtered": self.paths["duration_filtered"],
                    "tou_optimized": output_files
                },
                "statistics": self._generate_statistics(output_files)
            }

            print("\n✅ Energy optimization workflow completed successfully!")
            return result

        except Exception as e:
            error_msg = f"Optimization workflow failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "failed", "error": error_msg}

    def _get_tariff_configs(self, tariff_names: List[str], region: str) -> List[Dict[str, str]]:
        """Get tariff configuration paths based on names and region"""
        config_mapping = {
            "TOU_D": self.paths["tou_d_config"],
            "Germany_Variable": self.paths["germany_config"],
            "Economy_7": self.paths["tariff_config"],
            "Economy_10": self.paths["tariff_config"]
        }

        return [
            {"name": name, "config_path": config_mapping.get(name, self.paths["tariff_config"])}
            for name in tariff_names
        ]

    def _generate_statistics(self, output_files: List[str]) -> Dict:
        """Generate summary statistics from output files"""
        stats = {
            "total_files": len(output_files),
            "tariff_results": {}
        }

        for file_path in output_files:
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    tariff_name = os.path.basename(file_path).split('_')[-1].replace('.csv', '')

                    stats["tariff_results"][tariff_name] = {
                        "total_events": len(df),
                        "reschedulable_events": len(df[df['is_reschedulable'] == True]),
                        "filter_efficiency": (len(df) - len(df[df['is_reschedulable'] == True])) / len(df) * 100 if len(df) > 0 else 0
                    }
                except Exception as e:
                    print(f"⚠️ Error generating stats for {file_path}: {e}")

        return stats


# Agent-callable functions
def optimize_household_energy(
    user_instruction: str,
    tariff_names: List[str] = None,
    region: str = "California",
    base_dir: str = "."
) -> Dict:
    """
    Agent-callable function for household energy optimization

    Args:
        user_instruction: Natural language constraint instruction
        tariff_names: List of tariff names to process
        region: Region for tariff selection
        base_dir: Base directory for file operations

    Returns:
        Optimization result dictionary
    """
    optimizer = EnergyOptimizer(base_dir=base_dir)
    return optimizer.optimize_energy_consumption(
        user_instruction=user_instruction,
        tariff_names=tariff_names,
        region=region
    )


if __name__ == "__main__":
    # Example usage
    print("🧪 Testing Agent Energy Optimizer")

    # Test with California TOU_D
    user_instruction = (
        "For Washing Machine, Tumble Dryer, and Dishwasher:\n"
        "- Do not operate between 23:30 and 06:00 (next day)\n"
        "- Must finish by 14:00 of the next day\n"
        "- Ignore events shorter than 5 minutes\n"
        "Keep default rules for other appliances."
    )

    result = optimize_household_energy(
        user_instruction=user_instruction,
        tariff_names=["TOU_D"],
        region="California"
    )

    print(f"\n📋 Optimization Result:")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Processed tariffs: {result['processed_tariffs']}")
        print(f"Output files: {len(result['output_files'])}")
        print(f"LLM parsing success: {result['llm_parsing_success']}")
        print(f"Statistics: {result['statistics']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
