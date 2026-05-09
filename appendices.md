# APPENDICES

## Appendix A: Customer Service Survey Questionnaire

**Survey Title:** Customer Service Experience in Kenyan Telecommunications

**Instructions:** Please answer all questions honestly. This survey is anonymous and will be used solely for academic research purposes.

**Section A: Demographic Information**

1. Age group: [ ] 18-30  [ ] 31-45  [ ] 46-60  [ ] 60+
2. Location type: [ ] Urban  [ ] Peri-urban  [ ] Rural
3. Primary telecommunications provider: [ ] Safaricom  [ ] Airtel Kenya  [ ] Telkom Kenya  [ ] Other
4. Highest education level: [ ] Primary  [ ] Secondary  [ ] Certificate/Diploma  [ ] University degree+

**Section B: Current Customer Service Experience**

5. How often do you contact customer service per month?
   [ ] Never  [ ] 1-2 times  [ ] 3-5 times  [ ] More than 5 times

6. What is your typical wait time to reach a human agent?
   [ ] Less than 5 minutes  [ ] 5-15 minutes  [ ] 15-30 minutes  [ ] More than 30 minutes

7. Rate your satisfaction with current customer service (1 = Very Unsatisfied, 5 = Very Satisfied):
   1  2  3  4  5

8. What is your most frequent reason for contacting customer service? (Select all that apply)
   [ ] Account or data balance  [ ] M-Pesa / mobile money issue  [ ] Billing dispute
   [ ] Technical or network problem  [ ] Service activation or deactivation  [ ] General inquiry

**Section C: AI Customer Service Preferences**

9. Would you be willing to interact with an AI-powered voice agent for routine inquiries?
   [ ] Yes  [ ] No  [ ] Unsure

10. What would most concern you about AI customer service? (Select all that apply)
    [ ] Privacy of my data  [ ] Accuracy of responses  [ ] Difficulty reaching a human agent
    [ ] Language support  [ ] System not understanding my problem

11. In which language would you prefer AI customer service?
    [ ] English  [ ] Kiswahili  [ ] Either  [ ] Local language

---

## Appendix B: Industry Professional Interview Protocol

**Interview Title:** AI-Powered Customer Service in Kenyan Telecommunications — Industry Perspective

**Duration:** 45-60 minutes | **Format:** Semi-structured interview

**Section 1 — Current Operations**

- Describe your organisation's current customer service infrastructure and channels.
- What are the typical daily call volumes and peak period characteristics?
- What are the most common categories of customer inquiry your team handles?
- How is call routing and escalation to specialist agents currently managed?

**Section 2 — Pain Points and Challenges**

- What are the most significant operational challenges in your customer service operations today?
- How does your organisation perform against CAK service level agreement requirements?
- What is the annual attrition rate among customer service agents, and what are the training cost implications?
- How does your current system capture and use customer interaction data for service improvement?

**Section 3 — AI and Automation Perspectives**

- Is your organisation currently using or evaluating any AI or automation tools for customer service?
- What features or capabilities would be most valuable in an AI-powered customer service system?
- What technical or organisational barriers do you see as most significant for AI implementation?
- How important is Kiswahili language support for your customer base?

**Section 4 — Implementation Considerations**

- What integration requirements would an AI system need to satisfy to connect with your existing CRM and telephony infrastructure?
- What regulatory or compliance considerations are most critical for AI customer service in the Kenyan context?
- How would you define "success" for an AI customer service implementation in your organisation?

---

## Appendix C: CALLSUP API Endpoint Reference

The CALLSUP Audio Engine API exposes the endpoints listed below. Full OpenAPI 3.0 specification is available at `callsup/openapi.yaml`.

| Method | Endpoint | Auth | Description |
|--------|---------|------|-------------|
| GET | `/health` | Public | System liveness check |
| POST | `/auth/register` | Public | Register new business account, returns JWT |
| POST | `/auth/login` | Public | Authenticate and receive JWT |
| GET | `/auth/me` | Bearer | Return current user profile |
| POST | `/audio/ingest` | Public | Upload audio file for encryption and transcription |
| GET | `/audio/transcript/{conv_id}` | Public | Retrieve PII-redacted transcript segments |
| POST | `/audio/simulate` | Public | Inject text script as transcript (demo/testing) |
| POST | `/audio/voice/chat` | Public | AI conversation turn with escalation detection |
| POST | `/audio/voice/tts` | Public | Text-to-speech synthesis, returns MP3 binary |
| POST | `/audio/voice/stt` | Public | Audio-to-text transcription |
| GET | `/escalation-queue` | Bearer | List escalation tickets for business |
| POST | `/escalation-queue` | Bearer | Manually create escalation ticket |
| PATCH | `/escalation-queue/{id}` | Bearer | Update ticket status (claim or resolve) |
| GET | `/escalation-queue/stream` | SSE token | Server-Sent Events real-time ticket stream |
| GET | `/escalation-rules` | Bearer | List active escalation rules |
| POST | `/escalation-rules` | Bearer | Create new escalation rule |
| PATCH | `/escalation-rules/{id}` | Bearer | Update or deactivate escalation rule |
| GET | `/context` | Bearer | List business context documents |
| POST | `/context` | Bearer | Create new context document |
| PATCH | `/context/{id}` | Bearer | Update context document content |
| DELETE | `/context/{id}` | Bearer | Delete context document |
| GET | `/metrics` | Public | Prometheus metrics endpoint |

