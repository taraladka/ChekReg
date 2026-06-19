#!/usr/bin/env python3
"""
chekreg — Digital Footprint Mapper
"""

import os, sys, argparse, subprocess, re

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    print("\n[!] Missing dependencies. Run:\n")
    print("    pip install --upgrade tldextract colorama flask duckduckgo-search requests\n")
    sys.exit(1)

from engine import Scanner, Report, VERSION

# Terminal colors
R  = Fore.RED;    Y = Fore.YELLOW;  G = Fore.GREEN
C  = Fore.CYAN;   M = Fore.MAGENTA; B = Fore.BLUE
W  = Fore.WHITE;  D = Style.DIM;    BR = Style.BRIGHT
RS = Style.RESET_ALL

def clr(text, *styles):
    return "".join(styles) + str(text) + RS

def _menu_pick(prompt: str, options: list, default: int = 0) -> int:
    print(f"\n  {BR}{prompt}{RS}")
    for i, (label, desc) in enumerate(options):
        marker  = f"{G}>{RS}" if i == default else f"{D} {RS}"
        idx_txt = clr(f"[{i + 1}]", BR, C)
        print(f"  {marker} {idx_txt}  {BR}{label:<26}{RS}  {D}{desc}{RS}")
    print()
    while True:
        try:
            raw = input(f"  {D}Enter number (default {default + 1}):{RS} ").strip()
            if raw == "": return default
            idx = int(raw) - 1
            if 0 <= idx < len(options): return idx
            print(f"  {Y}Please enter a number between 1 and {len(options)}{RS}")
        except (ValueError, KeyboardInterrupt):
            print(f"\n  {Y}Cancelled.{RS}\n")
            sys.exit(0)

def _menu_input(prompt: str, placeholder: str = "") -> str:
    try:
        val = input(f"  {D}{prompt}{RS} ").strip()
        return val or placeholder
    except KeyboardInterrupt:
        print(f"\n  {Y}Cancelled.{RS}\n")
        sys.exit(0)

def _menu_yesno(prompt: str, default: bool = True) -> bool:
    yn = "Y/n" if default else "y/N"
    while True:
        try:
            raw = input(f"  {D}{prompt} [{yn}]:{RS} ").strip().lower()
            if raw == "":
                return default
            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no"):
                return False
            print(f"  {Y}Please type y or n{RS}")
        except KeyboardInterrupt:
            print(f"\n  {Y}Cancelled.{RS}\n")
            sys.exit(0)


# ── Developer Tools ──
def _developer_menu(report: Report):
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\n  {BR}{C}Developer Tools{RS}")
        print(f"  {D}{'─' * 54}{RS}")
        
        choice = _menu_pick(
            "Select an operation:",
            [
                ("Extract Missing Links",   "Save orgs with NO delete/unsub links to missing_links.json"),
                ("Auto-Resolve Missing",    "Fetch missing links from the web and merge into sites.json"),
                ("Merge/Append JSON DB",    "Merge a custom JSON file into the primary sites.json DB"),
                ("Back to Main Menu",       "Return to the post-scan dashboard"),
            ],
            default=0
        )
        
        if choice == 0:
            path = os.path.join('reports', 'missing_links.json')
            count = report.export_missing_links(path)
            if count > 0:
                print(f"  {G}✓{RS}  Saved {count} missing organizations to {path}\n")
            else:
                print(f"  {G}✓{RS}  No missing links! All organizations have action links.\n")
            input(f"  {D}Press Enter to continue...{RS}")
            
        elif choice == 1:
            print(f"  {BR}Running fetch_missing_links.py...{RS}\n")
            script_path = os.path.join('scripts', 'fetch_missing_links.py')
            subprocess.run([sys.executable, script_path])
            input(f"\n  {D}Press Enter to continue...{RS}")
            
        elif choice == 2:
            custom_path = _menu_input("Enter path to JSON file to merge (e.g. data/new_sites.json) →")
            if custom_path and os.path.exists(custom_path):
                print(f"  {BR}Running merge_db.py on {custom_path}...{RS}\n")
                script_path = os.path.join('scripts', 'merge_db.py')
                subprocess.run([sys.executable, script_path, custom_path])
            else:
                print(f"  {Y}File not found or invalid path.{RS}")
            input(f"\n  {D}Press Enter to continue...{RS}")
            
        elif choice == 3:
            break


