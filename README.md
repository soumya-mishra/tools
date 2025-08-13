## MCP
- This is a model context protocol(MCP) server creation method.
- The FastMCP implementation automatically handles tool registration and execution with just the @mcp.tool() decorators.

1. summarize_text - Uses your SummarizationAgent

2. analyze_sentiment - Uses your SentimentAgent

3. translate_to_french - Uses your TranslationAgent

## Make the server stateless:
mcp = FastMCP("Demo",stateless_http=True)

So that we can access the server in postman

- url: http://127.0.0.1:8000/mcp

- Body : raw

{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "summarize_text",
                "arguments": {"text":"summarise this content:Bedrock is the solid rock that underlies looser surface material. An exposed portion of bedrock is often called an outcrop. The various kinds of broken and weathered rock material, such as soil and subsoil, that may overlie the bedrock are known as regolith."}
            }
        }

header: application/json
Accept: application/json, text/event-stream

<img width="468" height="301" alt="image" src="https://github.com/user-attachments/assets/4bc8b9bc-6f1c-403d-a59b-89a9930bd0b0" />

