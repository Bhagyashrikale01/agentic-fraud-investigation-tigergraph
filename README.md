# agentic-fraud-investigation-tigergraph
# Agentic Fraud Investigation

An agentic fraud-investigation system built for the **TigerGraph Hacker House Goa 2026** challenge.

The system investigates benchmark fraud cases by combining transaction data, customer history, candidate device-fingerprint connections, historical fraud evidence, a graph-based investigation layer, and a policy/action engine.

> **Important:** The fraud probabilities produced by the current local agent are heuristic decision-support scores. They are not trained or validated fraud probabilities and the transaction risk score is treated as an input/trigger rather than a fraud verdict.

---

## 1. Problem Statement

Traditional fraud investigation often requires an analyst to manually collect information from multiple sources before deciding what to do with a suspicious transaction.

This project uses an **agentic investigation workflow** to:

1. Start from a suspicious case or transaction.
2. Retrieve transaction details.
3. Retrieve customer transaction history.
4. Examine recent activity and unusual behavior.
5. Search for candidate device/fingerprint connections.
6. Connect those candidates to historical fraud evidence.
7. Identify a possible fraud pattern.
8. Estimate an investigation probability using available signals.
9. Select the next-best action.
10. Determine the required approval route.
11. Decide whether a suspicious activity report should be considered.
12. Stop the investigation when the available evidence is sufficient for the current decision.

The challenge requires investigation outputs for all 20 benchmark cases, including evidence, next-best actions, approval routing, SAR/reporting decisions where applicable, and a case graph record.

---

## 2. Solution Architecture

```text
                         ┌──────────────────────┐
                         │   Benchmark Case     │
                         │      HHG-001...020   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │   Investigation Agent  │
                       └──────────┬─────────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
   ┌─────────────────┐   ┌─────────────────┐   ┌──────────────────┐
   │ Transaction     │   │ Customer        │   │ Device /         │
   │ Details         │   │ History         │   │ Fingerprint      │
   └────────┬────────┘   └────────┬────────┘   │ Evidence         │
            │                     │            └────────┬─────────┘
            └─────────────────────┼─────────────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │ Evidence Aggregation    │
                     └────────────┬────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │ Pattern Detection       │
                     │ - Card testing          │
                     │ - CNP fraud             │
                     │ - New device            │
                     │ - Account takeover      │
                     │ - Out-of-region use     │
                     └────────────┬────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │ Risk / Probability       │
                     │ Assessment               │
                     └────────────┬────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │ Policy / Action Engine   │
                     └────────────┬────────────┘
                                  ▼
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
        Next-best action    Approval route       SAR/report
              │
              ▼
        Case Graph Record
```

---

## 3. TigerGraph Implementation

The project uses **TigerGraph Savanna** as the graph layer.

Graph:

`SavannaTransactionGraph`

### Vertices

- `Transaction`
- `Customer`
- `Card`

### Edges

- `transaction_belongs_to_customer`
- `transaction_uses_card`

The graph allows the investigation to move from a customer to transactions and from transactions to cards.

### Transaction attributes

The reduced Savanna transaction dataset contains:

- `transaction_id`
- `transaction_dt`
- `transaction_amt`
- `product_cd`
- `card1`–`card6`
- `addr1`
- `addr2`
- `dist1`
- `dist2`
- `p_emaildomain`
- `r_emaildomain`
- `customer_id`
- `ts`
- `channel`
- `risk_score`

The original transaction dataset contains more columns than the Savanna import limit, so a reduced graph-ready transaction file was created for the graph layer.

---

## 4. GSQL Investigation Queries

Several GSQL queries were created and tested in TigerGraph.

Examples include:

### Get customer transactions

```gsql
CREATE QUERY get_customer_transactions(STRING cid)
FOR GRAPH SavannaTransactionGraph {
    Start = SELECT c
            FROM Customer:c
            WHERE c.customer_id == cid;

    Result = SELECT t
             FROM Start:s
             -(transaction_belongs_to_customer:e)->
             Transaction:t;

    PRINT Result;
}
```

### Get transaction details

```gsql
USE GRAPH SavannaTransactionGraph

CREATE OR REPLACE DISTRIBUTED QUERY
get_transaction_details(INT tid) {

    Result = SELECT t
             FROM Transaction:t
             WHERE t.transaction_id == tid;

    PRINT Result;
}
```

### Get transaction context

```gsql
USE GRAPH SavannaTransactionGraph

CREATE OR REPLACE DISTRIBUTED QUERY
get_transaction_context(INT tid) {

    CustomerResult = SELECT c
                     FROM Customer:c
                     -(transaction_belongs_to_customer:e)->
                     Transaction:t
                     WHERE t.transaction_id == tid;

    CardResult = SELECT card
                 FROM Transaction:t
                 -(transaction_uses_card:e)->
                 Card:card
                 WHERE t.transaction_id == tid;

    PRINT CustomerResult;
    PRINT CardResult;
}
```

