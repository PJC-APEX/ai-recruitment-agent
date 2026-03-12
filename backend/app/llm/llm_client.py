"""LLM client for Azure OpenAI API interactions."""

import logging
import json
from typing import Dict, Any, Optional, List
from openai import AsyncAzureOpenAI
import tiktoken

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with Azure OpenAI LLM."""
    
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model: str = "gpt-4",
        api_version: str = "2024-02-15-preview",
        temperature: float = 0.7
    ):
        """Initialize LLM client.
        
        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            model: Model deployment name
            api_version: Azure OpenAI API version
            temperature: Temperature for generation
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.api_version = api_version
        self.temperature = temperature
        self.client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        self.logger = logger
        
        # Initialize tokenizer
        try:
            self.encoding = tiktoken.encoding_for_model("gpt-4")
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    async def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        max_tokens: int = 2000
    ) -> str:
        """Generate a text response from the LLM.
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        try:
            messages = []
            
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            
            result = response.choices[0].message.content
            self.logger.info(f"Generated response with {len(result)} characters")
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    async def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, str],
        system_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON output from the LLM.
        
        Args:
            prompt: User prompt
            schema: Expected output schema (field: type description)
            system_message: Optional system message
            
        Returns:
            Parsed JSON response
        """
        try:
            schema_str = json.dumps(schema, indent=2)
            
            structured_prompt = f"""{prompt}

You must respond with valid JSON matching this exact schema:
{schema_str}

Respond with ONLY the JSON object, no additional text."""
            
            response_text = await self.generate_response(
                prompt=structured_prompt,
                system_message=system_message or "You are a helpful assistant that responds with valid JSON.",
                max_tokens=2000
            )
            
            # Extract JSON from response
            json_response = self._extract_json(response_text)
            return json_response
            
        except Exception as e:
            self.logger.error(f"Error generating structured output: {str(e)}")
            raise Exception(f"Failed to generate structured output: {str(e)}")
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text response.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Parsed JSON object
        """
        try:
            # Try to parse the entire text as JSON
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON within the text
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = text[start_idx:end_idx + 1]
                return json.loads(json_str)
            
            raise ValueError("No valid JSON found in response")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))
    
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000
    ) -> str:
        """Generate response for chat conversation.
        
        Args:
            messages: List of message dictionaries with role and content
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error in chat response: {str(e)}")
            raise Exception(f"Failed to generate chat response: {str(e)}")
