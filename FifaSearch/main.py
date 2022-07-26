import threading
from tkinter.scrolledtext import ScrolledText
from threading import Event
from tkinter.ttk import Progressbar

from search import Search, SearchThread, parse_date
from tkinter import *
from tkinter import ttk
from tkHyperlinkManager import HyperlinkManager
import webbrowser
from functools import partial
from tkcalendar import DateEntry
from datetime import timezone, datetime


REQUEST_SIZE = 50
DATE_ASCENDING = "dateAsc"
DATE_DESCENDING = "dateDesc"
DATA_KEY = "data"
TOTAL_KEY = "total"
TITLE_KEY = "title"
DATE_KEY = "date"
ORIGINAL_DATE_KEY = "originalDate"

class App:

    def __init__(self):
        self.searches = []
        self.thread = None
        self.search_active = False

    def on_thread_update(self, percent, msg=""):
        self.prog_lbl.config(text=f"Searching: {msg}")
        self.progress['value'] = percent
        self.root.update_idletasks()

    def on_complete_search(self, success, msg=""):
        if success:
            self.result_text.insert(1.0, "\nSearch complete.\n\n\n\n")
        else:
            self.result_text.insert(1.0, "\n\nSearch failed. No entries matched given parameters.")
        self.progress['value'] = 0
        self.prog_lbl.config(text="")
        self.search_button.config(text="Search")
        self.search_active = False

    def update_result_view(self, index, search_term, entry):
        self.result_text.insert(1.0, '------------------------\n')
        self.result_text.insert(1.0, f"\nPage matched: {entry['page']}\n\n")
        hyperlink = HyperlinkManager(self.result_text)
        self.result_text.insert(1.0, "\nView PDF", hyperlink.add(partial(webbrowser.open, entry['download']['url'])))
        self.result_text.insert(1.0, f"\nOriginal Date: {entry[ORIGINAL_DATE_KEY]}")
        self.result_text.insert(1.0, f"\nDate: {entry['date']}")
        self.result_text.insert(1.0, f"\nTag: {entry['tag']}")
        self.result_text.insert(1.0, f"\nTitle: {entry['title']}")
        self.result_text.insert(1.0, f"\nFound match for term: {search_term}\n")
        self.result_text.insert(1.0, f"\n#{index}:\n")

    def callback(url):
       webbrowser.open_new_tab(url)


    def on_click_search(self):
        if self.search_active:
            self.stop_event.set()
            self.search_active = False
            self.search_button.config(text="Search")
            return
        search_term = str(self.search_input.get())

        start_date = datetime.combine(parse_date(self.start_cal.get()), datetime.min.time()).replace(tzinfo=timezone.utc)
        end_date = datetime.combine(parse_date(self.end_cal.get()), datetime.min.time()).replace(tzinfo=timezone.utc)
        tags = ""
        for i in self.categories_lb.curselection():
            item = self.categories_lb.get(i)
            if not tags == "":
                tags += ","
            tags += Search.TAGS[item]
        if tags == "":
            for tag in Search.TAGS.values():
                if not tags== "":
                    tags += ","
                tags += tag
        sort_by_oldest = bool(self.date_asc.get())
        new_search = Search(search_term, start_date, end_date, tags)
        self.stop_event = threading.Event()
        self.thread = SearchThread(new_search, self.update_result_view, update_cb=self.on_thread_update, end_cb=self.on_complete_search, stop_event=self.stop_event)
        self.searches.append(new_search)
        self.result_text.insert(1.0, "\n\n\n\n\n------------------------------------------------------------------\n\n\n\n\n")
        self.result_text.insert(1.0, f"\nSearching for term: {search_term}")
        print(f'Searching for term: {search_term}\n')


        self.thread.start()
        self.search_button.config(text="Stop")
        self.search_active = True


    def run(self):
        self.root = Tk()
        self.root.title("Fifa Legal Search")
        #self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.mainframe = ttk.Frame(self.root, padding="3 3 12 12", height=self.root.winfo_height(), width=self.root.winfo_width())
        self.mainframe.pack(fill=BOTH, expand=True)
        self.mainframe.grid(column=0, row=0, sticky=(N, S, E, W))
        self.mainframe.grid_rowconfigure(15,weight=1)
        self.mainframe.columnconfigure(1, weight=1)
        self.mainframe.columnconfigure(3,pad=7)

        self.result_text = ScrolledText(self.mainframe)
        self.result_text.grid(column=1, row=2, columnspan=20, rowspan=20, sticky=NSEW)

        self.search_input = StringVar()
        self.search_entry = ttk.Entry(self.mainframe, width=60, textvariable=self.search_input)
        self.search_entry.grid(column=1, row=0, sticky=NW)
        self.search_button = ttk.Button(self.mainframe, text="Search", command=self.on_click_search)
        self.search_button.grid(column=0, row=0, sticky=NE)


        self.categories_lb = Listbox(self.mainframe, selectmode="multiple")
        self.categories_lb.grid(column=0, row=2, sticky=N+W)
        for category in Search.TAGS.keys():
            self.categories_lb.insert(0, category)


        self.search_mode_combo = ttk.Combobox(self.mainframe)
        self.search_mode_combo.grid(column=0, row=3, sticky=N+W)

        self.date_asc = BooleanVar()
        self.sort_checkbox = ttk.Checkbutton(self.mainframe, text='Sort by oldest', variable=self.date_asc)
        self.sort_checkbox.grid(column=0, row=4, sticky=NW)

        self.start_date_lbl = ttk.Label(self.mainframe, text="Start date: ").grid(column=0, row=5, sticky=NW)
        self.start_cal = DateEntry(self.mainframe, width=15, background="magenta3", foreground="white", bd=2)
        self.start_cal.grid(column=0, row=6, sticky=NW)
        self.start_cal._top_cal.overrideredirect(False)

        self.end_date_lbl = ttk.Label(self.mainframe, text="End date: ").grid(column=0, row=7, sticky=NW)
        self.end_cal = DateEntry(self.mainframe, width= 15, background="magenta3", foreground="white", bd=2)
        self.end_cal.grid(column=0, row=8, sticky=NW)
        self.end_cal._top_cal.overrideredirect(False)

        self.prog_lbl = ttk.Label(self.mainframe, text="")
        self.prog_lbl.grid(column=1, row=1, sticky=S+E+W)
        self.progress = Progressbar(self.mainframe, orient=HORIZONTAL,
                               length=100, mode='determinate')
        self.progress.grid(column=0, row=9, sticky=S+E+W)

        for child in self.mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)

        tags = ""
        for tag in Search.TAGS.values():
            if not tag == "":
                tags += ","
            tags += tag
        start_search = Search("", tags=tags)
        first, last = start_search.get_date_range()
        self.start_cal.set_date(first)
        self.end_cal.set_date(last)

        self.root.mainloop()


if __name__ == "__main__":
   app = App()
   app.run()




