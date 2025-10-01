import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import json
import re
import nltk
import string
import unicodedata
from collections import Counter, defaultdict
import emoji
import requests
from urllib.parse import urlparse
import threading
from spellchecker import SpellChecker
import stanza
import os
import difflib

class AdvancedTextProcessor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Advanced Text Processor - Gelişmiş Metin İşleyici v3.0")
        self.root.geometry("1000x700")

        # Data variables
        self.df = None
        self.original_df = None
        self.current_file = None
        self.processing = False

        # Spell checkers
        self.init_spell_checkers()

        # Stanza NLP pipeline
        self.stanza_nlp = None
        self.stanza_ready = False
        self.init_stanza_async()

        # Stopwords dosyası
        self.stopwords_file = "stopwords.json"
        self.load_stopwords()

        # Custom corrections (user-provided or learned from corpus)
        self.custom_corrections = {}
        self.custom_corrections_file = "custom_corrections.json"
        self.load_custom_corrections_json(silent=True)

        # Ana GUI'yi oluştur
        self.create_widgets()
    
    def init_stanza_async(self):
        """Stanza'yı arka planda başlat"""
        def init_stanza():
            try:
                print("Stanza NLP sistemi başlatılıyor...")
                self.stanza_nlp = stanza.Pipeline('tr', verbose=False)
                self.stanza_ready = True
                print("✅ Stanza hazır!")
                # GUI'yi güncelle
                if hasattr(self, 'status_label'):
                    self.status_label.config(text="Durum: Stanza NLP hazır ✅")
            except Exception as e:
                print(f"Stanza başlatılamadı: {e}")
                self.stanza_ready = False
                if hasattr(self, 'status_label'):
                    self.status_label.config(text="Durum: Stanza yüklenemedi ❌")
        
        # Thread'de başlat
        threading.Thread(target=init_stanza, daemon=True).start()
    
    def init_spell_checkers(self):
        """Initialize spell checkers for different languages"""
        try:
            # English spell checker
            self.spell_en = SpellChecker(language='en')
            
            # For Turkish, we'll use a basic approach since pyspellchecker doesn't have Turkish
            # You could add a Turkish word list here
            self.spell_tr = None  # We'll implement a basic Turkish checker
            
            self.spell_available = True
        except Exception as e:
            print(f"Spell checker initialization failed: {e}")
            self.spell_available = False
            self.spell_en = None
            self.spell_tr = None
        
    def download_nltk_data(self):
        """Download required NLTK data"""
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
        except:
            pass
    
    def load_stopwords(self):
        """Load stopwords from JSON file"""
        try:
            with open('stopwords.json', 'r', encoding='utf-8') as f:
                self.stopwords = json.load(f)
        except FileNotFoundError:
            messagebox.showwarning("Warning", "stopwords.json not found. Using default stopwords.")
            self.stopwords = {
                "turkish": ["ve", "ile", "bu", "bir", "o", "şu", "da", "de", "ki", "mi", "mı", "mu", "mü"],
                "english": ["and", "the", "is", "in", "to", "of", "a", "that", "it", "with", "for", "as", "was", "on", "are"]
            }
    
    def create_widgets(self):
        """Create the main GUI widgets"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Main processing tab
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Main Processing")
        
        # Settings tab
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="Settings")
        
        # Results tab
        results_tab = ttk.Frame(notebook)
        notebook.add(results_tab, text="Results & Analysis")
        
        self.create_main_tab(main_tab)
        self.create_settings_tab(settings_tab)
        self.create_results_tab(results_tab)
    
    def create_main_tab(self, parent):
        """Create main processing tab"""
        # File operations
        file_frame = ttk.LabelFrame(parent, text="File Operations", padding="5")
        file_frame.pack(fill='x', pady=(0, 10))
        
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill='x')
        
        ttk.Button(btn_frame, text="Select CSV File", command=self.select_file).pack(side='left', padx=(0, 5))
        ttk.Button(btn_frame, text="Process File", command=self.process_file).pack(side='left', padx=(0, 5))
        ttk.Button(btn_frame, text="Save Results", command=self.save_results).pack(side='left', padx=(0, 5))
        ttk.Button(btn_frame, text="Test Hybrid NLP", command=self.test_hybrid_nlp).pack(side='left', padx=(0, 5))
        
        # Selected file label
        self.file_label = ttk.Label(file_frame, text="Dosya seçilmedi", foreground="gray")
        self.file_label.pack(pady=(5, 0), anchor='w')
        
        # Data info frame
        info_frame = ttk.LabelFrame(parent, text="Data Information", padding="10")
        info_frame.pack(fill='x', pady=(0, 10))
        
        self.info_text = tk.Text(info_frame, height=4, wrap=tk.WORD)
        info_scroll = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scroll.set)
        self.info_text.pack(side='left', fill='both', expand=True)
        info_scroll.pack(side='right', fill='y')
        
        # Column selection section
        column_frame = ttk.LabelFrame(parent, text="Processing Configuration", padding="10")
        column_frame.pack(fill='x', pady=(0, 10))
        
        # Column selection
        col_select_frame = ttk.Frame(column_frame)
        col_select_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(col_select_frame, text="Text Column:").pack(side='left', padx=(0, 10))
        self.column_var = tk.StringVar()
        self.column_combo = ttk.Combobox(col_select_frame, textvariable=self.column_var, state="readonly", width=20)
        self.column_combo.pack(side='left', padx=(0, 20))
        
        ttk.Label(col_select_frame, text="Language:").pack(side='left', padx=(0, 10))
        self.language_var = tk.StringVar(value="turkish")
        language_combo = ttk.Combobox(col_select_frame, textvariable=self.language_var, 
                                    values=["turkish", "english"], state="readonly", width=15)
        language_combo.pack(side='left')
        
        # Processing options
        options_frame = ttk.LabelFrame(column_frame, text="Processing Options", padding="5")
        options_frame.pack(fill='x')
        
        # Create checkboxes in a grid
        self.create_processing_checkboxes(options_frame)
        
        # Process buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="Process Text", command=self.process_text_threaded).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Step-by-Step Analysis", command=self.open_step_analysis).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Save Processed CSV", command=self.save_csv).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Reset Data", command=self.reset_data).pack(side='left', padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stop Processing", command=self.stop_processing, state='disabled')
        self.stop_button.pack(side='left')
        
        # Progress section
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding="5")
        progress_frame.pack(fill='x', pady=(10, 0))
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill='x', pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack()
        
        # Stanza status
        self.status_label = ttk.Label(progress_frame, text="Stanza NLP: Yükleniyor... ⏳", font=('Arial', 8))
        self.status_label.pack(pady=(5, 0))
    
    def create_processing_checkboxes(self, parent):
        """Create processing option checkboxes"""
        self.lowercase_var = tk.BooleanVar(value=True)
        self.punctuation_var = tk.BooleanVar(value=True)
        self.special_chars_var = tk.BooleanVar(value=True)
        self.numbers_var = tk.BooleanVar(value=False)
        self.normalize_var = tk.BooleanVar(value=True)
        self.tokenize_var = tk.BooleanVar(value=True)
        self.stopwords_var = tk.BooleanVar(value=True)
        self.lemmatize_var = tk.BooleanVar(value=True)
        self.negation_var = tk.BooleanVar(value=True)
        self.spellcheck_var = tk.BooleanVar(value=False)
        self.use_custom_corrections_var = tk.BooleanVar(value=True)

        options = [
            ("Lowercase", self.lowercase_var),
            ("Remove Punctuation", self.punctuation_var),
            ("Remove Special Chars/URLs/Emojis", self.special_chars_var),
            ("Remove Numbers", self.numbers_var),
            ("Normalize Turkish Characters", self.normalize_var),
            ("Tokenization", self.tokenize_var),
            ("Remove Stopwords", self.stopwords_var),
            ("Lemmatization/Stemming", self.lemmatize_var),
            ("Handle Negations", self.negation_var),
            ("Spell Check", self.spellcheck_var),
            ("Use Custom Corrections", self.use_custom_corrections_var),
        ]

        for i, (text, var) in enumerate(options):
            row = i // 3
            col = i % 3
            ttk.Checkbutton(parent, text=text, variable=var).grid(row=row, column=col, sticky='w', padx=5, pady=2)
    
    def create_settings_tab(self, parent):
        """Create settings tab"""
        # Stopwords editor
        stopwords_frame = ttk.LabelFrame(parent, text="Stopwords Management", padding="10")
        stopwords_frame.pack(fill='both', expand=True, pady=(0, 10))

        # Language selection for stopwords
        lang_frame = ttk.Frame(stopwords_frame)
        lang_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(lang_frame, text="Language:").pack(side='left', padx=(0, 10))
        self.stopwords_lang_var = tk.StringVar(value="turkish")
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.stopwords_lang_var,
                                  values=["turkish", "english"], state="readonly")
        lang_combo.pack(side='left', padx=(0, 20))
        lang_combo.bind('<<ComboboxSelected>>', self.update_stopwords_display)

        ttk.Button(lang_frame, text="Refresh", command=self.update_stopwords_display).pack(side='left')

        # Stopwords text area
        self.stopwords_text = tk.Text(stopwords_frame, height=15, wrap=tk.WORD)
        stopwords_scroll = ttk.Scrollbar(stopwords_frame, orient=tk.VERTICAL, command=self.stopwords_text.yview)
        self.stopwords_text.configure(yscrollcommand=stopwords_scroll.set)
        self.stopwords_text.pack(side='left', fill='both', expand=True)
        stopwords_scroll.pack(side='right', fill='y')

        # Stopwords buttons
        stopwords_btn_frame = ttk.Frame(parent)
        stopwords_btn_frame.pack(fill='x', pady=5)

        ttk.Button(stopwords_btn_frame, text="Save Stopwords", command=self.save_stopwords).pack(side='left', padx=(0, 10))
        ttk.Button(stopwords_btn_frame, text="Reset to Default", command=self.reset_stopwords).pack(side='left')

        self.update_stopwords_display()

        # Custom corrections management
        cc_frame = ttk.LabelFrame(parent, text="Custom Corrections", padding="10")
        cc_frame.pack(fill='x', pady=(10, 5))

        ttk.Label(cc_frame, text="Manage explicit word-level corrections (applied before other spell rules). ").grid(row=0, column=0, columnspan=4, sticky='w')

        ttk.Button(cc_frame, text="Load JSON…", command=self.load_custom_corrections_json).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Button(cc_frame, text="Save JSON", command=self.save_custom_corrections_json).grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(cc_frame, text="Build from /input CSVs", command=self.build_corrections_from_input_dir).grid(row=1, column=2, padx=5, pady=5, sticky='w')
        ttk.Button(cc_frame, text="Clear In-Memory", command=self.clear_custom_corrections).grid(row=1, column=3, padx=5, pady=5, sticky='w')

        # Small info
        self.cc_status_label = ttk.Label(cc_frame, text=f"Loaded {len(self.custom_corrections)} corrections.")
        self.cc_status_label.grid(row=2, column=0, columnspan=4, sticky='w', padx=5)
    
    def create_results_tab(self, parent):
        """Create results and analysis tab"""
        # Results text area
        self.results_text = tk.Text(parent, wrap=tk.WORD, font=('Consolas', 10))
        results_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scroll.set)
        
        self.results_text.pack(side='left', fill='both', expand=True)
        results_scroll.pack(side='right', fill='y')
        
        # Results buttons
        results_btn_frame = ttk.Frame(parent)
        results_btn_frame.pack(side='bottom', fill='x', pady=5)
        
        ttk.Button(results_btn_frame, text="Clear Results", command=self.clear_results).pack(side='left', padx=(0, 10))
        ttk.Button(results_btn_frame, text="Export Results", command=self.export_results).pack(side='left')
    
    def update_stopwords_display(self, event=None):
        """Update stopwords display based on selected language"""
        lang = self.stopwords_lang_var.get()
        self.stopwords_text.delete(1.0, tk.END)
        if lang in self.stopwords:
            stopwords_str = '\n'.join(self.stopwords[lang])
            self.stopwords_text.insert(1.0, stopwords_str)
    
    def save_stopwords(self):
        """Save edited stopwords"""
        lang = self.stopwords_lang_var.get()
        content = self.stopwords_text.get(1.0, tk.END).strip()
        self.stopwords[lang] = [word.strip() for word in content.split('\n') if word.strip()]
        
        try:
            with open('stopwords.json', 'w', encoding='utf-8') as f:
                json.dump(self.stopwords, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Success", f"Stopwords for {lang} saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save stopwords: {str(e)}")
    
    def reset_stopwords(self):
        """Reset stopwords to default"""
        # Default stopwords (simplified)
        defaults = {
            "turkish": ["ve", "ile", "bu", "bir", "o", "şu", "da", "de", "ki", "mi", "mı", "mu", "mü", "için", "olan", "olarak", "ama", "ancak", "çok", "daha", "her", "hiç", "kendi", "ne", "sonra", "var", "yok", "şey", "yani"],
            "english": ["the", "and", "is", "in", "to", "of", "a", "that", "it", "with", "for", "as", "was", "on", "are", "but", "they", "be", "at", "one", "have", "this", "from", "or", "had", "by", "word", "not", "what", "all"]
        }
        
        lang = self.stopwords_lang_var.get()
        if lang in defaults:
            self.stopwords[lang] = defaults[lang]
            self.update_stopwords_display()
            messagebox.showinfo("Success", f"Stopwords for {lang} reset to default!")
    
    def load_csv(self):
        """Load CSV file"""
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # Try different encodings
                for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']:
                    try:
                        self.df = pd.read_csv(file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise UnicodeDecodeError("Could not decode file with any encoding")
                
                self.original_df = self.df.copy()
                
                # Update column combobox
                self.column_combo['values'] = list(self.df.columns)
                if 'comment' in self.df.columns:
                    self.column_combo.set('comment')
                elif len(self.df.columns) > 0:
                    self.column_combo.set(self.df.columns[0])
                
                self.file_label.config(text=f"Loaded: {file_path.split('/')[-1]}")
                
                # Update info display
                self.update_info_display()
                
                self.log_result(f"CSV file loaded successfully! Encoding: {encoding}")
                self.log_result(f"Shape: {self.df.shape}")
                self.log_result(f"Columns: {list(self.df.columns)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")
    
    def update_info_display(self):
        """Update data information display"""
        if self.df is not None:
            self.info_text.delete(1.0, tk.END)
            
            info = f"Shape: {self.df.shape}\n"
            info += f"Columns: {', '.join(self.df.columns)}\n"
            
            # Show data types
            info += "Data types:\n"
            for col, dtype in self.df.dtypes.items():
                info += f"  {col}: {dtype}\n"
            
            self.info_text.insert(1.0, info)
    
    def process_text_threaded(self):
        """Process text in a separate thread"""
        if self.processing:
            messagebox.showwarning("Warning", "Processing is already in progress.")
            return
        
        thread = threading.Thread(target=self.process_text)
        thread.daemon = True
        thread.start()
    
    def process_text(self):
        """Process the selected text column"""
        if self.df is None:
            messagebox.showwarning("Warning", "Please load a CSV file first.")
            return
        
        if not self.column_var.get():
            messagebox.showwarning("Warning", "Please select a column to process.")
            return
        
        column_name = self.column_var.get()
        language = self.language_var.get()
        
        if column_name not in self.df.columns:
            messagebox.showerror("Error", f"Column '{column_name}' not found in the dataset.")
            return
        
        self.processing = True
        self.stop_button.config(state='normal')
        
        try:
            # Create new column name for processed text
            processed_column = f"{column_name}_processed"
            
            self.log_result(f"\nStarting processing of column '{column_name}' with language '{language}'...")
            
            processed_texts = []
            total_rows = len(self.df)
            
            self.progress.config(maximum=total_rows)
            
            for idx, text in enumerate(self.df[column_name]):
                if not self.processing:  # Check if stopped
                    self.log_result("Processing stopped by user.")
                    return
                
                processed_text = self.clean_text(text, language)
                processed_texts.append(processed_text)
                
                # Update progress
                self.progress.config(value=idx + 1)
                self.progress_label.config(text=f"Processing {idx + 1}/{total_rows}")
                self.root.update_idletasks()
            
            # Add processed column to dataframe
            self.df[processed_column] = processed_texts
            
            # Add ID column based on total rows
            self.add_id_column()
            
            # Add comment length columns for both original and processed text
            self.add_comment_length_columns(column_name, processed_column)
            
            # Add sentiment analysis columns if score exists
            self.add_sentiment_columns()
            
            # Show results
            self.show_processing_results(column_name, processed_column)
            
            self.log_result(f"Processing completed successfully!")
            
        except Exception as e:
            self.log_result(f"Error during processing: {str(e)}")
            messagebox.showerror("Error", f"Failed to process text: {str(e)}")
        
        finally:
            self.processing = False
            self.stop_button.config(state='disabled')
            self.progress_label.config(text="Ready")
            self.progress.config(value=0)
    
    def stop_processing(self):
        """Stop text processing"""
        self.processing = False
    
    def clean_text(self, text, language="turkish", debug_mode=False):
        """Clean and process text based on selected options"""
        if pd.isna(text):
            return ""
        
        text = str(text)
        original_text = text
        
        # Debug tracking
        debug_steps = []
        if debug_mode:
            debug_steps.append(("0. Original Text", original_text))
        
        # Step 1: Lowercase
        if self.lowercase_var.get():
            text = text.lower()
            if debug_mode:
                debug_steps.append(("1. Lowercase", text))
        
        # Step 2: Remove URLs and social media elements
        if self.special_chars_var.get():
            text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
            text = re.sub(r'@\w+|#\w+', '', text)  # Remove mentions and hashtags
            if debug_mode:
                debug_steps.append(("2. Remove URLs/Social", text))
        
        # Step 3: Remove emojis
        if self.special_chars_var.get():
            text = emoji.demojize(text)
            text = re.sub(r':[a-z_&+-]+:', '', text)  # Remove emoji text representations
            if debug_mode:
                debug_steps.append(("3. Remove Emojis", text))
        
        # Step 4: Normalize Turkish characters (optional)
        if self.normalize_var.get() and language == "turkish":
            text = self.normalize_turkish_text(text)
            if debug_mode:
                debug_steps.append(("4. Normalize Turkish", text))
        
        # Step 5: Remove numbers
        if self.numbers_var.get():
            text = re.sub(r'\d+', '', text)
            if debug_mode:
                debug_steps.append(("5. Remove Numbers", text))
        
        # Step 6: Remove punctuation
        if self.punctuation_var.get():
            text = text.translate(str.maketrans('', '', string.punctuation))
            if debug_mode:
                debug_steps.append(("6. Remove Punctuation", text))
        
        # Step 7: Remove extra special characters
        if self.special_chars_var.get():
            text = re.sub(r'[^\w\s]', '', text)
            if debug_mode:
                debug_steps.append(("7. Remove Special Chars", text))
        
        # Step 8: Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        if debug_mode:
            debug_steps.append(("8. Clean Whitespace", text))
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Step 9: Advanced tokenization and processing
        if self.tokenize_var.get():
            # Advanced tokenization
            tokens = self.advanced_tokenize(text, language)
            if debug_mode:
                debug_steps.append(("9. Tokenization", ' '.join(tokens)))
            
            # Handle negations BEFORE removing stopwords
            if self.negation_var.get():
                tokens = self.handle_negations_advanced(tokens, language)
                if debug_mode:
                    debug_steps.append(("10. Handle Negations", ' '.join(tokens)))
            
            # Remove stopwords (but preserve negation markers)
            if self.stopwords_var.get() and language in self.stopwords:
                filtered_tokens = []
                for token in tokens:
                    # Keep negation markers and important words
                    if '_NEG' in token or '_NOT' in token or token.lower() not in self.stopwords[language]:
                        filtered_tokens.append(token)
                tokens = filtered_tokens
                if debug_mode:
                    debug_steps.append(("11. Remove Stopwords", ' '.join(tokens)))
            
            # Spell checking BEFORE stemming
            if self.spellcheck_var.get():
                tokens = self.spell_check_tokens(tokens, language)
                if debug_mode:
                    debug_steps.append(("12. Spell Check", ' '.join(tokens)))
            
            # Advanced lemmatization/stemming
            if self.lemmatize_var.get():
                if self.stanza_ready:
                    # Stanza ile profesyonel lemmatization
                    text_for_stanza = ' '.join(tokens)
                    lemmatized_tokens = self.stanza_lemmatize(text_for_stanza, language)
                    tokens = lemmatized_tokens
                    if debug_mode:
                        debug_steps.append(("13. Stanza Lemmatization", ' '.join(tokens)))
                else:
                    # Fallback: Stanza yoksa uyarı ver
                    if debug_mode:
                        debug_steps.append(("13. Lemmatization (Stanza not ready)", ' '.join(tokens)))
            
            # Final token cleanup: remove single-character tokens
            tokens = [token for token in tokens if len(token) > 1 or token in 'aioueıöü']
            if debug_mode:
                debug_steps.append(("14. Final Token Cleanup", ' '.join(tokens)))
            
            # Join tokens back to text
            text = ' '.join(tokens)
        
        # Final cleanup
        text = re.sub(r'\s+', ' ', text).strip()
        if debug_mode:
            debug_steps.append(("15. Final Result", text))
            
        # Return debug info if requested
        if debug_mode:
            return text, debug_steps
        
        return text
    
    def handle_negations(self, text, language):
        """Handle negations in text"""
        if language == "turkish":
            # Turkish negation patterns
            negation_patterns = [
                (r'\bdeğil\b', ' NOT_'),
                (r'\byok\b', ' NOT_'),
                (r'\bhiç\b', ' NOT_'),
                (r'\b-me\b', ' NOT_'),
                (r'\b-ma\b', ' NOT_')
            ]
        else:
            # English negation patterns
            negation_patterns = [
                (r'\bnot\b', ' NOT_'),
                (r'\bno\b', ' NOT_'),
                (r'\bnever\b', ' NOT_'),
                (r'\bnothing\b', ' NOT_'),
                (r"\bcan't\b", ' NOT_'),
                (r"\bwon't\b", ' NOT_'),
                (r"\bdon't\b", ' NOT_')
            ]
        
        for pattern, replacement in negation_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def normalize_turkish_text(self, text):
        """Normalize Turkish characters"""
        # Keep original Turkish characters for now, just clean
        return text
    
    def advanced_tokenize(self, text, language="turkish"):
        """Advanced tokenization with proper sentence and word segmentation"""
        if not text or pd.isna(text):
            return []
        
        text = str(text).strip()
        
        # Basic tokenization using NLTK
        try:
            # Use word_tokenize for better tokenization
            tokens = nltk.word_tokenize(text, language='turkish' if language == 'turkish' else 'english')
            
            # Clean tokens - remove empty and single character tokens (except meaningful ones)
            meaningful_single_chars = {'a', 'i', 'o', 'u', 'e'}  # Meaningful single character words
            cleaned_tokens = []
            
            for token in tokens:
                token = token.strip()
                if len(token) >= 2 or token.lower() in meaningful_single_chars:
                    cleaned_tokens.append(token)
            
            return cleaned_tokens
            
        except Exception as e:
            # Fallback to simple split
            return text.split()
    
    def handle_negations_advanced(self, tokens, language="turkish"):
        """Advanced negation handling that combines negation words with following words"""
        if not tokens:
            return []
        
        if language == "turkish":
            negation_words = ['değil', 'yok', 'hiç', 'asla', 'hayır', 'olmaz', 'imkansız']
            negation_suffixes = ['ma', 'me', 'maz', 'mez']
        else:
            negation_words = ['not', 'no', 'never', 'nothing', 'nobody', 'nowhere', 'neither']
            contractions = ["n't", "nt"]
        
        result_tokens = []
        i = 0
        
        while i < len(tokens):
            current_token = tokens[i].lower()
            original_token = tokens[i]
            
            # Check for negation words
            if current_token in negation_words:
                # Sonraki kelimeyi al ve birleştir
                if i + 1 < len(tokens):
                    next_token = tokens[i+1]
                    combined = f"{next_token}_NEG"
                    result_tokens.append(combined)
                    i += 2  # Hem negasyon kelimesini hem de sonraki kelimeyi atla
                else:
                    # Cümlenin sonunda tek başına kalmışsa, sadece işareti ekle
                    result_tokens.append(f"{original_token}_NEG")
                    i += 1
            
            # Check for Turkish negation suffixes
            elif language == "turkish" and any(current_token.endswith(suffix) for suffix in negation_suffixes):
                # Kelimeyi _NEG ile işaretle
                base_word = original_token
                for suffix in negation_suffixes:
                    if base_word.endswith(suffix):
                        base_word = base_word[:-len(suffix)]
                        break
                result_tokens.append(f"{base_word}_NEG")
                i += 1
            
            # Check for English contractions
            elif language == "english" and any(current_token.endswith(contr) for contr in contractions):
                # Handle contractions like "don't", "won't"
                if "n't" in current_token:
                    base_word = current_token.replace("n't", "")
                    result_tokens.append(f"{base_word}_NOT")
                else:
                    base_word = current_token.replace("nt", "")
                    result_tokens.append(f"{base_word}_NOT")
                i += 1
            
            else:
                result_tokens.append(original_token)
                i += 1
        
        return result_tokens
        
    def simple_turkish_stem(self, word):
        """Improved Turkish stemming with better validation"""
        if not word or len(word) < 4:  # Don't stem very short words
            return word
        
        original_word = word
        word_lower = word.lower()
        
        # Common Turkish suffixes (more conservative approach)
        conservative_suffixes = [
            'ları', 'leri',  # Plural possessive
            'ların', 'lerin',  # Plural genitive  
            'lardan', 'lerden',  # Plural ablative
            'larda', 'lerde',  # Plural locative
            'lar', 'ler',  # Plural
            'nin', 'nın', 'nun', 'nün',  # Genitive
            'den', 'dan', 'ten', 'tan',  # Ablative
            'nde', 'nda',  # Locative
            'ile', 'le',  # Instrumental
        ]
        
        # Only apply to words longer than suffix + 3 characters
        for suffix in sorted(conservative_suffixes, key=len, reverse=True):
            if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 3:
                stemmed = word[:-len(suffix)]
                # Additional validation - avoid over-stemming
                if len(stemmed) >= 3 and not self.is_over_stemmed(stemmed, suffix):
                    return stemmed
        
        return original_word
    
    def is_over_stemmed(self, stemmed, removed_suffix):
        """Check if stemming removed too much"""
        # Don't stem if result is too short relative to original
        if len(stemmed) < 3:
            return True
        
        # Don't stem common words that might be over-stemmed
        protected_words = {
            'havalimanı': True,  # havalimanı -> havaliman (BAD)
            'yoğun': True,       # yoğun -> yog (BAD)
            'güzel': True,       # güzel should stay güzel
            'mükemmel': True,    # mükemmel should stay mükemmel
        }
        
        if stemmed in protected_words:
            return True
            
        return False
    
    def spell_check_tokens(self, tokens, language="turkish"):
        """Apply spell checking to tokens"""
        if not self.spell_available or not tokens:
            return tokens
        
        corrected_tokens = []
        
        for token in tokens:
            # Skip negation markers and special tokens
            if '_NEG' in token or '_NOT' in token or len(token) < 3:
                corrected_tokens.append(token)
                continue

            # Apply custom corrections first (exact match on lowercase)
            if self.use_custom_corrections_var.get():
                t_low = token.lower()
                if t_low in self.custom_corrections:
                    corrected_tokens.append(self.custom_corrections[t_low])
                    continue
            
            if language == "english" and self.spell_en:
                # Use pyspellchecker for English
                if token.lower() not in self.spell_en:
                    # Get correction
                    correction = self.spell_en.correction(token.lower())
                    if correction and correction != token.lower():
                        corrected_tokens.append(correction)
                    else:
                        corrected_tokens.append(token)
                else:
                    corrected_tokens.append(token)
            
            elif language == "turkish":
                # Basic Turkish spell checking using common patterns
                corrected = self.basic_turkish_spell_check(token)
                corrected_tokens.append(corrected)
            
            else:
                corrected_tokens.append(token)
        
        return corrected_tokens

    def load_custom_corrections_json(self, silent=False):
        """Load custom corrections from a JSON file."""
        try:
            # If called from UI, open file dialog; else use default path if exists
            file_path = None
            if not silent:
                file_path = filedialog.askopenfilename(
                    title="Select custom_corrections.json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
            else:
                # try default
                if os.path.exists(self.custom_corrections_file):
                    file_path = self.custom_corrections_file
            
            if not file_path:
                if not silent:
                    messagebox.showinfo("Info", "No JSON selected.")
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Normalize keys to lowercase strings
                self.custom_corrections = {str(k).lower(): str(v) for k, v in data.items()}
            if hasattr(self, 'cc_status_label'):
                self.cc_status_label.config(text=f"Loaded {len(self.custom_corrections)} corrections from {os.path.basename(file_path)}")
            if not silent:
                messagebox.showinfo("Success", f"Loaded {len(self.custom_corrections)} corrections.")
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to load corrections: {e}")

    def save_custom_corrections_json(self):
        """Save current custom corrections to JSON file."""
        try:
            file_path = filedialog.asksaveasfilename(
                title="Save custom corrections",
                defaultextension=".json",
                initialfile="custom_corrections.json",
                filetypes=[("JSON files", "*.json")]
            )
            if not file_path:
                return
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.custom_corrections, f, ensure_ascii=False, indent=2)
            if hasattr(self, 'cc_status_label'):
                self.cc_status_label.config(text=f"Saved {len(self.custom_corrections)} corrections to {os.path.basename(file_path)}")
            messagebox.showinfo("Success", f"Saved {len(self.custom_corrections)} corrections.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save corrections: {e}")

    def clear_custom_corrections(self):
        """Clear in-memory custom corrections."""
        self.custom_corrections = {}
        if hasattr(self, 'cc_status_label'):
            self.cc_status_label.config(text="Loaded 0 corrections.")

    def build_corrections_from_input_dir(self):
        """Auto-build corrections from CSVs under ./input (speel.csv, speelbygemini.csv)."""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            input_dir = os.path.join(base_dir, 'input')
            candidates = [
                os.path.join(input_dir, 'speel.csv'),
                os.path.join(input_dir, 'speelbygemini.csv')
            ]
            files = [p for p in candidates if os.path.exists(p)]
            if not files:
                messagebox.showwarning("Warning", "No CSVs found in ./input (speel.csv, speelbygemini.csv)")
                return
            learned = self.build_corrections_from_csvs(files)
            # Merge into existing
            self.custom_corrections.update(learned)
            if hasattr(self, 'cc_status_label'):
                self.cc_status_label.config(text=f"Loaded {len(self.custom_corrections)} corrections (learned {len(learned)}).")
            messagebox.showinfo("Success", f"Learned {len(learned)} corrections from corpus.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to build from input: {e}")

    def build_corrections_from_csvs(self, file_paths, min_support=3, cutoff=0.84):
        """Derive token-level corrections from CSV(s) with columns 'comment' and 'comment_processed'.
        Returns a dict mapping wrong_token -> corrected_token.
        """
        mapping_counts = defaultdict(Counter)

        def tokenize_orig(text):
            if pd.isna(text):
                return []
            text = str(text).lower()
            # Keep Turkish letters
            return re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+", text)

        def tokenize_proc(text):
            if pd.isna(text):
                return []
            toks = str(text).split()
            # Keep unigram-like tokens: letters-only; drop bigrams/NEG markers
            out = []
            for t in toks:
                t = t.strip()
                if not t or '_' in t:
                    continue
                if re.fullmatch(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+", t):
                    out.append(t.lower())
            return out

        for path in file_paths:
            try:
                df = pd.read_csv(path, encoding='utf-8')
            except Exception:
                df = pd.read_csv(path, encoding='latin-1')

            if not {'comment', 'comment_processed'} <= set(df.columns):
                # Skip if required columns not present
                continue

            for _, row in df.iterrows():
                orig_tokens = tokenize_orig(row['comment'])
                proc_tokens = tokenize_proc(row['comment_processed'])
                if not orig_tokens or not proc_tokens:
                    continue
                # Unique processed set for faster matching
                proc_set = set(proc_tokens)
                for w in orig_tokens:
                    if w in proc_set:
                        continue
                    # Find close match in processed tokens
                    # Candidates sharing prefix to reduce false matches
                    pref = w[:2]
                    pool = [p for p in proc_set if p.startswith(pref) and abs(len(p) - len(w)) <= 3]
                    if not pool:
                        # fallback to whole set for very short words
                        pool = list(proc_set) if len(w) <= 4 else []
                    if not pool:
                        continue
                    match = difflib.get_close_matches(w, pool, n=1, cutoff=cutoff)
                    if match:
                        c = match[0]
                        if c != w:
                            mapping_counts[w][c] += 1

        learned = {}
        for wrong, cnts in mapping_counts.items():
            best, freq = cnts.most_common(1)[0]
            total = sum(cnts.values())
            # Accept if strong majority and enough support
            if freq >= min_support and freq / max(total, 1) >= 0.7:
                learned[wrong] = best

        return learned
    
    def basic_turkish_spell_check(self, word):
        """Basic Turkish spell checking with common fixes and abbreviation expansion"""
        word_lower = word.lower()
        
        # Turkish abbreviations and expansions
        abbreviations = {
            'zmn': 'zaman',
            'slm': 'selam',
            'mrb': 'merhaba', 
            'krm': 'kardeş',
            'tşk': 'teşekkür',
            'prgrm': 'program',
            'dvn': 'divan',
            'hyr': 'hayır',
            'evt': 'evet',
            'nsl': 'nasıl',
            'nrd': 'nerede',
            'ndn': 'neden',
            'tmm': 'tamam',
            'grv': 'görev',
            'blg': 'bilgi',
            'dkt': 'dikkat',
            'frk': 'fark',
            'snc': 'sonuç',
            'bnm': 'benim',
            'snin': 'senin',
            'bzm': 'bizim',
            'szin': 'sizin',
            'glb': 'galiba',
            'hrld': 'herhalde',
            'kbl': 'kabul',
            'msl': 'mesela',
            'rnk': 'renk',
            'frst': 'fırsat',
            'sbb': 'sebep',
            'drm': 'durum',
            'klt': 'kültür',
            'trc': 'tercih',
            'yml': 'yemek',
            'iş': 'iş',    # Keep as is
            'her': 'her',  # Keep as is
        }
        
        # Common Turkish spelling mistakes and fixes
        common_fixes = {
            # Yaygın yazım hataları
            'güzeel': 'güzel',
            'mükemmeel': 'mükemmel', 
            'havalimani': 'havalimanı',
            'yogurt': 'yoğurt',
            'turkiye': 'türkiye',
            'turkce': 'türkçe',
            'ingilizce': 'ingilizce',
            'arastirma': 'araştırma',
            'gelisme': 'gelişme',
            'dusunce': 'düşünce',
            'kullanici': 'kullanıcı',
            'saglik': 'sağlık',
            'egitim': 'eğitim',
            'ogretmen': 'öğretmen',
            'universite': 'üniversite',
            
            # Yaygın klavye hataları ve typo'lar
            'neseka': 'nasılsa',
            'yazdıpım': 'yazdığım',
            'fogurusunu': 'doğrusunu',
            'sekilde': 'şekilde',
            'kelimelrien': 'kelimelerin',
            'değişmeisni': 'değiştirmesini',
            'isityorum': 'istiyorum',
            'yazılım': 'yazılım',
            'porgram': 'program',
            'proğram': 'program',
            'comupter': 'computer',
            'bilgisyar': 'bilgisayar',
            'teknolji': 'teknoloji',
            'anlayabilyiorum': 'anlayabiliyorum',
            'yapabilyiorum': 'yapabiliyorum',
            'isteyiorum': 'istiyorum',
            'geliyorum': 'geliyorum',
            'gidyiorum': 'gidiyorum',
            'edyiorum': 'ediyorum',
            'yapiyor': 'yapıyor',
            'gidyior': 'gidiyor',
            'gelyior': 'geliyor',
            'istyior': 'istiyor',
            'çalışyior': 'çalışıyor',
            'düşünüyrum': 'düşünüyorum',
            'söylüyrum': 'söylüyorum',
            'biliyrum': 'biliyorum',
            'görüyrum': 'görüyorum',
            'anlıyorum': 'anlıyorum',
            'gerekiyor': 'gerekiyor',
            'lazım': 'lazım',
            'şimdi': 'şimdi',
            'sonra': 'sonra',
            'önce': 'önce',
            'şöyle': 'şöyle',
            'böyle': 'böyle',
            'neden': 'neden',
            'niçin': 'niçin',
            'çünkü': 'çünkü',
            'rğmen': 'rağmen',
            'dolayi': 'dolayı',
            'nedeniyle': 'nedeniyle',
            'sayesinde': 'sayesinde',
            'aracılgıyla': 'aracılığıyla',
            'veya': 'veya',
            'yada': 'ya da',
            'hemde': 'hem de',
            'ayrıca': 'ayrıca',
            'bunun': 'bunun',
            'şunun': 'şunun',
            'onun': 'onun',
            'benım': 'benim',
            'senın': 'senin',
            'bizım': 'bizim',
            'sizın': 'sizin',
            'onların': 'onların',
            'yakında': 'yakında',
            'uzakta': 'uzakta',
            'burada': 'burada',
            'şurada': 'şurada',
            'orada': 'orada',
            'nerede': 'nerede',
            'neresi': 'neresi',
            'hangisi': 'hangisi',
            'kimse': 'kimse',
            'hiçbir': 'hiçbir',
            'herkes': 'herkes',
            'herkez': 'herkes',
            'herşey': 'her şey',
            'hiçbirşey': 'hiçbir şey',
            'birşey': 'bir şey',
            'bazıları': 'bazıları',
            'çoğu': 'çoğu',
            'hepsi': 'hepsi',
            'tümü': 'tümü',
            'yarısı': 'yarısı',
            'çeyreği': 'çeyreği',
            'dörtte': 'dörtte',
            'üçte': 'üçte',
            'ikide': 'ikide',
            'birde': 'bir de',
            'aynı': 'aynı',
            'farklı': 'farklı',
            'benzer': 'benzer',
            'değişik': 'değişik',
            'başka': 'başka',
            'diğer': 'diğer',
            'öteki': 'öteki',
        }
        
        # First check abbreviations
        if word_lower in abbreviations:
            return abbreviations[word_lower]
        
        # Then check for exact matches in common fixes
        if word_lower in common_fixes:
            return common_fixes[word_lower]
        
        # Check for common character replacements
        corrected = word_lower
        
        # Common Turkish character corrections
        char_fixes = {
            'i̇': 'i',  # Dotted i
            'ı': 'ı',   # Dotless i
            'I': 'ı',   # Capital I to dotless i (in lowercase context)
        }
        
        for wrong, correct in char_fixes.items():
            corrected = corrected.replace(wrong, correct)
        
        # Advanced pattern-based corrections
        corrected = self.advanced_pattern_correction(corrected)
        
        # If word was modified, return corrected version
        if corrected != word_lower:
            return corrected
        
        # Return original if no correction found
        return word
    
    def advanced_pattern_correction(self, word):
        """Advanced pattern-based spelling correction"""
        
        # Protected words that should NOT be corrected
        protected_words = {
            'büyük', 'koruyucu', 'güzel', 'mükemmel', 'havalimanı', 
            'yoğun', 'küçük', 'oruyucu', 'üyük', 'öyle', 'böyle',
            'sürekli', 'gerçek', 'önemli', 'güvenli', 'doğru',
            'yuvarlak', 'oyuncu', 'sayısal', 'ayakkabı', 'yaşlı'
        }
        
        # Don't correct protected words
        if word.lower() in protected_words:
            return word
        
        # Common Turkish typing patterns and corrections
        patterns = [
            # SADECE bilinen hatalı yazımları düzelt
            
            # -rum yerine -yorum (sadece kelimenin sonunda)
            (r'([a-zA-ZşğüöçıİĞÜÖÇ]+)rum$', r'\1yorum'),  # biliyrum -> biliyorum
            
            # Duplicate letters - SADECE 3+ ardışık karakterler için
            (r'([a-zA-ZşğüöçıİĞÜÖÇ])\1{2,}', r'\1'),     # güzeeeel -> güzel, çoooook -> çok
            
            # Spesifik bilinen hatalar
            (r'yapiyor', 'yapıyor'),
            (r'gelyior', 'geliyor'),
            (r'gidyior', 'gidiyor'),
            (r'istyior', 'istiyor'),
            
            # Common consonant confusions
            (r'porgram', 'program'),
            (r'proğram', 'program'),
            (r'comupter', 'computer'),
            
            # ğ/g confusions
            (r'dogru', 'doğru'),
            (r'saglik', 'sağlık'),
            (r'ogrenci', 'öğrenci'),
        ]
        
        corrected = word
        for pattern, replacement in patterns:
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        return corrected
    
    def stanza_lemmatize(self, text, language="turkish"):
        """Stanza ile profesyonel lemmatization ve n-gram oluşturma"""
        if not self.stanza_ready or not text.strip():
            return text.split()
        
        try:
            doc = self.stanza_nlp(text)
            lemmas = []
            
            # Unigram'ları (tekli kelimeler) topla
            for sentence in doc.sentences:
                for word in sentence.words:
                    # Sadece anlamlı kelimeleri al (NOUN, VERB, ADJ, ADV, PROPN)
                    if word.upos in ['NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN']:
                        # Negasyon ekini koru
                        if '_NEG' in word.text or '_NOT' in word.text:
                            lemmas.append(f"{word.lemma}_NEG")
                        else:
                            lemmas.append(word.lemma.lower())
            
            # Bigram'ları (ikili kelime grupları) oluştur
            bigrams = ['_'.join(gram) for gram in nltk.bigrams(lemmas)]
            
            # Unigram ve Bigram'ları birleştir
            return lemmas + bigrams
            
        except Exception as e:
            print(f"Stanza lemmatization hatası: {e}")
            return text.split()
    
    def test_hybrid_nlp(self):
        """Hibrit NLP sistemini test et"""
        test_window = tk.Toplevel(self.root)
        test_window.title("Hibrit NLP Test")
        test_window.geometry("800x600")
        
        # Test input
        input_frame = ttk.LabelFrame(test_window, text="Test Input", padding="10")
        input_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(input_frame, text="Test metni (yazım hatalı da olabilir):").pack(anchor='w')
        input_text = tk.Text(input_frame, height=3, wrap='word')
        input_text.pack(fill='x', pady=(5, 0))
        input_text.insert('1.0', "neseka yazdıpım güzeeeel kitaplar okuyorum kardesm arkdş ile gelyior dogru")
        
        # Test button
        ttk.Button(input_frame, text="Test Et", 
                  command=lambda: self.run_hybrid_test(input_text, result_text)).pack(pady=10)
        
        # Results
        result_frame = ttk.LabelFrame(test_window, text="Test Results", padding="10")
        result_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        result_text = tk.Text(result_frame, wrap='word', font=('Courier', 10))
        result_text.pack(fill='both', expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=result_text.yview)
        scrollbar.pack(side='right', fill='y')
        result_text.config(yscrollcommand=scrollbar.set)
    
    def run_hybrid_test(self, input_widget, result_widget):
        """Hibrit test çalıştır"""
        test_text = input_widget.get('1.0', 'end-1c').strip()
        if not test_text:
            return
        
        result_widget.delete('1.0', 'end')
        result_widget.insert('end', "🚀 Hibrit NLP Test Sonuçları\n")
        result_widget.insert('end', "=" * 50 + "\n\n")
        
        # Orijinal
        result_widget.insert('end', f"📝 Orijinal Metin:\n{test_text}\n\n")
        
        # 1. Adım: Yazım düzeltme 
        result_widget.insert('end', "1️⃣ Yazım Düzeltme Sonucu:\n")
        corrected_text = self.clean_text(test_text)  # Sadece spell check
        result_widget.insert('end', f"{corrected_text}\n\n")
        
        # 2. Adım: Stanza lemmatization
        result_widget.insert('end', "2️⃣ Stanza Lemmatization:\n")
        if self.stanza_ready:
            lemmatized = self.stanza_lemmatize(corrected_text)
            result_widget.insert('end', f"{lemmatized}\n\n")
            
            result_widget.insert('end', "3️⃣ Detaylı Analiz:\n")
            try:
                doc = self.stanza_nlp(corrected_text)
                for sentence in doc.sentences:
                    for word in sentence.words:
                        result_widget.insert('end', 
                            f"  {word.text:<12} → {word.lemma:<12} [{word.upos}]\n")
            except Exception as e:
                result_widget.insert('end', f"Analiz hatası: {e}\n")
        else:
            result_widget.insert('end', "Stanza henüz yüklenmedi ❌\n\n")
        
        # Performance info
        result_widget.insert('end', "\n" + "=" * 50 + "\n")
        stanza_status = "✅ Hazır" if self.stanza_ready else "❌ Yüklenmedi"
        result_widget.insert('end', f"🔧 Stanza Durumu: {stanza_status}\n")
        result_widget.insert('end', f"📊 Test Tamamlandı!")
        
        result_widget.see('end')
    
    def select_file(self):
        """CSV dosyası seç"""
        filename = filedialog.askopenfilename(
            title="CSV Dosyası Seçin",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.current_file = filename
            
            # File label'ı güncelle
            file_name = filename.split('/')[-1]  # Sadece dosya adı
            self.file_label.config(text=f"📁 Seçilen: {file_name}", foreground="blue")
            
            self.info_text.delete('1.0', 'end')
            self.info_text.insert('end', f"Seçilen dosya: {filename}\n")
            
            # Dosya bilgilerini göster ve column combobox'ı güncelle
            try:
                df = pd.read_csv(filename, encoding='utf-8')
                self.update_file_info_and_columns(df, filename)
            except:
                try:
                    df = pd.read_csv(filename, encoding='latin-1')
                    self.update_file_info_and_columns(df, filename)
                except Exception as e:
                    self.info_text.insert('end', f"Dosya okuma hatası: {e}\n")
                    # File label'ı sıfırla
                    self.file_label.config(text="❌ Dosya okunamadı", foreground="red")
                    # Column combobox'ı temizle
                    self.column_combo['values'] = []
                    self.column_var.set("")
    
    def update_file_info_and_columns(self, df, filename):
        """Dosya bilgilerini göster ve column seçeneklerini güncelle"""
        # DataFrame'i sakla (process_text için gerekli)
        self.df = df
        self.original_df = df.copy()
        
        # Dosya bilgileri
        self.info_text.insert('end', f"Satır sayısı: {len(df)}\n")
        self.info_text.insert('end', f"Sütunlar: {list(df.columns)}\n")
        
        # Text içeren sütunları bul
        text_columns = []
        for col in df.columns:
            if df[col].dtype == 'object':  # String sütunlar
                # İlk 5 satıra bak, text içeriyor mu?
                sample_texts = df[col].dropna().head(5)
                if len(sample_texts) > 0:
                    # En az bir örnekte 10+ karakter varsa text sütunu kabul et
                    has_text = any(len(str(text)) > 10 for text in sample_texts)
                    if has_text:
                        text_columns.append(col)
        
        # Column combobox'ı güncelle
        if text_columns:
            self.column_combo['values'] = text_columns
            self.column_var.set(text_columns[0])  # İlk text sütununu seç
            self.info_text.insert('end', f"Text sütunları: {text_columns}\n")
            self.info_text.insert('end', f"Seçilen sütun: {text_columns[0]}\n")
        else:
            self.column_combo['values'] = list(df.columns)
            self.column_var.set("")
            self.info_text.insert('end', "⚠️  Text sütunu bulunamadı. Tüm sütunlar gösteriliyor.\n")
        
        # Örnek veri göster
        self.info_text.insert('end', f"\n📝 İlk 3 satır örneği:\n")
        for i in range(min(3, len(df))):
            for col in df.columns[:3]:  # İlk 3 sütun
                value = str(df.iloc[i][col])[:50] + "..." if len(str(df.iloc[i][col])) > 50 else str(df.iloc[i][col])
                self.info_text.insert('end', f"{col}: {value}\n")
            self.info_text.insert('end', "---\n")
    
    def process_file(self):
        """Seçilen CSV dosyasını işle"""
        if not hasattr(self, 'current_file'):
            messagebox.showwarning("Uyarı", "Önce bir CSV dosyası seçin.")
            return
        
        try:
            # Dosyayı oku
            df = self.detect_and_read_csv(self.current_file)
            if df is None:
                return
            
            # Seçilen sütunu kontrol et
            selected_column = self.column_var.get()
            if not selected_column:
                messagebox.showerror("Hata", "Lütfen işlenecek sütunu seçin.")
                return
            
            if selected_column not in df.columns:
                messagebox.showerror("Hata", f"Seçilen sütun '{selected_column}' dosyada bulunamadı.")
                return
            
            # Seçilen sütunu işle
            column = selected_column
            self.progress_label.config(text=f"İşleniyor: {column}")
            
            # İşleme başla
            self.current_data = df.copy()
            self.original_data = df.copy()
            
            processed_texts = []
            total_rows = len(df)
            self.progress.config(maximum=total_rows)
            
            for idx, text in enumerate(df[column]):
                if pd.isna(text):
                    processed_texts.append("")
                else:
                    processed = self.clean_text(str(text))
                    processed_texts.append(processed)
                
                # Progress güncellemesi
                self.progress.config(value=idx + 1)
                self.progress_label.config(text=f"İşleniyor: {idx + 1}/{total_rows}")
                self.root.update_idletasks()
            
            # Sonuçları kaydet
            self.current_data[f'{column}_processed'] = processed_texts
            
            # Sonuçları göster
            self.results_text.delete('1.0', 'end')
            self.results_text.insert('end', f"İşlem tamamlandı!\n\n")
            self.results_text.insert('end', f"İşlenen sütun: {column}\n")
            self.results_text.insert('end', f"Toplam satır: {total_rows}\n\n")
            
            # İlk 5 örneği göster
            for i in range(min(5, len(df))):
                original = str(df.iloc[i][column])[:100]
                processed = processed_texts[i][:100]
                self.results_text.insert('end', f"Örnek {i+1}:\n")
                self.results_text.insert('end', f"  Orijinal: {original}...\n")
                self.results_text.insert('end', f"  İşlenmiş: {processed}...\n\n")
            
            self.progress_label.config(text="Tamamlandı ✅")
            messagebox.showinfo("Başarılı", "Dosya işleme tamamlandı!")
            
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya işleme hatası: {e}")
            self.progress_label.config(text="Hata ❌")
    
    def save_results(self):
        """İşlenmiş sonuçları kaydet"""
        if not hasattr(self, 'current_data'):
            messagebox.showwarning("Uyarı", "Önce bir dosya işleyin.")
            return
        
        filename = filedialog.asksaveasfilename(
            title="İşlenmiş CSV'yi Kaydet",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.current_data.to_csv(filename, index=False, encoding='utf-8')
                messagebox.showinfo("Başarılı", f"Sonuçlar kaydedildi: {filename}")
            except Exception as e:
                messagebox.showerror("Hata", f"Kaydetme hatası: {e}")
    
    def detect_and_read_csv(self, filename):
        """CSV dosyasını encoding tespit ederek oku"""
        try:
            # Önce utf-8 dene
            return pd.read_csv(filename, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # Latin-1 dene
                return pd.read_csv(filename, encoding='latin-1')
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya okunamadı: {e}")
                return None
    
    def run(self):
        """Uygulamayı başlat"""
        self.root.mainloop()
    
    def advanced_lemmatize(self, tokens, language="turkish"):
        """Improved lemmatization/stemming with better control"""
        if not tokens:
            return tokens
        
        lemmatized_tokens = []
        
        for token in tokens:
            # Skip negation markers and special tokens
            if '_NEG' in token or '_NOT' in token or len(token) < 3:
                lemmatized_tokens.append(token)
                continue
            
            if language == "turkish":
                # Use improved Turkish stemming (less aggressive)
                stemmed = self.simple_turkish_stem(token)
                lemmatized_tokens.append(stemmed)
            else:
                # For English, use basic stemming
                stemmed = self.basic_english_stem(token)
                lemmatized_tokens.append(stemmed)
        
        return lemmatized_tokens
    
    def basic_english_stem(self, word):
        """Basic English stemming"""
        # Simple English suffixes
        suffixes = ['ing', 'ed', 'er', 'est', 'ly', 'tion', 'ness', 'ment', 's']
        
        word_lower = word.lower()
        for suffix in sorted(suffixes, key=len, reverse=True):
            if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 2:
                return word[:-len(suffix)]
        
        return word
    
    def add_sentiment_columns(self):
        """Add sentiment analysis columns based on score"""
        if 'score' in self.df.columns:
            def categorize_sentiment(score):
                try:
                    score = float(score)
                    if score in [1, 2]:
                        return 'negative'
                    elif score == 3:
                        return 'neutral'
                    elif score in [4, 5]:
                        return 'positive'
                    else:
                        return 'unknown'
                except:
                    return 'unknown'
            
            self.df['sentiment'] = self.df['score'].apply(categorize_sentiment)
            self.log_result("Added sentiment categorization based on score.")
    
    def add_id_column(self):
        """Add ID column with dynamic format based on total rows"""
        total_rows = len(self.df)
        
        # Determine number of digits needed
        digits = len(str(total_rows))
        
        # Generate IDs with proper padding
        ids = []
        for i in range(1, total_rows + 1):
            id_str = str(i).zfill(digits)
            ids.append(id_str)
        
        # Add ID column at the beginning
        self.df.insert(0, 'comment_id', ids)
        self.log_result(f"Added comment_id column with {digits}-digit format (e.g., {ids[0]}, {ids[-1]})")
    
    def add_comment_length_columns(self, original_column, processed_column):
        """Add comment length columns for both original and processed text"""
        # Calculate length of original text
        self.df['comment_length_original'] = self.df[original_column].astype(str).str.len()
        
        # Calculate length of processed text
        self.df['comment_length_processed'] = self.df[processed_column].astype(str).str.len()
        
        # Show statistics
        original_avg = self.df['comment_length_original'].mean()
        processed_avg = self.df['comment_length_processed'].mean()
        reduction = ((original_avg - processed_avg) / original_avg * 100) if original_avg > 0 else 0
        
        self.log_result(f"Added comment length columns:")
        self.log_result(f"  - comment_length_original (avg: {original_avg:.1f} chars)")
        self.log_result(f"  - comment_length_processed (avg: {processed_avg:.1f} chars)")
        self.log_result(f"  - Length reduction: {reduction:.1f}%")
    
    def show_processing_results(self, original_column, processed_column):
        """Show processing results"""
        self.log_result("\n" + "="*60)
        self.log_result("PROCESSING RESULTS")
        self.log_result("="*60)
        
        # Show before/after examples
        self.log_result("\nBefore/After Examples:")
        for i in range(min(5, len(self.df))):
            original = str(self.df[original_column].iloc[i])[:150]
            processed = str(self.df[processed_column].iloc[i])[:150]
            self.log_result(f"\nExample {i+1}:")
            self.log_result(f"Original:  {original}...")
            self.log_result(f"Processed: {processed}...")
            self.log_result("-" * 40)
        
        # Show statistics
        self.show_statistics(original_column, processed_column)
    
    def show_statistics(self, original_column, processed_column):
        """Show processing statistics"""
        self.log_result("\nProcessing Statistics:")
        self.log_result("-" * 30)
        
        # Count non-empty texts
        original_non_empty = self.df[original_column].notna().sum()
        processed_non_empty = self.df[processed_column].str.len().gt(0).sum()
        
        self.log_result(f"Total rows: {len(self.df)}")
        self.log_result(f"Original non-empty: {original_non_empty}")
        self.log_result(f"Processed non-empty: {processed_non_empty}")
        
        # Average text length
        original_avg_len = self.df[original_column].str.len().mean()
        processed_avg_len = self.df[processed_column].str.len().mean()
        
        self.log_result(f"Average original length: {original_avg_len:.1f} chars")
        self.log_result(f"Average processed length: {processed_avg_len:.1f} chars")
        self.log_result(f"Length reduction: {((original_avg_len - processed_avg_len) / original_avg_len * 100):.1f}%")
        
        # Show column info
        self.log_result(f"\nNew columns added:")
        self.log_result(f"- comment_id")
        self.log_result(f"- {processed_column}")
        self.log_result(f"- comment_length_original")
        self.log_result(f"- comment_length_processed")
        
        if 'sentiment' in self.df.columns:
            self.log_result("- sentiment")
            sentiment_counts = self.df['sentiment'].value_counts()
            self.log_result(f"\nSentiment distribution:")
            for sentiment, count in sentiment_counts.items():
                percentage = (count / len(self.df)) * 100
                self.log_result(f"  {sentiment}: {count} ({percentage:.1f}%)")
        
        self.log_result(f"\nFinal dataframe shape: {self.df.shape}")
    
    def log_result(self, message):
        """Log message to results"""
        self.results_text.insert(tk.END, message + "\n")
        self.results_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_results(self):
        """Clear results text"""
        self.results_text.delete(1.0, tk.END)
    
    def export_results(self):
        """Export results to text file"""
        content = self.results_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showwarning("Warning", "No results to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Results",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Results exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export results: {str(e)}")
    
    def save_csv(self):
        """Save processed CSV file"""
        if self.df is None:
            messagebox.showwarning("Warning", "No data to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save processed CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.df.to_csv(file_path, index=False, encoding='utf-8')
                messagebox.showinfo("Success", f"File saved successfully!")
                self.log_result(f"File saved to: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
    
    def reset_data(self):
        """Reset data to original state"""
        if self.original_df is not None:
            self.df = self.original_df.copy()
            self.update_info_display()
            self.log_result("Data reset to original state.")
            messagebox.showinfo("Success", "Data reset to original state.")
        else:
            messagebox.showwarning("Warning", "No original data to reset to.")
    
    def open_step_analysis(self):
        """Open step-by-step analysis window"""
        analysis_window = tk.Toplevel(self.root)
        analysis_window.title("Step-by-Step Text Processing Analysis")
        analysis_window.geometry("900x700")
        
        # Input section
        input_frame = ttk.LabelFrame(analysis_window, text="Test Input", padding="10")
        input_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(input_frame, text="Test metni girin:").pack(anchor='w')
        input_text = tk.Text(input_frame, height=3, wrap='word')
        input_text.pack(fill='x', pady=(5, 0))
        input_text.insert('1.0', "Bu harika bir ürün yapiyor! Neseka yazdıpım güzeeeel yorumlar çoooook beğeniliyor. @kullanici #hashtag https://example.com")
        
        # Language selection
        lang_frame = ttk.Frame(input_frame)
        lang_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Label(lang_frame, text="Dil:").pack(side='left', padx=(0, 10))
        analysis_lang_var = tk.StringVar(value="turkish")
        ttk.Combobox(lang_frame, textvariable=analysis_lang_var, 
                    values=["turkish", "english"], state="readonly", width=15).pack(side='left')
        
        # Analyze button
        ttk.Button(input_frame, text="🔍 Adım Adım Analiz Et", 
                  command=lambda: self.run_step_analysis(input_text, analysis_lang_var, result_text)).pack(pady=10)
        
        # Results section
        result_frame = ttk.LabelFrame(analysis_window, text="Step-by-Step Results", padding="10")
        result_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create text widget with scrollbar
        result_text = tk.Text(result_frame, wrap='word', font=('Consolas', 10))
        scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=result_text.yview)
        result_text.config(yscrollcommand=scrollbar.set)
        
        result_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bottom buttons
        button_frame = ttk.Frame(analysis_window)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(button_frame, text="Temizle", 
                  command=lambda: result_text.delete(1.0, 'end')).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Sonuçları Kaydet", 
                  command=lambda: self.save_step_analysis(result_text)).pack(side='left')
    
    def run_step_analysis(self, input_widget, lang_var, result_widget):
        """Run step-by-step analysis"""
        test_text = input_widget.get('1.0', 'end-1c').strip()
        if not test_text:
            messagebox.showwarning("Uyarı", "Lütfen test metni girin.")
            return
        
        language = lang_var.get()
        
        result_widget.delete('1.0', 'end')
        result_widget.insert('end', "🔍 ADIM ADIM METİN İŞLEME ANALİZİ\n")
        result_widget.insert('end', "=" * 80 + "\n\n")
        
        try:
            # Get step-by-step processing
            final_result, debug_steps = self.clean_text(test_text, language, debug_mode=True)
            
            # Show each step
            for step_name, step_result in debug_steps:
                result_widget.insert('end', f"📋 {step_name}:\n")
                result_widget.insert('end', f"   '{step_result}'\n")
                result_widget.insert('end', f"   Uzunluk: {len(step_result)} karakter\n")
                result_widget.insert('end', "-" * 60 + "\n\n")
            
            # Summary
            result_widget.insert('end', "\n🎯 ÖZET ANALİZ\n")
            result_widget.insert('end', "=" * 40 + "\n")
            
            original_len = len(debug_steps[0][1]) if debug_steps else 0
            final_len = len(final_result)
            reduction = ((original_len - final_len) / original_len * 100) if original_len > 0 else 0
            
            result_widget.insert('end', f"📏 Orijinal uzunluk: {original_len} karakter\n")
            result_widget.insert('end', f"📏 Final uzunluk: {final_len} karakter\n")
            result_widget.insert('end', f"📊 Uzunluk azalması: {reduction:.1f}%\n")
            result_widget.insert('end', f"🔢 Toplam adım sayısı: {len(debug_steps)}\n")
            
            # Processing options status
            result_widget.insert('end', f"\n⚙️  AKTİF İŞLEME SEÇENEKLERİ:\n")
            options_status = [
                ("Küçük harf", self.lowercase_var.get()),
                ("Noktalama kaldır", self.punctuation_var.get()),
                ("Özel karakter/URL/Emoji kaldır", self.special_chars_var.get()),
                ("Sayıları kaldır", self.numbers_var.get()),
                ("Türkçe normalizasyon", self.normalize_var.get()),
                ("Tokenization", self.tokenize_var.get()),
                ("Stopword kaldır", self.stopwords_var.get()),
                ("Lemmatization", self.lemmatize_var.get()),
                ("Negasyon işleme", self.negation_var.get()),
                ("Yazım denetimi", self.spellcheck_var.get())
            ]
            
            for option_name, is_active in options_status:
                status = "✅" if is_active else "❌"
                result_widget.insert('end', f"   {status} {option_name}\n")
            
            # Stanza status
            stanza_status = "✅ Aktif" if self.stanza_ready else "❌ Yüklenmedi"
            result_widget.insert('end', f"\n🧠 Stanza NLP: {stanza_status}\n")
            
        except Exception as e:
            result_widget.insert('end', f"❌ HATA: {str(e)}\n")
            messagebox.showerror("Hata", f"Analiz sırasında hata oluştu: {str(e)}")
        
        result_widget.see('end')
    
    def save_step_analysis(self, result_widget):
        """Save step analysis results"""
        content = result_widget.get(1.0, 'end')
        if not content.strip():
            messagebox.showwarning("Uyarı", "Kaydedilecek sonuç yok.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Adım Adım Analiz Sonuçlarını Kaydet",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Başarılı", f"Analiz sonuçları kaydedildi: {file_path}")
            except Exception as e:
                messagebox.showerror("Hata", f"Kaydetme hatası: {str(e)}")

def main():
    app = AdvancedTextProcessor()
    app.run()

if __name__ == "__main__":
    main()
