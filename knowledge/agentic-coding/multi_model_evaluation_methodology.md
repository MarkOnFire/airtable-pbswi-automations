# Multi-Model Evaluation and Dispatch Methodology

**Last Updated**: 2025-11-20
**Purpose**: To define a systematic approach for auditing the performance and cost of multiple Large Language Models (LLMs) and to create a dynamic "Interviewer Agent" that selects the optimal model for any given task.

---

## 1. Overview

The objective is to leverage the unique strengths of different LLMs (e.g., Claude, GPT, Gemini) while optimizing for both performance and token cost. This methodology is divided into two main components:

1.  **Static Benchmarking Framework**: A system for running a suite of standardized tests across all available models to gather empirical data on their quality, cost, and latency for various task types.
2.  **Dynamic Interviewer Agent**: An intelligent agent that uses the benchmark data to make real-time, informed decisions about which LLM to delegate a specific sub-task to.

---

## 2. Task Categorization

To effectively benchmark the models, we must first establish a clear taxonomy of common development tasks. This allows for a granular understanding of where each model excels or falls short.

**Proposed Task Categories:**

*   **A. Code Generation**: Scaffolding new components, classes, or functions from a detailed prompt or docstring.
*   **B. Code Refactoring**: Optimizing existing code for readability, performance, or to adhere to new API standards.
*   **C. Code Translation**: Migrating code from one programming language to another (e.g., Python to JavaScript).
*   **D. Documentation & Summarization**: Generating README files, creating docstrings, or summarizing complex code sections.
*   **E. Creative Brainstorming & Architecture**: Proposing novel solutions, suggesting architectural patterns, or outlining new features.
*   **F. Data Analysis & Extraction**: Parsing structured information from unstructured text (e.g., log files, reports) and performing analysis.
*   **G. Tool Use & Function Calling**: Executing a sequence of tool calls to achieve a complex, multi-step goal.

---

## 3. The Benchmarking Framework

This framework is the foundation for our decision-making process. It involves creating a standardized test suite and a runner to collect performance data.

### 3.1. Creating a Challenge Suite

For each task category, create a `challenges.json` file containing 5-10 representative prompts. Each challenge should include an "ideal" or "golden" answer for automated evaluation.

**Example `challenges_code_generation.json`:**
```json
[
  {
    "id": "CG001",
    "prompt": "Write a Python function `is_palindrome(s: str) -> bool` that checks if a string is a palindrome. It should be case-insensitive and ignore non-alphanumeric characters.",
    "eval": {
      "type": "unit_test",
      "test_cases": [
        {"input": "A man, a plan, a canal: Panama", "expected": true},
        {"input": "race a car", "expected": false}
      ]
    }
  }
]
```

### 3.2. Evaluation Metrics

For each model's response to a challenge, we will capture the following metrics:

| Metric | Description | How to Measure |
| :--- | :--- | :--- |
| **Correctness** | How accurately the model's output matches the desired outcome. | - **Unit Tests**: For code generation/refactoring, automatically run predefined tests against the output. <br>- **Linting Score**: For code, run a standard linter (e.g., `pylint`, `ruff`, `eslint`) and capture the score. <br>- **Semantic Similarity**: For text-based tasks, use a sentence-transformer model to calculate the cosine similarity between the model's output and the "golden" answer. |
| **Latency** | The time (in seconds) from sending the request to receiving the complete response. | Simple `time.time()` start/end capture around the API call. |
| **Input Tokens** | The number of tokens sent in the prompt. | Provided by the model's API response. |
| **Output Tokens**| The number of tokens in the generated response. | Provided by the model's API response. |
| **Estimated Cost**| The financial cost of the API call. | Calculated using the token counts and the provider's public pricing. |

**Model Pricing (per 1 Million Tokens, as of late 2025):**

| Model | Input Cost | Output Cost |
| :--- | :--- | :--- |
| **Claude 3.5 Sonnet** | $3.00 | $15.00 |
| **OpenAI GPT-4o** | $5.00 | $15.00 |
| **Google Gemini 1.5 Pro** | $3.50 | $10.50 |