Other investigation queries were created for:

- Customer history
- Customer cards
- Previous transactions
- Online transactions
- High-value transactions
- Card-testing signals
- Recent customer activity
- High-risk transactions
- Target transaction details

---

## 5. Agent Workflow

The current local investigation agent is implemented in:

```text
final_agent.py
```

For every benchmark case, the agent performs the following workflow.

### Step 1 — Identify the case

The agent reads:

```text
case_pack.csv
```

and identifies the case ID, customer, and flagged transaction.

### Step 2 — Retrieve transaction

The transaction is retrieved from:

```text
benchmark_transactions.csv
```

The transaction amount, channel, transaction ID and risk score are collected.

### Step 3 — Retrieve customer history

The agent uses:

```text
benchmark_customer_history.csv
```

to obtain signals such as:

- Previous transaction count
- Recent 48-hour activity
- Online activity
- Small online transactions
- Amount unusualness
- Address history

### Step 4 — Gather device evidence

The agent checks:

```text
benchmark_device_case_evidence_top3.csv
```

for candidate device/fingerprint connections.

These connections are treated carefully:

> A matching device fingerprint is a candidate connection and is not treated as proof that two transactions came from the same physical device.

Historical information associated with the matched customer is then used as supporting evidence.

### Step 5 — Detect a pattern

The agent considers patterns including:

- `card_testing`
- `card_not_present_fraud`
- `card_not_present_new_device`
- `out_of_region_use`
- `account_takeover`
- `none`
- `undocumented`

### Step 6 — Calculate investigation probability

The starting risk score is used as a trigger/input.

The current prototype adds heuristic adjustments when additional investigation evidence supports a pattern.

Therefore:

```text
fraud_probability != ground-truth fraud probability
```

It is a prototype decision-support score.

### Step 7 — Select next-best action

The agent selects actions according to the available evidence and configured fraud-policy thresholds.

Examples include:

- `VERIFY_WITH_CUSTOMER`
- `STEP_UP_AUTH`
- `MONITOR_CARD`
- `DECLINE_TRANSACTION`
- `BLOCK_CARD`
- `CREATE_CASE`
- `ESCALATE_TO_ANALYST`
- `FILE_REPORT`

### Step 8 — Determine approval route

Actions can be routed to:

- `AUTO`
- `L1`
- `L2`

The route is included with each recommended action.

### Step 9 — SAR/report decision

The agent records whether a report should be considered based on the configured reporting conditions and available evidence.

### Step 10 — Stop investigation

The agent records a `stop_reason` explaining why the current investigation ended.

---

## 6. Evidence Model

Each investigation produces evidence from multiple sources.

### Transaction evidence

Contains:

- Transaction ID
- Amount
- Channel
- Input risk score

### Customer-history evidence

Contains:

- Previous transaction count
- Recent 48-hour activity
- Online transactions
- Amount unusualness

### Device-history evidence

Contains:

- Matched customer
- Historical confirmed-fraud count
- Historical patterns
- Historical maximum exposure
- Device/fingerprint match count

The final evidence record is designed to make the investigation traceable instead of producing only a final decision.

---

## 7. Policy / Action Engine

The prototype contains policy-driven action selection.

Examples of configured decision behavior:

| Situation | Example response |
|---|---|
| Card testing | Decline/step-up or block depending on exposure |
| High-confidence suspicious activity | Block card + create case |
| Moderate uncertainty | Verify customer + create case |
| High exposure with uncertainty | Escalate to analyst |
| Low-confidence activity | Monitor card |
| Strong reporting conditions | Add `FILE_REPORT` |

Approval routing is recorded with each action.

The system is designed so that the recommendation is accompanied by the evidence and policy-driven reason rather than being an unexplained output.

---

## 8. 20-Case Benchmark

The final agent successfully processed all 20 benchmark cases:

```text
HHG-001
HHG-002
HHG-003
HHG-004
HHG-005
HHG-006
HHG-007
HHG-008
HHG-009
HHG-010
HHG-011
HHG-012
HHG-013
HHG-014
HHG-015
HHG-016
HHG-017
HHG-018
HHG-019
HHG-020
```

Final output:

```text
final_20_case_outputs.json
```

The output contains, for each case:

- Case information
- Evidence requests
- Gathered evidence
- Pattern assessment
- Fraud probability
- Next-best actions
- Approval route
- SAR/report status
- Stop reason
- Tool-call trace
- Latency

---

## 9. Case Graph Record

The generated case graph record is:

```text
case_graph_records.csv
case_graph_records.json
```

Current record:

```text
Cases: 20
Graph records: 166
```

The record represents relationships such as:

