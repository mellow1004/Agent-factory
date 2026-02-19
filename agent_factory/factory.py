"""
factory.py — Core orchestration for the Agent Factory.

Accepts a role description, calls the Anthropic API to generate
tailored agent content, then writes a complete agent folder to disk.

Usage as a library (for Streamlit or other frontends):
    from agent_factory import create_agent
    result = create_agent("SaaS Legal Expert", model="claude-sonnet-4-5-20250929")

Usage from CLI:
    python create_agent.py "Cloud Architect"
"""

from __future__ import annotations

import json
import os
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from jinja2 import Environment, FileSystemLoader

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEMPLATES_DIR = Path(__file__).parent / "templates"
AGENTS_DIR = Path(__file__).parent / "agents"
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert AI-systems architect. Your job is to design a
    specialized agent definition given a role description.

    Return your answer as a single JSON object with these keys — no
    markdown fences, no commentary outside the JSON:

    {
      "agent_name":        "<snake_case identifier, e.g. saas_legal_expert>",
      "display_name":      "<Human-friendly title>",
      "tagline":           "<One-sentence elevator pitch for this agent>",
      "domain":            "<Primary knowledge domain>",
      "tone":              "<Communication style, e.g. formal / conversational>",
      "primary_tasks": [
        "<task 1>",
        "<task 2>",
        "<task 3>"
      ],
      "tools": [
        "<tool or capability the agent should use>"
      ],
      "constraints": [
        "<guardrail or boundary>"
      ],
      "instructions":      "<Detailed system-prompt text (300-500 words) that will be placed in instructions.md. Write in second person ('You are…'). Include sections: Role, Expertise, Communication Style, Workflow, and Limitations.>",
      "example_prompts": [
        "<Example user prompt 1>",
        "<Example user prompt 2>",
        "<Example user prompt 3>"
      ]
    }
""")


def _build_user_prompt(role_description: str, instructions: str | None = None) -> str:
    prompt = (
        f"Design an agent definition for the following role:\n\n"
        f"\"{role_description}\"\n\n"
    )
    if instructions:
        prompt += (
            f"The user has also provided the following instructions. Weave these into the agent's "
            f"behavior, goals, and expertise. Reflect them in the \"instructions\" field (the text that "
            f"will go into instructions.md) so the final agent behaves accordingly:\n\n"
            f"\"\"\"\n{instructions}\n\"\"\"\n\n"
        )
    prompt += "Respond with the JSON object only."
    return prompt


# ---------------------------------------------------------------------------
# API interaction
# ---------------------------------------------------------------------------

def _call_anthropic(
    role_description: str,
    *,
    instructions: str | None = None,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Send the role description (and optional user instructions) to Anthropic and parse the JSON response."""
    client = Anthropic(api_key=api_key)  # uses ANTHROPIC_API_KEY env var if None

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": _build_user_prompt(role_description, instructions)},
        ],
    )

    raw_text = message.content[0].text.strip()

    # Strip markdown code fences if the model wraps them anyway
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Anthropic returned invalid JSON.\n\n--- raw response ---\n{raw_text}"
        ) from exc


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def _render_templates(agent_data: dict[str, Any]) -> dict[str, str]:
    """Render all Jinja2 templates and return {filename: content}."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    rendered: dict[str, str] = {}
    for template_file in TEMPLATES_DIR.glob("*.j2"):
        output_name = template_file.stem  # e.g. instructions.md
        template = env.get_template(template_file.name)
        rendered[output_name] = template.render(
            **agent_data,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    return rendered


# ---------------------------------------------------------------------------
# Folder writer
# ---------------------------------------------------------------------------

def _write_agent_folder(
    agent_name: str,
    rendered_files: dict[str, str],
    agent_data: dict[str, Any],
    output_dir: Path | None = None,
) -> Path:
    """Create the agent folder and write all files into it."""
    base = output_dir or AGENTS_DIR
    agent_dir = base / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Write rendered template files
    for filename, content in rendered_files.items():
        (agent_dir / filename).write_text(content, encoding="utf-8")

    # Write the raw generation data for reproducibility
    (agent_dir / "generation_data.json").write_text(
        json.dumps(agent_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Write the execution script
    _write_run_script(agent_dir, agent_name)

    return agent_dir


def _write_run_script(agent_dir: Path, agent_name: str) -> None:
    """Write a ready-to-run Python script that loads this agent's instructions."""
    script = textwrap.dedent(f'''\
        #!/usr/bin/env python3
        """
        run_agent.py — Execute the {agent_name} agent in an interactive loop.

        Usage:
            python run_agent.py
            python run_agent.py "Your question here"
        """

        from __future__ import annotations

        import sys
        from pathlib import Path

        from anthropic import Anthropic

        AGENT_DIR = Path(__file__).parent
        INSTRUCTIONS = (AGENT_DIR / "instructions.md").read_text(encoding="utf-8")
        MODEL = "claude-sonnet-4-5-20250929"


        def run(user_input: str | None = None) -> None:
            client = Anthropic()
            conversation: list[dict] = []

            if user_input:
                prompts = [user_input]
            else:
                prompts = None  # interactive mode

            print(f"\\n🤖  Agent loaded: {{AGENT_DIR.name}}")
            print("    Type 'quit' or 'exit' to stop.\\n")

            while True:
                if prompts:
                    prompt = prompts.pop(0)
                else:
                    try:
                        prompt = input("You: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        break

                if prompt.lower() in ("quit", "exit", "q"):
                    break

                conversation.append({{"role": "user", "content": prompt}})

                response = client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=INSTRUCTIONS,
                    messages=conversation,
                )

                reply = response.content[0].text
                conversation.append({{"role": "assistant", "content": reply}})
                print(f"\\nAgent: {{reply}}\\n")

                if prompts is not None and not prompts:
                    break  # single-shot mode


        if __name__ == "__main__":
            run(sys.argv[1] if len(sys.argv) > 1 else None)
    ''')
    script_path = agent_dir / "run_agent.py"
    script_path.write_text(script, encoding="utf-8")
    script_path.chmod(0o755)


