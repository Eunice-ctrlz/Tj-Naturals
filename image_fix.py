import csv
import os

# --- SETTINGS FOR TJNATURALS ---
csv_filename = 'products.csv'  
column_name = 'image_name'     
image_folder = './images/'     # Relative to your TJNATURALS folder
# ------------------------------

def check_images():
    # 1. Check if CSV exists
    if not os.path.exists(csv_filename):
        print(f"❌ Error: Could not find '{csv_filename}' in {os.getcwd()}")
        print("Make sure the file is named exactly 'products.csv'")
        return

    missing_files = []
    
    # 2. Open and read
    with open(csv_filename, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_name = row.get(column_name)
            if not img_name:
                continue
            
            # Check if the file exists on your computer
            full_path = os.path.join(image_folder, img_name.strip())
            if not os.path.exists(full_path):
                missing_files.append(img_name)

    # 3. Report
    if not missing_files:
        print("✅ Success! Every image listed in products.csv exists in the /images/ folder.")
    else:
        print(f"❌ Found {len(missing_files)} broken links:")
        for missing in missing_files[:10]:
            print(f"  - {missing}")
        if len(missing_files) > 10:
            print(f"  ... and {len(missing_files) - 10} more.")

if __name__ == "__main__":
    check_images()