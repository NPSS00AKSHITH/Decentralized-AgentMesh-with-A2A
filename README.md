# Decentralized Agent Mesh with A2A Communication

## Introduction

In the rapidly evolving landscape of Multi-Agent Systems (MAS), the traditional **Hub-and-Spoke** model (centralized orchestration) is becoming a bottleneck. As agent networks grow in complexity and scale, a single central controller introduces latency, fragility, and a **Single Point of Failure (SPOF)**.

This project demonstrates a robust alternative: a **Decentralized Agent Mesh** enabled by the **Agent-to-Agent (A2A)** protocol. By shifting from centralized *Orchestration* to peer-to-peer *Choreography*, we create a system where agents are autonomous, resilient, and capable of direct collaboration.

## Concept: Orchestration vs. Choreography

To understand the value of this architecture, it is crucial to distinguish between two primary coordination patterns:

### 1. The Orchestration Pattern (Traditional)
In an orchestrated system, a central "Conductor" (e.g., a central LLM or Dispatcher) controls every interaction.
*   **Flow:** Agent A -> Conductor -> Agent B -> Conductor -> Agent C.
*   **Problem:** If the Conductor fails, the entire system halts. The Conductor also becomes a performance bottleneck as message volume increases.

### 2. The Choreography Pattern (This Project)
In a choreographed mesh, agents know their roles and reacting to events directly, similar to dancers in a ballet who know their steps without a conductor shouting every move.
*   **Flow:** Agent A -> Agent B -> Agent C.
*   **Advantage:** **Zero Single Point of Failure.** If one node fails, others can route around it. Communication is faster (lower latency) and infinitely scalable.

## Solving the Single Point of Failure (SPOF)

We overcame the inherent risks of centralized orchestration by implementing a **Mesh Architecture** where:
*   **Direct Communication:** Agents use the A2A protocol to send authenticated, direct messages to each other, bypassing the central dispatcher when necessary.
*   **Semantic Failover:** Agents are aware of their peers' capabilities. If a primary delegate (e.g., the Medical Agent) is unreachable, the calling agent (e.g., Fire Chief) can autonomously reroute the request to a backup (e.g., Police Chief) without human intervention.
*   **Circuit Breakers:** The system detects failing nodes and temporarily "opens the circuit" to prevent cascading failures, allowing the network to heal.

## The Use Case: Disaster Management System

To prove the viability of this decentralized architecture, we have implemented a **Disaster Management System** as a comprehensive **example use case**. 

We chose Disaster Management because it perfectly illustrates the need for:
*   **High Availability:** Emergency systems cannot afford downtime.
*   **Rapid Response:** Direct A2A communication reduces decision latency.
*   **Resilience:** The system must function even if the central command center (Dispatch) goes offline.

### How it Works in this Example
In this scenario, a network of autonomous agents works together to handle city-wide emergencies:
1.  **Dispatch Agent:** The initial router (simulating a 911 operator).
2.  **Specialist Agents:** Fire, Medical, Police, and Utility agents that typically receive orders from Dispatch but can effectively "talk" to each other directly to coordinate scene safety, casualty triage, and hazard containment.
3.  **Sensor Agents:** IoT and Camera agents that can trigger alerts. *Critically, if Dispatch acts as a bottleneck or fails, these sensors can be configured to alert specialists directly.*

**⚠️ Disclaimer:** This Disaster Management implementation is a **MOCK** and **PROOF OF CONCEPT**. It is designed to demonstrate the *technological capabilities* of the Decentralized Agent Mesh and A2A protocol. It constitutes a simulation environment, not a production-ready emergency services system.

## System Architecture

### 1. Standard Workflow (Orchestration)

This diagram represents the "Happy Path" where the **Dispatch Agent** acts as the central router, receiving inputs and delegating tasks to specialists. This mimics a traditional centralized system.

![Standard Workflow Orchestration](images/orchestration%20layer.png)

### 2. Decentralized Choreography & Failover

This diagram illustrates the **Mesh Architecture**. It starts with the **Input Agents** receiving data and effectively "activating" the mesh. Crucially, it shows how agents communicate directly (**A2A**) and how sensors can **bypass** Dispatch to trigger specialists instantly.

![Decentralized Choreography Failover](images/choreography%20layer.png)

## Getting Started

Follow these instructions to run the project and test the decentralized mesh capabilities yourself.

### Prerequisites
*   **Python 3.10+**
*   **Node.js & npm** (for the Frontend visualization)
*   **PostgreSQL** (required for DB-backed handshakes)

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd Decentralized-AgentMesh-with-A2A

# Create and activate virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
# source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Fill in your **Gemini API Key** and **Database URL** in the `.env` file.

### 3. Running the Mesh

The system comprises three parts that must run simultaneously. We provide batch scripts for convenience on Windows.

**Step A: Start the Agent Logic (ADK)**
Runs the "Brains" of the agents.
```bash
./start_agents.bat
```

**Step B: Start the A2A Network (Servers)**
Runs the "Bodies" that handle peer-to-peer communication.
```bash
./start_a2a_servers.bat
```

**Step C: Start the Visualization (Frontend)**
Launches the Control Center dashboard.
```bash
./start_frontend.bat
```

### 4. Testing the System
1.  Go to `http://localhost:3000`.
2.  **Scenario 1 (Standard):** Type "Fire at Central Park" in the **Human Intake** panel. Watch Dispatch delegate to Fire Chief, who then coordinates with Medical.
3.  **Scenario 2 (Resilience):** Kill the **Medical Agent** process. Submit a request involving casualties. Observe how the Fire Chief detects the failure and re-routes the request to the Police Chief or logs the failover action.
