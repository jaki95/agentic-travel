# Langfuse Tracing Setup for Flight Agent

This document explains how to set up and use Langfuse tracing with your flight agent to monitor and debug AI agent interactions.

## Overview

The flight agent now includes comprehensive tracing using [Langfuse](https://langfuse.com/) via OpenTelemetry. This provides:

- **Complete visibility** into agent execution flows
- **Performance monitoring** of MCP server interactions
- **Error tracking** and debugging capabilities
- **Cost tracking** for OpenAI API calls
- **Query analysis** and optimization insights

## Setup Instructions

### 1. Install Dependencies

The required dependencies are already included in `pyproject.toml`:

```toml
dependencies = [
    "langfuse>=2.60.7",
    "opentelemetry-sdk>=1.33.1", 
    "opentelemetry-exporter-otlp>=1.33.1",
    "openinference-instrumentation-agno>=0.1.4",
]
```

### 2. Configure Environment Variables

Add the following to your `.env` file:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# Langfuse Configuration for Tracing
# Get these from your Langfuse project settings: https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here

# Langfuse Host (choose your region)
LANGFUSE_HOST=https://cloud.langfuse.com  # EU region
# LANGFUSE_HOST=https://us.cloud.langfuse.com  # US region
```

### 3. Get Langfuse Credentials

1. Sign up at [Langfuse Cloud](https://cloud.langfuse.com) (free tier available)
2. Create a new project
3. Go to Project Settings → API Keys
4. Copy your Public Key and Secret Key

## How It Works

### Automatic Instrumentation

The tracing is automatically initialized when the `flight_service` module is imported:

```python
from observability import setup_tracing, get_tracer

# Initialize tracing on module import
setup_tracing()
tracer = get_tracer(__name__)
```

### Manual Spans

Key operations are wrapped in custom spans for detailed observability:

- `flight_search` - Main search operation
- `mcp_agent_execution` - Agent execution with MCP tools
- `flight_search_sync` - Synchronous wrapper

### Span Attributes

Each span includes relevant metadata:

```python
span.set_attribute("flight.query", query)
span.set_attribute("service.name", "flight_service")
span.set_attribute("agent.model", "gpt-4o-mini")
span.set_attribute("response.length", len(result))
```

## Testing the Setup

Run the test script to verify tracing is working:

```bash
cd backend
python test_tracing.py
```

This will:
1. Execute sample flight searches
2. Send traces to Langfuse
3. Display results in the console

## Viewing Traces in Langfuse

After running your flight agent:

1. Go to your Langfuse dashboard
2. Navigate to the "Traces" section
3. You'll see traces for each flight search operation

### What You'll See

- **Trace Timeline**: Complete execution flow from query to response
- **Span Details**: Individual operations (MCP server calls, agent execution)
- **Attributes**: Query text, model used, response length, etc.
- **Error Information**: Stack traces and error messages for failed operations
- **Performance Metrics**: Execution times for each component

## Trace Structure

```
flight_search (root span)
├── Attributes: flight.query, service.name
├── mcp_agent_execution
│   ├── Attributes: agent.model, agent.tools, response.length
│   └── OpenAI API calls (auto-instrumented by Agno)
└── Error handling (if applicable)
```

## Benefits

### For Development
- **Debug agent behavior**: See exactly what the agent is doing
- **Optimize performance**: Identify slow operations
- **Track errors**: Get detailed error information with context

### For Production
- **Monitor usage**: Track API costs and usage patterns
- **Quality assurance**: Monitor response quality and success rates
- **User analytics**: Understand common query patterns

## Troubleshooting

### Tracing Not Working

1. **Check environment variables**: Ensure all Langfuse credentials are set
2. **Verify network access**: Ensure your environment can reach Langfuse
3. **Check logs**: Look for tracing setup messages in the console

### Missing Traces

1. **Delayed appearance**: Traces may take a few seconds to appear in Langfuse
2. **Sampling**: Check if sampling is enabled (disabled by default)
3. **Network issues**: Verify OTLP endpoint connectivity

### Common Issues

```python
# If you see this warning:
# "Langfuse environment variables not fully configured. Tracing will be disabled."

# Check that all required variables are set:
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

## Advanced Configuration

### Custom Spans

Add custom spans for specific operations:

```python
from observability import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("custom.attribute", "value")
    # Your code here
```

### Error Tracking

Errors are automatically captured with context:

```python
except Exception as e:
    span.set_attribute("error", True)
    span.set_attribute("error.type", type(e).__name__)
    span.set_attribute("error.message", str(e))
```

## Resources

- [Langfuse Documentation](https://langfuse.com/docs)
- [Agno Integration Guide](https://langfuse.com/docs/integrations/other/agno-agents)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) 