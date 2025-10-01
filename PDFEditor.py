import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import fitz  # PyMuPDF
import os

class PDFEditorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📄 PDF Editor - Upload & Edit")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")
        
        self.pdf_path = None
        self.doc = None
        
        self.create_widgets()
    
    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=60)
        header.pack(fill=tk.X)
        
        title = tk.Label(
            header, 
            text="📄 PDF Editor", 
            font=("Arial", 20, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title.pack(pady=15)
        
        # Main Container
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Upload Section
        upload_frame = tk.LabelFrame(
            main_frame,
            text="📤 Step 1: Upload PDF",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#2c3e50",
            padx=15,
            pady=15
        )
        upload_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.upload_btn = tk.Button(
            upload_frame,
            text="🗂️ Browse & Upload PDF",
            command=self.upload_pdf,
            font=("Arial", 12, "bold"),
            bg="#3498db",
            fg="white",
            activebackground="#2980b9",
            activeforeground="white",
            cursor="hand2",
            padx=20,
            pady=10
        )
        self.upload_btn.pack()
        
        self.file_label = tk.Label(
            upload_frame,
            text="No file selected",
            font=("Arial", 10),
            bg="white",
            fg="#7f8c8d"
        )
        self.file_label.pack(pady=(10, 0))
        
        # Edit Section
        edit_frame = tk.LabelFrame(
            main_frame,
            text="✏️ Step 2: Edit PDF",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#2c3e50",
            padx=15,
            pady=15
        )
        edit_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Search & Replace
        replace_frame = tk.Frame(edit_frame, bg="white")
        replace_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            replace_frame,
            text="Find:",
            font=("Arial", 10, "bold"),
            bg="white"
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        self.old_text = tk.Entry(replace_frame, font=("Arial", 11), width=30)
        self.old_text.grid(row=0, column=1, padx=5)
        
        tk.Label(
            replace_frame,
            text="Replace with:",
            font=("Arial", 10, "bold"),
            bg="white"
        ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        
        self.new_text = tk.Entry(replace_frame, font=("Arial", 11), width=30)
        self.new_text.grid(row=1, column=1, padx=5, pady=(10, 0))
        
        self.replace_btn = tk.Button(
            replace_frame,
            text="🔄 Replace",
            command=self.replace_text,
            font=("Arial", 10, "bold"),
            bg="#27ae60",
            fg="white",
            cursor="hand2",
            state="disabled"
        )
        self.replace_btn.grid(row=0, column=2, rowspan=2, padx=10)
        
        # Preview Section
        preview_label = tk.Label(
            edit_frame,
            text="📄 PDF Preview (Text):",
            font=("Arial", 10, "bold"),
            bg="white"
        )
        preview_label.pack(anchor="w", pady=(20, 5))
        
        self.preview_text = scrolledtext.ScrolledText(
            edit_frame,
            font=("Courier", 9),
            wrap=tk.WORD,
            height=15,
            bg="#ecf0f1",
            state="disabled"
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Action Buttons
        action_frame = tk.Frame(main_frame, bg="#f0f0f0")
        action_frame.pack(fill=tk.X)
        
        self.save_btn = tk.Button(
            action_frame,
            text="💾 Save Edited PDF",
            command=self.save_pdf,
            font=("Arial", 12, "bold"),
            bg="#e74c3c",
            fg="white",
            activebackground="#c0392b",
            activeforeground="white",
            cursor="hand2",
            padx=20,
            pady=10,
            state="disabled"
        )
        self.save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.extract_btn = tk.Button(
            action_frame,
            text="📋 Extract All Text",
            command=self.extract_all_text,
            font=("Arial", 12, "bold"),
            bg="#9b59b6",
            fg="white",
            cursor="hand2",
            padx=20,
            pady=10,
            state="disabled"
        )
        self.extract_btn.pack(side=tk.LEFT)
        
        # Status Bar
        self.status_bar = tk.Label(
            self.root,
            text="Ready to upload PDF...",
            font=("Arial", 9),
            bg="#34495e",
            fg="white",
            anchor="w",
            padx=10
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def upload_pdf(self):
        """PDF file upload karo"""
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                self.pdf_path = file_path
                self.doc = fitz.open(file_path)
                
                filename = os.path.basename(file_path)
                self.file_label.config(
                    text=f"✅ {filename} ({len(self.doc)} pages)",
                    fg="#27ae60"
                )
                
                # Enable buttons
                self.replace_btn.config(state="normal")
                self.save_btn.config(state="normal")
                self.extract_btn.config(state="normal")
                
                # Show preview
                self.show_preview()
                
                self.status_bar.config(text=f"✅ Loaded: {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load PDF:\n{e}")
                self.status_bar.config(text="❌ Error loading PDF")
    
    def show_preview(self):
        """PDF ka text preview dikhao"""
        if self.doc:
            try:
                # First page ka text extract karo
                page = self.doc[0]
                text = page.get_text()
                
                self.preview_text.config(state="normal")
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.insert(1.0, text[:2000] + "\n\n... (showing first 2000 chars)")
                self.preview_text.config(state="disabled")
                
            except Exception as e:
                self.preview_text.config(state="normal")
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.insert(1.0, f"Error: {e}")
                self.preview_text.config(state="disabled")
    
    def replace_text(self):
        """Text find karke replace karo"""
        if not self.doc:
            messagebox.showwarning("Warning", "Please upload a PDF first!")
            return
        
        old = self.old_text.get()
        new = self.new_text.get()
        
        if not old:
            messagebox.showwarning("Warning", "Please enter text to find!")
            return
        
        try:
            replaced_count = 0
            
            for page in self.doc:
                text_instances = page.search_for(old)
                
                for inst in text_instances:
                    page.add_redact_annot(inst, fill=(1, 1, 1))
                
                page.apply_redactions()
                
                for inst in text_instances:
                    page.insert_text(
                        (inst.x0, inst.y0 + 10),
                        new,
                        fontsize=11,
                        color=(0, 0, 0)
                    )
                    replaced_count += 1
            
            if replaced_count > 0:
                messagebox.showinfo(
                    "Success", 
                    f"✅ Replaced '{old}' with '{new}'\n{replaced_count} instances found"
                )
                self.status_bar.config(text=f"✅ Replaced {replaced_count} instances")
                self.show_preview()
            else:
                messagebox.showinfo("Info", f"No instances of '{old}' found")
                self.status_bar.config(text=f"❌ Text '{old}' not found")
                
        except Exception as e:
            messagebox.showerror("Error", f"Replace failed:\n{e}")
    
    def save_pdf(self):
        """Modified PDF save karo"""
        if not self.doc:
            messagebox.showwarning("Warning", "No PDF loaded!")
            return
        
        save_path = filedialog.asksaveasfilename(
            title="Save Edited PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        
        if save_path:
            try:
                self.doc.save(save_path)
                messagebox.showinfo("Success", f"✅ Saved to:\n{save_path}")
                self.status_bar.config(text=f"✅ Saved: {os.path.basename(save_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Save failed:\n{e}")
    
    def extract_all_text(self):
        """Saara text extract karke dikhao"""
        if not self.doc:
            messagebox.showwarning("Warning", "No PDF loaded!")
            return
        
        try:
            all_text = ""
            for page_num, page in enumerate(self.doc):
                all_text += f"\n{'='*50}\nPage {page_num + 1}\n{'='*50}\n"
                all_text += page.get_text()
            
            self.preview_text.config(state="normal")
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, all_text)
            self.preview_text.config(state="disabled")
            
            self.status_bar.config(text="✅ Extracted all text")
            
        except Exception as e:
            messagebox.showerror("Error", f"Extraction failed:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFEditorGUI(root)
    root.mainloop()