import argparse
import csv
import configparser
import shutil
import zipfile
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.ini"


def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding="utf-8")
    return config


def get_config_value(config, section: str, key: str, fallback: str):
    if config.has_option(section, key):
        return config.get(section, key)
    return fallback


def resolve_root_dir(path_setting: str) -> Path:
    path = Path(path_setting)
    if not path.is_absolute():
        path = ROOT_DIR / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_rar_executable() -> str | None:
    candidates = [
        shutil.which("rar"),
        str(Path("C:/Program Files/WinRAR/rar.exe")),
        str(Path("C:/Program Files (x86)/WinRAR/rar.exe")),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def render_readme(template_path: Path, country: str, csv_filename: str) -> str:
    if not template_path.exists():
        raise FileNotFoundError(f"README template not found: {template_path}")

    return template_path.read_text(encoding="utf-8")


def prompt_if_missing(label: str, current: str | None, default: str = "") -> str:
    value = (current or "").strip()
    if value:
        return value
    prompt = f"{label}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "
    entered = input(prompt).strip()
    return entered or default


def gather_metadata(csv_path: Path, country: str, record_count: int, forced_type: str | None, config) -> dict[str, str]:
    defaults = {
        "package_title": f"{country} VFR Points",
        "country": country,
        "csv_filename": csv_path.name,
        "record_count": str(record_count),
        "source_file": csv_path.name,
        "generator_name": get_config_value(config, "package", "generator_name", "VFR-Points-Worldwide"),
        "generated_on": datetime.now().strftime("%Y-%m-%d"),
        "description": f"VFR points for {country} prepared for Little Navmap import.",
        "forced_type": forced_type or get_config_value(config, "defaults", "forced_type", "TBD") or "TBD",
        "flightsim_title": f"{country} VFR Points",
        "flightsim_description": f"CSV package with VFR points for {country}.",
        "version": "1.0",
        "manual_notes": "Add any flightsim.to specific details here if needed.",
    }

    if not defaults["package_title"]:
        defaults["package_title"] = f"{country} VFR Points"

    if not defaults["description"]:
        defaults["description"] = f"VFR points for {country} prepared for Little Navmap import."

    if not defaults["flightsim_title"]:
        defaults["flightsim_title"] = f"{country} VFR Points"

    if not defaults["flightsim_description"]:
        defaults["flightsim_description"] = f"CSV package with VFR points for {country}."

    if sys.stdin.isatty():
        print("\nFill the package metadata. Press Enter to keep the default shown in brackets.\n")
        defaults["package_title"] = prompt_if_missing("Package title", defaults["package_title"], defaults["package_title"])
        defaults["description"] = prompt_if_missing("Description", defaults["description"], defaults["description"])
        defaults["flightsim_title"] = prompt_if_missing("flightsim.to title", defaults["flightsim_title"], defaults["flightsim_title"])
        defaults["flightsim_description"] = prompt_if_missing("flightsim.to description", defaults["flightsim_description"], defaults["flightsim_description"])
        defaults["version"] = prompt_if_missing("Version", defaults["version"], defaults["version"])
        defaults["manual_notes"] = prompt_if_missing("Manual notes", defaults["manual_notes"], defaults["manual_notes"])

    return defaults


def create_archive_with_rar(rar_path: Path, folder_to_archive: Path, csv_filename: str) -> bool:
    rar_exe = find_rar_executable()
    if not rar_exe:
        return False
    subprocess.run(
        [rar_exe, "a", "-ep1", str(rar_path), "README.md", csv_filename],
        check=True,
        cwd=str(folder_to_archive),
    )
    return True


def create_zip_archive(zip_path: Path, folder_to_archive: Path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in folder_to_archive.iterdir():
            if item.is_file():
                zf.write(item, arcname=item.name)


def main():
    parser = argparse.ArgumentParser(description="Create an upload-ready package with CSV + README")
    parser.add_argument("csv", help="Path to the already processed CSV file")
    parser.add_argument("-c", "--country", default=None, help="Country name")
    parser.add_argument("-o", "--output", default=None, help="Output archive filename (.rar or .zip)")
    parser.add_argument("--no-archive", action="store_true", help="Only build the folder, do not create archive")
    parser.add_argument("--interactive", action="store_true", help="Prompt for missing metadata before building the package")
    args = parser.parse_args()

    config = load_config()
    package_dir = resolve_root_dir(get_config_value(config, "package", "package_dir", "dist"))
    template_path = ROOT_DIR / get_config_value(config, "package", "readme_template", "upload_readme_template.md")
    archive_format = get_config_value(config, "package", "archive_format", "rar").lower().strip() or "rar"

    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = (Path.cwd() / csv_path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        csv_rows = list(reader)
    record_count = max(len(csv_rows) - 1, 0)

    country = (args.country or csv_path.parent.name or "Unknown").strip() or "Unknown"
    package_name = csv_path.stem
    package_root = package_dir / package_name
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True, exist_ok=True)

    target_csv = package_root / csv_path.name
    shutil.copy2(csv_path, target_csv)

    metadata = gather_metadata(csv_path, country, record_count, args.country, config) if args.interactive or sys.stdin.isatty() else {
        "package_title": f"{country} VFR Points",
        "country": country,
        "csv_filename": csv_path.name,
        "record_count": str(record_count),
        "source_file": csv_path.name,
        "generator_name": get_config_value(config, "package", "generator_name", "VFR-Points-Worldwide"),
        "generated_on": datetime.now().strftime("%Y-%m-%d"),
        "description": f"VFR points for {country} prepared for Little Navmap import.",
        "forced_type": get_config_value(config, "defaults", "forced_type", "TBD") or "TBD",
        "flightsim_title": f"{country} VFR Points",
        "flightsim_description": f"CSV package with VFR points for {country}.",
        "version": "1.0",
        "manual_notes": "Add any flightsim.to specific details here if needed.",
    }

    readme_text = render_readme(template_path, country, csv_path.name).format(**metadata)
    (package_root / "README.md").write_text(readme_text, encoding="utf-8")

    if args.no_archive:
        print(f"Package folder created at {package_root}")
        return

    output_name = args.output or f"{csv_path.stem}.{archive_format}"
    output_path = package_dir / output_name

    if archive_format == "rar" and create_archive_with_rar(output_path, package_root, csv_path.name):
        print(f"Created RAR archive: {output_path}")
        return

    # Fallback to zip if RAR is unavailable
    zip_path = output_path.with_suffix(".zip") if output_path.suffix.lower() != ".zip" else output_path
    create_zip_archive(zip_path, package_root)
    print(f"RAR tool not found; created ZIP archive instead: {zip_path}")


if __name__ == "__main__":
    main()
