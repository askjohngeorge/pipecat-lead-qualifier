# Guide: Implementing Page Navigation Events in RTVI

This guide explains how to implement server-triggered page navigation in your RTVI bot system, allowing the server to direct Next.js client-side navigation.

## Part 1: Server-Side Implementation (Python)

### Step 1: Define Navigation Message Types
Add these classes to your bot file (e.g., `bot-openai.py`):

```python
from typing import Literal, Optional
from pydantic import BaseModel

class NavigationEventData(BaseModel):
    """Data structure for navigation events."""
    path: str  # The path to navigate to (e.g., "/dashboard", "/settings")
    query: Optional[dict] = None  # Optional query parameters
    replace: bool = False  # Whether to replace current history entry

class NavigationEventMessage(BaseModel):
    """RTVI message for navigation events."""
    label: Literal["rtvi-ai"] = "rtvi-ai"
    type: Literal["navigation-request"] = "navigation-request"
    data: NavigationEventData
```

### Step 2: Add Navigation Method to Your Bot
Add this method to your bot class:

```python
class OpenAIBot(RTVIProcessor):
    async def request_navigation(
        self, 
        path: str, 
        query: Optional[dict] = None, 
        replace: bool = False
    ):
        """Request the client to navigate to a specific page.
        
        Args:
            path: The path to navigate to (e.g., "/dashboard")
            query: Optional query parameters (e.g., {"id": "123"})
            replace: If True, replace current history entry instead of pushing
        """
        message = NavigationEventMessage(
            data=NavigationEventData(
                path=path,
                query=query,
                replace=replace
            )
        )
        await self._push_transport_message(message)

    # Example usage in your bot's methods:
    async def handle_dashboard_request(self):
        # Process something...
        await self.request_navigation("/dashboard", {"view": "analytics"})
```

## Part 2: Client-Side Implementation (Next.js/TypeScript)

### Step 1: Define TypeScript Types
Create `types/navigation.ts`:

```typescript
interface NavigationEventData {
  path: string;
  query?: Record<string, string>;
  replace?: boolean;
}

interface NavigationEventMessage {
  label: 'rtvi-ai';
  type: 'navigation-request';
  data: NavigationEventData;
}
```

### Step 2: Create Navigation Handler Component
Create `components/NavigationHandler.tsx`:

```typescript
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useRTVIClientEvent } from '../hooks/useRTVIClientEvent';

export function NavigationHandler() {
  const router = useRouter();

  useRTVIClientEvent("navigation-request", async (message) => {
    const { path, query, replace } = message.data;
    
    try {
      // Convert query object to URLSearchParams format if present
      const queryString = query 
        ? '?' + new URLSearchParams(query).toString() 
        : '';
        
      // Perform the navigation
      if (replace) {
        await router.replace(path + queryString);
      } else {
        await router.push(path + queryString);
      }
      
      console.log(`Navigation ${replace ? 'replaced' : 'pushed'} to: ${path}${queryString}`);
    } catch (error) {
      console.error('Navigation failed:', error);
    }
  });

  // This component doesn't render anything
  return null;
}
```

### Step 3: Add Navigation Handler to Your App
In your `pages/_app.tsx`:

```typescript
import type { AppProps } from 'next/app';
import { NavigationHandler } from '../components/NavigationHandler';

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <>
      <NavigationHandler />
      <Component {...pageProps} />
    </>
  );
}

export default MyApp;
```

## Usage Examples

### Server-Side (Python)
```python
# Navigate to dashboard
await bot.request_navigation("/dashboard")

# Navigate with query parameters
await bot.request_navigation(
    "/products", 
    query={"category": "electronics", "sort": "price"}
)

# Replace current history entry (user can't go back)
await bot.request_navigation("/login", replace=True)
```

### Error Handling

#### Server-Side
```python
async def safe_navigate(self, path: str, query: Optional[dict] = None):
    try:
        await self.request_navigation(path, query)
    except Exception as e:
        await self.send_error(f"Navigation failed: {str(e)}")
        # Optionally fall back to a safe page
        await self.request_navigation("/error")
```

#### Client-Side
```typescript
useRTVIClientEvent("navigation-request", async (message) => {
  try {
    const { path, query, replace } = message.data;
    
    // Validate path before navigation
    if (!path.startsWith('/')) {
      throw new Error('Invalid path format');
    }
    
    // Perform navigation...
    await router.push(path);
    
  } catch (error) {
    console.error('Navigation error:', error);
    // Optionally show error UI or navigate to error page
    router.push('/error');
  }
});
```

## Best Practices

1. **Path Validation**:
   - Always validate paths on both server and client
   - Ensure paths start with "/"
   - Consider maintaining a list of valid paths

2. **Error Handling**:
   - Handle navigation failures gracefully
   - Provide feedback to users
   - Log errors for debugging

3. **History Management**:
   - Use `replace: true` for login/logout flows
   - Preserve history for normal navigation
   - Consider user experience when managing browser history

4. **Query Parameters**:
   - Sanitize query parameters
   - Use TypeScript types for type safety
   - Consider URL length limitations

5. **Security**:
   - Validate navigation requests
   - Check user permissions before navigation
   - Sanitize paths and query parameters

## Testing

### Server-Side Tests
```python
async def test_navigation():
    bot = OpenAIBot()
    
    # Test basic navigation
    await bot.request_navigation("/dashboard")
    
    # Test query parameters
    await bot.request_navigation("/search", {"q": "test"})
    
    # Test history replacement
    await bot.request_navigation("/login", replace=True)
```

### Client-Side Tests
```typescript
import { render, act } from '@testing-library/react';
import { NavigationHandler } from './NavigationHandler';

describe('NavigationHandler', () => {
  it('handles navigation requests', async () => {
    const mockRouter = {
      push: jest.fn(),
      replace: jest.fn(),
    };
    
    // Mock useRouter
    jest.mock('next/router', () => ({
      useRouter: () => mockRouter,
    }));
    
    render(<NavigationHandler />);
    
    // Simulate navigation event
    await act(async () => {
      // Simulate RTVI event...
    });
    
    expect(mockRouter.push).toHaveBeenCalledWith('/dashboard');
  });
});
```

## Troubleshooting

Common issues and solutions:

1. **Navigation Not Working**:
   - Check RTVI connection status
   - Verify event type matches exactly
   - Check console for errors
   - Verify path format

2. **History Issues**:
   - Check `replace` flag usage
   - Verify browser history state
   - Test back/forward navigation

3. **Query Parameter Problems**:
   - Check parameter encoding
   - Verify URL length
   - Test special characters

Need help? Contact the RTVI team for support.
