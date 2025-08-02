# 🧪 Test Cases for Delve AI Support Agent

This document contains comprehensive test cases to validate the improved LangChain-based RAG system. Use these test cases to evaluate system performance, accuracy, and escalation logic.

## 📋 How to Use These Test Cases

1. **Run Manual Tests**: Use `python run_manual_test.py` 
2. **Run Dashboard**: Use `streamlit run src/simple_dashboard.py`
3. **Copy Questions**: Copy the questions below and paste them into the testing interface
4. **Evaluate Results**: Compare actual results with expected outcomes

---

## 🎯 Test Categories

### 1. **Basic Product Information** 
*Expected: High confidence, no escalation*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "What is Delve?" | ≥ 0.8 | None | No |
| "How does Delve work?" | ≥ 0.7 | None | No |
| "What services does Delve provide?" | ≥ 0.8 | None | No |
| "Tell me about compliance automation" | ≥ 0.7 | None | No |

### 2. **SOC2 Compliance Questions**
*Expected: High confidence, SOC2 framework detection*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "How does SOC2 compliance work with Delve?" | ≥ 0.8 | SOC2 | No |
| "What SOC2 Type II controls does Delve implement?" | ≥ 0.8 | SOC2 | No |
| "Help me prepare for a SOC2 audit" | ≥ 0.7 | SOC2 | No |
| "What are the SOC2 security criteria?" | ≥ 0.8 | SOC2 | No |
| "How do I generate SOC2 compliance reports?" | ≥ 0.7 | SOC2 | No |

### 3. **HIPAA Compliance Questions**
*Expected: High confidence, HIPAA framework detection*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "What are the HIPAA requirements for healthcare data?" | ≥ 0.8 | HIPAA | No |
| "How does Delve help with HIPAA compliance?" | ≥ 0.8 | HIPAA | No |
| "What HIPAA safeguards does Delve implement?" | ≥ 0.7 | HIPAA | No |
| "How do I handle protected health information (PHI)?" | ≥ 0.8 | HIPAA | No |
| "Can Delve help with HIPAA risk assessments?" | ≥ 0.7 | HIPAA | No |

### 4. **GDPR Compliance Questions**
*Expected: High confidence, GDPR framework detection*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "How does GDPR compliance work?" | ≥ 0.8 | GDPR | No |
| "What are data subject rights under GDPR?" | ≥ 0.8 | GDPR | No |
| "How do I handle GDPR data breaches?" | ≥ 0.7 | GDPR | No |
| "Can Delve help with GDPR Article 30 records?" | ≥ 0.7 | GDPR | No |
| "What is the right to be forgotten?" | ≥ 0.8 | GDPR | No |

### 5. **ISO27001 Questions**
*Expected: High confidence, ISO27001 framework detection*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "How does ISO27001 certification work?" | ≥ 0.8 | ISO27001 | No |
| "What are ISO27001 security controls?" | ≥ 0.8 | ISO27001 | No |
| "Help me with ISO27001 risk management" | ≥ 0.7 | ISO27001 | No |
| "What is an Information Security Management System?" | ≥ 0.8 | ISO27001 | No |

### 6. **Technical Configuration Questions**
*Expected: Medium to high confidence, no escalation*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "How do I configure API authentication?" | ≥ 0.6 | None | No |
| "How do I set up SAML SSO?" | ≥ 0.6 | None | No |
| "What API endpoints are available?" | ≥ 0.7 | None | No |
| "How do I export audit logs?" | ≥ 0.7 | None | No |
| "Can I integrate with Active Directory?" | ≥ 0.6 | None | No |

### 7. **Pricing and Sales Questions**
*Expected: Medium confidence, possible escalation*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "What are your pricing plans?" | ≥ 0.6 | None | Maybe |
| "How much does enterprise licensing cost?" | ≥ 0.5 | None | Yes |
| "Do you offer volume discounts?" | ≥ 0.5 | None | Yes |
| "What's included in the professional plan?" | ≥ 0.6 | None | Maybe |

### 8. **Demo and Support Requests**
*Expected: Medium confidence, likely escalation*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "Can we schedule a demo for next week?" | ≥ 0.6 | None | Yes |
| "I need to speak with a sales representative" | ≥ 0.7 | None | Yes |
| "Can you show me how the audit trail works?" | ≥ 0.6 | None | Maybe |
| "We're evaluating compliance tools" | ≥ 0.6 | None | Yes |

### 9. **Critical/Urgent Issues**
*Expected: Any confidence, should escalate*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "The API is returning 500 errors and our production is down!" | Any | None | Yes |
| "We have a security incident and need immediate help" | Any | None | Yes |
| "Our audit is tomorrow and we need compliance reports" | Any | Any | Yes |
| "There's a data breach in our system" | Any | GDPR | Yes |

