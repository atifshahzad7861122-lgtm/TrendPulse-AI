import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from config import DEV_AUTHOR, DEV_WHATSAPP, DEV_EMAIL

def export_to_excel(product_data: dict, specs: dict, reviews: list, output_filepath: str = "final_out.xlsx"):
    """
    Appends structured product details, specs, and reviews into a single unified Excel sheet.
    Loads pre-existing final_out.xlsx rows if the file exists.
    """
    # Theme styles
    navy_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    dev_font = Font(name="Segoe UI", size=9, bold=True, color="94A3B8")
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'), right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'), bottom=Side(style='thin', color='CBD5E1')
    )
    left_align = Alignment(horizontal="left", vertical="center")
    center_align = Alignment(horizontal="center", vertical="center")

    file_exists = os.path.exists(output_filepath)
    if file_exists:
        try:
            wb = openpyxl.load_workbook(output_filepath)
        except Exception:
            wb = openpyxl.Workbook()
            file_exists = False
    else:
        wb = openpyxl.Workbook()

    # -------------------------------------------------------------
    # Sheet 1: Product Overview
    # -------------------------------------------------------------
    if "Product Overview" in wb.sheetnames:
        ws_overview = wb["Product Overview"]
    else:
        ws_overview = wb.active
        ws_overview.title = "Product Overview"
        
    ws_overview.views.sheetView[0].showGridLines = True

    # Setup headers if Sheet is fresh
    if ws_overview.max_row < 4:
        ws_overview.delete_rows(1, ws_overview.max_row) # Clear raw workbook garbage
        ws_overview['A1'] = "TrendPulse AI - Daraz Intelligence Extraction"
        ws_overview['A1'].font = Font(name="Segoe UI", size=15, bold=True, color="1E293B")
        
        ws_overview['A2'] = f"Engineered by: {DEV_AUTHOR} | WhatsApp: {DEV_WHATSAPP} | Email: {DEV_EMAIL}"
        ws_overview['A2'].font = dev_font
        
        headers = [
            "Product ID", "SKU", "Product Title", "Description", "Current Price", "Original Price", 
            "Discount", "Currency", "Brand", "Category Hierarchy", "Rating", "Total Reviews Count", 
            "Sold Count", "Seller Name", "Seller ID", "Product Variations", "Product Gallery URLs", 
            "Product URL", "Seller Metrics"
        ]
        ws_overview.append([]) # Row 3 spacer
        ws_overview.append(headers) # Row 4 headers
        
        for col_idx, h in enumerate(headers, start=1):
            cell = ws_overview.cell(row=4, column=col_idx)
            cell.fill, cell.font = navy_fill, header_font
            cell.alignment = center_align
            cell.border = thin_border

    # Build seller metrics string
    metrics_list = []
    for k, v in product_data.get("seller_metrics", {}).items():
        metrics_list.append(f"{k}: {v}")
    seller_metrics_str = ", ".join(metrics_list)

    overview_row = [
        product_data.get("product_id"),
        product_data.get("sku"),
        product_data.get("title"),
        product_data.get("description"),
        product_data.get("current_price"),
        product_data.get("original_price"),
        product_data.get("discount"),
        product_data.get("currency"),
        product_data.get("brand"),
        product_data.get("category"),
        product_data.get("rating"),
        product_data.get("total_reviews"),
        product_data.get("sold_count"),
        product_data.get("seller_name"),
        product_data.get("seller_id"),
        ", ".join(product_data.get("variations", [])),
        ", ".join(product_data.get("image_gallery", [])),
        product_data.get("url"),
        seller_metrics_str
    ]

    ws_overview.append(overview_row)
    new_overview_row_idx = ws_overview.max_row
    for col_idx in range(1, len(overview_row) + 1):
        cell = ws_overview.cell(row=new_overview_row_idx, column=col_idx)
        cell.border = thin_border
        cell.font = Font(name="Segoe UI", size=10, color="0F172A")
        cell.alignment = center_align if col_idx in [1, 2, 5, 6, 7, 8, 11, 12, 13, 15] else left_align
        if new_overview_row_idx % 2 == 0:
            cell.fill = zebra_fill

    # -------------------------------------------------------------
    # Sheet 2: Specifications
    # -------------------------------------------------------------
    if "Specifications" in wb.sheetnames:
        ws_specs = wb["Specifications"]
    else:
        ws_specs = wb.create_sheet(title="Specifications")
        
    ws_specs.views.sheetView[0].showGridLines = True

    if ws_specs.max_row < 1:
        headers = ["Product ID", "Product Title", "Specification Attribute", "Specification Value"]
        ws_specs.append(headers)
        for col_idx, h in enumerate(headers, start=1):
            cell = ws_specs.cell(row=1, column=col_idx)
            cell.fill, cell.font = navy_fill, header_font
            cell.border = thin_border
            cell.alignment = center_align

    for k, v in specs.items():
        ws_specs.append([
            product_data.get("product_id"),
            product_data.get("title"),
            k,
            v
        ])
        row_idx = ws_specs.max_row
        for c_idx in range(1, 5):
            cell = ws_specs.cell(row=row_idx, column=c_idx)
            cell.border = thin_border
            cell.font = Font(name="Segoe UI", size=10)
            cell.alignment = center_align if c_idx in [1, 3] else left_align
            if row_idx % 2 == 1:
                cell.fill = zebra_fill

    # -------------------------------------------------------------
    # Sheet 3: Customer Reviews
    # -------------------------------------------------------------
    if "Customer Reviews" in wb.sheetnames:
        ws_reviews = wb["Customer Reviews"]
    else:
        ws_reviews = wb.create_sheet(title="Customer Reviews")
        
    ws_reviews.views.sheetView[0].showGridLines = True

    if ws_reviews.max_row < 1:
        headers = ["Product ID", "Product Title", "Page", "Reviewer Name", "Review Date", "Rating (Stars)", "Variation Purchased", "Review Text", "Review Images"]
        ws_reviews.append(headers)
        for col_idx, h in enumerate(headers, start=1):
            cell = ws_reviews.cell(row=1, column=col_idx)
            cell.fill, cell.font = navy_fill, header_font
            cell.border = thin_border
            cell.alignment = center_align

    for rev in reviews:
        ws_reviews.append([
            product_data.get("product_id"),
            product_data.get("title"),
            rev.get("page", 1),
            rev.get("reviewer", "Anonymous"),
            rev.get("date", "N/A"),
            rev.get("rating", 5),
            rev.get("variation", "N/A"),
            rev.get("content", "No written review"),
            rev.get("images", "")
        ])
        row_idx = ws_reviews.max_row
        for c_idx in range(1, 10):
            cell = ws_reviews.cell(row=row_idx, column=c_idx)
            cell.border = thin_border
            cell.font = Font(name="Segoe UI", size=10)
            if c_idx in [1, 3, 5, 6]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align
            if row_idx % 2 == 1:
                cell.fill = zebra_fill

    # Auto Column Sizing
    for ws in [ws_overview, ws_specs, ws_reviews]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or '')
                if len(val) > 45 and (col_letter in ['A', 'P', 'Q', 'R'] or 'http' in val):
                    val = val[:35] + "..."
                if len(val) > max_len:
                    max_len = len(val)
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 14), 70)

    wb.save(output_filepath)
    return output_filepath
