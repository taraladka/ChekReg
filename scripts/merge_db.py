import sys
import json
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="Merge a JSON file of new sites into the main ChekReg sites.json database.")
    parser.add_argument("file", help="Path to the JSON file to merge/append.")
    parser.add_argument("--db", default="data/sites.json", help="Path to the main sites.json database.")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"[!] Error: Target file '{args.file}' not found.")
        sys.exit(1)
        
    db_path = args.db
    if not os.path.exists(db_path):
        print(f"[*] Main database '{db_path}' not found. Creating a new one.")
        db = {"sites": {}}
    else:
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                db = json.load(f)
        except json.JSONDecodeError:
            print(f"[!] Error: Main database '{db_path}' is corrupted or invalid JSON.")
            sys.exit(1)
            
    sites = db.get("sites", db)
    initial_count = len(sites)
    
    print(f"[*] Loading '{args.file}'...")
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            new_data = json.load(f)
    except json.JSONDecodeError:
        print(f"[!] Error: Target file '{args.file}' is invalid JSON.")
        sys.exit(1)
        
    new_sites = new_data.get("sites", new_data)
    if not isinstance(new_sites, dict):
        print("[!] Error: Target file does not contain a dictionary of sites.")
        sys.exit(1)
        
    added = 0
    updated = 0
    for domain, details in new_sites.items():
        if domain in sites:
            updated += 1
        else:
            added += 1
        sites[domain] = details
        
    db["sites"] = sites
    
    print(f"[*] Saving to '{db_path}'...")
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)
        
    print("-" * 30)
    print("Merge Complete!")
    print(f"  Added:   {added} new domains")
    print(f"  Updated: {updated} existing domains")
    print(f"  Total DB Size: {len(sites)} domains")
    print("-" * 30)

if __name__ == "__main__":
    main()
