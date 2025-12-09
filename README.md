# Decentralized Agent Mesh with A2A Communication

## 🧠 Core Concept: Validating the Decentralized Agent Mesh

### 1. The Core Problem: The Micromanagement Bottleneck
To understand why this architecture exists, look at a traditional corporate office.

Imagine a company with a strict micromanager. In this system, employees are not allowed to talk to each other. If the *Marketing Manager* needs a graphic from the *Design Team*, they cannot just ask the Designer. They must send an email to the **CEO**, who reads it, approves it, and forwards it. The Designer sends the work back to the CEO, who forwards it to Marketing.

This is the **"Hub-and-Spoke" Model (Orchestration)**. It creates three major flaws:
1.  **Delays:** Every decision waits in the CEO's inbox.
2.  **Fragility:** If the CEO gets sick (Server Crash), the entire company freezes. No one knows what to do.
3.  **Burnout:** As the company grows, the CEO cannot possibly handle every single email.

Most Multi-Agent Systems today are built exactly like this. A central "brain" controls every action, creating a massive **Single Point of Failure (SPOF)**.

### 2. The Solution: A Hybrid Fallback System
This project introduces a **Decentralized Agent Mesh** that acts as both a safety net and a speed booster.

We are not just replacing the Manager; we are creating a dynamic ecosystem. We use **Orchestration** as the default (for ease of management) but switch to **Choreography** immediately if:
1.  The Orchestrator fails (**Failover**).
2.  The situation is urgent (**Urgency Bypass**).

#### Comparison: Orchestration vs. Choreography

| Feature | Orchestration (Standard Mode) | Choreography (Fallback/Mesh Mode) |
| :--- | :--- | :--- |
| **Analogy** | The Manager directing the team | The Team working autonomously |
| **Communication** | Indirect (Agent -> Hub -> Agent) | Direct (Agent <-> Agent) |
| **Point of Failure** | **High** (If Hub fails, system stops) | **None** (Resilient to node failure) |
| **Latency** | Slower (Two hops per message) | Faster (Direct One-hop connection) |
| **Role in Project** | Primary System | Critical Fallback & Urgency Bypass |


### 3. What We Achieved
My absolute primary goal was to eliminate the **Single Point of Failure (SPOF)**. 
Developers often focus on making agents *smart*. I wanted to make the system *survivable*. I aimed to prove that:
*   ✅ Agents can bypass a broken leader to keep working.
*   ✅ Reliability is just as important as intelligence.

### 4. How This Idea Thinks Differently
The fundamental shift is **Agent-to-Agent (A2A) Communication**.

*   **Traditional Approach:** Agents are passive. They wait for orders.
*   **My Approach:** Agents are active. They are aware of their peers.

We implemented two key behaviors:
1.  **Semantic Failover:** In a normal system, if an Input Agent tries to reach the Dispatcher and gets no response, it gives up. In this Mesh, the Input Agent is smart enough to bypass the broken Dispatcher and route data directly to the Specialists.
2.  **Urgency Bypass:** Even if the Orchestrator is fully functional, agents can choose to bypass it. If a Fire Agent detects an explosion, it doesn't waste time reporting up the chain; it communicates directly with the Medical Agent. Speed overrides protocol.

### 5. Use Case: Disaster Management (Proof of Concept)

> **⚠️ IMPORTANT DISCLAIMER:**
> This Disaster Management scenario is a **MOCK IMPLEMENTATION** designed strictly to demonstrate the *architectural capabilities* of the Decentralized Agent Mesh. 
> *   These agents **DO NOT** have real-world capabilities (they cannot actually dispatch fire trucks or access real police scanners).
> *   All sensor data, map coordinates, and incident outcomes are **simulated** for testing purposes.
> *   This is a technical demonstration of software resilience, NOT a production-ready emergency response system.

To prove this architecture works, I built a prototype simulating a city Emergency Response system.

#### Scenario A: Normal Operation (Orchestration)
1.  **Input Agent** (Human/IoT) sends alert to **Dispatch Agent** (The Manager).
2.  **Dispatch Agent** analyzes and delegates to **Fire** and **Medical**.
3.  **Specialists** execute the order.

![Standard Workflow Orchestration](images/orchestration%20layer.png)

#### Scenario B: The Failure & Fallback (Choreography)
1.  **FAILURE:** The Dispatch Center goes offline (Simulated Crash).
2.  **BYPASS:** The Input Agent detects the failure and switches to **Choreography Mode**, talking directly to Specialists.
3.  **COLLABORATION:** The **Fire Agent** arrives but needs help. It uses A2A to call the **Medical Agent** directly.
4.  **RESULT:** The mission succeeds because the system fell back to a peer-to-peer mesh.

![Decentralized Choreography Failover](images/choreography%20layer.png)

### 6. Why This Matters
*   **Resilience:** The system has no "off" switch. If the head is cut off, the body keeps moving.
*   **Continuity:** Critical services function even during total server failure of the main node.
*   **Autonomy:** Agents become independent thinkers rather than just order-takers.

### 7. Limitations & Honest Boundaries
*   **Complexity:** It is harder to track what is happening when everyone is talking at once. Debugging a decentralized system is inherently more difficult than checking one central log.
*   **Trust:** In a production environment, strict security rules are needed so agents don't "gossip" or share sensitive data unnecessarily.

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

## License

This project is licensed under the Apache 2.0 License. See the `LICENSE` file for details.

## Built by
Akshith Npss