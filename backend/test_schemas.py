"""Test tool schema generation."""

from app.agents.tools import SearchCandidatesInput, GetCandidateDetailsInput
import json

print("=" * 60)
print("Testing Tool Schema Generation")
print("=" * 60)

# Test SearchCandidatesInput
print("\n1. SearchCandidatesInput:")
print(f"   Class: {SearchCandidatesInput}")
print(f"   Has schema method: {hasattr(SearchCandidatesInput, 'schema')}")
print(f"   Has model_json_schema: {hasattr(SearchCandidatesInput, 'model_json_schema')}")

if hasattr(SearchCandidatesInput, 'schema'):
    schema = SearchCandidatesInput.schema()
    print(f"\n   Schema (old method):")
    print(json.dumps(schema, indent=4))

if hasattr(SearchCandidatesInput, 'model_json_schema'):
    schema = SearchCandidatesInput.model_json_schema()
    print(f"\n   Schema (new method):")
    print(json.dumps(schema, indent=4))

# Test GetCandidateDetailsInput  
print("\n2. GetCandidateDetailsInput:")
if hasattr(GetCandidateDetailsInput, 'model_json_schema'):
    schema = GetCandidateDetailsInput.model_json_schema()
    print(json.dumps(schema, indent=4))

print("\n" + "=" * 60)
