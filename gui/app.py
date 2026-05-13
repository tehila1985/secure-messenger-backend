import tkinter as tk
from tkinter import messagebox, scrolledtext
import api

# ── constants ──────────────────────────────────────────────────────────────
BG       = "#1e1e2e"
BG2      = "#2a2a3e"
ACCENT   = "#7c6af7"
FG       = "#cdd6f4"
FG_DIM   = "#6c7086"
FONT     = ("Segoe UI", 11)
FONT_B   = ("Segoe UI", 11, "bold")
FONT_SM  = ("Segoe UI", 9)


# ── helpers ────────────────────────────────────────────────────────────────
def styled_entry(parent, show=None):
    e = tk.Entry(parent, bg=BG2, fg=FG, insertbackground=FG,
                 relief="flat", font=FONT, show=show)
    e.config(highlightthickness=1, highlightbackground=ACCENT)
    return e


def styled_button(parent, text, command):
    return tk.Button(parent, text=text, command=command,
                     bg=ACCENT, fg="white", activebackground="#6a58e0",
                     relief="flat", font=FONT_B, cursor="hand2", padx=12, pady=6)


# ── Auth screen ────────────────────────────────────────────────────────────
class AuthScreen(tk.Frame):
    def __init__(self, master, on_login):
        super().__init__(master, bg=BG)
        self.on_login = on_login
        self._build()

    def _build(self):
        tk.Label(self, text="🔐 Secure Messenger", bg=BG, fg=FG,
                 font=("Segoe UI", 16, "bold")).pack(pady=(40, 20))

        form = tk.Frame(self, bg=BG)
        form.pack()

        tk.Label(form, text="Username", bg=BG, fg=FG_DIM, font=FONT_SM).grid(
            row=0, column=0, sticky="w", pady=(0, 2))
        self.username = styled_entry(form)
        self.username.grid(row=1, column=0, ipadx=8, ipady=6, pady=(0, 10))

        tk.Label(form, text="Password", bg=BG, fg=FG_DIM, font=FONT_SM).grid(
            row=2, column=0, sticky="w", pady=(0, 2))
        self.password = styled_entry(form, show="•")
        self.password.grid(row=3, column=0, ipadx=8, ipady=6)

        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=20)
        styled_button(btns, "Login",    self._login).pack(side="left", padx=6)
        styled_button(btns, "Register", self._register).pack(side="left", padx=6)

        self.status = tk.Label(self, text="", bg=BG, fg="#f38ba8", font=FONT_SM)
        self.status.pack()

    def _login(self):
        err = api.login(self.username.get().strip(), self.password.get())
        if err:
            self.status.config(text=err)
        else:
            self.on_login()

    def _register(self):
        msg = api.register(self.username.get().strip(), self.password.get())
        self.status.config(text=msg, fg="#a6e3a1")


# ── Chat screen ────────────────────────────────────────────────────────────
class ChatScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG)
        self._build()
        api.start_listener(
            on_message=self._on_message,
            on_status=self._on_status,
        )

    def _build(self):
        # header
        header = tk.Frame(self, bg=BG2, pady=8)
        header.pack(fill="x")
        tk.Label(header, text=f"💬  Logged in as  {api._state['username']}",
                 bg=BG2, fg=FG, font=FONT_B).pack()

        # input row — must be packed BEFORE the log so it's not squeezed out
        bottom = tk.Frame(self, bg=BG, pady=8)
        bottom.pack(side="bottom", fill="x", padx=10)

        # chat log
        self.log = scrolledtext.ScrolledText(
            self, bg=BG2, fg=FG, font=FONT, relief="flat",
            state="disabled", wrap="word", padx=10, pady=10,
        )
        self.log.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self.log.tag_config("incoming", foreground="#89dceb")
        self.log.tag_config("outgoing", foreground="#a6e3a1")
        self.log.tag_config("status",   foreground=FG_DIM)

        tk.Label(bottom, text="To:", bg=BG, fg=FG_DIM, font=FONT).pack(side="left")
        self.recipient = styled_entry(bottom)
        self.recipient.pack(side="left", ipadx=6, ipady=4, padx=(4, 10))

        self.msg_var = tk.StringVar()
        msg_entry = tk.Entry(bottom, textvariable=self.msg_var,
                             bg=BG2, fg=FG, insertbackground=FG,
                             relief="flat", font=FONT,
                             highlightthickness=1, highlightbackground=ACCENT)
        msg_entry.pack(side="left", fill="x", expand=True, ipadx=6, ipady=4)
        msg_entry.bind("<Return>", lambda _: self._send())

        styled_button(bottom, "Send", self._send).pack(side="left", padx=(8, 0))

    def _append(self, text, tag="status"):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _on_message(self, sender, recipient, content):
        tag = "outgoing" if sender == api._state["username"] else "incoming"
        self.after(0, self._append, f"[{sender} → {recipient}]: {content}", tag)

    def _on_status(self, text):
        self.after(0, self._append, f"⚡ {text}", "status")

    def _send(self):
        recipient = self.recipient.get().strip()
        content   = self.msg_var.get().strip()
        if not recipient or not content:
            return
        err = api.send_message(recipient, content)
        if err:
            self.after(0, self._append, f"Error: {err}", "status")
        else:
            self.msg_var.set("")


# ── Main ───────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Secure Messenger")
        self.geometry("600x520")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._show_auth()

    def _show_auth(self):
        AuthScreen(self, on_login=self._show_chat).pack(fill="both", expand=True)

    def _show_chat(self):
        for w in self.winfo_children():
            w.destroy()
        ChatScreen(self).pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
