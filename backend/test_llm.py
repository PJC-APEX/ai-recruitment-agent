"""Quick test to verify Azure OpenAI LLM is working."""

import asyncio
import sys
from app.config import get_settings
from app.llm.llm_client import LLMClient


async def test_llm():
    """Test LLM connectivity and response."""
    print("=" * 60)
    print("Testing Azure OpenAI LLM Connection")
    print("=" * 60)
    
    # Get settings
    settings = get_settings()
    print(f"\n✓ Configuration loaded:")
    print(f"  - Endpoint: {settings.azure_openai_endpoint}")
    print(f"  - Model: {settings.azure_openai_model}")
    print(f"  - API Version: {settings.azure_openai_api_version}")
    
    try:
        # Initialize LLM client
        print(f"\n⏳ Initializing LLM client...")
        llm_client = LLMClient(
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            model=settings.azure_openai_model,
            api_version=settings.azure_openai_api_version,
            temperature=0.7
        )
        print("✓ LLM client initialized successfully")
        
        # Test simple query
        print(f"\n⏳ Sending test query to Azure OpenAI...")
        test_query = "Say 'Hello! I am working correctly.' in exactly 5 words."
        
        response = await llm_client.generate_response(
            prompt=test_query,
            max_tokens=50
        )
        
        print(f"\n✅ SUCCESS! LLM is working!\n")
        print(f"Query: {test_query}")
        print(f"Response: {response}\n")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: LLM test failed!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}\n")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_llm())
    sys.exit(0 if result else 1)
