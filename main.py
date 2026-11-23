"""Example: generate FortiGate CLI snippets and a guide from them.

Expected layout next to this file:

    configs/example.yaml
    configs/device_fgt70G.yaml
    snippets/<name>.j2
    snippets/test/guide.j2
"""

from pathlib import Path

from fireconf.generator import Config, ConfigRenderer

BASE_DIR = Path(__file__).parent


def print_rendered(rendered: dict[str, str]) -> None:
    """Print every rendered snippet.

    Args:
        rendered: Rendered text per snippet name.
    """
    for text in rendered.values():
        print(text)


def main() -> None:
    """Render the CLI snippets, then the guide that is built from them."""
    renderer = ConfigRenderer(BASE_DIR / "snippets")

    # Step 1: load the base file, then the device file on top of it
    cli_config = Config()
    cli_config.load_config(BASE_DIR / "configs" / "example.yaml")
    cli_config.load_config(BASE_DIR / "configs" / "device_fgt70G.yaml")

    # Step 2: render the CLI snippets listed under `snippets:` in the YAML files
    rendered_cli = renderer.render_snippets(cli_config)
    print_rendered(rendered_cli)

    # Step 3: use the rendered CLI text as variables for the guide
    guide_config = Config()
    guide_config.set_vars(rendered_cli, source="rendered cli snippets")
    guide_config.set_snippets(["test/guide"])

    # Step 4: render the guide
    rendered_guide = renderer.render_snippets(guide_config)
    print_rendered(rendered_guide)


if __name__ == "__main__":
    main()