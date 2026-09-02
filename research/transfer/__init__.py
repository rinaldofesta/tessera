"""Raw-data-free analysis for Tessera's synthetic-to-real transfer study."""

from .analysis import StudyError, analyze_study, kendall_tau_b, render_markdown

__all__ = ["StudyError", "analyze_study", "kendall_tau_b", "render_markdown"]
