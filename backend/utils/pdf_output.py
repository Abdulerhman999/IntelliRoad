import fitz  # PyMuPDF

def generate_output_pdf(path, project, prediction_text):
    try:
        doc = fitz.open()
        
        # Page dimensions (A4)
        page_width = 595
        page_height = 842
        margin = 40
        
        # Font settings - Use built-in fonts only to avoid font loading issues
        font_size = 9
        line_height = 12
        title_font_size = 14
        
        # Starting position
        y_pos = margin
        
        # Create first page
        page = doc.new_page(width=page_width, height=page_height)
        
        # Split text into lines
        lines = prediction_text.split('\n')
        
        for i, line in enumerate(lines):
            # Check if we need a new page
            if y_pos > page_height - margin - 30:
                # Add page number to current page
                page_num_text = f"Page {len(doc)}"
                try:
                    page.insert_text(
                        (page_width - margin - 50, page_height - 25),
                        page_num_text,
                        fontsize=8,
                        color=(0.5, 0.5, 0.5)
                    )
                except Exception as e:
                    print(f"[WARN] Could not add page number: {e}")
                
                # Create new page
                page = doc.new_page(width=page_width, height=page_height)
                y_pos = margin
            
            # Determine font style
            is_title = line.startswith('ROAD COST PREDICTION REPORT')
            is_header = any(line.startswith(h) for h in [
                'PROJECT DETAILS:', 'ROAD SPECIFICATIONS:', 
                'COST PREDICTION:', 'ENVIRONMENTAL IMPACT:',
                'BILL OF QUANTITIES:', 'MATERIAL BREAKDOWN:',
                'RECOMMENDATIONS', 'ML MODEL PREDICTION:',
                'BUDGET ANALYSIS:', 'DETAILED BILL',
                'COST BREAKDOWN:', 'POTENTIAL SAVINGS:',
                'RISK FACTORS:', 'VALIDITY', 'ENVIRONMENTAL IMPACT ASSESSMENT:'
            ])
            
            # Check if line contains cost amounts that should be bold
            is_cost_line = any(pattern in line for pattern in [
                '**TOTAL COST', 
                'TOTAL MATERIALS COST',
                'Total Materials Cost (BOQ)',
                '**'  # Any line with ** markers
            ])
            
            # Choose font and color - using only built-in fonts
            if is_title:
                current_font_size = title_font_size
                fontname = "helv-bold"  # Helvetica Bold (built-in)
                color = (0.18, 0.49, 0.20)  # Dark green
            elif is_header or is_cost_line:
                current_font_size = 11 if is_header else font_size
                fontname = "helv-bold"  # Helvetica Bold (built-in)
                color = (0.26, 0.49, 0.29) if is_header else (0.18, 0.49, 0.20)  # Medium/dark green
            else:
                current_font_size = font_size
                fontname = "helv"  # Helvetica (built-in)
                color = (0, 0, 0)  # Black
            
            # Remove ** markers from text if present
            line = line.replace('**', '')
            
            # Handle long lines by wrapping
            max_chars = 95
            
            if len(line) > max_chars:
                # Split long line
                words = line.split()
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " + word if current_line else word)
                    
                    if len(test_line) <= max_chars:
                        current_line = test_line
                    else:
                        # Insert current line
                        if current_line:
                            try:
                                page.insert_text(
                                    (margin, y_pos),
                                    current_line,
                                    fontsize=current_font_size,
                                    fontname=fontname,
                                    color=color
                                )
                            except Exception as e:
                                # Fallback to default font if there's an issue
                                print(f"[WARN] Font issue, using default: {e}")
                                page.insert_text(
                                    (margin, y_pos),
                                    current_line,
                                    fontsize=current_font_size,
                                    color=color
                                )
                            
                            y_pos += line_height
                            
                            # Check for page break
                            if y_pos > page_height - margin - 30:
                                # Add page number
                                page_num_text = f"Page {len(doc)}"
                                try:
                                    page.insert_text(
                                        (page_width - margin - 50, page_height - 25),
                                        page_num_text,
                                        fontsize=8,
                                        color=(0.5, 0.5, 0.5)
                                    )
                                except:
                                    pass
                                page = doc.new_page(width=page_width, height=page_height)
                                y_pos = margin
                        
                        current_line = word
                
                # Insert remaining text
                if current_line:
                    try:
                        page.insert_text(
                            (margin, y_pos),
                            current_line,
                            fontsize=current_font_size,
                            fontname=fontname,
                            color=color
                        )
                    except Exception as e:
                        # Fallback to default font
                        print(f"[WARN] Font issue, using default: {e}")
                        page.insert_text(
                            (margin, y_pos),
                            current_line,
                            fontsize=current_font_size,
                            color=color
                        )
                    y_pos += line_height
            else:
                # Insert line as is
                try:
                    page.insert_text(
                        (margin, y_pos),
                        line,
                        fontsize=current_font_size,
                        fontname=fontname,
                        color=color
                    )
                except Exception as e:
                    # Fallback to default font
                    print(f"[WARN] Font issue, using default: {e}")
                    page.insert_text(
                        (margin, y_pos),
                        line,
                        fontsize=current_font_size,
                        color=color
                    )
                y_pos += line_height
            
            # Add extra spacing after headers
            if is_header or is_title:
                y_pos += 3
        
        # Add page number to last page
        try:
            page_num_text = f"Page {len(doc)} of {len(doc)}"
            page.insert_text(
                (page_width - margin - 70, page_height - 25),
                page_num_text,
                fontsize=8,
                color=(0.5, 0.5, 0.5)
            )
        except:
            pass
        
        # Save document
        try:
            doc.save(path)
            print(f"[INFO] PDF saved successfully: {path} ({len(doc)} pages)")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save PDF: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            doc.close()
            
    except Exception as e:
        print(f"[ERROR] PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise