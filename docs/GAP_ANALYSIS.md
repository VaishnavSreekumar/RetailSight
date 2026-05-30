# Challenge Gap Analysis - EY Techathon 6.0: Retail Track

This gap analysis compares the current **Retail Intelligence Platform** implementation against the official **Challenge V: Retail [ABFRL]** requirements.

---

## 1. Challenge Overview & Alignment

The Retail Challenge V focuses on building an **AI-driven Conversational Sales Agent** that operates across online and physical channels (web, mobile app, WhatsApp/Telegram, in-store kiosks) to emulate a top-tier sales associate and orchestrate specialized worker agents (recommendation, inventory, payment, fulfillment, loyalty, post-purchase).

The current repository implements a **CCTV-based In-Store Customer Tracking & Analytics Engine**. Instead of the conversational agentic interface, it focuses on the **physical telemetry layer**—tracking customer movements, debouncing zones, stitching fragmented camera tracks using heuristics, reconstructing customer journeys, matching transactions, and reporting shop floor metrics (funnels, anomalies, audits).

This physical telemetry layer serves as the **critical infrastructure** for the in-store kiosk and omnichannel personalization: it captures real-world customer intent (which aisles they visited, how long they dwelled, and checkout patterns) and links it back to a global visitor profile, providing the context that a conversational assistant would need.

---

## 2. Requirement-by-Requirement Mapping

### A. Core Agentic AI System
| Challenge Requirement | Current Status | Current Implementation Details | Gap / Next Steps |
|---|---|---|---|
| **Master Agent (Conversation Orchestrator)** | **Missing** | None. The system uses a FastAPI backend with service/repository patterns instead of an LLM-based orchestrator (e.g. CrewAI/LangGraph). | Implement conversational Master Agent to handle chat/voice flow. |
| **Recommendation Worker Agent** | **Missing** | None. (Though we track zone browse times, we do not have an LLM recommender). | Add a worker agent to suggest products/bundles based on browsing history. |
| **Inventory Worker Agent** | **Missing** | None. | Create dummy inventory checker (API/mock DB) for "click & collect" or "ship to home". |
| **Payment Worker Agent** | **Missing** | None. | Implement payment gateway stub for card, UPI, and gift card validation. |
| **Fulfillment Worker Agent** | **Missing** | None. | Add reservation scheduler for in-store try-on and home deliveries. |
| **Loyalty & Offers Worker Agent** | **Missing** | None. | Create mock rules engine to apply coupons and calculate loyalty tier points. |
| **Post-Purchase Support Agent** | **Missing** | None. | Add returns/exchanges and feedback collector. |

### B. User Interfaces & Omnichannel Continuity
| Challenge Requirement | Current Status | Current Implementation Details | Gap / Next Steps |
|---|---|---|---|
| **Web Chat & Mobile App Interface** | **Missing** | No frontend user interface exists. All APIs are accessed via JSON REST endpoints. | Build conversational chat widgets. |
| **WhatsApp / Telegram Integration** | **Missing** | None. | Add webhook integrations for messaging platforms. |
| **In-Store Kiosk / Voice Assistant** | **Missing** | None. | Create voice-to-text kiosk simulation. |
| **Context Switching & Continuity** | **Missing** | None. | Establish shared session store to maintain customer state across app, kiosk, and WhatsApp. |

### C. Data & System Assumptions
| Challenge Requirement | Current Status | Current Implementation Details | Gap / Next Steps |
|---|---|---|---|
| **Synthetic Customer Profiles (>=10)** | **Partially Implemented** | We generate synthetic visitor tracks (e.g., 22 global visitors in E2E runs), but they lack rich profile metadata (loyalty tier, preferences). | Add a database table for `CustomerProfile` with preferences, history, and loyalty tier. |
| **Product Catalog API** | **Missing** | None. | Create a product catalog database table/API mock. |
| **Inventory Server** | **Missing** | None. | Create mock inventory server. |
| **Payment Gateway Stub** | **Missing** | None. | Integrate mock payment endpoints. |
| **Loyalty & Promotions Service** | **Missing** | None. | Implement loyalty lookup logic. |
| **POS Terminal Integration** | **Partially Implemented** | Transaction matcher links transactions from database. POS transaction CSV files can be ingested. | Add interactive barcode scan/checkout terminal mock. |

### D. In-Store CCTV & Analytics (Current Strengths)
The current system implements advanced telemetry that goes *beyond* the base conversational requirements to solve the physical store tracking challenge:
* **Detection Pipeline**: YOLOv8 + ByteTrack tracking on raw MP4 footage.
* **Event Generation**: Emits debounced events (`ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT`, `ZONE_DWELL`, `BILLING_QUEUE_JOIN`).
* **Cross-Camera Stitching**: Heuristic-based correlation engine stitching local camera tracks (`CAM1`, `CAM2`, `CAM4`) to global visitor IDs (`VIS_Gxxx`) with confidence tracking.
* **Session Hydration**: Reconstructs complete customer journeys in the store database.
* **Transaction Matching**: Links POS transactions (`Transaction` model) to visitor journeys.
* **Funnels, Anomalies & Audits**: REST APIs to report store funnel conversion, queue anomalies, dead zones, and journey quality audits.

---

## 3. Summary of Gap Classifications

* **Implemented (Telemetry Layer)**:
  * Raw CCTV video detection & tracking pipeline.
  * Spatial retail zone mapping & exit timeouts.
  * Heuristic Cross-Camera Correlation (Stitching) engine.
  * Database schema & repositories for `Event`, `VisitorSession`, `Transaction`.
  * Session hydration & transaction linking engines.
  * Metrics API, Funnel API, and Anomaly Engine.
  * Customer Journey diagnostics & audit service.
* **Partially Implemented**:
  * POS integration (attributing transactions in database, but missing interactive terminal scan simulation).
  * Synthetic customer data (represented as global visitor IDs, but missing demographic/profile files).
* **Missing (Conversational/Agentic Layer)**:
  * Conversational UI (Web, mobile, WhatsApp, voice kiosk).
  * Master Agent conversaion orchestrator (LangGraph/CrewAI framework).
  * Worker agents (Recommendation, Inventory, Payment, Fulfillment, Loyalty, Post-Purchase).
  * Product Catalog API, Inventory Database, Payment Gateway Stub, Loyalty rules engine.
* **Optional**:
  * File uploads (e.g. uploading a coupon or receipt image for verification).
