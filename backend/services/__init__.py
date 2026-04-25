__all__ = [
    "AnalysisCacheService",
    "AnalysisService",
    "BackendRuntime",
    "BackofficeService",
    "BlueprintService",
    "ExportService",
    "PromptLibrary",
    "SessionHistoryService",
    "TelemetryService",
    "bootstrap_runtime",
    "build_demo_catalog",
    "build_demo_match_payload",
    "build_demo_rally_payload",
]


def __getattr__(name):
    if name == "AnalysisService":
        from .analysis_service import AnalysisService

        return AnalysisService
    if name in {"BackendRuntime", "bootstrap_runtime"}:
        from .runtime_service import BackendRuntime, bootstrap_runtime

        return {"BackendRuntime": BackendRuntime, "bootstrap_runtime": bootstrap_runtime}[name]
    if name == "TelemetryService":
        from .telemetry_service import TelemetryService

        return TelemetryService
    if name == "SessionHistoryService":
        from .session_history_service import SessionHistoryService

        return SessionHistoryService
    if name == "AnalysisCacheService":
        from .analysis_cache_service import AnalysisCacheService

        return AnalysisCacheService
    if name == "ExportService":
        from .export_service import ExportService

        return ExportService
    if name == "PromptLibrary":
        from .prompt_library import PromptLibrary

        return PromptLibrary
    if name == "BlueprintService":
        from .blueprint_service import BlueprintService

        return BlueprintService
    if name == "BackofficeService":
        from .backoffice_service import BackofficeService

        return BackofficeService
    if name in {"build_demo_catalog", "build_demo_match_payload", "build_demo_rally_payload"}:
        from .demo_payloads import build_demo_catalog, build_demo_match_payload, build_demo_rally_payload

        return {
            "build_demo_catalog": build_demo_catalog,
            "build_demo_match_payload": build_demo_match_payload,
            "build_demo_rally_payload": build_demo_rally_payload,
        }[name]
    raise AttributeError(f"module 'services' has no attribute {name!r}")
