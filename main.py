import json
import re
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import random

import db


def day_options():
    return ["All Days"] + [f"Day {d}" for d in db.get_days()]


def parse_day_selection(selection):
    if selection == "All Days":
        return None
    return int(selection.replace("Day ", ""))


class VocabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Daily Vocab Quiz")
        self.geometry("560x520")

        db.init_db()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.register_tab = RegisterTab(notebook)
        self.study_tab = StudyTab(notebook)
        self.quiz_tab = QuizTab(notebook)

        notebook.add(self.register_tab, text="Register")
        notebook.add(self.study_tab, text="Study")
        notebook.add(self.quiz_tab, text="Quiz")

        notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._notebook = notebook

    def _on_tab_changed(self, event):
        current = self._notebook.nametowidget(self._notebook.select())
        if current is self.study_tab:
            self.study_tab.load_words()
        elif current is self.quiz_tab:
            self.quiz_tab.on_tab_shown()


class RegisterTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        ttk.Label(
            self,
            text="Paste the JSON you got from GPT web below",
        ).pack(pady=(15, 5))

        placeholder = (
            '{\n  "day": 39,\n  "words": [\n'
            '    {"word": "Flame", "pos": "n.", "definition": "...",\n'
            '     "example": "...", "example_form": "flames"}\n'
            "  ]\n}"
        )
        self.json_text = tk.Text(self, height=15, width=64)
        self.json_text.pack(pady=10)
        self.json_text.insert(tk.END, placeholder)
        self.json_text.bind("<FocusIn>", self._clear_placeholder, add="+")

        button_row = ttk.Frame(self)
        button_row.pack(pady=5)
        ttk.Button(button_row, text="Save", command=self.save_to_db).pack(
            side="left", padx=5
        )
        ttk.Button(button_row, text="Check Day", command=self.check_day).pack(
            side="left", padx=5
        )
        ttk.Button(button_row, text="Delete Day", command=self.delete_day).pack(
            side="left", padx=5
        )

        self._placeholder_cleared = False

    def _clear_placeholder(self, event):
        if not self._placeholder_cleared:
            self.json_text.delete("1.0", tk.END)
            self._placeholder_cleared = True

    def save_to_db(self):
        raw = self.json_text.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("Warning", "No JSON pasted.")
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON format.\n{e}")
            return

        day = data.get("day")
        words = data.get("words", [])
        if day is None:
            messagebox.showerror("Error", "Missing 'day' value.")
            return
        if not words:
            messagebox.showerror("Error", "'words' list is empty.")
            return

        handout_id, saved_count, duplicate_count, skipped_count = db.save_handout(
            day, None, words
        )

        lines = [f"Day {day} — Newly saved: {saved_count}"]
        if duplicate_count:
            lines.append(f"Already registered (duplicate): {duplicate_count}")
        if skipped_count:
            lines.append(f"Skipped (missing word/definition): {skipped_count}")

        messagebox.showinfo("Save Result", "\n".join(lines))

    def check_day(self):
        day = simpledialog.askinteger("Check Day", "Enter the Day number to check")
        if day is None:
            return

        rows = db.get_words(day)
        if not rows:
            messagebox.showinfo("Lookup Result", f"No words saved for Day {day}.")
            return

        word_list = "\n".join(f"- {r[1]}" for r in rows)
        messagebox.showinfo(
            "Lookup Result",
            f"Words already saved for Day {day} ({len(rows)})\n\n{word_list}",
        )

    def delete_day(self):
        day = simpledialog.askinteger("Delete Day", "Enter the Day number to delete")
        if day is None:
            return

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete ALL data for Day {day}? This cannot be undone.",
        ):
            return

        deleted = db.delete_handout_by_day(day)
        if deleted:
            messagebox.showinfo(
                "Deleted", f"Day {day} and all its words have been deleted."
            )
        else:
            messagebox.showinfo("Not Found", f"No data found for Day {day}.")


