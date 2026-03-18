import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
import questionary
from rich import print
from rich.rule import Rule
from rich.panel import Panel

app = typer.Typer()


def check_python_version() -> None:
    """Check if Python >= 3.12 is installed."""
    if sys.version_info < (3, 12):
        print(f"[red]❌ Python 3.12+ required. Current: {sys.version_info.major}.{sys.version_info.minor}[/red]")
        print("[yellow]Install from: https://www.python.org/downloads/[/yellow]")
        raise typer.Exit(1)


def check_uv_installed() -> None:
    """Check if uv is installed."""
    if shutil.which("uv") is None:
        print("[red]❌ uv package manager not found[/red]")
        print("[yellow]Install from: https://docs.astral.sh/uv/getting-started/installation/[/yellow]")
        raise typer.Exit(1)


def snake_case(text: str) -> str:
    """Convert text to snake_case."""
    return text.lower().replace("-", "_").replace(" ", "_")


def get_system_username() -> str:
    """Get system username."""
    return os.environ.get("USER", "bindu_user")


def run_command(cmd: list[str], cwd: Optional[str] = None) -> bool:
    """Run shell command and return success status."""
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[red]❌ Command failed: {' '.join(cmd)}[/red]")
        if e.stderr:
            print(f"[red]{e.stderr}[/red]")
        return False


