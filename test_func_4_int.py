import json
from tools.p_041_get_appliance_list import get_appliance_list_from_csv

def appliance_event_reason(user_input=None):
    """
    Provide default appliance scheduling rules and appliance mapping.
    """
    result = get_appliance_list_from_csv()

    # 默认调度规则说明
    explanation = (
        "\n📌 Default Scheduling Rules:\n"
        "For all appliances with shiftability type 'Shiftable':\n"
        "  - Forbidden operating hours: from 23:00 to 06:30 (next day);\n"
        "  - Allowed shifting direction: only delay (no early start);\n"
        "  - Each event must finish no later than 14:00 of the next day (i.e., 38:00);\n"
        "  - These constraints will be applied during the action space pruning in scheduling optimization."
    )
    print(explanation)

    return {
        "appliance_mapping": result,  # 🔁 
        "default_constraints": {
            "shiftable": {
                "forbidden_time": ["23:00", "06:30"],
                "latest_finish": "38:00",
                "shift_rule": "only_delay"
            }
        },
        "note": "Default scheduling constraints applied for all shiftable appliances."
    }
if __name__ == "__main__":
    result = appliance_event_reason()
    print("\nReturned structure:")
    # print("\n返回结构：")
    print(json.dumps(result, indent=2, ensure_ascii=False))  