# 🧪 Testing Guide - Delve AI Support Agent

This guide explains how to test the improved LangChain-based RAG system using the provided testing tools.

## 🚀 Quick Start

### Prerequisites
1. **Ollama with llama3.2:3b model**:
   ```bash
   ollama serve
   ollama pull llama3.2:3b
   ```

2. **Virtual environment activated**:
   ```bash
   source venv/bin/activate
   ```

3. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

## 📋 Testing Options

### 1. 🎮 Manual Interactive Testing
**Best for: Quick testing with your own questions**

```bash
python run_manual_test.py
```

**Features:**
- Interactive command-line interface
- Real-time question processing
- Detailed response analysis
- Framework detection validation
- Performance metrics

**Options:**
- Interactive Testing (ask your own questions)
- Predefined Test Cases (automated validation)

### 2. 📊 Web Dashboard Testing
**Best for: Visual testing and batch operations**

```bash
python run_dashboard.py
```

**Or alternatively:**
```bash
streamlit run src/simple_dashboard.py
```

**Features:**
- 🧪 **Interactive Testing**: Web-based question interface
- 📊 **Batch Testing**: Run predefined test suites
- 🏥 **System Health**: Monitor component status
- ⚙️ **Configuration**: View system settings
- 📖 **Test Cases**: Reference documentation

### 3. 🔬 Unit Tests
**Best for: Automated validation**

```bash
python -m pytest tests/ -v
```

## 📝 Test Cases

Comprehensive test cases are provided in `test_cases.md` covering:

### 🎯 Core Categories
- **Basic Product Information** (high confidence, no escalation)
- **SOC2 Compliance** (high confidence, framework detection)
- **HIPAA Compliance** (high confidence, framework detection)
- **GDPR Compliance** (high confidence, framework detection)
- **ISO27001 Questions** (high confidence, framework detection)
- **Technical Configuration** (medium confidence)
- **Pricing & Sales** (medium confidence, possible escalation)
- **Demo Requests** (medium confidence, likely escalation)
- **Critical Issues** (any confidence, should escalate)
- **Out-of-Scope** (low confidence, should escalate)

### 📊 Expected Performance
- **Response Time**: < 30 seconds (< 15s excellent)
- **Confidence Scores**: 
  - High (≥0.8): Should not escalate
  - Medium (0.6-0.79): Context-dependent
  - Low (<0.6): Should escalate
- **Framework Detection**: Accurate identification of SOC2, HIPAA, GDPR, ISO27001

## 🔍 What to Test

### 1. Framework Detection
```
✅ "How does SOC2 compliance work?" → Should detect SOC2
✅ "What are HIPAA requirements?" → Should detect HIPAA
✅ "Help with GDPR data rights" → Should detect GDPR
✅ "ISO27001 certification process" → Should detect ISO27001
```

### 2. Confidence Scoring
```
✅ "What is Delve?" → High confidence (≥0.8)
✅ "How do I configure SSO?" → Medium confidence (0.6-0.8)
✅ "What is quantum computing?" → Low confidence (<0.4)
```

### 3. Escalation Logic
```
✅ Critical issues → Always escalate
✅ Out-of-scope questions → Should escalate
✅ Low confidence responses → Should escalate
✅ Well-covered topics → Should not escalate
```

### 4. Response Quality
```
✅ Relevant and accurate information
✅ Proper source citations
✅ Professional tone
✅ Appropriate length
```

## 📈 Performance Benchmarks

### ⚡ Response Time Targets
- 🟢 **Excellent**: < 15 seconds
- 🟡 **Good**: 15-30 seconds
- 🔴 **Needs Improvement**: > 30 seconds

### 🎯 Accuracy Targets
- 🟢 **Framework Detection**: > 90% accuracy
- 🟢 **Confidence Scoring**: Appropriate for content
- 🟢 **Escalation Logic**: > 90% appropriate decisions

## 🐛 Troubleshooting

### Common Issues

1. **"RAG system failed to initialize"**
   ```bash
   # Check Ollama is running
   curl http://localhost:11434/api/tags
   
   # Restart Ollama if needed
   ollama serve
   ```

2. **Slow response times**
   - Check Ollama server load
   - Verify model is fully loaded
   - Restart Ollama service

3. **Low confidence scores**
   - Verify knowledge base is loaded
   - Check if question is in scope
   - Review RAG system initialization

4. **Import errors**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt
   
   # Check virtual environment
   which python
   ```

## 📊 Sample Test Session

Here's what a typical test session looks like:

```
🤔 Your question: How does SOC2 compliance work with Delve?

🔄 Processing: How does SOC2 compliance work with Delve?
──────────────────────────────────────────────

📊 RESULTS:
   Agent: rag_agent
   Processing Time: 12.34s
   Confidence: 0.87
   Confidence Level: 0.87
✅ No escalation needed
   Frameworks Detected: SOC2

💬 RESPONSE:
Delve helps organizations achieve SOC2 compliance by providing automated 
evidence collection, continuous monitoring, and comprehensive reporting 
for all five trust service criteria: Security, Availability, Processing 
Integrity, Confidentiality, and Privacy...

📚 SOURCES (3):
   1. 📖 SOC2 Compliance Overview > Trust Service Criteria (SOC2)
   2. 📖 Automated Evidence Collection > Continuous Monitoring (SOC2)
   3. 📖 Compliance Reporting > SOC2 Type II Reports (SOC2)
```

## ✅ Test Results Template

Use this template to record your testing results:

```markdown
## Test Session - [Date]

### System Performance
- Average Response Time: ___s
- Tests Completed: ___/___
- Overall Pass Rate: ___%

### Framework Detection
- SOC2: ___/___
- HIPAA: ___/___  
- GDPR: ___/___
- ISO27001: ___/___

### Confidence Accuracy
- High Confidence Questions: ___/___
- Medium Confidence Questions: ___/___
- Low Confidence Questions: ___/___

### Escalation Logic
- Appropriate Escalations: ___/___
- Missed Critical Escalations: ___/___

### Issues Found
1. ___
2. ___

### Overall Assessment
Performance: ⭐⭐⭐⭐⭐ (1-5 stars)
Accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)
```

## 🎯 Testing Checklist

Before you start testing:
- [ ] Ollama is running (`ollama serve`)
- [ ] llama3.2:3b model is available (`ollama list`)
- [ ] Virtual environment is activated
- [ ] All dependencies are installed
- [ ] Choose your testing method (manual vs dashboard)

During testing:
- [ ] Test questions from each category
- [ ] Record response times
- [ ] Validate framework detection
- [ ] Check escalation decisions
- [ ] Note any issues or errors

After testing:
- [ ] Calculate performance metrics
- [ ] Document any issues found
- [ ] Share results for system improvement

Happy testing! 🚀