---

## Appendix D: Project Directory Structure

```
callsup/
├── app/
│   ├── main.py              # App factory, audio and voice routes, escalation logic
│   ├── auth.py              # /auth router — register, login, /me (JWT + SHA-256)
│   ├── config.py            # Settings via pydantic-settings (CALLSUP_AUDIO_ENGINE_ prefix)
│   ├── models.py            # Shared Pydantic v2 data models
│   ├── storage.py           # AudioRepository — Fernet-encrypted audio + transcripts
│   ├── transcription.py     # STT wrappers: RapidAPI Whisper, OpenAI Whisper, mock
│   ├── business_context.py  # Load business name and context documents for LLM prompt
│   ├── context_store.py     # /context router — CRUD for knowledge documents
│   ├── escalation_queue.py  # /escalation-queue router — tickets and SSE stream
│   ├── escalation_rules.py  # /escalation-rules router — CRUD for rules
│   ├── pii_redaction.py     # Regex PII scrubbing: email, phone, SSN, card
│   ├── metrics.py           # Prometheus counters and histograms
│   └── logging_config.py    # Structured JSON logging setup
├── callsup-web/             # React 19 + TypeScript + Vite frontend dashboard
├── callsup-specs/           # OpenAPI contract specifications for all modules
├── consolidated/            # Module baselines delivered via PR sequence
│   ├── callsup-audio-engine/
│   ├── callsup-intelligence-engine/
│   ├── callsup-platform/
│   └── callsup-knowledge-ops/
├── svc_llm_adapter.py       # Mock LLM adapter for local smoke-testing
├── svc-llm-adapter/         # LLM adapter service directory
├── smoke_test.py            # End-to-end system smoke test (no framework dependencies)
├── smoke_result.txt         # Recorded smoke test output
├── tests/                   # pytest unit and integration tests
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_pii_redaction.py
│   └── test_transcription.py
├── test_escalation_e2e.py   # Escalation lifecycle end-to-end test
├── data/                    # Runtime data (git-ignored)
├── .env                     # Environment variables (not committed)
├── requirements.txt         # Python production dependencies
├── requirements-dev.txt     # Development and testing dependencies
├── openapi.yaml             # Full OpenAPI 3.0 API specification
├── Dockerfile               # Container image definition
└── pytest.ini               # Test configuration and coverage settings
```

---

## Appendix E: Sample Annotated Conversation Transcripts

The following transcripts illustrate the two primary system outcomes: successful automated resolution and correct escalation to a human agent.

**Sample 1 — Successful Balance Inquiry Automation**

> **AI Agent:** Thank you for contacting customer support. How can I assist you today?
>
> **Customer:** I want to know how much data I have left.
>
> **AI Agent:** I can help with that. Could you please confirm your phone number so I can look up your account?
>
> **Customer:** My number is 0722 [REDACTED_PHONE].
>
> **AI Agent:** Thank you. You currently have 2.3 GB of data remaining, valid until the 15th of this month. Would you like to purchase a top-up package, or is there anything else I can help you with?
>
> **Customer:** No, that is fine. Thank you.
>
> **AI Agent:** You are welcome. Have a great day!

*Outcome: Task completed in 4 turns. No escalation triggered. Intent classified as `balance_inquiry` (confidence 0.94).*

---

**Sample 2 — Automatic Escalation to Human Agent**

> **AI Agent:** Thank you for contacting customer support. How can I assist you today?
>
> **Customer:** I was charged twice for an M-Pesa transaction and I need my money back now.
>
> **AI Agent:** I understand your concern about the duplicate charge on your M-Pesa account. Billing disputes involving transaction refunds require review by our specialist finance team who have the authorisation to process refunds directly. I am connecting you to a human agent now who will investigate this and arrange the reversal for you. Please stay on the line.

*Outcome: Escalation detected via keyword pattern ("connecting you to a human agent"). Ticket created — priority: high, reason: "M-Pesa duplicate charge refund request". Human agent received SSE notification with full conversation history within 85 ms. Agent resolved ticket within 6 minutes.*
