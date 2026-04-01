from pathlib import Path


def extract_extension(filename: str) -> str:
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def ensure_supported_extension(filename: str, supported_extensions: tuple[str, ...]) -> str:
    extension = extract_extension(filename)
    if extension not in supported_extensions:
        allowed = ", ".join(sorted(supported_extensions))
        raise ValueError(f"Неподдерживаемый формат файла. Разрешены: {allowed}")
    return extension


def ensure_workspace_scope(resource_workspace_id: str, requested_workspace_id: str) -> None:
    if resource_workspace_id != requested_workspace_id:
        raise ValueError("Ресурс недоступен в контексте текущего workspace")
