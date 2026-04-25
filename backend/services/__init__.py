__all__ = ["AnalysisService", "BackendRuntime", "bootstrap_runtime"]


def __getattr__(name):
    if name == "AnalysisService":
        from .analysis_service import AnalysisService

        return AnalysisService
    if name in {"BackendRuntime", "bootstrap_runtime"}:
        from .runtime_service import BackendRuntime, bootstrap_runtime

        return {"BackendRuntime": BackendRuntime, "bootstrap_runtime": bootstrap_runtime}[name]
    raise AttributeError(f"module 'services' has no attribute {name!r}")
