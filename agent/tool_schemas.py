"""
tool_schemas.py
---------------
JSON Schema definitions for the Agent's tools.
These schemas are passed to Groq/Llama for function calling.
"""

search_policy_schema = {
    "type": "function",
    "function": {
        "name": "search_policy",
        "description": "Retrieves University policy information from Snowflake based on a given query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query or question to retrieve policy context for."
                },
                "top_k": {
                    "type": "integer",
                    "description": "Optional number of chunks to retrieve. Defaults to 5."
                }
            },
            "required": ["query"]
        }
    }
}

simulate_whatif_schema = {
    "type": "function",
    "function": {
        "name": "simulate_whatif",
        "description": "Runs a what-if simulation across multiple alternative queries simultaneously to find the best phrasing.",
        "parameters": {
            "type": "object",
            "properties": {
                "scenarios": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of query variations to simulate."
                },
                "top_k": {
                    "type": "integer",
                    "description": "Optional number of chunks to retrieve per scenario. Defaults to 5."
                }
            },
            "required": ["scenarios"]
        }
    }
}

get_eval_metrics_schema = {
    "type": "function",
    "function": {
        "name": "get_eval_metrics",
        "description": "Retrieves the historical evaluation metrics or performance summary of the RAG pipeline.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "boolean",
                    "description": "If true, returns aggregated summary by version. If false, returns recent history."
                }
            },
            "required": []
        }
    }
}

# The list of all schemas for the Groq client
ALL_TOOLS = [search_policy_schema, simulate_whatif_schema, get_eval_metrics_schema]
