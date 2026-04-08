"""lintルール群。"""

from drafter.linter.rules.pandoc_compat import LintError, check_pandoc_compat

ALL_RULES = [check_pandoc_compat]

__all__ = ["ALL_RULES", "LintError", "check_pandoc_compat"]
