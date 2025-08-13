#!/usr/bin/env python3
from mcp.server.fastmcp import FastMCP
from tools import SummarizationAgent, SentimentAgent, TranslationAgent

mcp = FastMCP("bedrock-tools",stateless_http=True)

# Initialize tool instances
summarization_agent = SummarizationAgent()
sentiment_agent = SentimentAgent()
translation_agent = TranslationAgent()

@mcp.tool()
def summarize_text(text: str) -> str:
    """Create a concise summary of a long piece of text"""
    return summarization_agent.execute(text)

@mcp.tool()
def analyze_sentiment(text: str) -> str:
    """Determine the sentiment (POSITIVE, NEGATIVE, or NEUTRAL) of text"""
    return sentiment_agent.execute(text)

@mcp.tool()
def translate_to_french(text: str) -> str:
    """Translate English text into French"""
    return translation_agent.execute(text)

if __name__ == "__main__":
    
    mcp.run(transport="streamable-http")