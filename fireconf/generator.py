"""Render Jinja2 snippets from layered YAML configuration files."""

import copy
import logging
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

logger = logging.getLogger(__name__)


class Config:
    """Configuration data loaded from YAML files or in-memory dicts.

    Sources are layered on top of each other with `load_config` and
    `load_vars`.

    Attributes:
        data: Top-level sections of the configuration, keyed by section name.
        snippets: Names of the snippets to render, without duplicates.
    """

    def __init__(self) -> None:
        """Create an empty configuration."""
        self.data: dict[str, Any] = {}
        self.snippets: list[str] = []

    def load_config(self, config_file: Path) -> None:
        """Merge a YAML file into the existing configuration.

        The top-level key `snippets` is treated separately: it must be a list
        of snippet names and is passed to `set_snippets`. Everything else is
        passed to `set_vars`. A file without `snippets` is fine.

        Args:
            config_file: Path to the YAML file to merge in.

        Raises:
            ValueError: If `snippets` is not a list of strings.
        """
        with open(config_file, "r") as file:
            extra = yaml.safe_load(file) or {}

        # pop so 'snippets' does not end up in self.data as a variable
        snippets = extra.pop("snippets", None)
        if snippets is None:
            snippets = []

        if not isinstance(snippets, list) or not all(
            isinstance(name, str) for name in snippets
        ):
            raise ValueError(
                f"{config_file.name}: 'snippets' must be a list of strings"
            )

        self.set_snippets(snippets, config_file.name)
        self.set_vars(extra, config_file.name)

    def set_vars(self, variables: dict[str, Any], source: str = "vars") -> None:
        """Merge a dict from memory into the existing variables.

        The merge goes exactly one level deep:

        - A section that does not exist yet is added.
        - If a section is a dict in both the existing and the new data, the
          keys inside it are merged. Keys only present in the existing data
          are kept, and a warning is logged for each key that is overwritten.
        - In all other cases (lists, scalars, mixed types) the whole section
          is replaced and a warning is logged.

        Args:
            variables: Sections to merge in, keyed by section name.
            source: Label used in log warnings to show where the values
                came from.
        """
        # deepcopy so later merges don't modify the caller's dict
        variables = copy.deepcopy(variables)

        for section, values in variables.items():
            current = self.data.get(section)

            # New section: nothing to overwrite
            if current is None:
                self.data[section] = values
                continue

            # Both sides are dicts: merge one layer deeper
            if isinstance(current, dict) and isinstance(values, dict):
                for key, value in values.items():
                    if key in current:
                        logger.warning(
                            "%s overwrites existing variable '%s.%s'",
                            source, section, key,
                        )
                    current[key] = value
                continue

            # Lists or scalars can't be merged, the whole section is replaced
            logger.warning("%s replaces the whole section '%s'", source, section)
            self.data[section] = values

    def set_snippets(self, snippets: list[str], source: str = "snippets") -> None:
        """Add snippet names to the existing list.

        Names that are not in the list yet are appended in the given order.
        A name that is already present is skipped and a warning is logged.
        The position of existing names never changes.

        Args:
            snippets: Snippet names, without the `.j2` extension.
            source: Label used in log warnings to show where the names
                came from.
        """
        for name in snippets:
            if name in self.snippets:
                logger.warning(
                    "%s: snippet '%s' is already present, order of the list not changed",
                    source, name,
                )
                continue
            self.snippets.append(name)


class ConfigRenderer:
    """Renders Jinja2 snippet templates with the values from a `Config`."""

    def __init__(self, snippet_dir: Path) -> None:
        """Set up the Jinja2 environment.

        Args:
            snippet_dir: Directory containing the `<name>.j2` snippet templates.

        Raises:
            RuntimeError: If `snippet_dir` does not exist.
        """
        if not snippet_dir.exists():
            raise RuntimeError("snippets directory does not exist")

        self._env = Environment(
            loader=FileSystemLoader(snippet_dir),
            trim_blocks=True,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )

    def render_snippet(self, name: str, config: Config) -> str:
        """Render a single snippet.

        The template `<name>.j2` is loaded from the snippet directory and
        rendered with the full configuration data.

        Args:
            name: Snippet name, without the `.j2` extension.
            config: The configuration used as template variables.

        Returns:
            The rendered text.

        Raises:
            jinja2.TemplateNotFound: If there is no template for `name`.
            jinja2.UndefinedError: If the template uses a variable that is
                not in the configuration.
        """
        template = self._env.get_template(f"{name}.j2")
        return template.render(config.data)

    def render_snippets(self, config: Config) -> dict[str, str]:
        """Render several snippets.

        Args:
            names: Snippet names to render, without the `.j2` extension.
            config: The configuration used as template variables.

        Returns:
            Rendered text per snippet name, in the order of `names`.

        Raises:
            jinja2.TemplateNotFound: If a name has no matching template.
            jinja2.UndefinedError: If a template uses a variable that is not
                in the configuration.
        """
        return {snippet: self.render_snippet(snippet, config) for snippet in config.snippets}
