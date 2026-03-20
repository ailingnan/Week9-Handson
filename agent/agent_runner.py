"""
agent_runner.py
---------------
Core execution loop for the Snowflake Agent.
Handles user input -> Groq LLM routing -> Tool Execution -> Final Response.
Provides multi-step reasoning traces and robust error handling.
"""

import sys
import os
import time
import json
import logging

# Add parent dir to path so we can import app and agent modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app.core_services as cs
from agent.tools import TOOL_MAP
from agent.tool_schemas import ALL_TOOLS
from core.config import SETTINGS
from core.logger import get_logger

logger = get_logger("agent_runner")

SYSTEM_PROMPT = """You are a helpful, intelligent agent assisting UMKC (University of Missouri-Kansas City) students and staff with policy questions and pipeline analytics.
You have access to a set of specialized tools. 
When the user asks a question, determine which tool (if any) is best suited to find the answer.
If you need to retrieve policy information, ALWAYS use search_policy.
If you need to simulate different phrasing for queries to see which performs better, use simulate_whatif.
If you need to check the historical evaluation metrics of the pipeline, use get_eval_metrics.

If the context returned from a tool doesn't contain enough information to answer the question, clearly state that.
If you don't need a tool (for example, just a pleasantry), you can reply directly.
Ensure your answers are concise, accurate, and helpful based on the retrieved evidence."""

def run_agent(user_query: str) -> dict:
    """
    Executes the agent workflow:
    1. Send user query + tool schemas to Groq.
    2. Check if a tool needs to be called.
    3. Execute the tool, gather results.
    4. Pass results back to Groq for final answer generation.
    """
    trace = []
    evidence = []
    
    trace.append({"step": "Received user query", "content": user_query})
    
    # 1. Initialize Client
    client = cs.get_groq_client()
    if not client:
        return {
            "answer": "⚠️ Error: GROQ_API_KEY missing or invalid. Agent cannot run.",
            "trace": trace,
            "evidence": evidence
        }

    # 2. Initial Message
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]
    
    trace.append({"step": "Calling LLM for intent routing", "content": "Checking if tools are needed..."})

    try:
        t0 = time.time()
        # 3. First LLM Call (Routing)
        response = client.chat.completions.create(
            model=SETTINGS.get("llm_model", "llama-3.1-8b-instant"),
            messages=messages,
            tools=ALL_TOOLS,
            tool_choice="auto",
            max_tokens=1024,
            temperature=0.1
        )
        ms = int((time.time() - t0) * 1000)
        trace.append({"step": "LLM responded", "latency_ms": ms})
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # 4. Handle Tool Calls
        if tool_calls:
            messages.append(response_message)
            
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                
                trace.append({
                    "step": f"Executing tool: {func_name}", 
                    "args": func_args
                })
                
                # Execute mapped function safely
                if func_name in TOOL_MAP:
                    try:
                        t1 = time.time()
                        func_result = TOOL_MAP[func_name](**func_args)
                        exec_ms = int((time.time() - t1) * 1000)
                        
                        trace.append({
                            "step": f"Tool '{func_name}' completed", 
                            "latency_ms": exec_ms,
                            "status": "success"
                        })
                        
                        # Save chunks to evidence separately if present
                        if "chunks" in func_result:
                            evidence.extend(func_result["chunks"])
                            
                        # Append tool response back to messages
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": func_name,
                            "content": json.dumps(func_result)
                        })
                    except Exception as e:
                        error_msg = f"Error executing {func_name}: {e}"
                        trace.append({"step": f"Tool '{func_name}' failed", "error": error_msg})
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": func_name,
                            "content": json.dumps({"status": "error", "message": error_msg})
                        })
                else:
                    trace.append({"step": "Error", "content": f"Unknown tool: {func_name}"})
            
            # 5. Second LLM Call (Final Answer Generation based on tool results)
            trace.append({"step": "Generating final answer", "content": "Synthesizing tool results..."})
            t2 = time.time()
            final_response = client.chat.completions.create(
                model=SETTINGS.get("llm_model", "llama-3.1-8b-instant"),
                messages=messages,
                max_tokens=1024,
                temperature=0.2
            )
            final_ms = int((time.time() - t2) * 1000)
            trace.append({"step": "Answer generated", "latency_ms": final_ms})
            
            final_answer = final_response.choices[0].message.content.strip()
            
            return {
                "answer": final_answer,
                "trace": trace,
                "evidence": evidence
            }
        else:
            # No tools needed, just return the direct answer
            trace.append({"step": "No tools required", "content": "Direct response generated."})
            return {
                "answer": response_message.content.strip(),
                "trace": trace,
                "evidence": evidence
            }
            
    except Exception as e:
        err = f"Agent execution failed: {e}"
        logger.error(err)
        trace.append({"step": "Agent Error", "content": err})
        return {
            "answer": f"⚠️ {err}",
            "trace": trace,
            "evidence": evidence
        }
