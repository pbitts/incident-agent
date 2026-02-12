# 🚨 Incident Agent

An intelligent, autonomous incident response agent built with LangChain that automatically processes monitoring alerts, manages tickets, and sends notifications.

## Overview

This project demonstrates an AI-powered incident management system that receives webhooks from monitoring platforms (Zabbix, AppDynamics), intelligently processes them, and takes appropriate actions like creating/resolving tickets and sending notifications.

The agent uses:
- **LangChain** for agent orchestration and tool execution
- **Groq** for fast LLM inference
- **LangSmith** for observability and tracing
- **MongoDB** for persistent storage

## Features

✅ **Automatic Incident Detection** - Processes incoming webhooks from monitoring platforms  
✅ **Intelligent Decision Making** - Uses LLM to analyze incidents and determine appropriate actions  
✅ **Ticket Management** - Creates and resolves tickets automatically  
✅ **Notification System** - Sends email alerts for incidents  
✅ **Event Persistence** - Stores all incident data and actions in MongoDB  
✅ **Multi-Platform Support** - Handles Zabbix and AppDynamics monitoring systems  
✅ **Structured Output** - Returns parsed, structured responses

## Architecture

```
Webhook → FastAPI → LangChain Agent → Tools → MongoDB
                         ↓
                    Groq LLM (gpt-oss-120b)
                         ↓
                   LangSmith Tracing
```

The agent follows this workflow:

1. **Receive** webhook payload from monitoring platform
2. **Persist** raw payload to MongoDB
3. **Analyze** incident using LLM
4. **Execute** appropriate tools (create/resolve ticket, notify)
5. **Persist** all actions taken
6. **Return** structured summary

## Prerequisites

- Docker & Docker Compose
- Groq API key ([get one here](https://console.groq.com))
- LangSmith API key ([get one here](https://smith.langchain.com))

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/pbitts/incident-agent
cd incident-agent
```

### 2. Configure environment variables

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```env
GROQ_API_KEY="your_groq_api_key_here"
LANGSMITH_TRACING="true"
LANGSMITH_API_KEY="your_langsmith_api_key_here"
LANGSMITH_PROJECT="incident-agent"
MONGO_URI="mongodb://root:changeme@localhost:27017/"
MONGO_DB_NAME="incident_agent"
```

### 3. Start the services

```bash
docker compose up -d
```

This will start:
- MongoDB on port 27017
- Incident Agent API on port 8000

### 4. Test the webhook

Send a test incident:

```bash
curl -X 'POST' \
  'http://localhost:8000/webhook' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "incident_id": 6,
  "status": "PROBLEM",
  "severity": "high",
  "monitoring_platform": "zabbix",
  "trigger": "memory_utilization"
}'
```

Expected response:

```json
{
  "event_type": "ticket_created",
  "ticket_id": "240",
  "comment": "Detailed comment about memory utilization problem (severity high) with title 'Incident 6 - memory_utilization problem'.",
  "thought_process": "Parsed the incident summary, identified that a ticket was created with ID 240..."
}
```

## Configuration

### Model Settings (config.py)

```python
MODEL_NAME = "openai/gpt-oss-120b"  # Groq model
MODEL_TEMPERATURE = 0.1              # Low temperature for consistent responses
MODEL_MAX_TOKENS = None              # No limit
```

### Status Mapping

The agent recognizes different status keywords for each platform:

**Zabbix - Problem Status:**
- `problem`, `PROBLEM`, `Problem`
- `incident`, `INCIDENT`, `Incident`

**Zabbix - Resolved Status:**
- `ok`, `Ok`, `OK`
- `resolved`, `Resolved`, `RESOLVED`

**AppDynamics - Problem Status:**
- `falha`, `Falha`, `FALHA`

**AppDynamics - Resolved Status:**
- `resolução`, `Resolução`, `RESOLUÇÃO`

## How It Works

### Incident Creation Flow

1. Webhook receives payload with `status: "PROBLEM"`
2. Agent persists payload to MongoDB
3. Agent calls `create_ticket` tool
4. Agent calls `notify` tool to send email
5. Both actions are persisted in the `actions` array
6. Structured response is returned

### Incident Resolution Flow

1. Webhook receives payload with `status: "RESOLVED"`
2. Agent retrieves existing ticket using `find_ticket_by_incident`
3. Agent calls `resolve_ticket` tool
4. Agent calls `notify` tool
5. All actions are persisted
6. Structured response is returned

## Document Schema

Each incident is stored in MongoDB with the following structure:

```json
{
  "incident_id": 6,
  "zabbix_payload": { /* original payload */ },
  "status": "PROBLEM",
  "created_date": "2024-02-12T10:30:00Z",
  "updated_date": "2024-02-12T10:30:00Z",
  "ticket_id": "240",
  "actions": [
    {
      "type": "ticket_created",
      "tool": "create_ticket",
      "input": { /* tool input */ },
      "output": { /* tool output */ },
      "timestamp": "2024-02-12T10:30:05Z"
    },
    {
      "type": "notification_sent",
      "tool": "notify",
      "input": { /* tool input */ },
      "output": { /* tool output */ },
      "timestamp": "2024-02-12T10:30:06Z"
    }
  ]
}
```

## Available Tools

The agent has access to these tools:

- **`create_ticket`** - Creates a new ticket in the ticketing system
- **`resolve_ticket`** - Resolves an existing ticket
- **`find_ticket_by_incident`** - Retrieves ticket ID for an incident
- **`notify`** - Sends email notifications
- **`persist_event`** - Stores events and actions in MongoDB

> **Note:** The current implementation uses mock tools for demonstration. Replace with real integrations in production.

## Observability

All agent executions are traced in LangSmith, allowing you to:
- Debug agent reasoning
- View tool calls and responses
- Monitor performance
- Analyze failure patterns

Access your traces at: https://smith.langchain.com

## API Documentation

Once running, view the interactive API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
