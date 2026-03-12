"""Test agent's tool schema generation."""

import asyncio
from app.dependencies import get_retrieval_pipeline
from app.agents.tools import (
    create_search_candidates_tool,
    create_list_all_candidates_tool,
    create_get_candidate_details_tool
)
import json


async def test_agent_schemas():
    print("=" * 60)
    print("Testing Agent Tool Schema Generation")
    print("=" * 60)
    
    # Create retrieval pipeline
    pipeline = await get_retrieval_pipeline()
    
    # Create tools
    tools = [
        create_search_candidates_tool(pipeline),
        create_list_all_candidates_tool(pipeline),
        create_get_candidate_details_tool(pipeline)
    ]
    
    # Test schema extraction like the agent does
    for tool in tools:
        print(f"\n{tool.name}:")
        print(f"  Description: {tool.description[:80]}...")
        print(f"  Has args_schema: {hasattr(tool, 'args_schema')}")
        print(f"  args_schema value: {tool.args_schema}")
        
        if hasattr(tool, 'args_schema') and tool.args_schema:
            if hasattr(tool.args_schema, 'schema'):
                tool_schema = tool.args_schema.schema()
                print(f"\n  Generated OpenAI function schema:")
                schema = {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool_schema.get('properties', {}),
                        "required": tool_schema.get('required', [])
                    }
                }
                print(json.dumps(schema, indent=4))
        else:
            print("  No args_schema - tool takes no parameters")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_agent_schemas())
