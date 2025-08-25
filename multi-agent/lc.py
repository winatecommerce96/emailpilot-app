#!/usr/bin/env python3
"""
LangChain CLI tool for EmailPilot
Usage: python lc.py <command> [options]
"""

import sys
import os
import click

# Add multi-agent to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
multi_agent_dir = os.path.join(current_dir, 'multi-agent')
sys.path.insert(0, multi_agent_dir)

@click.group()
def cli():
    """LangChain CLI for EmailPilot"""
    pass

@cli.group()
def rag():
    """RAG commands"""
    pass

@rag.command('ask')
@click.option('-q', '--question', required=True, help='Question to ask')
@click.option('-k', type=int, default=5, help='Number of documents to retrieve')
@click.option('--max-tokens', type=int, default=600, help='Max tokens in response')
def rag_ask(question, k, max_tokens):
    """Ask a question using RAG"""
    try:
        # Import from the multi-agent package
        from integrations.langchain_core.rag.chain import rag_query
        result = rag_query(question, k=k, max_tokens=max_tokens)
        click.echo(f"Answer: {result.get('answer', 'No answer')}")
        if result.get('citations'):
            click.echo("\nCitations:")
            for citation in result['citations']:
                click.echo(f"  - {citation}")
    except ImportError as e:
        click.echo(f"Error: LangChain Core not installed - {e}")
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.group()
def agent():
    """Agent commands"""
    pass

@agent.command('run')
@click.option('-t', '--task', required=True, help='Task to execute')
@click.option('--brand', help='Brand context')
@click.option('--user-id', help='User ID')
@click.option('--timeout', type=int, default=30, help='Timeout in seconds')
def agent_run(task, brand, user_id, timeout):
    """Run an agent task"""
    try:
        from integrations.langchain_core.agents.agent import run_agent
        result = run_agent(
            task=task,
            brand=brand,
            user_id=user_id,
            timeout=timeout
        )
        click.echo(f"Result: {result.get('final_answer', 'No result')}")
        if result.get('tool_calls'):
            click.echo(f"Tools used: {len(result['tool_calls'])}")
    except ImportError as e:
        click.echo(f"Error: LangChain Core not installed - {e}")
    except Exception as e:
        click.echo(f"Error: {e}")

if __name__ == '__main__':
    cli()