# ── Post-scan Interactive Loop ──
def _post_scan_loop(report: Report):
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\n  {BR}{C}Scan Complete!{RS}")
        print(f"  {D}{'─' * 62}{RS}")
        print(f"  Found {len(report.all)} organizations, {len(report.breached)} breached.\n")
        
        choice = _menu_pick(
            "What would you like to view?",
            [
                ("Master Action Dashboard", "All accounts grouped by category with action links"),
                ("Breached Accounts",       "Only show accounts found in data breaches"),
                ("Export Reports",          "Save JSON/TXT reports to the reports/ directory"),
                ("Developer Tools",         "Extract missing links and run maintenance scripts"),
                ("Scan Another Email",      "Start a new scan from the beginning"),
                ("Exit",                    "Quit the application"),
            ],
            default=0
        )
        
        os.system('cls' if os.name == 'nt' else 'clear')
        report.print_banner()
        
        if choice == 0:
            report.print_scorecard()
            report.print_dashboard()
        elif choice == 1:
            report.print_breaches()
        elif choice == 2:
            j_path = os.path.join('reports', 'report.json')
            t_path = os.path.join('reports', 'report.txt')
            report.export_json(j_path)
            report.export_txt(t_path)
            print(f"  {G}✓{RS}  Reports saved successfully to the `reports/` folder.")
            print(f"       JSON: {j_path}")
            print(f"       TEXT: {t_path}\n")
        elif choice == 3:
            _developer_menu(report)
            continue
        elif choice == 4:
            return "restart"
        elif choice == 5:
            print(f"  {G}Goodbye!{RS}\n")
            sys.exit(0)
            
        input(f"  {D}Press Enter to return to the menu...{RS}")


# ── CLI Interactive Flow ──
def run_cli_interactive():
    # ── email address ──
    email = ""
    email_regex = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    while not email:
        email = _menu_input("Your Email address →")
        if not email:
            print(f"  {R}Email is required.{RS}")
        elif not email_regex.match(email):
            print(f"  {R}That doesn't look like a valid email.{RS}")
            email = ""

    # ── imap settings ──
    import getpass
    print(f"\n  {D}Enter your IMAP connection details.{RS}")
    host = _menu_input("IMAP Server (e.g. imap.gmail.com) →", "imap.gmail.com")
    port_str = _menu_input("IMAP Port (default 993) →", "993")
    port = int(port_str) if port_str.isdigit() else 993
    print(f"  {D}IMAP App Password (input hidden) →{RS}", end="")
    password = getpass.getpass("")

    use_hibp = _menu_yesno("Check for data breaches via HaveIBeenPwned? (Requires API Key)", default=False)
    hibp_key = None
    if use_hibp:
        print(f"  {D}HIBP API Key (input hidden) →{RS}", end="")
        hibp_key = getpass.getpass("")

    print(f"\n  {BR}Ready to scan...{RS}\n")
    scanner = Scanner(email, quiet=False)

    print(f"  {D}[1/3]{RS} Authenticating to {host}:{port}…")
    if not scanner.authenticate(host, port, password):
        sys.exit(1)
    print(f"  {G}✓{RS}  Authenticated\n")

    try:
        print(f"  {D}[2/3]{RS} Scanning via IMAP…")
        scanner.scan_imap()
        print()

        print(f"  {D}[3/3]{RS} Breach check…")
        scanner.run_hibp(api_key=hibp_key)
        print()
    finally:
        scanner.close()

    if not scanner.orgs:
        print(f"  {Y}No data found.{RS} Check your credentials and try again.\n")
        sys.exit(0)

    report = Report(scanner.orgs, email, hibp_checked=bool(hibp_key))

    # Show the full report first, then enter the interactive loop
    report.print_all()
    input(f"  {D}Press Enter to continue to the menu...{RS}")

    result = _post_scan_loop(report)
    if result == "restart":
        return main()


def main():
    # Make argparse output colored using ANSI escapes natively
    parser = argparse.ArgumentParser(
        prog='chekreg',
        description=f"{BR}{C}chekreg{RS} {D}v{VERSION} — Local Digital Footprint Mapper{RS}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"{D}Example usage:{RS}\n"
               f"  python chekreg.py          {D}# Starts the interactive menu{RS}\n"
               f"  python chekreg.py --web    {D}# Starts the Web GUI dashboard directly{RS}\n"
               f"  python chekreg.py --cli    {D}# Starts the Terminal Interface directly{RS}\n"
    )
    
    parser.add_argument('--web', action='store_true', help='Launch the Web Interface (GUI dashboard)')
    parser.add_argument('--cli', action='store_true', help='Launch the Terminal Interface (CLI mode)')
    
    args = parser.parse_args()

    os.system('cls' if os.name == 'nt' else 'clear')

    if args.web:
        import server
        server.run_server()
        return
    elif args.cli:
        run_cli_interactive()
        return

    print()
    print(f"  {G}" + r"   ____ _          _    ____           " + f"{RS}")
    print(f"  {G}" + r"  / ___| |__   ___| | _|  _ \ ___  __ _" + f"{RS}")
    print(f"  {G}" + r" | |   | '_ \ / _ \ |/ / |_) / _ \/ _` |" + f"{RS}")
    print(f"  {G}" + r" | |___| | | |  __/   <|  _ <  __/ (_| |" + f"{RS}")
    print(f"  {G}" + r"  \____|_| |_|\___|_|\_\_| \_\___|\__, |" + f"{RS}")
    print(f"  {G}" + r"                                  |___/ " + f"{RS}")
    print()
    
    choice = _menu_pick(
        "Select Launch Mode:",
        [
            ("CLI", "[Terminal]"),
            ("GUI", "[Web]")
        ],
        default=1
    )
    
    if choice == 0:
        run_cli_interactive()
    else:
        import server
        server.run_server()

if __name__ == '__main__':
    main()