# ---------------------------------------------------------------------------
# Public API  (importable by Streamlit, CLI, tests, etc.)
# ---------------------------------------------------------------------------

class AgentFactory:
    """Stateful factory — useful when you want to customise defaults."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        output_dir: Path | str | None = None,
    ):
        self.model = model
        self.api_key = api_key
        self.output_dir = Path(output_dir) if output_dir else AGENTS_DIR

    def create(self, role_description: str, instructions: str | None = None) -> dict[str, Any]:
        """Generate an agent and return a summary dict."""
        return create_agent(
            role_description,
            instructions=instructions,
            model=self.model,
            api_key=self.api_key,
            output_dir=self.output_dir,
        )

    def create_agent(self, role_description: str, instructions: str | None = None) -> dict[str, Any]:
        """Convenience alias for create(): generate an agent and return a summary dict."""
        return self.create(role_description, instructions=instructions)

    def list_agents(self) -> list[str]:
        """Return names of all generated agents."""
        if not self.output_dir.exists():
            return []
        return sorted(
            d.name for d in self.output_dir.iterdir()
            if d.is_dir() and (d / "instructions.md").exists()
        )


def create_agent(
    role_description: str,
    *,
    instructions: str | None = None,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """
    One-call convenience function: describe a role (and optional instructions) → get an agent folder.

    Returns a dict with keys:
        agent_name, display_name, agent_dir, files_written
    """
    output_path = Path(output_dir) if output_dir else AGENTS_DIR

    # 1. Generate structured agent definition via the API
    agent_data = _call_anthropic(
        role_description,
        instructions=instructions,
        model=model,
        api_key=api_key,
    )
    agent_name = agent_data["agent_name"]

    # 2. Weave user instructions into the agent's instructions.md if provided
    if instructions:
        existing = agent_data.get("instructions", "") or ""
        agent_data["instructions"] = (
            f"{existing.rstrip()}\n\n---\n\n## Användarens instruktioner\n\n{instructions}"
        )

    # 3. Render templates with the generated data
    rendered = _render_templates(agent_data)

    # 4. Write everything to disk
    agent_dir = _write_agent_folder(agent_name, rendered, agent_data, output_path)

    return {
        "agent_name": agent_name,
        "display_name": agent_data.get("display_name", agent_name),
        "agent_dir": str(agent_dir),
        "files_written": sorted(f.name for f in agent_dir.iterdir()),
        "data": agent_data,
    }
