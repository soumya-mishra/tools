import boto3
import json
import os
from loguru import logger
# --- Configuration ---
BEDROCK_REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"
# --- Bedrock Client Initialization ---
try:
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name=BEDROCK_REGION
    )
except Exception as e:
    print(f"Error initializing Bedrock client: {e}")
    exit()

# ==============================================================================
# --- SPECIALIZED AGENT DEFINITIONS (OUR "TOOLS") ---
# These classes are our well-defined, executable tools.
# ==============================================================================

class SummarizationAgent:
    """Tool to summarize text."""
    def execute(self, text: str) -> str:
        print("...[Tool] SummarizationAgent Activated...")
        prompt = f"Human: Please provide a concise, high-level summary of the following text.\n\n<text>{text}</text>\n\nAssistant:"
        return self._invoke_model(prompt)

    def _invoke_model(self, prompt: str) -> str:
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            })
            response = bedrock_runtime.invoke_model(body=body, modelId=MODEL_ID)
            response_body = json.loads(response.get('body').read())
            return response_body['content'][0]['text']
        except Exception as e:
            return f"Error: {str(e)}"

class SentimentAgent:
    """Tool to analyze sentiment."""
    def execute(self, text: str) -> str:
        print("...[Tool] SentimentAgent Activated...")
        prompt = f"Human: Analyze the sentiment of the following text. Respond with only one word: POSITIVE, NEGATIVE, or NEUTRAL.\n\n<text>{text}</text>\n\nAssistant:"
        response_text = self._invoke_model(prompt).strip().upper()
        return response_text if response_text in ["POSITIVE", "NEGATIVE", "NEUTRAL"] else "NEUTRAL"

    def _invoke_model(self, prompt: str) -> str:
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            })
            response = bedrock_runtime.invoke_model(body=body, modelId=MODEL_ID)
            response_body = json.loads(response.get('body').read())
            return response_body['content'][0]['text']
        except Exception as e:
            return "NEUTRAL"

class TranslationAgent:
    """Tool to translate text to French."""
    def execute(self, text: str) -> str:
        print("...[Tool] TranslationAgent Activated...")
        prompt = f"Human: Translate the following English text into French. Provide only the French translation.\n\n<english_text>{text}</english_text>\n\nAssistant:"
        return self._invoke_model(prompt)

    def _invoke_model(self, prompt: str) -> str:
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            })
            response = bedrock_runtime.invoke_model(body=body, modelId=MODEL_ID)
            response_body = json.loads(response.get('body').read())
            return response_body['content'][0]['text']
        except Exception as e:
            return f"Translation error: {str(e)}"

# ==============================================================================
# --- THE INTELLIGENT ORCHESTRATOR AGENT ---
# This agent uses an LLM to decide which tool to use.
# ==============================================================================

