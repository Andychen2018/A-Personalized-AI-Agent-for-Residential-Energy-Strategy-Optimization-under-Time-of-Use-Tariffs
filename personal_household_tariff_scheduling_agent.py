import importlib
import json
from test_func_1_int import agent_tariff_cost_summary_and_recommendation
from llm import chat_with_api

def print_red(text):
    """Print debug text in red color"""
    print(f"\033[91m{text}\033[0m")

def print_green(text):
    """Print debug text in green color"""
    print(f"\033[92m{text}\033[0m")

def print_blue(text):
    """Print debug text in blue color"""
    print(f"\033[94m{text}\033[0m")

def print_yellow(text):
    """Print debug text in yellow color"""
    print(f"\033[93m{text}\033[0m")

# Tool registry
TOOLS = [

    {
        "name": "preprocess",
        "description": "Analyze the user's appliance list and determine if the devices can be scheduled.",
        "parameters": {
            "user_input": "A string describing the user's appliances and scheduling request."
        },
      
    },
    {
        "name": "simulate_tariff_and_recommend",
        "description": "Analyze electricity cost under different tariff schemes and recommend the optimal one.",
        "parameters": {
            "user_input": "Optional appliance description or comment (can be empty)."
        },
       
    },
    {
        "name": "appliance_event_reason",
        "description": "Analyze appliance scheduling rules and explain the default forbidden time intervals.",
        "parameters": {"user_input": "Optional user message (can be ignored)"},
        
    },
    {
    "name": "filter_events_by_constraints_and_tariff",
    "description": "Filter appliance events based on LLM-revised constraints and pricing schemes.",
    "parameters": {
        "user_instruction": "Optional constraint modification instruction. If empty, uses default rules."
                },
    },
    {
    "name": "peak_valley_tariff_appliance_scheduling_analyzer_tool",
    "description": "Analyze and visualize appliance scheduling under peak-valley tariffs.",
    "parameters": {
        "user_instruction": "Optional user instruction for scheduling analysis (can be empty)."
                }   
    }

    ]



class Assistant:
    def __init__(self):
        self.messages = []
        self._initialize_system_prompt()
    
    def _initialize_system_prompt(self):
        system_prompt = self._build_system_prompt()
        self.messages = [{"role": "system", "content": system_prompt}]
    
    def _get_tools_prompt(self):
        return (
            "Available tools:\n" +
            "\n".join(
                f"- {tool['name']}: {tool['description']} (parameters: {', '.join(tool['parameters'].keys())})"
                for tool in TOOLS
            )
        )

    def _build_system_prompt(self):
        return (
        "You are a smart home butler assistant (家庭管家助手). "
        "You help users manage their home appliances and optimize energy usage through intelligent scheduling. "
        "You are friendly, helpful, and knowledgeable about home appliance management.\n\n"

        "You have access to several callable tools. Your goal is to assist users by selecting and calling these tools appropriately. "
        "You can reason step-by-step and break down complex tasks into multiple tool calls if needed.\n\n"

        "The user may proceed step-by-step, such as:\n"
        "- \"First help me recognize appliances\"\n"
        "- Then: \"Now analyze tariffs\"\n"
        "- Then: \"What are the default rules\"\n"
        "- Then: \"Please help me to analyze all appliances constrains\"\n"
        "- Then: \"Now I want to filter events by constraints and tariff\"\n"
        "- Then: \"Now I want to analyze and visualize appliance scheduling under peak-valley tariffs\"\n"
       
        "- And so on.\n\n"

        "Your job is to understand the user's current goal or subgoal and return a callable tool signature "
        "in the following strict JSON format:\n"
        "{\"intent\": ..., \"tool\": {\"name\": ..., \"args\": {...}}}\n\n"

        "Available tools:\n" +
        self._get_tools_prompt() +
        "\n\n"
        "If you don’t have enough information to call a tool, ask the user for more details. "
        "Otherwise, do not explain your reasoning—just output the JSON for tool invocation. "
        "Only respond in natural language when asking clarification or concluding the conversation."
    )


    def chat(self, user_input):
        """Process user input and return assistant response"""
        self.messages.append({"role": "user", "content": user_input})
        llm_response = chat_with_api(self.messages)

        if not llm_response or "choices" not in llm_response:
            return "Sorry, I'm having trouble connecting right now. Please try again."

        content = llm_response["choices"][0]["message"]["content"]
        self.messages.append({"role": "assistant", "content": content})

        try:
            result = json.loads(content)
            intent = result.get("intent")
            tool_info = result.get("tool", {})
            tool_name = tool_info.get("name")
            tool_args = tool_info.get("args", {})

            print_red(f"[DEBUG] intent: {intent}")
            print_red(f"[DEBUG] tool name: {tool_name}")
            print_red(f"[DEBUG] tool args: {tool_args}")


            import test_func_2_int
            import test_func_3_int
            import test_func_4_int
            import test_func_5_int  
            import test_func_6_int

            # ✅ Tool 1: preprocess
            if tool_name == "preprocess" and "user_input" in tool_args:
                try:
                    tool_result = test_func_2_int.preprocess(tool_args["user_input"])
                    tool_response = f"Based on my analysis: {tool_result}"
                    self.messages.append({"role": "assistant", "content": tool_response})
                    return tool_response
                except Exception as e:
                    error_msg = f"❌ Error in preprocess: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg

            # ✅ Tool 3: simulate_tariff_and_recommend
            elif tool_name == "simulate_tariff_and_recommend":
                try:
                    # 安全获取 user_input（可以为空）
                    user_input_param = tool_args.get("user_input", None)
                    tool_result = test_func_3_int.simulate_tariff_and_recommend(user_input_param)
                    response = json.dumps(tool_result, indent=2, ensure_ascii=False)
                    self.messages.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_msg = f"❌ Error in simulate_tariff_and_recommend: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg
                
            # ✅ Tool 4: appliance_event_reason
            elif tool_name == "appliance_event_reason":
                try:
                    tool_result = test_func_4_int.appliance_event_reason()
                    response = json.dumps(tool_result, indent=2, ensure_ascii=False)
                    self.messages.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_msg = f"❌ Error in appliance_event_reason: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg
                
            
            # ✅ Tool 5: filter_events_by_constraints_and_tariff
            elif tool_name == "filter_events_by_constraints_and_tariff":
                try:
                    # 安全获取 user_instruction（可以为空）
                    user_input_param = tool_args.get("user_instruction", None)
                    
                    tool_result = test_func_5_int.filter_events_by_constraints_and_tariff(user_input_param)
                    response = json.dumps(tool_result, indent=2, ensure_ascii=False)
                    self.messages.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_msg = f"❌ Error in filter_events_by_constraints_and_tariff: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg
                
            # ✅ Tool 6: peak_valley_tariff_appliance_scheduling_analyzer
            elif tool_name == "peak_valley_tariff_appliance_scheduling_analyzer_tool":
                try:
                    # 安全获取 user_instruction（可以为空）
                    user_input_param = tool_args.get("user_instruction", None)
                    
                    tool_result = test_func_6_int.peak_valley_tariff_appliance_scheduling_analyzer_tool()
                    response = json.dumps(tool_result, indent=2, ensure_ascii=False)
                    self.messages.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_msg = f"❌ Error in peak_valley_tariff_appliance_scheduling_analyzer_tool: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg

            else:
                return content

        except json.JSONDecodeError:
            return content
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_msg})
            return error_msg

    def reset_conversation(self):
        self._initialize_system_prompt()

    def get_conversation_history(self):
        return self.messages.copy()

