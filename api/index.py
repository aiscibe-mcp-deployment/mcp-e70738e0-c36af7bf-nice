"""Vercel serverless handler for MCP server."""
import os
import sys

# Add the app directory to sys.path so we can import mcp_server
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, Response

# CORS middleware to handle all origins
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

try:
    from mcp_server import mcp
    
    # Get the SSE app from FastMCP
    if hasattr(mcp, 'sse_app'):
        mcp_app = mcp.sse_app()
    elif hasattr(mcp, '_sse_app'):
        mcp_app = mcp._sse_app
    elif hasattr(mcp, 'app'):
        mcp_app = mcp.app
    else:
        mcp_app = None
    
    async def health(request):
        return JSONResponse({
            "status": "ok",
            "server": "Nice MCP Server",
            "endpoints": ["/", "/health", "/sse", "/messages"]
        })
    
    async def sse_handler(request):
        """Handle SSE connections by delegating to the MCP app."""
        if mcp_app:
            # Forward to MCP app
            return await mcp_app(request.scope, request.receive, request._send)
        return JSONResponse({"error": "MCP app not initialized"}, status_code=500)
    
    # Create routes
    routes = [
        Route("/", health),
        Route("/health", health),
    ]
    
    # Mount MCP app if available
    if mcp_app:
        routes.append(Mount("/", app=mcp_app))
    
    app = Starlette(routes=routes, middleware=middleware)

except Exception as e:
    import traceback
    error_msg = f"Initialization Error: {str(e)}\n{traceback.format_exc()}"
    
    async def error_handler(request):
        return JSONResponse({
            "status": "error", 
            "message": "Server failed to start", 
            "details": str(e)
        }, status_code=500)
    
    app = Starlette(
        routes=[Route("/{path:path}", error_handler)],
        middleware=middleware
    )
