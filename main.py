import os
import shutil
import subprocess
from pathlib import Path


# =========================
# YAZONII OS V1
# =========================

HOME = Path.home()
DOWNLOADS = HOME / "Downloads"
DESKTOP = HOME / "Desktop"
DOCUMENTS = HOME / "Documents"

PROJECTS = HOME / "YazoniiProjects"
BACKUPS = HOME / "YazoniiBackups"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def pause():
    input("\nPress Enter to continue...")


def header():
    clear()
    print("╔══════════════════════════════════╗")
    print("║         YAZONII OS v1.0          ║")
    print("║       Personal Automation        ║")
    print("╚══════════════════════════════════╝")
    print()


# =========================
# CODING MODE
# =========================

def coding_mode():
    header()

    print("🚀 Starting Coding Mode...\n")

    programs = [
        ("VS Code", "code"),
        ("GitHub", "https://github.com"),
    ]

    for name, command in programs:
        try:
            if command.startswith("http"):
                os.startfile(command)
            else:
                subprocess.Popen(command, shell=True)

            print(f"✓ Opened {name}")

        except Exception:
            print(f"⚠ Could not open {name}")

    pause()


# =========================
# SCHOOL MODE
# =========================

def school_mode():
    header()

    print("📚 SCHOOL MODE\n")

    school_sites = [
        "https://classroom.google.com",
        "https://drive.google.com",
    ]

    for site in school_sites:
        try:
            os.startfile(site)
            print(f"✓ Opened {site}")
        except Exception:
            print(f"⚠ Could not open {site}")

    pause()


# =========================
# MINECRAFT MODE
# =========================

def minecraft_mode():
    header()

    print("🎮 MINECRAFT MODE\n")

    minecraft_folder = HOME / "AppData" / "Roaming" / ".minecraft"

    if minecraft_folder.exists():
        os.startfile(minecraft_folder)
        print("✓ Opened Minecraft folder")
    else:
        print("⚠ Minecraft folder not found.")

    pause()


# =========================
# DOWNLOAD ORGANIZER
# =========================

def organize_downloads():
    header()

    print("📁 ORGANIZING DOWNLOADS...\n")

    folders = {
        "Images": [".png", ".jpg", ".jpeg", ".gif", ".webp"],
        "Videos": [".mp4", ".mov", ".mkv", ".avi"],
        "Documents": [".pdf", ".docx", ".txt", ".pptx", ".xlsx"],
        "Archives": [".zip", ".rar", ".7z"],
        "Programs": [".exe", ".msi"],
    }

    for folder in folders:
        (DOWNLOADS / folder).mkdir(exist_ok=True)

    moved = 0

    for file in DOWNLOADS.iterdir():

        if not file.is_file():
            continue

        extension = file.suffix.lower()

        for folder, extensions in folders.items():

            if extension in extensions:

                destination = DOWNLOADS / folder / file.name

                try:
                    shutil.move(str(file), str(destination))
                    print(f"✓ {file.name} → {folder}")
                    moved += 1

                except Exception as error:
                    print(f"⚠ Could not move {file.name}: {error}")

                break

    print(f"\nFinished. Organized {moved} files.")
    pause()


# =========================
# PROJECT BACKUP
# =========================

def backup_projects():
    header()

    print("💾 PROJECT BACKUP\n")

    if not PROJECTS.exists():
        print(f"Creating project folder:")
        print(PROJECTS)
        PROJECTS.mkdir(parents=True)

    BACKUPS.mkdir(parents=True, exist_ok=True)

    backup_name = BACKUPS / "latest"

    if backup_name.exists():
        shutil.rmtree(backup_name)

    shutil.copytree(PROJECTS, backup_name)

    print("✓ Projects backed up successfully.")
    print(f"Backup location: {backup_name}")

    pause()


# =========================
# MAIN MENU
# =========================

def main():

    while True:

        header()

        print("1. 🚀 Coding Mode")
        print("2. 📚 School Mode")
        print("3. 🎮 Minecraft Mode")
        print("4. 📁 Organize Downloads")
        print("5. 💾 Backup Projects")
        print("0. ❌ Exit")

        print()

        choice = input("> ")

        if choice == "1":
            coding_mode()

        elif choice == "2":
            school_mode()

        elif choice == "3":
            minecraft_mode()

        elif choice == "4":
            organize_downloads()

        elif choice == "5":
            backup_projects()

        elif choice == "0":
            clear()
            print("Yazonii OS shutting down...")
            break

        else:
            print("\n⚠ Invalid option.")
            pause()


if __name__ == "__main__":
    main()