class EditWordDialog(tk.Toplevel):
    def __init__(self, parent, row, on_saved):
        super().__init__(parent)
        self.title("Edit Word")
        self.resizable(False, False)

        vid, word, pos, definition, example, example_form = row
        self.vid = vid
        self.on_saved = on_saved

        ttk.Label(self, text="Word").pack(anchor="w", padx=10, pady=(10, 0))
        self.word_entry = ttk.Entry(self, width=45)
        self.word_entry.insert(0, word)
        self.word_entry.pack(padx=10)

        ttk.Label(self, text="Part of speech").pack(anchor="w", padx=10, pady=(10, 0))
        self.pos_entry = ttk.Entry(self, width=45)
        self.pos_entry.insert(0, pos or "")
        self.pos_entry.pack(padx=10)

        ttk.Label(self, text="Definition").pack(anchor="w", padx=10, pady=(10, 0))
        self.definition_text = tk.Text(self, height=3, width=48)
        self.definition_text.insert("1.0", definition)
        self.definition_text.pack(padx=10)

        ttk.Label(self, text="Example").pack(anchor="w", padx=10, pady=(10, 0))
        self.example_text = tk.Text(self, height=3, width=48)
        self.example_text.insert("1.0", example or "")
        self.example_text.pack(padx=10)

        ttk.Label(
            self, text="Example form (word exactly as it appears in the example)"
        ).pack(anchor="w", padx=10, pady=(10, 0))
        self.example_form_entry = ttk.Entry(self, width=45)
        self.example_form_entry.insert(0, example_form or "")
        self.example_form_entry.pack(padx=10)

        button_row = ttk.Frame(self)
        button_row.pack(pady=15)
        ttk.Button(button_row, text="Save", command=self.save).pack(
            side="left", padx=5
        )
        ttk.Button(button_row, text="Cancel", command=self.destroy).pack(
            side="left", padx=5
        )

    def save(self):
        word = self.word_entry.get().strip()
        pos = self.pos_entry.get().strip() or None
        definition = self.definition_text.get("1.0", tk.END).strip()
        example = self.example_text.get("1.0", tk.END).strip() or None
        example_form = self.example_form_entry.get().strip() or None

        if not word or not definition:
            messagebox.showerror(
                "Error", "Word and definition are required.", parent=self
            )
            return

        db.update_word(self.vid, word, pos, definition, example, example_form)
        self.on_saved()
        self.destroy()


class StudyTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        top_row = ttk.Frame(self)
        top_row.pack(pady=10, padx=10, fill="x")
        ttk.Label(top_row, text="Day:").pack(side="left")
        self.day_var = tk.StringVar(value="All Days")
        self.day_combo = ttk.Combobox(
            top_row, textvariable=self.day_var, state="readonly", width=15
        )
        self.day_combo.pack(side="left", padx=5)
        self.day_combo.bind("<<ComboboxSelected>>", lambda e: self.load_words())
        ttk.Button(top_row, text="Refresh", command=self.load_words).pack(
            side="left", padx=5
        )

        columns = ("word", "pos")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        self.tree.heading("word", text="Word")
        self.tree.heading("pos", text="POS")
        self.tree.column("word", width=220)
        self.tree.column("pos", width=80)
        self.tree.pack(pady=5, padx=10, fill="x")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.detail_label = ttk.Label(
            self,
            text="Select a word to see its details.",
            wraplength=500,
            justify="left",
            font=("", 11),
        )
        self.detail_label.pack(pady=10, padx=10, anchor="w")

        ttk.Button(self, text="Edit Selected Word", command=self.edit_selected).pack(
            pady=5
        )

        self._rows_by_iid = {}
        self.load_words()

    def load_words(self):
        current = self.day_var.get()
        options = day_options()
        self.day_combo["values"] = options
        self.day_var.set(current if current in options else "All Days")

        day_number = parse_day_selection(self.day_var.get())

        self.tree.delete(*self.tree.get_children())
        self._rows_by_iid = {}
        self.detail_label.config(text="Select a word to see its details.")
        for row in db.get_words(day_number):
            vid, word, pos, definition, example, example_form = row
            iid = self.tree.insert("", "end", values=(word, pos or ""))
            self._rows_by_iid[iid] = row

    def _on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        _vid, word, pos, definition, example, example_form = self._rows_by_iid[
            selection[0]
        ]
        pos_text = f"({pos}) " if pos else ""
        text = f"{word}\n\n{pos_text}{definition}"
        if example:
            text += f"\n\nExample: {example}"
        if example_form:
            text += f"\nBlank-quiz answer: {example_form}"
        self.detail_label.config(text=text)

    def edit_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a word first.")
            return
        row = self._rows_by_iid[selection[0]]
        EditWordDialog(self, row, on_saved=self.load_words)


