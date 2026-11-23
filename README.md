# fireconf

Generate configuration text (e.g. FortiGate CLI) from layered YAML files and Jinja2 snippets.

You describe a device in YAML, write the config as small `.j2` snippets, and fireconf renders them.

## Installation

Requires Python 3.9+. Dependencies are installed automatically.

```bash
pip install git+https://github.com/Lufu251/fireconf.git
```

For a specific version, add a tag: `...fireconf.git@v0.1.0`.

This installs the library only. To run the example, clone the repo, because `configs/` and `snippets/` are not part of the package.

## Usage

**1. Write a YAML config.** Everything except `snippets` becomes template variables. `snippets` lists which templates to render, in order.

```yaml
# configs/example.yaml
snippets:
  - hostname

system:
  hostname: fw-01
```

**2. Write a snippet** named `<name>.j2`:

```jinja
{# snippets/hostname.j2 #}
config system global
    set hostname "{{ system.hostname }}"
end
```

**3. Render it.**

```python
from pathlib import Path
from fireconf import Config, ConfigRenderer

renderer = ConfigRenderer(Path("snippets"))

config = Config()
config.load_config(Path("configs/example.yaml"))
config.load_config(Path("configs/device_fgt70G.yaml"))  # layered on top

rendered = renderer.render_snippets(config)  # {snippet name: text}
for text in rendered.values():
    print(text)
```

Run the full example with `python main.py`.

## How layering works

- Files are merged one level deep: sections are merged key by key, and a key that already exists is overwritten (a warning is logged).
- Lists and scalars replace the whole section.
- Snippet names are appended in order; duplicates are skipped with a warning.
- Undefined variables raise an error instead of rendering as empty text.

## Using rendered output as input

Rendered snippets can be fed back in as variables, for example to build a guide from the generated CLI:

```python
guide_config = Config()
guide_config.set_vars(rendered, source="rendered cli snippets")
guide_config.set_snippets(["test/guide"])

print(renderer.render_snippets(guide_config)["test/guide"])
```

Inside `guide.j2` each rendered snippet is available as `{{ hostname }}`.
