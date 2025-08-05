# 🚀 Chainlit Interface Setup Guide

This guide helps you set up the interactive Chainlit interface to test your LangGraph workflow system.

## 📦 Installation

### 1. Install Chainlit
```bash
# Install Chainlit 
pip install chainlit>=1.0.0

# Or install from requirements
pip install -r requirements.txt
```

### 2. Verify Installation
```bash
chainlit hello
```
This should open a test interface at `http://localhost:8000`

## 🎯 Available Interfaces

### 1. **Standard Interface** (`chainlit_app.py`)
- Complete workflow testing
- Intent analysis and validation
- Test case buttons
- Performance metrics
- Session summaries

### 2. **Advanced Interface** (`chainlit_advanced.py`)  
- Real-time LangGraph execution visualization
- Node-by-node workflow streaming
- Detailed performance analysis
- Architecture insights

## 🚀 Quick Start

### Method 1: Using the Launcher Script
```bash
python start_chainlit.py
```

### Method 2: Direct Chainlit Commands
```bash
# Standard interface
chainlit run chainlit_app.py -w

# Advanced interface  
chainlit run chainlit_advanced.py -w
```

### Method 3: Manual Python Execution
```bash
# Standard
python chainlit_app.py

# Advanced
python chainlit_advanced.py
```

## 🎯 What to Test

### 🔍 **Information Queries** (Should route to RAG Agent)
- "What is Delve?"
- "How does SOC2 work?"
- "What features do you have?"
- "Tell me about compliance"

### 📅 **Scheduling Requests** (Should route to Demo Scheduler)
- "I want to schedule a demo"
- "Can we book a meeting?"
- "When can we schedule a call?"
- "Let's set up a demo"

### 🔧 **Technical Support** (Should route to Technical Agent)
- "I'm getting an API error"
- "The integration is not working"
- "Help me troubleshoot this issue"
- "I have a bug"

### ⚠️ **Critical Edge Cases** (Test Disambiguation)
- "What is a demo?" → Should go to RAG (NOT demo scheduler!)
- "Tell me about your demo process" → Should go to RAG (NOT demo scheduler!)
- "How long is a demo?" → Should go to RAG (NOT demo scheduler!)

## 📊 Key Metrics to Watch

### ✅ **Success Indicators**
- Intent classification accuracy: **100%**
- Routing accuracy: **100%** 
- Processing time: **<30 seconds**
- False scheduling triggers: **0**

### 🎯 **What the Interface Shows**
1. **Intent Analysis** - Confidence scores and pattern matching
2. **LangGraph Execution** - Workflow orchestration in action
3. **Agent Selection** - Which agent was chosen and why
4. **Response Quality** - Confidence and escalation decisions
5. **Routing Validation** - Confirms correct agent routing

## 🔧 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Make sure you're in the project directory
cd /path/to/slack_agent

# Activate virtual environment
source venv/bin/activate
```

**2. Port Already in Use**
```bash
# Use different port
chainlit run chainlit_app.py -w --port 8001
```

**3. Missing Dependencies**
```bash
# Install missing packages
pip install -r requirements.txt
```

## 🎉 Expected Results

When everything works correctly, you should see:

### ✅ **Perfect Intent Detection**
- "What is a demo?" → `information` (confidence: 0.90)
- "I want to schedule a demo" → `scheduling` (confidence: 0.95)
- "API error 500" → `technical_support` (confidence: 0.95)

### ✅ **Correct Agent Routing**
- Information → `enhanced_rag_agent`
- Scheduling → `demo_scheduler`
- Technical → `technical_support`

### ✅ **Fast Processing**
- Information queries: ~1-3 seconds
- Scheduling requests: ~1-2 seconds
- Technical support: ~0.1 seconds

## 🎯 Interface URLs

Once running, access the interfaces at:

- **Standard Interface**: http://localhost:8000
- **Advanced Interface**: http://localhost:8000 (when running advanced version)

## 📈 Performance Benchmarks

Your LangGraph system should achieve:
- **Intent Classification**: 100% accuracy
- **Agent Routing**: 100% correct routing
- **Response Time**: <30 seconds average
- **False Positives**: 0 (no "What is demo?" scheduling triggers)

---

**Ready to test?** Start with the standard interface to get familiar, then try the advanced interface to see the LangGraph execution in detail!