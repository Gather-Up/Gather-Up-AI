def generate_vendor_recommendation(prompt: str, vendor_data: list) -> str:
    vendor_names = [v['vendorName'] for v in vendor_data[:3]]
    return f"Recommended vendors: {', '.join(vendor_names)}"
