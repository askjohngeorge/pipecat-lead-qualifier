# Integrating External APIs with Static Flows

This guide explains how to integrate external APIs with static flows in Pipecat, using the movie explorer example as a reference.

## Overview

Adding external API integration to your flows involves several key steps:

1. API Client Setup
2. Type Definitions
3. Function Handlers
4. Flow Configuration Integration

## 1. API Client Setup

Create a dedicated API client class to handle all API interactions:

```python
class APIClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    async def make_request(self, session: aiohttp.ClientSession, endpoint: str, params: dict):
        # Implement common request handling
        pass
```

## 2. Type Definitions

Define clear types for your API responses and flow results:

```python
class APIResponse(TypedDict):
    field1: str
    field2: int

class FlowAPIResult(FlowResult):
    data: APIResponse
```

## 3. Function Handlers

Create handler functions that:
- Take FlowArgs as input
- Return Union[SuccessResult, ErrorResult]
- Handle API calls and errors
- Transform API responses into flow results

Example pattern:
```python
async def api_handler(args: FlowArgs) -> Union[SuccessResult, ErrorResult]:
    async with aiohttp.ClientSession() as session:
        try:
            result = await api_client.make_request(session, ...)
            return SuccessResult(data=result)
        except Exception as e:
            return ErrorResult(status="error", error=str(e))
```

## 4. Flow Configuration Integration

Add your handlers to the flow configuration:

```python
flow_config: FlowConfig = {
    "nodes": {
        "node_name": {
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "api_function",
                        "handler": api_handler,
                        "description": "Description of API call",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                # Define required parameters
                            }
                        }
                    }
                }
            ]
        }
    }
}
```

## Best Practices

1. **Error Handling**
   - Always wrap API calls in try/except blocks
   - Return typed error results
   - Log errors appropriately

2. **Type Safety**
   - Use TypedDict for API responses
   - Define clear return types for handlers
   - Validate API responses

3. **Session Management**
   - Use aiohttp.ClientSession for HTTP requests
   - Handle session lifecycle properly
   - Consider connection pooling for performance

4. **Configuration**
   - Store API keys in environment variables
   - Use configuration objects for API settings
   - Document required environment variables

## Example Implementation

The movie explorer example demonstrates these concepts with the TMDB API:

1. **API Client**: `TMDBApi` class handles all TMDB API interactions
2. **Types**: `MovieBasic`, `MovieDetails`, etc. define response structures
3. **Handlers**: `get_movies()`, `get_movie_details()`, etc. implement the function pattern
4. **Flow Integration**: Handlers are integrated into the flow configuration with appropriate transitions

For a complete implementation example, refer to the movie explorer code in the repository. 