*Note: Prices are subject to change and should be periodically updated.*

### 3.3. Implementation

*   **Benchmark Runner**: A script (`scripts/run_model_benchmarks.py`) that:
    1.  Loads the challenge suites.
    2.  Iterates through each challenge, sending the prompt to all three models.
    3.  Runs the appropriate evaluation for each response.
    4.  Collects all metrics.
*   **Data Storage**: The results should be saved to a structured file, such as `reports/model_benchmark_results.json`.

---

## 4. The Dynamic "Interviewer" Agent

This agent acts as an intelligent router. When assigned a task, its job is to choose the best LLM for the job based on the empirical data collected by the benchmarking framework.

### 4.1. Workflow

1.  **Task Analysis**: The Interviewer Agent receives a task. It uses a high-tier model (like GPT-4o or Claude 3.5 Sonnet) to classify the task into one of the predefined categories (A-G).

2.  **Consult Benchmark Data**: It queries the `model_benchmark_results.json` file, filtering for the identified task category. It ranks the models based on a weighted score.

    *   `Score = (weight_quality * avg_quality) - (weight_cost * avg_cost) - (weight_latency * avg_latency)`
    *   The weights (`weight_quality`, `weight_cost`, `weight_latency`) should be configurable, allowing you to prioritize what matters most for a given project (e.g., prioritize cost for personal projects).

3.  **Live Interview (Micro-Benchmark)**: For high-stakes or ambiguous tasks, the agent can perform a "live interview."
    *   It selects a representative, simple prompt from the challenge suite for that task category.
    *   It sends this prompt to the top two candidate models from the previous step.
    *   It evaluates their responses in real-time to make a final, context-aware decision. This helps account for any temporary model degradation or recent improvements not captured in the last full benchmark run.

4.  **Task Delegation**: The Interviewer Agent formats the original, full task prompt and delegates it to the selected LLM. It then returns the result to the user or the next agent in the chain.

### 4.2. Integration into `workspace_ops`

The Interviewer Agent should be integrated into your existing multi-agent framework (`conventions/AGENT_COOPERATION.md`) as a specialized "dispatcher" or "router" agent. It can be the first agent in any complex workflow, ensuring that all subsequent sub-tasks are handled by the most appropriate model.

---

## 5. Role-Based Evaluation for Project-Specific Agents

Beyond task-specific delegation, the Interviewer Agent can be extended to perform a deeper, project-level analysis, recommending the optimal LLM for *each defined agent role* within a larger multi-agent system (like your `editorial-assistant`).

### 5.1. Identifying Agent Roles

The first step is for the Interviewer Agent (or a human operator providing context) to understand the defined agent roles and their responsibilities within the target project. This typically involves:

*   **Code Review**: Analyzing the project's source code (e.g., Python scripts, TypeScript services) for agent implementations, class definitions, or function names that clearly delineate specific roles (e.g., `TitleSuggester`, `TranscriptSummarizer`, `CopyEditor`).
*   **Documentation Analysis**: Reading project documentation (`AGENT_COORDINATION.md`, `README.md`, `MCP_SERVER_SPEC.md`) that explicitly lists or describes agent functionalities and their purposes.
*   **MCP Service Inspection**: Examining the MCP server's exposed tools and resources to infer the underlying agent roles that fulfill those services.

Each identified role should be accompanied by a clear description of its primary responsibilities and the types of LLM-powered tasks it performs.

### 5.2. Mapping Roles to Task Categories & Developing Role-Specific Challenges

Once agent roles are identified, each role's core responsibilities can be mapped to the generic Task Categories defined in Section 2 (Code Generation, Documentation & Summarization, Creative Brainstorming, etc.).

For each role:
1.  **Identify Core Tasks**: Break down the role's responsibilities into discrete LLM-powered tasks.
2.  **Map to Categories**: Assign each core task to one or more relevant Task Categories.
3.  **Develop Role-Specific Challenges**: Create a set of challenge prompts that directly reflect the inputs and desired outputs of that role. Leverage existing project data (e.g., `test_transcript.txt`, `transcripts/`) to create realistic scenarios.

