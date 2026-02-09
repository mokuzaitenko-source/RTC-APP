# Prompting Book

## Chapter 1: Foundational Prompt Techniques (Basics)
Used for most everyday tasks.

- Direct / Zero-Shot: Simple instruction, no examples
- One-Shot / Few-Shot / Multi-Shot: Show examples to define patterns
- Role / Persona Prompting: Assign expertise or perspective
- Instruction Prompting: Explicit commands
- Contextual Priming: Provide background first
- Output Priming: Start the response format
- Style Mimicry: Match a tone or voice

## Chapter 2: Reasoning and Decomposition Techniques
Used for multi-step logic, math, analysis, or planning.

- Chain-of-Thought (CoT): Step-by-step reasoning
- Zero-Shot / Few-Shot CoT: With or without examples
- Self-Ask: Generate and answer sub-questions
- Least-to-Most: Solve easy parts first
- Step-Back / Abstraction: Zoom out before solving
- Skeleton-of-Thoughts: Outline first, then fill
- Tree / Graph-of-Thoughts: Explore multiple reasoning paths
- Program-Aided (PAL): Use code to reason
- ReAct: Reason + act (tool use)
- Generated Knowledge: Create facts before solving

## Chapter 3: Verification and Quality Control
Used to improve correctness and trust.

- Chain-of-Verification: Check answers step-by-step
- Self-Consistency: Generate multiple answers, pick majority
- Think-Twice / Verify-Step-by-Step
- Confidence Calibration: Rate certainty
- Hallucination Avoidance Prompting

## Chapter 4: Iteration and Refinement
Used for improving outputs over time.

- Prompt Chaining: Sequential prompts
- Self-Refine / Reflexion: Improve past outputs
- Active Prompting: Model generates examples
- Automatic Prompt Engineer (APE)
- Human-in-the-Loop: User feedback cycles

## Chapter 5: Retrieval and Tool-Integrated Prompting
Used when accuracy or freshness matters.

- RAG / RAP: Retrieve external data
- Chunking: Split long inputs
- ART: Automatic tool selection
- Batch Prompting: Multiple queries at once

## Chapter 6: Constraints, Safety, and Defense
Used in production or sensitive tasks.

- Negative Examples (what not to do)
- Ethical Alignment Prompting
- Prompt Injection Defense
- Constraint-Heavy Prompting

## Chapter 7: Agentic and Evolutionary Prompting
Used for automation and research (not everyday use).

- Agentic Prompting: Autonomous agents
- Evolutionary Prompting / PromptBreeder
- Ensemble Prompting
- Language Model Cascading

## Chapter 8: Multimodal and Creative Extensions
Used for images, emotion, and design.

- Multimodal Prompting (text + image)
- Visual Prompting
- Emotion / Directional Stimulus Prompting
- Contrastive and Counterfactual Prompting
- Reverse Prompting
- Time-Travel Prompting

## Hierarchy (Mental Model)

- Level 0 - Basics: Direct, Role, Instruction
- Level 1 - Examples: One-Shot, Few-Shot, Output Structure
- Level 2 - Reasoning: Decompose, Step-Back, CoT
- Level 3 - Exploration: ToT, Ensembles, Self-Refine
- Level 4 - Systems: RAG, Agents, Evolutionary Prompts

## Key Insight
Most techniques are variations of a small set of moves:
Instruct -> Example -> Decompose -> Abstract -> Verify -> Iterate -> Retrieve -> Constrain -> Evolve
