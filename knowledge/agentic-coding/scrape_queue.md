# Crawl Queue

Entries to fetch when Crawl4AI access is approved. Capture full article text (markdown) plus key takeaways for Librarian knowledge base.

## Completed on 2025-11-11
- https://www.anthropic.com/engineering/claude-code-best-practices — stored in `knowledge/anthropic_claude_code_best_practices.raw.md`.
- https://www.ranthebuilder.cloud/post/agentic-ai-prompting-best-practices-for-smarter-vibe-coding — stored in `knowledge/ranthebuilder_agentic_prompting.raw.md`.
- https://www.reddit.com/r/AI_Agents/comments/1lpj771/ai_agent_best_practices_from_one_year_as_ai/ — stored in `knowledge/reddit_ai_agent_best_practices.raw.md`.
- https://github.com/ashishpatel26/500-AI-Agents-Projects?tab=readme-ov-file — stored in `knowledge/ashishpatel26_500_agents.raw.md`.

## Next targets
1. https://docs.anthropic.com/en/docs/build-with-claude/agents/building-effective-agents — Anthropic’s deeper dive on agent design patterns.
2. https://python.langchain.com/docs/how_to/agents/agent_best_practices — LangChain/LangGraph operational guidance.
3. https://platform.openai.com/docs/guides/code — OpenAI guidance on coding agents and assistant guardrails.

After fetching each item, store cleaned markdown and a short summary in `knowledge/`.
