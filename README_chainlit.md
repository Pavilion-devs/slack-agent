# 🚀 Delve LangGraph Workflow Tester

Welcome to the interactive testing interface for Delve's revolutionary **LangGraph-based agent routing system**!

## 🎯 What This Tests

This interface demonstrates how we solved the major routing issues in the previous system:

### ❌ **Before (Old System Problems):**
- "What is a demo?" would incorrectly trigger demo scheduling
- First registered agent would win in routing conflicts
- Hardcoded responses and routing logic
- Agents competing and interfering with each other

### ✅ **After (LangGraph Solution):**
- **Perfect Intent Detection** - "What is a demo?" goes to information, not scheduling
- **Confidence-Based Routing** - Best agent selected by confidence scores
- **Graph Orchestration** - Clean state management eliminates conflicts
- **Parallel Execution** - Subgraphs run efficiently without interference

## 🧪 How to Test

1. **Type any message** or click the **test case buttons** 
2. **Watch the workflow** process your message through:
   - 🧠 **Intent Detection** - Classifies your message
   - ⚙️ **LangGraph Execution** - Routes to appropriate agent
   - 💬 **Agent Response** - Gets intelligent response
   - ✅ **Validation** - Confirms routing was correct

## 📊 Key Metrics Tracked

- **Intent Classification Accuracy**
- **Agent Routing Correctness** 
- **Processing Speed**
- **Disambiguation Success**

## 🎯 Test Categories

### 🔍 **Information Queries** → RAG Agent
- "What is Delve?"
- "How does SOC2 work?"
- "What features do you have?"

### 📅 **Scheduling Requests** → Demo Scheduler
- "I want to schedule a demo"
- "Can we book a meeting?"
- "When can we schedule a call?"

### 🔧 **Technical Support** → Technical Agent
- "I'm getting an API error"
- "The integration is not working"
- "Help me troubleshoot this issue"

### ⚠️ **Edge Cases** → Tests Disambiguation
- "What is a demo?" (Should NOT trigger scheduling!)
- "Tell me about your demo process" (Information, not booking)
- "I want to schedule a demo" (SHOULD trigger scheduling)

## 🏆 Success Criteria

- ✅ **100% Intent Classification Accuracy**
- ✅ **Correct Agent Routing**
- ✅ **Sub-30 second response times**
- ✅ **Zero false scheduling triggers**

---

**Ready to test?** Start typing or click a test case button to see the LangGraph system in action!