### 10. **Out-of-Scope Questions**
*Expected: Low confidence, should escalate*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "What is quantum computing?" | ≤ 0.4 | None | Yes |
| "How do I cook pasta?" | ≤ 0.3 | None | Yes |
| "What's the weather like today?" | ≤ 0.3 | None | Yes |
| "Can you help me with my taxes?" | ≤ 0.4 | None | Yes |

### 11. **Multi-Framework Questions**
*Expected: High confidence, multiple frameworks detected*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "How does Delve help with both SOC2 and HIPAA?" | ≥ 0.8 | SOC2, HIPAA | No |
| "What's the difference between GDPR and SOC2?" | ≥ 0.7 | GDPR, SOC2 | No |
| "We need ISO27001 and SOC2 certification" | ≥ 0.7 | ISO27001, SOC2 | No |

### 12. **Complex Compliance Scenarios**
*Expected: Medium to high confidence, framework detection*

| Question | Expected Confidence | Expected Frameworks | Should Escalate |
|----------|-------------------|-------------------|----------------|
| "How do I implement data classification for GDPR?" | ≥ 0.7 | GDPR | No |
| "What access controls are required for SOC2 Type II?" | ≥ 0.8 | SOC2 | No |
| "How do I conduct a HIPAA risk assessment?" | ≥ 0.7 | HIPAA | No |
| "What documentation is needed for ISO27001?" | ≥ 0.7 | ISO27001 | No |

---

## 📊 Performance Benchmarks

### Response Time Targets
- ✅ **Excellent**: < 15 seconds
- ✅ **Good**: 15-30 seconds  
- ⚠️ **Acceptable**: 30-60 seconds
- ❌ **Needs Improvement**: > 60 seconds

### Confidence Score Ranges
- 🟢 **High Confidence**: ≥ 0.8 (Should not escalate)
- 🟡 **Medium Confidence**: 0.6-0.79 (Context-dependent escalation)
- 🔴 **Low Confidence**: < 0.6 (Should escalate)

### Framework Detection Accuracy
- ✅ Should detect mentioned frameworks (SOC2, HIPAA, GDPR, ISO27001)
- ✅ Should not detect frameworks not mentioned
- ✅ Should handle multiple frameworks in one question

### Escalation Logic Validation
- ✅ Critical/urgent issues should always escalate
- ✅ Out-of-scope questions should escalate
- ✅ Low confidence responses should escalate
- ✅ Sales/demo requests should typically escalate
- ✅ Well-covered topics should not escalate

---

## 🔍 Testing Checklist

### Before Testing
- [ ] Ollama is running: `ollama serve`
- [ ] llama3.2:3b model is available: `ollama pull llama3.2:3b`
- [ ] Virtual environment is activated
- [ ] Dependencies are installed: `pip install -r requirements.txt`

### During Testing
- [ ] Record response times for each question
- [ ] Note confidence scores for each response
- [ ] Check if appropriate frameworks are detected
- [ ] Verify escalation decisions are appropriate
- [ ] Evaluate response quality and relevance

### After Testing
- [ ] Calculate average response time
- [ ] Calculate average confidence score
- [ ] Review escalation accuracy
- [ ] Identify any issues or improvements needed

---

## 📝 Test Results Template

Copy this template to record your test results:

```
## Test Results - [Date]

### System Performance
- Average Response Time: ___ seconds
- Tests Completed: ___/___
- Tests Passed: ___/___

### Confidence Scores
- High Confidence (≥0.8): ___/___
- Medium Confidence (0.6-0.79): ___/___  
- Low Confidence (<0.6): ___/___

### Framework Detection
- SOC2 Questions: ___/___ correctly detected
- HIPAA Questions: ___/___ correctly detected
- GDPR Questions: ___/___ correctly detected
- ISO27001 Questions: ___/___ correctly detected

### Escalation Logic
- Appropriate Escalations: ___/___
- Inappropriate Escalations: ___/___
- Missed Escalations: ___/___

### Issues Found
1. ___
2. ___
3. ___

### Overall Assessment
- Performance: Excellent/Good/Acceptable/Needs Improvement
- Accuracy: Excellent/Good/Acceptable/Needs Improvement
- Escalation Logic: Excellent/Good/Acceptable/Needs Improvement
```

---

## 🚀 Quick Start Testing

1. **Start Ollama**: `ollama serve`
2. **Activate environment**: `source venv/bin/activate`
3. **Run manual test**: `python run_manual_test.py`
4. **Choose option 1** for interactive testing
5. **Try questions from each category above**
6. **Record results using the template**

Happy testing! 🎉