@app.callback(invoke_without_command=True)
def onboard() -> None:
    """
    🎯 Bindu Agent Onboarding Flow
    
    Creates a new Bindu agent project with interactive setup.
    """
    print(Panel("[bold cyan]🚀 Bindu Agent Onboarding[/bold cyan]", expand=False))
    
    # ============= STEP 0: Pre-check =============
    print(Rule("[yellow]Pre-check[/yellow]", style="yellow"))
    
    check_python_version()
    check_uv_installed()
    print("[green]✅ Python 3.12+[/green]")
    print("[green]✅ uv installed[/green]")
    
    # ============= STEP 1: Core project inputs =============
    print()
    print(Rule("[cyan]Project Setup[/cyan]", style="cyan"))
    
    project_name = questionary.text(
        "📁 Project name?",
        default="my-bindu-agent"
    ).ask()
    
    if not project_name:
        print("[red]❌ Project name cannot be empty[/red]")
        raise typer.Exit(1)
    
    use_defaults = questionary.confirm(
        "🎯 Use default configuration?",
        default=True
    ).ask()
    
    # ============= STEP 2: Handle configuration mode =============
    if use_defaults:
        print("[cyan]📋 Using default configuration...[/cyan]")
        project_slug = snake_case(project_name)
        author = get_system_username()
        email = ""
        github_handle = ""
        dockerhub_username = ""
        agent_framework = "agno"
        skill_names = ""
        auth_provider = "n"
        observability_provider = "none"
        storage_type = "memory"
        scheduler_type = "memory"
        security_features = "did-only"
        enable_paywall = "n"
        include_github_actions = "n"
        open_source_license = "MIT license"
    else:
        print()
        print(Rule("[yellow]Custom Configuration[/yellow]", style="yellow"))
        
        author = questionary.text(
            "✏️  Author name?",
            default=get_system_username()
        ).ask() or get_system_username()
        
        email = questionary.text(
            "📧 Email?",
            default=""
        ).ask() or ""
        
        github_handle = questionary.text(
            "🐙 GitHub handle?",
            default=""
        ).ask() or ""
        
        dockerhub_username = questionary.text(
            "🐳 DockerHub username?",
            default=""
        ).ask() or ""
        
        agent_framework = questionary.select(
            "🤖 Agent framework?",
            choices=["agno", "langchain", "crew", "fastagent", "openai agent", "google adk agent", "custom"],
            default="agno"
        ).ask()
        
        skill_names = questionary.text(
            "🧠 Skill names? (comma-separated, or press Enter to skip)",
            default=""
        ).ask() or ""
        
        auth_provider = questionary.confirm(
            "🔐 Enable authentication?",
            default=False
        ).ask()
        auth_provider = "y" if auth_provider else "n"
        
        observability_provider = questionary.select(
            "📊 Observability provider?",
            choices=["none", "phoenix", "jaeger", "langfuse"],
            default="none"
        ).ask()
        
        storage_type = questionary.select(
            "💾 Storage type?",
            choices=["memory", "postgres"],
            default="memory"
        ).ask()
        
        scheduler_type = questionary.select(
            "⏱️  Scheduler type?",
            choices=["memory", "redis"],
            default="memory"
        ).ask()
        
        security_features = questionary.select(
            "🔒 Security features?",
            choices=["did-and-pki", "did-only", "pki-only", "none"],
            default="did-only"
        ).ask()
        
        enable_paywall = questionary.confirm(
            "💳 Enable paywall?",
            default=False
        ).ask()
        enable_paywall = "y" if enable_paywall else "n"
        
        include_github_actions = questionary.confirm(
            "🐙 Include GitHub Actions?",
            default=False
        ).ask()
        include_github_actions = "y" if include_github_actions else "n"
        
        open_source_license = questionary.select(
            "📜 Open source license?",
            choices=[
                "Apache Software License 2.0",
                "MIT license",
                "BSD license",
                "ISC license",
                "GNU General Public License v3",
                "Not open source"
            ],
            default="MIT license"
        ).ask()
        
        project_slug = snake_case(project_name)
    
    # ============= STEP 3: Run cookiecutter (non-interactive) =============
    print()
    print(Rule("[green]Creating Project[/green]", style="green"))
    
    cookiecutter_url = "https://github.com/getbindu/create-bindu-agent.git"
    
    cookiecutter_args = [
        "uvx",
        "cookiecutter",
        cookiecutter_url,
        "--no-input",
        "--overwrite-if-exists",
        f"author={author}",
        f"email={email}",
        f"author_github_handle={github_handle}",
        f"dockerhub_username={dockerhub_username}",
        f"project_name={project_name}",
        f"project_slug={project_slug}",
        f"project_description=A Bindu AI agent for intelligent task handling",
        f"agent_framework={agent_framework}",
        f"skill_names={skill_names}",
        f"auth_provider={auth_provider}",
        f"observability_provider={observability_provider}",
        f"storage_type={storage_type}",
        f"scheduler_type={scheduler_type}",
        f"security_features={security_features}",
        f"enable_paywall={enable_paywall}",
        f"include_github_actions={include_github_actions}",
        f"open_source_license={open_source_license}",
    ]
    
    print(f"[cyan]🍪 Running cookiecutter...[/cyan]")
    if not run_command(cookiecutter_args):
        raise typer.Exit(1)
    
    # ============= STEP 4: Move into project directory =============
    project_dir = Path.cwd() / project_name
    if not project_dir.exists():
        print(f"[red]❌ Project directory not created: {project_dir}[/red]")
        raise typer.Exit(1)
    
    print(f"[green]✅ Project created at: {project_dir}[/green]")
    
    # ============= STEP 5: Create .env file =============
    env_example = project_dir / ".env.example"
    env_file = project_dir / ".env"
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print(f"[green]✅ .env file created[/green]")
    
    # ============= STEP 6: Ask environment-related inputs =============
    print()
    print(Rule("[yellow]Environment Setup[/yellow]", style="yellow"))
    
    openrouter_key = questionary.password(
        "🔑 OPENROUTER API key? (press Enter to skip)",
        default=""
    ).ask() or ""
    
    mem0_key = questionary.password(
        "🧠 MEM0 API key? (press Enter to skip)",
        default=""
    ).ask() or ""
    
    # Write to .env file
    if env_file.exists():
        env_content = env_file.read_text()
        
        # Update or add OPENROUTER_API_KEY
        if "OPENROUTER_API_KEY" in env_content:
            env_content = env_content.replace(
                [line for line in env_content.split("\n") if line.startswith("OPENROUTER_API_KEY")][0],
                f"OPENROUTER_API_KEY={openrouter_key}"
            )
        else:
            env_content += f"\nOPENROUTER_API_KEY={openrouter_key}"
        
        # Update or add MEM0_API_KEY
        if "MEM0_API_KEY" in env_content:
            env_content = env_content.replace(
                [line for line in env_content.split("\n") if line.startswith("MEM0_API_KEY")][0],
                f"MEM0_API_KEY={mem0_key}"
            )
        else:
            env_content += f"\nMEM0_API_KEY={mem0_key}"
        
        env_file.write_text(env_content)
        print("[green]✅ Environment variables set[/green]")
    
    # ============= STEP 7: Install dependencies =============
    print()
    print(Rule("[cyan]Installing Dependencies[/cyan]", style="cyan"))
    
    if not run_command(["uv", "sync"], cwd=str(project_dir)):
        raise typer.Exit(1)
    
    print("[green]✅ Dependencies installed[/green]")
    
    # ============= STEP 8: Final output =============
    print()
    print(Panel(
        f"""[green]✅ Project created successfully[/green]

[bold]📂 Project:[/bold] ./{project_name}

[bold]👉 To start your agent:[/bold]
[cyan]cd {project_name}[/cyan]
[cyan]uv run python -m {project_slug}.main[/cyan]

[bold]💡 Next steps:[/bold]
  • Edit [cyan].env[/cyan] if needed
  • Add skills in [cyan]/{project_slug}/skills[/cyan]
  • Run [cyan]uv run python -m {project_slug}.main[/cyan]""",
        expand=False,
        style="green"
    ))


if __name__ == "__main__":
    app()