class LLMOrchestratorAgent:
    def __init__(self, client):
        self.client = client
        self.model_id = MODEL_ID
        
        # Instantiate and map the tools
        self.tools = {
            "summarize_text": SummarizationAgent(),
            "analyze_sentiment": SentimentAgent(),
            "translate_to_french": TranslationAgent()
        }
        
        # Create the tool definition string for the prompt
        self.tool_definitions = """
        <tools>
        <tool>
            <name>summarize_text</name>
            <description>Use this tool to create a concise summary of a long piece of text. The input is the text to summarize.</description>
            <input_schema>{"text": "string"}</input_schema>
        </tool>
        <tool>
            <name>analyze_sentiment</name>
            <description>Use this tool to determine the sentiment (POSITIVE, NEGATIVE, or NEUTRAL) of a piece of text. The input is the text to analyze.</description>
            <input_schema>{"text": "string"}</input_schema>
        </tool>
        <tool>
            <name>translate_to_french</name>
            <description>Use this tool to translate English text into the French language. The input is the English text to translate.</description>
            <input_schema>{"text": "string"}</input_schema>
        </tool>
        <tool>
            <name>no_tool_found</name>
            <description>Use this tool if none of the other tools are suitable for the user's request. The input should be a reason why no tool was chosen.</description>
            <input_schema>{"reason": "string"}</input_schema>
        </tool>
        </tools>
        """

    def _get_tool_selection_prompt(self, user_request: str) -> str:
        return f"""
        Human: You are an intelligent router that selects the best tool to respond to a user's request.
        Based on the user's request and the available tools, choose the most appropriate tool and provide the necessary input for it.
        Respond ONLY with a single valid JSON object containing "tool_name" and "tool_input".

        {self.tool_definitions}

        <user_request>
        {user_request}
        </user_request>

        Assistant:
        """

    def process_request(self, user_request: str) -> str:
        print("🧠 Orchestrator is thinking...")
        
        # === STEP 1: CHOOSE THE TOOL ===
        prompt = self._get_tool_selection_prompt(user_request)
        logger.info(f"process request:{prompt}")
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0
        })
        
        try:
            response = self.client.invoke_model(body=body, modelId=self.model_id)
            response_body = json.loads(response.get('body').read())
            tool_selection_json_str = response_body['content'][0]['text']
            tool_selection = json.loads(tool_selection_json_str)
            
            tool_name = tool_selection.get("tool_name")
            tool_input = tool_selection.get("tool_input", {})
            
            logger.info(f"✅ Tool selected: {tool_name}")
            logger.info(f"   Input provided: {tool_input}")

        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error parsing LLM response for tool selection: {e}")
            return "I'm sorry, I had trouble understanding which tool to use. Could you please rephrase your request?"

        # === STEP 2: EXECUTE THE TOOL ===
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            logger.info(f"in STEP 2 Execute Tool:{tool}")
            text_input = tool_input.get("text")
            if not text_input:
                 return "I understood which tool to use, but I couldn't find the text to process in your request."
            
            print("🛠️ Executing tool...")
            tool_result = tool.execute(text_input)
            print("✔️ Tool execution complete.")
            
            # === STEP 3: GENERATE FINAL RESPONSE ===
            # We ask the LLM to present the result in a friendly way.
            final_prompt = f"""
            Human: A user asked the following question: "{user_request}"
            We used a tool and got this result: "{tool_result}"
            Please present this result to the user in a clear and friendly final answer.

            Assistant:
            """
            final_body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": final_prompt}],
                "temperature": 0.7
            })
            final_response = self.client.invoke_model(body=final_body, modelId=self.model_id)
            final_response_body = json.loads(final_response.get('body').read())
            final_answer = final_response_body['content'][0]['text']
            return final_answer

        elif tool_name == "no_tool_found":
            return "I'm sorry, I don't have a tool that can help with that. I can summarize, analyze sentiment, or translate text to French."
        else:
            return f"I'm sorry, I selected an invalid tool ('{tool_name}'). Please try rephrasing your request."


# ==============================================================================
# --- INTERACTIVE MAIN FUNCTION ---
# ==============================================================================

def main():
    print("🚀 Intelligent Agentic AI Application - Initializing...")
    orchestrator = LLMOrchestratorAgent(bedrock_runtime)
    
    print("\n" + "="*60)
    print("🤖 Welcome! I am an intelligent AI assistant.")
    print("   Tell me what you need in plain English.")
    print("   For example:")
    print("     - 'Give me the short version of this article: [paste article]'")
    print("     - 'How does this review sound? [paste review]'")
    print("     - 'Can you say 'hello world' in French?'")
    print("\nType 'exit' or 'quit' to end the session.")
    print("="*60)

    while True:
        try:
            user_input = input("\n▶️  You: ")
            if user_input.lower() in ['exit', 'quit']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue

            response = orchestrator.process_request(user_input)

            print("\n" + "-"*60)
            print(f"🤖 AI: {response}")
            print("-"*60)

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    main()