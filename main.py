import tkinter as tk
from tkinter import filedialog, messagebox
import google.generativeai as genai
import pysrt
import webvtt
import threading
import os
import time


def setup_model(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name="gemini-1.5-flash")

def parse_vtt(file_path):
    vtt = webvtt.read(file_path)
    return [{
        'index': i + 1,
        'start': caption.start,
        'end': caption.end,
        'text': caption.text.replace('\n', ' ')
    } for i, caption in enumerate(vtt)]

def parse_srt(file_path):
    subs = pysrt.open(file_path)
    return [{
        'index': s.index,
        'start': s.start.to_time().strftime('%H:%M:%S,%f')[:-3],
        'end': s.end.to_time().strftime('%H:%M:%S,%f')[:-3],
        'text': s.text
    } for s in subs]

def batch_lines(subs, batch_size=10):
    return [subs[i:i+batch_size] for i in range(0, len(subs), batch_size)]

def translate_batch(model, prompt, batch):
    input_text = "\n".join([f"{line['text']}" for line in batch])
    full_prompt = f"{prompt}\n\nTexts:\n{input_text}\n\nPersian Translation:"
    response = model.generate_content(full_prompt)
    return response.text.strip().splitlines()

def save_translated_srt(subs, output_path):
    srt_file = pysrt.SubRipFile()
    for i, sub in enumerate(subs):
        srt_file.append(pysrt.SubRipItem(
            index=i+1,
            start=sub['start'],
            end=sub['end'],
            text=sub['text']
        ))
    srt_file.save(output_path, encoding='utf-8')

def process_translation(file_path, prompt, api_key):
    try:
        model = setup_model(api_key)
        ext = os.path.splitext(file_path)[1].lower()
        
        subs = parse_vtt(file_path) if ext == ".vtt" else parse_srt(file_path)
        batches = batch_lines(subs, 10)

        translated_subs = []
        for batch in batches:
            translated_lines = translate_batch(model, prompt, batch)
            for i, line in enumerate(batch):
                line['text'] = translated_lines[i] if i < len(translated_lines) else "[ترجمه نشد]"
            translated_subs.extend(batch)

        # ساخت مسیر ذخیره‌سازی خودکار
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        name, _ = os.path.splitext(base_name)
        output_path = os.path.join(dir_name, f"{name}-fa.srt")

        save_translated_srt(translated_subs, output_path)
        return output_path

    except Exception as e:
        raise Exception(f"خطا در پردازش: {str(e)}")

class TranslationApp:
    def __init__(self, master):
        self.master = master
        master.title("مترجم زیرنویس v2.0")
        self.create_widgets()

    def create_widgets(self):
        # بخش انتخاب فایل
        self.file_frame = tk.Frame(self.master)
        self.file_frame.pack(pady=10)
        
        self.btn_browse = tk.Button(
            self.file_frame, 
            text="انتخاب فایل زیرنویس",
            command=self.browse_file
        )
        self.btn_browse.pack(side=tk.LEFT, padx=5)

        self.lbl_file = tk.Label(self.file_frame, text="هیچ فایلی انتخاب نشده")
        self.lbl_file.pack(side=tk.LEFT)

        # بخش API Key
        self.api_frame = tk.Frame(self.master)
        self.api_frame.pack(pady=5)
        
        self.lbl_api = tk.Label(self.api_frame, text="کلید API:")
        self.lbl_api.pack(side=tk.LEFT)
        
        self.ent_api = tk.Entry(self.api_frame, width=50, show="*")
        self.ent_api.pack(side=tk.LEFT, padx=5)

        # بخش دستورات ترجمه
        self.prompt_frame = tk.Frame(self.master)
        self.prompt_frame.pack(pady=5)
        
        self.lbl_prompt = tk.Label(self.prompt_frame, text="دستورات ویژه (اختیاری):")
        self.lbl_prompt.pack()
        
        self.txt_prompt = tk.Text(self.prompt_frame, height=4, width=60)
        self.txt_prompt.pack()

        # دکمه شروع
        self.btn_start = tk.Button(
            self.master,
            text="شروع ترجمه",
            command=self.start_translation,
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=10
        )
        self.btn_start.pack(pady=15)

    def browse_file(self):
        file_types = [("فایل‌های زیرنویس", "*.srt *.vtt")]
        file_path = filedialog.askopenfilename(filetypes=file_types)
        if file_path:
            self.lbl_file.config(text=os.path.basename(file_path))
            self.file_path = file_path

    def start_translation(self):
        if not hasattr(self, 'file_path'):
            messagebox.showerror("خطا", "لطفا یک فایل انتخاب کنید")
            return

        api_key = self.ent_api.get().strip()
        if not api_key:
            messagebox.showerror("خطا", "کلید API وارد نشده")
            return

        prompt = self.txt_prompt.get("1.0", tk.END).strip()
        
        self.btn_start.config(state=tk.DISABLED, text="در حال ترجمه...")
        
        def translation_thread():
            try:
                output_path = process_translation(
                    self.file_path,
                    prompt,
                    api_key
                )
                messagebox.showinfo(
                    "ترجمه کامل شد",
                    f"فایل ترجمه شده ذخیره شد در:\n{output_path}"
                )
            except Exception as e:
                messagebox.showerror("خطا", str(e))
            finally:
                self.btn_start.config(state=tk.NORMAL, text="شروع ترجمه")

        threading.Thread(target=translation_thread, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = TranslationApp(root)
    root.geometry("600x400")
    root.mainloop()