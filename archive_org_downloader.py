#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


ARCHIVE_METADATA_URL = "https://archive.org/metadata/{id}"
ARCHIVE_DOWNLOAD_URL = "https://archive.org/download/{id}/{name}"
DEFAULT_EXTENSIONS = [".txt", ".cue", ".bin"]


def extract_identifier_and_subdir(url_or_id: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(url_or_id)
    if parsed.scheme and parsed.netloc:
        path = parsed.path.strip("/")
        if path.startswith("details/"):
            parts = path[len("details/") :].split("/")
        elif path.startswith("download/"):
            parts = path[len("download/") :].split("/")
        else:
            parts = path.split("/")

        if not parts or not parts[0]:
            raise ValueError(f"Impossible d'extraire l'identifiant depuis l'URL : {url_or_id}")

        identifier = parts[0]
        subdir_components = [urllib.parse.unquote(p) for p in parts[1:] if p]
        subdir = "/".join(subdir_components)
        return identifier, subdir
    return url_or_id, ""


def extract_identifier(url_or_id: str) -> str:
    identifier, _ = extract_identifier_and_subdir(url_or_id)
    return identifier


def get_archive_files(identifier: str) -> list[dict]:
    url = ARCHIVE_METADATA_URL.format(id=urllib.parse.quote(identifier))
    with urllib.request.urlopen(url) as response:
        data = json.load(response)
    return data.get("files", [])


def is_valid_file(name: str, extensions: list[str]) -> bool:
    lower_name = name.lower()
    return any(lower_name.endswith(ext) for ext in extensions)


def build_local_path(download_dir: str, file_name: str) -> str:
    clean_name = file_name.replace("/", os.sep)
    return os.path.join(download_dir, clean_name)


def quote_archive_name(name: str) -> str:
    components = name.split("/")
    return "/".join(urllib.parse.quote(component, safe="") for component in components)


def format_bytes(size: int) -> str:
    for unit in ["octets", "Ko", "Mo", "Go"]:
        if size < 1024 or unit == "Go":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} Go"


def download_file(identifier: str, file_name: str, dest_path: str) -> None:
    url_name = quote_archive_name(file_name)
    url = ARCHIVE_DOWNLOAD_URL.format(id=urllib.parse.quote(identifier), name=url_name)
    print(f"Téléchargement: {file_name} -> {dest_path}")

    def reporthook(block_count: int, block_size: int, total_size: int) -> None:
        downloaded = block_count * block_size
        if total_size > 0:
            downloaded = min(downloaded, total_size)
            percent = downloaded / total_size * 100
            bar_width = 40
            filled = int(bar_width * downloaded / total_size)
            bar = "#" * filled + "-" * (bar_width - filled)
            sys.stdout.write(
                f"\r[{bar}] {percent:5.1f}% {format_bytes(downloaded)}/{format_bytes(total_size)}"
            )
        else:
            sys.stdout.write(f"\rTéléchargé: {format_bytes(downloaded)}")
        sys.stdout.flush()

    urllib.request.urlretrieve(url, dest_path, reporthook=reporthook)
    sys.stdout.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Télécharge les fichiers .txt, .cue et .bin d'un item archive.org en conservant l'arborescence."
    )
    parser.add_argument("url", help="URL archive.org de l'item ou identifiant de l'archive")
    parser.add_argument(
        "--download-dir",
        default="Download",
        help="Dossier de destination où créer l'arborescence et enregistrer les fichiers (par défaut: Download)",
    )
    parser.add_argument(
        "--extensions",
        default=",".join(DEFAULT_EXTENSIONS),
        help="Extensions à télécharger, séparées par des virgules (par défaut: .txt,.cue,.bin)",
    )
    args = parser.parse_args()

    try:
        identifier, subdir = extract_identifier_and_subdir(args.url)
    except ValueError as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        return 1

    extensions = [ext.strip().lower() for ext in args.extensions.split(",") if ext.strip()]
    download_dir = os.path.abspath(args.download_dir)
    os.makedirs(download_dir, exist_ok=True)

    print(f"Item archive.org: {identifier}")
    if subdir:
        print(f"Sous-dossier: {subdir}")
    print(f"Dossier de destination: {download_dir}")
    print(f"Extensions recherchées: {', '.join(extensions)}")

    try:
        archive_files = get_archive_files(identifier)
    except Exception as exc:
        print(f"Impossible de récupérer les métadonnées archive.org: {exc}", file=sys.stderr)
        return 1

    candidates = []
    for f in archive_files:
        name = f.get("name", "")
        if not is_valid_file(name, extensions):
            continue
        if subdir:
            if not (name == subdir or name.startswith(subdir + "/") or
                    name.lower() == subdir.lower() or name.lower().startswith(subdir.lower() + "/")):
                continue
        candidates.append(f)
    if not candidates:
        print("Aucun fichier trouvé pour les extensions demandées.")
        return 0

    for file_info in candidates:
        name = file_info.get("name")
        if not name:
            continue
        local_path = build_local_path(download_dir, name)
        if os.path.exists(local_path):
            print(f"Fichier déjà existant, passage au suivant: {name}")
            continue
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            download_file(identifier, name, local_path)
        except Exception as exc:
            print(f"Échec du téléchargement de {name}: {exc}", file=sys.stderr)

    print("Téléchargement terminé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
