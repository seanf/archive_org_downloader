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

TRANSLATIONS = {
    "fr": {
        "extract_error": "Impossible d'extraire l'identifiant depuis l'URL : {0}",
        "download_start": "Téléchargement: {0} -> {1}",
        "downloaded": "Téléchargé: {0}",
        "cli_description": "Télécharge les fichiers .txt, .cue et .bin d'un item archive.org en conservant l'arborescence.",
        "cli_url_help": "URL archive.org de l'item ou identifiant de l'archive",
        "cli_dir_help": "Dossier de destination où créer l'arborescence et enregistrer les fichiers (par défaut: Download)",
        "cli_ext_help": "Extensions à télécharger, séparées par des virgules (par défaut: .txt,.cue,.bin)",
        "cli_lang_help": "Langue de l'interface (par défaut: auto-détection depuis l'environnement)",
        "error": "Erreur: {0}",
        "item": "Item archive.org: {0}",
        "subdir": "Sous-dossier: {0}",
        "dest_dir": "Dossier de destination: {0}",
        "extensions": "Extensions recherchées: {0}",
        "metadata_error": "Impossible de récupérer les métadonnées archive.org: {0}",
        "no_files": "Aucun fichier trouvé pour les extensions demandées.",
        "already_exists": "Fichier déjà existant, passage au suivant: {0}",
        "download_failed": "Échec du téléchargement de {0}: {1}",
        "done": "Téléchargement terminé.",
        "unit_octets": "octets",
        "unit_Ko": "Ko",
        "unit_Mo": "Mo",
        "unit_Go": "Go",
    },
    "en": {
        "extract_error": "Unable to extract the identifier from the URL: {0}",
        "download_start": "Downloading: {0} -> {1}",
        "downloaded": "Downloaded: {0}",
        "cli_description": "Download the .txt, .cue and .bin files of an archive.org item, preserving the folder structure.",
        "cli_url_help": "archive.org item URL or archive identifier",
        "cli_dir_help": "Destination folder where the structure is created and files are saved (default: Download)",
        "cli_ext_help": "Extensions to download, comma-separated (default: .txt,.cue,.bin)",
        "cli_lang_help": "Interface language (default: auto-detect from the environment)",
        "error": "Error: {0}",
        "item": "archive.org item: {0}",
        "subdir": "Subfolder: {0}",
        "dest_dir": "Destination folder: {0}",
        "extensions": "Extensions searched: {0}",
        "metadata_error": "Unable to fetch archive.org metadata: {0}",
        "no_files": "No file found for the requested extensions.",
        "already_exists": "File already exists, skipping: {0}",
        "download_failed": "Failed to download {0}: {1}",
        "done": "Download complete.",
        "unit_octets": "bytes",
        "unit_Ko": "KB",
        "unit_Mo": "MB",
        "unit_Go": "GB",
    },
}

_LANG = "fr"


def activate_language(lang: str) -> None:
    global _LANG
    _LANG = lang if lang in TRANSLATIONS else "fr"


def _(key: str) -> str:
    return TRANSLATIONS[_LANG][key]


def detect_language() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value:
            code = value.split(".")[0].split("_")[0].lower()
            if code in TRANSLATIONS:
                return code
    return "fr"


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
            raise ValueError(_("extract_error").format(url_or_id))

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
    for unit_key in ["unit_octets", "unit_Ko", "unit_Mo", "unit_Go"]:
        unit = _(unit_key)
        if size < 1024 or unit_key == "unit_Go":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} {_('unit_Go')}"


def download_file(identifier: str, file_name: str, dest_path: str) -> None:
    url_name = quote_archive_name(file_name)
    url = ARCHIVE_DOWNLOAD_URL.format(id=urllib.parse.quote(identifier), name=url_name)
    print(_("download_start").format(file_name, dest_path))

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
            sys.stdout.write(f"\r{_('downloaded').format(format_bytes(downloaded))}")
        sys.stdout.flush()

    urllib.request.urlretrieve(url, dest_path, reporthook=reporthook)
    sys.stdout.write("\n")


def main() -> int:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument(
        "--lang",
        choices=sorted(TRANSLATIONS.keys()),
        default=None,
        help=_("cli_lang_help"),
    )
    pre_args, _remaining = pre_parser.parse_known_args()
    activate_language(pre_args.lang if pre_args.lang else detect_language())

    parser = argparse.ArgumentParser(description=_("cli_description"))
    parser.add_argument("url", help=_("cli_url_help"))
    parser.add_argument(
        "--download-dir",
        default="Download",
        help=_("cli_dir_help"),
    )
    parser.add_argument(
        "--extensions",
        default=",".join(DEFAULT_EXTENSIONS),
        help=_("cli_ext_help"),
    )
    parser.add_argument(
        "--lang",
        choices=sorted(TRANSLATIONS.keys()),
        default=None,
        help=_("cli_lang_help"),
    )
    args = parser.parse_args()

    try:
        identifier, subdir = extract_identifier_and_subdir(args.url)
    except ValueError as exc:
        print(_("error").format(exc), file=sys.stderr)
        return 1

    extensions = [ext.strip().lower() for ext in args.extensions.split(",") if ext.strip()]
    download_dir = os.path.abspath(args.download_dir)
    os.makedirs(download_dir, exist_ok=True)

    print(_("item").format(identifier))
    if subdir:
        print(_("subdir").format(subdir))
    print(_("dest_dir").format(download_dir))
    print(_("extensions").format(", ".join(extensions)))

    try:
        archive_files = get_archive_files(identifier)
    except Exception as exc:
        print(_("metadata_error").format(exc), file=sys.stderr)
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
        print(_("no_files"))
        return 0

    for file_info in candidates:
        name = file_info.get("name")
        if not name:
            continue
        local_path = build_local_path(download_dir, name)
        if os.path.exists(local_path):
            print(_("already_exists").format(name))
            continue
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            download_file(identifier, name, local_path)
        except Exception as exc:
            print(_("download_failed").format(name, exc), file=sys.stderr)

    print(_("done"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
