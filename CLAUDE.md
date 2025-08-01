# Delve Slack Support AI Agent - Development Guide

## Project Overview
This is an intelligent Slack Support AI Agent system for Delve, built using LangChain + LangGraph + Slack API + Vector DB + llama3.2:3b with Ollama. The system aims to automate 60-70% of first-line support with <30 second response times.

## Development Rules

### Code Quality
- Follow PEP 8 style guidelines for Python code
- Use type hints for all function parameters and return values
- Implement comprehensive error handling and logging
- Write docstrings for all classes and functions
- Maintain test coverage above 80%

### Architecture Principles
- Use LangGraph for multi-agent workflow orchestration
- Implement proper separation of concerns between agents
- Use dependency injection for testability
- Follow the single responsibility principle
- Implement proper async/await patterns for I/O operations

### Security & Compliance
- Never hardcode API keys or sensitive credentials
- Use environment variables for all configuration
- Implement proper data sanitization for user inputs
- Log all interactions for audit purposes
- Follow data retention policies for customer data

### Testing Strategy
- Write unit tests for all individual components
- Implement integration tests for agent workflows
- Create end-to-end tests for Slack interactions
- Mock external API calls in tests
- Test error scenarios and edge cases

### Git Workflow
After completing each major feature or fix:
1. Run all tests: `python3 -m pytest tests/ -v`
2. Run linting: `flake8 src/ tests/`
3. Run type checking: `mypy src/`
4. Format code: `black src/ tests/`
5. Check test coverage: `pytest --cov=src tests/`
6. If all checks pass, stage changes: `git add .`
7. Commit with descriptive message: `git commit -m "feat: implement [feature description]"`

### Project Structure
```
slack_agent/
├── src/
│   ├── agents/           # Individual agent implementations
│   ├── core/            # Core system components
│   ├── integrations/    # External service integrations
│   ├── models/          # Data models and schemas
│   ├── utils/           # Utility functions
│   └── workflows/       # LangGraph workflow definitions
├── tests/               # Test files
├── config/              # Configuration files
├── docs/               # Documentation
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
└── README.md           # Project documentation
```

### Environment Variables Required
- SLACK_BOT_TOKEN: Slack bot token for API access
- SLACK_SIGNING_SECRET: Slack signing secret for webhook verification
- PINECONE_API_KEY: Pinecone vector database API key
- OLLAMA_BASE_URL: Ollama server URL for llama3.2:3b (default: http://localhost:11434)
- LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)

### Agent Specifications

#### Intake Agent
- Provides instant acknowledgment (<15 seconds)
- Maintains conversation context
- Routes queries to appropriate specialized agents
- Implements confidence scoring for responses

#### Knowledge Agent
- Searches vector database of documentation
- Provides citations and source links
- Implements retrieval-augmented generation (RAG)
- Updates knowledge base from new resolutions

#### Compliance Agent
- Specialized in SOC2, ISO27001, GDPR, HIPAA
- Maps compliance frameworks to Delve features
- Provides audit-ready documentation
- Escalates complex audit scenarios

#### Escalation Agent
- Smart routing to human agents
- Provides conversation summaries
- Suggests potential solutions from similar issues
- Tags appropriate team members

### Performance Requirements
- Response acknowledgment: <15 seconds
- Full response generation: <3 minutes
- Automation rate target: 60-70%
- Escalation accuracy: >90%
- Customer satisfaction: >4.5/5

### Monitoring & Analytics
- Track response times and accuracy
- Monitor escalation patterns
- Analyze customer satisfaction scores
- Generate daily/weekly analytics reports
- Identify knowledge base gaps

### Development Commands
```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python3 -m pytest tests/ -v

# Run linting
flake8 src/ tests/

# Run type checking
mypy src/

# Format code
black src/ tests/

# Start development server
python3 -m src.main

# Start Streamlit dashboard (full version with plotly)
streamlit run src/dashboard.py

# Start simple dashboard (for quick testing)
streamlit run src/simple_dashboard.py

# Run with debug logging
LOG_LEVEL=DEBUG python3 -m src.main
```

### Deployment Phases
1. **Shadow Mode**: AI generates responses but doesn't send them
2. **Assisted Mode**: AI handles low-risk queries with human approval
3. **Autonomous Mode**: Full automation with smart escalation

## Getting Started
1. Copy `.env.example` to `.env` and fill in required values
2. Set up virtual environment and install dependencies
3. Run tests to ensure everything is working
4. Start development server
5. Test Slack integration with webhook endpoint

## Support
For questions or issues, refer to the PRD document or check the project issues tracker.