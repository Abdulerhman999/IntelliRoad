import fitz
def generate_output_pdf(path, project, prediction_text):
    doc = fitz.open()
    page = doc.new_page()

    text = f"""
Road Cost Prediction Report
--------------------------------
Length: {project['length']}
Width: {project['width']}
Location: {project['location']}
Project Type: {project['ptype']}

Prediction:
{prediction_text}
"""

    page.insert_text((50, 50), text, fontsize=12)
    doc.save(path)
    doc.close()
