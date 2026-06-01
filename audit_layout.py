
import openpyxl
from openpyxl_image_loader import SheetImageLoader
import os

# Define the path to the Excel file
LAYOUT_FILE_PATH = os.path.join(os.path.dirname(__file__), 'Brigade Road - Store layoutc5f5d56.xlsx')
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'docs', 'layout')

def audit_layout_workbook():
    """
    Audits the Excel workbook to find and extract layout information, including embedded images.
    """
    print(f"--- Auditing Workbook: {LAYOUT_FILE_PATH} ---")

    if not os.path.exists(LAYOUT_FILE_PATH):
        print(f"ERROR: Layout file not found at {LAYOUT_FILE_PATH}")
        return

    # Create assets directory if it doesn't exist
    os.makedirs(ASSETS_DIR, exist_ok=True)
    print(f"Assets will be saved to: {ASSETS_DIR}")

    try:
        # Load the workbook
        workbook = openpyxl.load_workbook(LAYOUT_FILE_PATH)
        
        report = []

        # 1. List all worksheets
        print(f"\nFound {len(workbook.sheetnames)} worksheets: {workbook.sheetnames}")

        # 2. Analyze each worksheet
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            sheet_report = {
                "Sheet Name": sheet_name,
                "Type": "Worksheet",
                "Dimensions": f"{sheet.max_row} rows x {sheet.max_column} columns",
                "Contains Data?": "NO",
                "Contains Drawing?": "UNKNOWN",
                "Contains Image?": "NO",
                "Contains Brand Names?": "NO"
            }

            # Check for cell data
            non_empty_cells = 0
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        non_empty_cells += 1
            if non_empty_cells > 5: # Heuristic to ignore sparse values
                sheet_report["Contains Data?"] = "YES"

            # 3. Attempt to extract images
            image_loader = SheetImageLoader(sheet)
            image_count = 0
            for i, image in enumerate(sheet._images):
                image_count += 1
                try:
                    # Generate a unique filename
                    image_filename = f"{sheet_name.replace(' ', '_')}_image_{i+1}.png"
                    image_path = os.path.join(ASSETS_DIR, image_filename)
                    
                    # Get image data and save it
                    img_data = image.ref
                    with open(image_path, 'wb') as f:
                        f.write(image.data())

                    print(f"  - Extracted image '{image_filename}' from sheet '{sheet_name}'.")
                    sheet_report["Contains Image?"] = "YES"

                except Exception as e:
                    print(f"  - ERROR: Could not extract image {i+1} from sheet '{sheet_name}': {e}")

            report.append(sheet_report)

        # 6. Create and print the final report
        print("\n--- Layout Audit Report ---")
        header = report[0].keys()
        rows = [list(r.values()) for r in report]
        
        # Calculate column widths
        widths = [len(h) for h in header]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))

        # Print header
        header_line = " | ".join(h.ljust(w) for h, w in zip(header, widths))
        print(header_line)
        print("-" * len(header_line))

        # Print rows
        for row in rows:
            row_line = " | ".join(str(c).ljust(w) for c, w in zip(row, widths))
            print(row_line)


    except Exception as e:
        print(f"\nERROR: An unexpected error occurred during the audit: {e}")

if __name__ == "__main__":
    audit_layout_workbook()
