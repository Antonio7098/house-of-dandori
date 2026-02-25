import os
import json
from flask import Blueprint, request, jsonify, Response
from openai import OpenAI

from src.core.auth import auth_service
from src.core.errors import handle_exception, BadRequestError
from src.core.logging import api_logger
from src.services.graph_rag_service import GraphRAGService
import os

chat_bp = Blueprint("chat", __name__)

# Initialize OpenRouter client
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY or "dummy_key_for_testing",
)

def get_graph_rag_service():
    try:
        from src.services.graph_rag_service import GraphRAGService
        return GraphRAGService()
    except Exception as e:
        api_logger.log_error(e, {"message": "Failed to initialize GraphRAGService"})
        return None

# OpenRouter model
MODEL = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """You are the Dandori Assistant, a helpful, whimsical, and friendly AI for the School of Dandori. 
The School of Dandori teaches wellbeing and encourages adults to reconnect with their younger, carefree days through evening and weekend classes.
Your goal is to help users discover the perfect courses for their interests, location, and budget.

You have access to a semantic search tool that lets you find relevant courses based on user queries.
When a user asks for recommendations, you should:
1. Use the search tool to find relevant courses.
2. Present the courses in a friendly, enthusiastic way.
3. Suggest the user click on the course artifacts that appear in the UI.

Keep your tone light, whimsical, and encouraging. Focus on wellbeing, joy, and learning.
"""

def search_courses(query: str, filters: dict = None) -> list:
    """Tool function to search for courses using GraphRAG."""
    try:
        if not filters:
            filters = {}
            
        graph_rag_service = get_graph_rag_service()
        if graph_rag_service:
            results = graph_rag_service.search(query, filters=filters, limit=3)
            return results
        else:
            # Fallback to standard search if GraphRAG fails
            from src.services.rag_service import rag_service
            results = rag_service.search(query, filters=filters, limit=3)
            return results
    except Exception as e:
        api_logger.log_error(e, {"query": query})
        return []

# Define the tools available to the model
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_courses",
            "description": "Search for courses offered by the School of Dandori based on a query and optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (e.g., 'pottery', 'relaxing weekend class', 'painting')",
                    },
                    "filters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city or location (e.g., 'London', 'Manchester')",
                            },
                            "course_type": {
                                "type": "string",
                                "description": "The type of course (e.g., 'Workshop', 'Course')",
                            },
                            "max_price": {
                                "type": "number",
                                "description": "The maximum price in pounds",
                            }
                        },
                    }
                },
                "required": ["query"],
            },
        }
    }
]

@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    """Basic chat endpoint that returns a complete response."""
    data = request.get_json()
    if not data or "message" not in data:
        error_dict, status_code = handle_exception(BadRequestError("Message required"))
        return jsonify(error_dict), status_code

    user_message = data["message"]
    history = data.get("history", [])
    
    # Format messages for the API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add history (limit to last 10 messages to save tokens)
    for msg in history[-10:]:
        role = "assistant" if msg.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": msg.get("content", "")})
        
    # Add current message
    messages.append({"role": "user", "content": user_message})

    try:
        # First call to see if the model wants to use tools
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        artifacts = []
        
        # If model wants to call tools
        if tool_calls:
            messages.append(response_message)
            
            for tool_call in tool_calls:
                if tool_call.function.name == "search_courses":
                    function_args = json.loads(tool_call.function.arguments)
                    query = function_args.get("query")
                    filters = function_args.get("filters", {})
                    
                    # Execute search
                    search_results = search_courses(query, filters)
                    artifacts.extend(search_results)
                    
                    # Create a summary of results for the model
                    results_summary = f"Found {len(search_results)} courses:\n"
                    for i, course in enumerate(search_results):
                        results_summary += f"{i+1}. {course.get('title')} by {course.get('instructor')} - £{course.get('cost', 'Free')} in {course.get('location')}\n"
                    
                    # Add tool response to messages
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": "search_courses",
                        "content": results_summary,
                    })
            
            # Second call to get final response with tool results
            second_response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
            )
            final_content = second_response.choices[0].message.content
        else:
            final_content = response_message.content
            
        return jsonify({
            "message": final_content,
            "artifacts": artifacts
        })
        
    except Exception as e:
        api_logger.log_error(e, {"message": user_message})
        return jsonify({
            "error": "Failed to process chat message",
            "message": "I'm sorry, I'm having a little trouble connecting right now. Please try again in a moment!"
        }), 500

@chat_bp.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """Streaming chat endpoint for better UX."""
    data = request.get_json()
    if not data or "message" not in data:
        error_dict, status_code = handle_exception(BadRequestError("Message required"))
        return jsonify(error_dict), status_code

    user_message = data["message"]
    history = data.get("history", [])
    
    # Format messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-10:]:
        role = "assistant" if msg.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_message})

    def generate():
        try:
            # First call (non-streaming) to handle tools
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            artifacts = []
            
            if tool_calls:
                messages.append(response_message)
                
                for tool_call in tool_calls:
                    if tool_call.function.name == "search_courses":
                        function_args = json.loads(tool_call.function.arguments)
                        query = function_args.get("query")
                        filters = function_args.get("filters", {})
                        
                        search_results = search_courses(query, filters)
                        artifacts.extend(search_results)
                        
                        # Send artifacts immediately
                        yield f"data: {json.dumps({'artifacts': artifacts})}\n\n"
                        
                        results_summary = f"Found {len(search_results)} courses:\n"
                        for i, course in enumerate(search_results):
                            results_summary += f"{i+1}. {course.get('title')} by {course.get('instructor')} - £{course.get('cost', 'Free')} in {course.get('location')}\n"
                        
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "search_courses",
                            "content": results_summary,
                        })
                
                # Stream the final response
                stream = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    stream=True,
                )
            else:
                # If no tools, just stream the response from a new call
                stream = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    stream=True,
                )
                
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
                    
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            api_logger.log_error(e, {"message": user_message})
            error_msg = "I'm sorry, I'm having a little trouble connecting right now. Please try again in a moment!"
            yield f"data: {json.dumps({'error': True, 'content': error_msg})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")