class QuizTab(ttk.Frame):
    NUM_DEFINE_QUESTIONS = 10
    NUM_BLANK_QUESTIONS = 10

    def __init__(self, parent):
        super().__init__(parent)
        self.questions = []
        self.current_index = 0
        self.score = 0
        self.wrong_answers = []
        self.selected_day = None

        # --- setup screen ---
        self.setup_frame = ttk.Frame(self)
        ttk.Label(
            self.setup_frame, text="Choose a day to quiz on", font=("", 11)
        ).pack(pady=(40, 10))
        self.day_var = tk.StringVar(value="All Days")
        self.day_combo = ttk.Combobox(
            self.setup_frame, textvariable=self.day_var, state="readonly", width=20
        )
        self.day_combo.pack(pady=5)
        ttk.Button(self.setup_frame, text="Start Quiz", command=self.start_quiz).pack(
            pady=15
        )

        # --- quiz screen ---
        self.quiz_frame = ttk.Frame(self)

        top_bar = ttk.Frame(self.quiz_frame)
        top_bar.pack(fill="x", padx=20, pady=(15, 0))

        self.progress_label = ttk.Label(top_bar, text="", font=("", 10))
        self.progress_label.pack(side="left")

        self.finish_button = ttk.Button(
            top_bar, text="Finish", command=self.confirm_finish
        )
        self.finish_button.pack(side="right")

        self.question_label = ttk.Label(
            self.quiz_frame, text="", wraplength=480, font=("", 12)
        )
        self.question_label.pack(pady=25)

        self.answer_entry = ttk.Entry(self.quiz_frame, width=30, font=("", 12))
        self.answer_entry.pack(pady=10)
        self.answer_entry.bind("<Return>", lambda e: self.submit_answer())

        button_row = ttk.Frame(self.quiz_frame)
        button_row.pack(pady=5)
        self.submit_button = ttk.Button(
            button_row, text="Submit", command=self.submit_answer
        )
        self.submit_button.pack(side="left", padx=5)
        self.show_button = ttk.Button(
            button_row, text="Show", command=self.show_answer
        )
        self.show_button.pack(side="left", padx=5)
        self.next_button = ttk.Button(
            button_row, text="Next", command=self.next_question, state="disabled"
        )
        self.next_button.pack(side="left", padx=5)

        self.feedback_label = ttk.Label(self.quiz_frame, text="", font=("", 11))
        self.feedback_label.pack(pady=10)

        # --- result screen ---
        self.result_frame = ttk.Frame(self)
        self.result_label = ttk.Label(
            self.result_frame, text="", font=("", 12), justify="left"
        )
        self.result_label.pack(pady=10)
        result_buttons = ttk.Frame(self.result_frame)
        result_buttons.pack(pady=10)
        ttk.Button(result_buttons, text="Retry", command=self.start_quiz).pack(
            side="left", padx=5
        )
        ttk.Button(
            result_buttons, text="Change Day", command=self.show_setup
        ).pack(side="left", padx=5)

        self.show_setup()

    def on_tab_shown(self):
        # 결과/퀴즈 화면 중이 아닐 때만 Day 목록을 새로고침
        if self.setup_frame.winfo_ismapped():
            self.day_combo["values"] = day_options()

    def show_setup(self):
        self.quiz_frame.pack_forget()
        self.result_frame.pack_forget()
        self.day_combo["values"] = day_options()
        if self.day_var.get() not in self.day_combo["values"]:
            self.day_var.set("All Days")
        self.setup_frame.pack(fill="both", expand=True)

    def start_quiz(self):
        self.selected_day = parse_day_selection(self.day_var.get())

        self.setup_frame.pack_forget()
        self.result_frame.pack_forget()
        self.quiz_frame.pack(fill="both", expand=True)

        self.score = 0
        self.wrong_answers = []
        self.current_index = 0
        self.answered = False
        self.questions = self._build_questions()
        self._show_question()

    def _build_questions(self):
        all_words = db.get_words(self.selected_day)

        define_pool = list(all_words)
        random.shuffle(define_pool)
        define_questions = []
        for row in define_pool:
            if len(define_questions) >= self.NUM_DEFINE_QUESTIONS:
                break
            vid, word, pos, definition, example, example_form = row
            prompt = f"({pos}) {definition}" if pos else definition
            define_questions.append(
                {"mode": "define", "id": vid, "answer": word, "prompt": prompt}
            )

        # 빈칸 문제는 example_form(예문에 실제 쓰인 형태)이 있는 단어만 후보로 사용
        blank_pool = [row for row in all_words if row[4] and row[5]]
        random.shuffle(blank_pool)
        blank_questions = []
        for row in blank_pool:
            if len(blank_questions) >= self.NUM_BLANK_QUESTIONS:
                break
            vid, word, pos, definition, example, example_form = row
            blanked = self._make_blank(example, example_form)
            if blanked is None:
                continue
            blank_questions.append(
                {"mode": "blank", "id": vid, "answer": example_form, "prompt": blanked}
            )

        return define_questions + blank_questions

    @staticmethod
    def _make_blank(example, example_form):
        pattern = re.compile(r"\b" + re.escape(example_form) + r"\b", re.IGNORECASE)
        match = pattern.search(example)
        if not match:
            return None
        blank = "_" * len(match.group(0))
        return pattern.sub(blank, example, count=1)

    def _show_question(self):
        self.answer_entry.delete(0, tk.END)
        self.feedback_label.config(text="")
        self.answered = False
        self.next_button.config(state="disabled")
        self.submit_button.config(state="normal")
        self.show_button.config(state="normal")
        self.answer_entry.focus_set()

        if not self.questions:
            self.progress_label.config(text="")
            self.question_label.config(
                text="No quizzable words for this selection yet."
            )
            return

        if self.current_index >= len(self.questions):
            self._show_results()
            return

        q = self.questions[self.current_index]
        self.progress_label.config(
            text=f"Question {self.current_index + 1} / {len(self.questions)}"
        )
        self.question_label.config(text=q["prompt"])

    def submit_answer(self):
        if not self.questions or self.current_index >= len(self.questions):
            return
        if self.answered:
            return

        q = self.questions[self.current_index]
        user_input = self.answer_entry.get().strip()
        is_correct = user_input.lower() == q["answer"].lower()

        db.record_attempt(q["id"], user_input, is_correct)

        if is_correct:
            self.score += 1
            self.answered = True
            self.feedback_label.config(text="Correct!", foreground="green")
            self.submit_button.config(state="disabled")
            self.show_button.config(state="disabled")
            self.next_button.config(state="normal")
        else:
            # 틀려도 정답은 안 보여주고 다시 시도할 수 있게 둠.
            # 같은 문구가 연달아 뜨면 안 바뀐 것처럼 보이니, 잠깐 지웠다가 다시 띄워서 눈에 띄게 함
            self.feedback_label.config(text="")
            self.answer_entry.delete(0, tk.END)
            self.answer_entry.focus_set()
            self.after(
                60,
                lambda: self.feedback_label.config(
                    text="Incorrect, try again.", foreground="red"
                ),
            )

    def show_answer(self):
        if not self.questions or self.current_index >= len(self.questions):
            return
        if self.answered:
            return

        q = self.questions[self.current_index]
        db.record_attempt(q["id"], self.answer_entry.get().strip(), False)

        self.wrong_answers.append(q["answer"])
        self.answered = True
        self.feedback_label.config(text=f"Answer: {q['answer']}", foreground="blue")
        self.submit_button.config(state="disabled")
        self.show_button.config(state="disabled")
        self.next_button.config(state="normal")

    def next_question(self):
        self.current_index += 1
        self._show_question()

    def confirm_finish(self):
        if not self.questions or self.current_index >= len(self.questions):
            return  # 이미 결과 화면이거나 문제가 없는 상태

        if not messagebox.askyesno(
            "Finish Quiz",
            "Finish the quiz now? Unanswered questions won't count.",
        ):
            return

        completed = self.current_index + (1 if self.answered else 0)
        self._show_results(total=completed)

    def _show_results(self, total=None):
        self.quiz_frame.pack_forget()

        if total is None:
            total = len(self.questions)
        lines = [f"Score: {self.score} / {total}"]
        if self.wrong_answers:
            lines.append("")
            lines.append("Words you missed:")
            lines.extend(f"- {w}" for w in self.wrong_answers)
        else:
            lines.append("")
            lines.append("Perfect score!")

        self.result_label.config(text="\n".join(lines))
        self.result_frame.pack(fill="both", expand=True, pady=20)


if __name__ == "__main__":
    app = VocabApp()
    app.mainloop()