**Example for an `editorial-assistant` project:**

*   **Role**: `TranscriptSummarizer`
    *   **Responsibilities**: Condense long video transcripts into concise summaries, bullet points, or key takeaways.
    *   **Mapped Task Categories**: D. Documentation & Summarization, F. Data Analysis & Extraction.
    *   **Role-Specific Challenge**: Given `test_transcript.txt`, generate a 3-point summary and 5 keywords. Evaluate for conciseness, accuracy, and keyword relevance against a "golden" summary.

*   **Role**: `TitleSuggester`
    *   **Responsibilities**: Generate creative, SEO-friendly titles for videos based on summaries or topics.
    *   **Mapped Task Categories**: E. Creative Brainstorming & Architecture.
    *   **Role-Specific Challenge**: Given a video summary, generate 10 unique, catchy, and relevant video titles. Evaluate for creativity, uniqueness, and SEO potential (manual review or automated keyword density check).

*   **Role**: `CopyEditor`
    *   **Responsibilities**: Proofread video scripts or captions for grammatical errors, spelling mistakes, clarity, and adherence to style guides (`ap_styleguide.pdf`).
    *   **Mapped Task Categories**: D. Documentation & Summarization.
    *   **Role-Specific Challenge**: Given a draft video script, identify and correct grammatical errors, improve sentence structure, and suggest rephrasing for clarity. Evaluate against a human-edited version for accuracy and adherence to style guides.

### 5.3. Role-Based Benchmarking and Recommendation Generation

The Interviewer Agent then orchestrates a benchmark run for each identified role, using its specific challenges and evaluating against the defined metrics (quality, cost, latency).

Upon completion, the agent compiles a detailed report for the project, including:

1.  **Recommended LLM per Role**: For each agent role, a clear recommendation for the optimal LLM, accompanied by a justification based on the benchmark results.
2.  **Performance Overview**: A summary of how each model performed across all roles, highlighting overall strengths and weaknesses.
3.  **Cost Analysis**: A breakdown of the estimated cost savings or increases by adopting the recommended model assignments.
4.  **Actionable Implementation Adjustments**: Specific recommendations for modifying the project's codebase:
    *   **MCP Service Routing**: How to adjust the MCP server (`mcp-server/src/index.ts` or related files) to dynamically route tasks for a given role to its recommended LLM. This might involve updating function calls (`openai.chat.completions.create` to `anthropic.messages.create` or `google.generativeai.GenerativeModel`).
    *   **Agent Logic Updates**: If an agent's internal logic needs to be tailored to a specific model's output format or capabilities, recommendations for those changes.
    *   **Configuration Updates**: Suggestions for updating configuration files (e.g., environment variables for API keys) to support the new model assignments.

By applying this role-based evaluation, you can granularly optimize your multi-agent projects, ensuring each component leverages the most effective and efficient LLM for its specialized function.

---

## 6. Implementation Plan

**Phase 1: Framework & Initial Benchmark**
1.  Create the `knowledge/challenges/` directory and populate it with initial `challenges_*.json` files for at least 3 task categories.
2.  Implement the benchmark runner script (`scripts/run_model_benchmarks.py`).
3.  Execute the first benchmark run and generate the initial `reports/model_benchmark_results.json` file.

**Phase 2: Interviewer Agent v1 (Static Selection)**
1.  Create the `InterviewerAgent` class in Python.
2.  Implement the logic for Task Analysis and consulting the benchmark data to select a model.
3.  Integrate this agent into a simple, manual workflow where you can give it a prompt and see which model it chooses.

**Phase 3: Integration & Dynamic Capabilities**
1.  Formalize the Interviewer Agent within your `AGENT_REGISTRY.md`.
2.  Integrate it as the entry point for your multi-agent workflows.
3.  Implement the optional "Live Interview" (micro-benchmark) capability for more dynamic decision-making.

By following this methodology, you can create a sophisticated, cost-aware system that ensures you are always using the right tool for the job, backed by empirical data from your own specific use cases.