```text
CASE
  │
  ├── INVOLVES_CUSTOMER ──> CUSTOMER
  │
  ├── evidence ───────────> TRANSACTION/HISTORY/DEVICE
  │
  └── RECOMMENDS ─────────> ACTION
```

Device connections use the relation:

```text
CANDIDATE_DEVICE_FINGERPRINT_MATCH
```

This terminology is intentional because the available fingerprint evidence does not prove that the same physical device was used.

---

## 10. Main Project Files

```text
data/
│
├── case_pack.csv
├── transactions.csv
├── transactions_savanna.csv
├── identity.csv
├── closed_cases_history.csv
│
├── benchmark_transactions.csv
├── benchmark_customer_history.csv
├── benchmark_evidence.csv
├── benchmark_identity.csv
├── benchmark_device_matches.csv
├── benchmark_device_fraud_evidence.csv
├── benchmark_device_case_evidence_top3.csv
│
├── final_agent.py
├── final_20_case_outputs.json
│
├── create_case_graph.py
├── case_graph_records.csv
└── case_graph_records.json
```

---

## 11. How to Run

### Requirements

Python 3.12+ and the following Python packages:

```text
pandas
```

Install:

```bash
pip install pandas
```

### Run the investigation agent

```bash
python final_agent.py
```

Expected result:

```text
AGENT INVESTIGATION COMPLETE
Cases processed: 20
Final JSON created successfully.
```

### Generate the case graph record

```bash
python create_case_graph.py
```

Expected result:

```text
CASE GRAPH RECORD CREATED
Cases: 20
Graph records: 166
```

---

## 12. Output Files

### Final investigation

```text
final_20_case_outputs.json
```

### Case graph CSV

```text
case_graph_records.csv
```

### Case graph JSON

```text
case_graph_records.json
```

These files provide the main machine-readable submission outputs.

---

## 13. Design Principles

### Evidence before action

The agent gathers transaction, customer, and historical evidence before selecting an action.

### Risk score is not the verdict

The supplied risk score is treated as an investigation trigger/input rather than automatically declaring a transaction fraudulent.

### Explainable decisions

The output records evidence, pattern assessment, action, approval route, and stop reason.

### Controlled evidence gathering

The workflow focuses on relevant evidence instead of blindly collecting every available field.

### Human approval where required

Actions can be routed through automatic, L1, or L2 approval paths.

### Conservative device interpretation

Fingerprint matches are treated as candidate relationships rather than definitive physical-device identity.

### Reproducible output

The same benchmark inputs can be processed again to regenerate the JSON and case graph records.

---

## 14. Current Limitations

This is a hackathon prototype and has several limitations:

1. The local probability score is heuristic and is not a calibrated machine-learning probability.
2. Device fingerprint matching is evidence of a candidate connection, not proof of shared physical-device ownership.
3. Some customer/device evidence is preprocessed into benchmark evidence files before the final local agent runs.
4. The current prototype does not represent every possible fraud pattern equally.
5. Customer and analyst responses are not live integrations in the current prototype.
6. Production deployment would require stronger model validation, access control, audit logging, monitoring, and integration with real investigation systems.

---

## 15. Future Improvements

Possible next improvements include:

- Full TigerGraph MCP integration with the agent
- GraphRAG over historical investigations
- Live tool-based evidence gathering
- Learned fraud-pattern classification
- Calibrated fraud probabilities
- Automated policy-rule evaluation
- Human-in-the-loop approval UI
- Case timeline visualization
- SAR/report generation workflow
- Connected-card investigation
- Real-time transaction investigation
- Investigation audit trail
- Production authentication and authorization

---

## 16. Demo Flow

A short demo can follow this sequence:

```text
1. Open TigerGraph Savanna
        ↓
2. Show SavannaTransactionGraph
        ↓
3. Show Customer → Transaction → Card relationships
        ↓
4. Show GSQL investigation query
        ↓
5. Run final_agent.py
        ↓
6. Show 20/20 cases processed
        ↓
7. Open final_20_case_outputs.json
        ↓
8. Show one case's evidence
        ↓
9. Show pattern + probability
        ↓
10. Show next-best action + approval route
        ↓
11. Show case_graph_records.csv/json
```

---

## 17. Summary

This project demonstrates an **agentic fraud-investigation workflow** that connects graph-based transaction relationships with customer history, device/fingerprint evidence, historical fraud information, and policy-driven actions.

The prototype successfully processes the complete 20-case benchmark and generates machine-readable investigation and case-graph outputs.

The central idea is:

```text
Suspicious Case
      ↓
Graph + History + Device Evidence
      ↓
Evidence Aggregation
      ↓
Fraud Pattern Assessment
      ↓
Policy / Action Engine
      ↓
Next-Best Action + Approval Route
      ↓
Explainable Case Record
```

Built for the TigerGraph Hacker House Goa 2026 challenge.