if __name__ == "__main__":
    assistant = Assistant()

    print("=== Home Butler Assistant ===")
    query = "hello, who are you?"
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    query = """
        Hi, I have several appliances at home:
        Aggregate, Fridge, Chest Freezer, Upright Freezer, Tumble Dryer, Washing Machine, Dishwasher, Computer Site, Television Site, Electric Heater..

        Note: Entry 0 is the aggregated total power of the household and not an actual appliance.
        These devices correspond to Appliance1 through Appliance9 in the dataset and will be used for energy analysis.

        Important:
        1. All appliance names that differ only by a numeric suffix or parenthesis 
        (e.g., "Electric Heater (2)", "Electric Heater(3)") should be treated as the same appliance type 
        as the base name (e.g., "Electric Heater") when determining shiftability.
        2. If an appliance name contains a brand or location descriptor (e.g., "MJY Computer", "Freezer (Utility Room)"),
        use only the core appliance type (e.g., "Computer", "Freezer") to determine shiftability.
        """


    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    query = "please analyze my appliances and tell me which tariffs is your recommand:."
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))

    query = "Please help me to analyze all appliances constrains:"
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))

    query = json.dumps({
    "intent": "Filter appliance events based on constraints and chosen tariff",
    "tool": {
        "name": "filter_events_by_constraints_and_tariff",
        "args": {
            "user_instruction": (
                "Set forbidden operating time for Washing Machine, Tumble Dryer, and Dishwasher as 23:30 to 06:00 (next day);\n"
                "Ensure each event completes by 14:00 the next day (i.e., 38:00);\n"
                "Ignore events shorter than 5 minutes;\n"
                "Keep all other appliance rules as default."
                        )
                    }
                }
            })

    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))

    query = json.dumps({
    "intent": "Analyze and visualize appliance scheduling under peak-valley tariffs",
    "tool": {
        "name": "peak_valley_tariff_appliance_scheduling_analyzer",
        "args": {
            "user_instruction": (
                "Analyze all appliances under peak-valley tariffs and visualize the scheduling."
            )       
        }
    }
    })  
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    
    agent_tariff_cost_summary_and_recommendation()
