import asyncio

import click
import pandas as pd
from rich.console import Console
from rich.table import Table

from src.analyzer import RelationshipAnalyzer
from src.api import GitHubAPI
from src.config import setup_logging
from src.storage import StorageEngine

console = Console()
setup_logging()


async def async_main(user: str, action: str, output: str):
    console.print(f"[bold blue]Analyzing GitHub user: {user}[/bold blue]")
    api = GitHubAPI()
    storage = StorageEngine()

    # Fetch data concurrently
    followers, following = await api.fetch_all(user)
    console.print(
        f"[green]Fetched {len(followers)} followers "
        f"and {len(following)} following.[/green]"
    )

    # Save to SQLite
    storage.save_users(user, followers, "followers")
    storage.save_users(user, following, "following")

    analyzer = RelationshipAnalyzer(user, storage)

    if action == "mutual":
        result = analyzer.get_mutual()
    elif action == "one-way":
        result = analyzer.get_one_way_following()
    elif action == "union":
        result = analyzer.get_union()
    elif action == "followers":
        result = list(analyzer.followers.values())
    elif action == "following":
        result = list(analyzer.following.values())
    else:
        result = []

    console.print(
        f"[bold cyan]Action '{action}' yielded {len(result)} results.[/bold cyan]"
    )

    if output == "table":
        table = Table(
            title=f"{user} - {action.capitalize()}",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("No.", style="dim", width=4)
        table.add_column("Login", style="cyan")
        table.add_column("Avatar URL", style="dim")
        table.add_column("HTML URL", style="blue")

        if action == "union":
            table.add_column("Relation Type")
            table.add_column("Is Following Back", justify="center")

        for idx, user_data in enumerate(result, 1):
            row = [
                str(idx),
                user_data["login"],
                user_data["avatar_url"],
                user_data["html_url"],
            ]
            if action == "union":
                row.append(user_data.get("relation_type", ""))
                is_following = user_data.get("is_following_back", False)
                row.append("✔" if is_following else "✗")
            table.add_row(*row)

        console.print(table)
    elif output == "csv":
        df = pd.DataFrame(result)
        df.to_csv(f"data/{user}_{action}.csv", index=False)
        console.print(f"[green]Saved to data/{user}_{action}.csv[/green]")
    elif output == "json":
        df = pd.DataFrame(result)
        df.to_json(f"data/{user}_{action}.json", orient="records", indent=2)
        console.print(f"[green]Saved to data/{user}_{action}.json[/green]")
    elif output == "html":
        df = pd.DataFrame(result)
        html_content = df.to_html(index=False, render_links=True, escape=False)
        with open(f"data/{user}_{action}.html", "w") as f:
            f.write(
                f"<html><head><title>{user} - {action}</title></head><body><h1>{user} - {action}</h1>{html_content}</body></html>"
            )
        console.print(f"[green]Saved HTML report to data/{user}_{action}.html[/green]")


@click.command()
@click.option("--user", required=True, help="GitHub username to analyze.")
@click.option(
    "--action",
    type=click.Choice(["followers", "following", "mutual", "one-way", "union"]),
    required=True,
    help="Analysis action to perform.",
)
@click.option(
    "--output",
    type=click.Choice(["table", "csv", "json", "html"]),
    default="table",
    help="Output format.",
)
def main(user, action, output):  # noqa: E501
    asyncio.run(async_main(user, action, output))


if __name__ == "__main__":
    main()
