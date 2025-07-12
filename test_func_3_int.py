import os
import pandas as pd

# Import key tool functions
from tools.p_03_tariff_modeling import simulate_tariff_cost_detailed
from tools.p_03_energy_summary import summarize_tariff_results_and_visualize

def simulate_tariff_and_recommend(user_input=None):
    """
    Simulate electricity costs under different tariff schemes and recommend the most cost-effective option.
    This function does not require actual user input.
    """

    # Define the input file paths
    event_csv = "./output/02_event_segments/02_appliance_event_segments_id.csv"
    power_csv = "./output/01_preprocessed/01_perception_alignment_result.csv"

    # Step 1: Simulate detailed cost results
    print("🔧 [Tariff Simulation] Running detailed cost evaluation for multiple tariff schemes...")
    result_df, summary_df = simulate_tariff_cost_detailed(event_csv, power_csv)

    # Step 2: Summarize and recommend the best tariff
    recommended_tariff = summarize_tariff_results_and_visualize()
    print(f"🎯 Recommended Tariff Scheme: {recommended_tariff}")

    # Step 3: Convert datetime fields to strings for JSON compatibility
    def convert_datetime(df):
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]':
                df[col] = df[col].dt.strftime('%Y-%m-%d')
        return df

    summary_df = convert_datetime(summary_df)
    result_df = convert_datetime(result_df)

    # Step 4: Return formatted results
    return {
        "recommended_tariff": recommended_tariff,
        "summary": summary_df.to_dict(orient="records"),
        "details": result_df.head(5).to_dict(orient="records")
    }

# Optional: Manual test execution
if __name__ == "__main__":
    result = simulate_tariff_and_recommend()

    print("\n✅ Recommended Tariff:", result["recommended_tariff"])
    print("\n📊 Summary of Costs (Top 3):")
    for item in result["summary"][:3]:
        print(item)

    print("\n📄 Sample Detailed Event Records (Top 5):")
    for row in result["details"]:
        print(row)
