from typing import List
import tkinter as tk

def clipboard_gui(data_list: List[str]):
    """
    Launches a GUI displaying data_list.
    Copies all items to clipboard and exits upon button click.
    """
    # Initialize the main window
    root = tk.Tk()
    root.title("Text Exporter")
    root.geometry("350x300")

    # Layout: Top Frame for List + Scrollbar
    frame = tk.Frame(root)
    frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Use 'exportselection=False' so clicking the button doesn't
    # deselect text in some environments
    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Populate the list from the input argument
    for item in data_list:
        listbox.insert(tk.END, str(item))

    scrollbar.config(command=listbox.yview)

    # Internal function for the button logic
    def on_click():
        # Join all list contents into a single string
        full_text = "\n".join(listbox.get(0, tk.END))

        root.clipboard_clear()
        root.clipboard_append(full_text)

        # Ensure the clipboard 'takes' before the window vanishes
        root.update()
        root.destroy()

    # Action Button
    copy_btn = tk.Button(
        root,
        text="Copy All & Close App",
        command=on_click,
        bg="#2c3e50",
        fg="white",
        font=("Arial", 10, "bold")
    )
    copy_btn.pack(pady=10, fill=tk.X, padx=10)

    root.mainloop()
