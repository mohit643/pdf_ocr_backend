import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import io

class PDFVisualEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("📄 PDF Visual Editor - Direct Edit")
        self.root.geometry("1200x800")
        self.root.configure(bg="#2c3e50")
        
        self.pdf_path = None
        self.doc = None
        self.current_page = 0
        self.zoom_level = 1.5
        self.selected_text_rects = []
        
        self.create_widgets()
    
    def create_widgets(self):
        # Top Toolbar
        toolbar = tk.Frame(self.root, bg="#34495e", height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Upload Button
        tk.Button(
            toolbar,
            text="📂 Open PDF",
            command=self.open_pdf,
            font=("Arial", 11, "bold"),
            bg="#3498db",
            fg="white",
            padx=20,
            pady=10,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=10, pady=10)
        
        # Page Navigation
        tk.Label(toolbar, text="Page:", bg="#34495e", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 5))
        
        self.prev_btn = tk.Button(
            toolbar,
            text="◀",
            command=self.prev_page,
            font=("Arial", 12, "bold"),
            bg="#95a5a6",
            fg="white",
            state="disabled",
            width=3
        )
        self.prev_btn.pack(side=tk.LEFT, padx=2)
        
        self.page_label = tk.Label(
            toolbar,
            text="0 / 0",
            bg="#34495e",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10
        )
        self.page_label.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = tk.Button(
            toolbar,
            text="▶",
            command=self.next_page,
            font=("Arial", 12, "bold"),
            bg="#95a5a6",
            fg="white",
            state="disabled",
            width=3
        )
        self.next_btn.pack(side=tk.LEFT, padx=2)
        
        # Zoom Controls
        tk.Label(toolbar, text="Zoom:", bg="#34495e", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 5))
        
        tk.Button(
            toolbar,
            text="−",
            command=self.zoom_out,
            font=("Arial", 14, "bold"),
            bg="#95a5a6",
            fg="white",
            width=3
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            toolbar,
            text="+",
            command=self.zoom_in,
            font=("Arial", 14, "bold"),
            bg="#95a5a6",
            fg="white",
            width=3
        ).pack(side=tk.LEFT, padx=2)
        
        # Save Button
        self.save_btn = tk.Button(
            toolbar,
            text="💾 Save PDF",
            command=self.save_pdf,
            font=("Arial", 11, "bold"),
            bg="#27ae60",
            fg="white",
            padx=20,
            pady=10,
            state="disabled",
            cursor="hand2"
        )
        self.save_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Main Content Area
        content_frame = tk.Frame(self.root, bg="#2c3e50")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left Side - PDF Viewer
        viewer_frame = tk.LabelFrame(
            content_frame,
            text="📄 PDF Viewer (Click on text to select)",
            font=("Arial", 11, "bold"),
            bg="white",
            fg="#2c3e50",
            padx=5,
            pady=5
        )
        viewer_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Canvas with Scrollbar
        canvas_frame = tk.Frame(viewer_frame, bg="white")
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas = tk.Canvas(
            canvas_frame,
            bg="#ecf0f1",
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.v_scrollbar.config(command=self.canvas.yview)
        self.h_scrollbar.config(command=self.canvas.xview)
        
        # Bind click event
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        # Right Side - Edit Panel
        edit_frame = tk.LabelFrame(
            content_frame,
            text="✏️ Edit Selected Text",
            font=("Arial", 11, "bold"),
            bg="white",
            fg="#2c3e50",
            padx=15,
            pady=15,
            width=350
        )
        edit_frame.pack(side=tk.RIGHT, fill=tk.Y)
        edit_frame.pack_propagate(False)
        
        # Selected Text Display
        tk.Label(
            edit_frame,
            text="Selected Text:",
            font=("Arial", 10, "bold"),
            bg="white"
        ).pack(anchor="w", pady=(0, 5))
        
        self.selected_text_display = tk.Text(
            edit_frame,
            height=3,
            font=("Arial", 10),
            bg="#ecf0f1",
            wrap=tk.WORD,
            state="disabled"
        )
        self.selected_text_display.pack(fill=tk.X, pady=(0, 15))
        
        # New Text Input
        tk.Label(
            edit_frame,
            text="Replace with:",
            font=("Arial", 10, "bold"),
            bg="white"
        ).pack(anchor="w", pady=(0, 5))
        
        self.new_text_entry = tk.Text(
            edit_frame,
            height=3,
            font=("Arial", 10),
            wrap=tk.WORD
        )
        self.new_text_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Replace Button
        self.replace_btn = tk.Button(
            edit_frame,
            text="🔄 Replace Selected Text",
            command=self.replace_selected,
            font=("Arial", 11, "bold"),
            bg="#e74c3c",
            fg="white",
            pady=10,
            state="disabled",
            cursor="hand2"
        )
        self.replace_btn.pack(fill=tk.X, pady=(0, 20))
        
        # Find & Replace All Section
        tk.Label(
            edit_frame,
            text="Find & Replace All:",
            font=("Arial", 10, "bold"),
            bg="white"
        ).pack(anchor="w", pady=(20, 5))
        
        tk.Label(edit_frame, text="Find:", bg="white", font=("Arial", 9)).pack(anchor="w")
        self.find_entry = tk.Entry(edit_frame, font=("Arial", 10))
        self.find_entry.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(edit_frame, text="Replace:", bg="white", font=("Arial", 9)).pack(anchor="w")
        self.replace_entry = tk.Entry(edit_frame, font=("Arial", 10))
        self.replace_entry.pack(fill=tk.X, pady=(0, 10))
        
        tk.Button(
            edit_frame,
            text="🔍 Replace All in Document",
            command=self.replace_all,
            font=("Arial", 10, "bold"),
            bg="#9b59b6",
            fg="white",
            pady=8,
            cursor="hand2"
        ).pack(fill=tk.X)
        
        # Instructions
        instructions = tk.Label(
            edit_frame,
            text="\n💡 Instructions:\n\n"
                 "1. Click on text in PDF\n"
                 "2. Enter new text\n"
                 "3. Click Replace\n"
                 "4. Save when done",
            font=("Arial", 9),
            bg="#ecf0f1",
            fg="#34495e",
            justify=tk.LEFT,
            padx=10,
            pady=10
        )
        instructions.pack(fill=tk.X, pady=(20, 0))
        
        # Status Bar
        self.status_bar = tk.Label(
            self.root,
            text="Ready - Open a PDF file to start editing",
            font=("Arial", 9),
            bg="#34495e",
            fg="white",
            anchor="w",
            padx=10
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def open_pdf(self):
        """PDF file open karo"""
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF Files", "*.pdf")]
        )
        
        if file_path:
            try:
                self.pdf_path = file_path
                self.doc = fitz.open(file_path)
                self.current_page = 0
                
                # Enable controls
                self.prev_btn.config(state="normal")
                self.next_btn.config(state="normal")
                self.save_btn.config(state="normal")
                
                self.render_page()
                self.status_bar.config(text=f"✅ Loaded: {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open PDF:\n{e}")
    
    def render_page(self):
        """Current page ko render karo"""
        if not self.doc:
            return
        
        try:
            page = self.doc[self.current_page]
            
            # Update page label
            self.page_label.config(text=f"{self.current_page + 1} / {len(self.doc)}")
            
            # Render page as image
            mat = fitz.Matrix(self.zoom_level, self.zoom_level)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(img)
            
            # Display on canvas
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to render page:\n{e}")
    
    def on_canvas_click(self, event):
        """Canvas par click detect karo"""
        if not self.doc:
            return
        
        # Canvas coordinates to PDF coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Adjust for zoom
        pdf_x = canvas_x / self.zoom_level
        pdf_y = canvas_y / self.zoom_level
        
        page = self.doc[self.current_page]
        
        # Find text at clicked position
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        bbox = span["bbox"]
                        if (bbox[0] <= pdf_x <= bbox[2] and 
                            bbox[1] <= pdf_y <= bbox[3]):
                            
                            selected_text = span["text"]
                            self.selected_text_rects = [fitz.Rect(bbox)]
                            
                            # Update display
                            self.selected_text_display.config(state="normal")
                            self.selected_text_display.delete(1.0, tk.END)
                            self.selected_text_display.insert(1.0, selected_text)
                            self.selected_text_display.config(state="disabled")
                            
                            self.replace_btn.config(state="normal")
                            self.status_bar.config(text=f"✅ Selected: {selected_text[:30]}...")
                            
                            return
    
    def replace_selected(self):
        """Selected text ko replace karo"""
        if not self.doc or not self.selected_text_rects:
            return
        
        old_text = self.selected_text_display.get(1.0, tk.END).strip()
        new_text = self.new_text_entry.get(1.0, tk.END).strip()
        
        if not new_text:
            messagebox.showwarning("Warning", "Please enter replacement text")
            return
        
        try:
            page = self.doc[self.current_page]
            
            # Remove old text
            for rect in self.selected_text_rects:
                page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()
            
            # Add new text
            rect = self.selected_text_rects[0]
            page.insert_text(
                (rect.x0, rect.y0 + 10),
                new_text,
                fontsize=11,
                color=(0, 0, 0)
            )
            
            # Re-render
            self.render_page()
            
            # Clear selection
            self.selected_text_display.config(state="normal")
            self.selected_text_display.delete(1.0, tk.END)
            self.selected_text_display.config(state="disabled")
            self.new_text_entry.delete(1.0, tk.END)
            self.replace_btn.config(state="disabled")
            
            self.status_bar.config(text=f"✅ Replaced: '{old_text}' → '{new_text}'")
            
        except Exception as e:
            messagebox.showerror("Error", f"Replace failed:\n{e}")
    
    def replace_all(self):
        """Document mein sabhi instances replace karo"""
        if not self.doc:
            return
        
        find_text = self.find_entry.get()
        replace_text = self.replace_entry.get()
        
        if not find_text:
            messagebox.showwarning("Warning", "Please enter text to find")
            return
        
        try:
            total_replaced = 0
            
            for page in self.doc:
                text_instances = page.search_for(find_text)
                
                for inst in text_instances:
                    page.add_redact_annot(inst, fill=(1, 1, 1))
                
                page.apply_redactions()
                
                for inst in text_instances:
                    page.insert_text(
                        (inst.x0, inst.y0 + 10),
                        replace_text,
                        fontsize=11,
                        color=(0, 0, 0)
                    )
                    total_replaced += 1
            
            self.render_page()
            
            if total_replaced > 0:
                messagebox.showinfo("Success", f"✅ Replaced {total_replaced} instances")
                self.status_bar.config(text=f"✅ Replaced {total_replaced} instances")
            else:
                messagebox.showinfo("Info", f"Text '{find_text}' not found")
            
        except Exception as e:
            messagebox.showerror("Error", f"Replace all failed:\n{e}")
    
    def prev_page(self):
        """Previous page par jao"""
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()
    
    def next_page(self):
        """Next page par jao"""
        if self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()
    
    def zoom_in(self):
        """Zoom in karo"""
        self.zoom_level += 0.2
        if self.doc:
            self.render_page()
    
    def zoom_out(self):
        """Zoom out karo"""
        if self.zoom_level > 0.5:
            self.zoom_level -= 0.2
            if self.doc:
                self.render_page()
    
    def save_pdf(self):
        """Edited PDF save karo"""
        if not self.doc:
            return
        
        save_path = filedialog.asksaveasfilename(
            title="Save PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        
        if save_path:
            try:
                self.doc.save(save_path)
                messagebox.showinfo("Success", f"✅ Saved to:\n{save_path}")
                self.status_bar.config(text=f"✅ Saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Save failed:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFVisualEditor(root)
    root.mainloop()