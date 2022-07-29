import threading
from tkinter.scrolledtext import ScrolledText
from threading import Event
from tkinter.ttk import Progressbar

from const import ORIGINAL_DATE_KEY, TITLE_KEY, DATE_KEY, TAG_KEY, DOWNLOAD_KEY, URL_KEY, PAGE_KEY, TAGS
from search import Search, SearchThread, parse_date, SearchMode
from tkinter import *
from tkinter import ttk
from tkHyperlinkManager import HyperlinkManager
import webbrowser
from functools import partial
from tkcalendar import DateEntry
from datetime import timezone, datetime

class App:

    def run(self):
        try:
            tags = []
            for tag in TAGS.keys():
                tags.append(tag)
            start_search = Search("", tags=tags)
            first, last = start_search.get_date_range()
            self.start_cal.set_date(first)
            self.end_cal.set_date(last)
        except Exception as e:
            print(e)
        self.root.mainloop()

    def on_search_update(self, percent, msg=""):
        self.prog_lbl.config(text=f"Searching: {msg}")
        self.progress['value'] = percent
        self.root.update_idletasks()

    def on_complete_search(self, success, matches_found=-1, total_searched=-1):
        if success:
            self.result_text.insert(1.0, f"\nSearch complete.\n\n\n")
            if matches_found > -1 and total_searched > -1:
                self.result_text.insert(1.0, f"\nFound {matches_found} match(es) out of {total_searched} searched.\n")
        else:
            self.result_text.insert(1.0, "\nSearch failed. No entries matched given parameters.\n\n")
        self.progress['value'] = 0
        self.prog_lbl.config(text="")
        self.search_button.config(text="Search")
        self.search_active = False

    def on_match_found(self, index, search_term, entry):
        self.result_text.insert(1.0, '\n------------------------\n')
        if PAGE_KEY in entry:
            page = int(entry[PAGE_KEY]) + 1
            self.result_text.insert(1.0, f"\nFound on page: {page}\n\n")
        hyperlink = HyperlinkManager(self.result_text)
        link = entry[DOWNLOAD_KEY][URL_KEY]
        self.result_text.insert(1.0, f"\n{link}", hyperlink.add(partial(webbrowser.open, link)))
        self.result_text.insert(1.0, f"\nOriginal Date: {entry[ORIGINAL_DATE_KEY]}")
        self.result_text.insert(1.0, f"\nDate: {entry[DATE_KEY]}")
        self.result_text.insert(1.0, f"\nTag: {entry[TAG_KEY]}")
        self.result_text.insert(1.0, f"\nTitle: {entry[TITLE_KEY]}")
        self.result_text.insert(1.0, f"\nFound match for term: {search_term}\n")
        self.result_text.insert(1.0, f"\n#{index}:\n")

    def on_click_search(self):
        if self.search_active:
            self.stop_event.set()
            self.search_active = False
            self.search_button.config(text="Search")
            self.progress['value'] = 0
            self.prog_lbl.config(text="")
            return
        search_term = str(self.search_input.get())

        start_date = datetime.combine(parse_date(self.start_cal.get()), datetime.min.time()).replace(tzinfo=timezone.utc)
        end_date = datetime.combine(parse_date(self.end_cal.get()), datetime.min.time()).replace(tzinfo=timezone.utc)
        tags = []
        for i in self.categories_lb.curselection():
            tags.append(self.categories_lb.get(i))
        if len(tags) <= 0:
            for tag in TAGS.keys():
                tags.append(tag)
        sort_by_oldest = bool(self.date_asc.get())
        mode = SearchMode.FULL
        selected_mode = self.search_mode_combo.get()
        for key in SearchMode:
            if key.value == selected_mode:
                mode = key
        new_search = Search(search_term, start_date, end_date, tags, mode=mode)
        self.stop_event = threading.Event()
        self.thread = SearchThread(new_search, self.on_match_found, update_cb=self.on_search_update, end_cb=self.on_complete_search, stop_event=self.stop_event)
        self.searches.append(new_search)
        self.result_text.insert(1.0, "\n\n\n\n\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n\n\n\n\n")
        self.result_text.insert(1.0, f"\nSearch mode: {mode.value}")
        self.result_text.insert(1.0, f"\nTags: {', '.join(tags)}")
        self.result_text.insert(1.0, f"\nSearching for term: {search_term}")
        self.thread.start()
        self.search_button.config(text="Stop")
        self.search_active = True
        print(f'Searching for term: {search_term}\n')

    def __init__(self):
        self.searches = []
        self.thread = None
        self.search_active = False

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

        self.result_text = ScrolledText(self.mainframe, foreground='black')
        self.result_text.grid(column=1, row=2, columnspan=20, rowspan=20, sticky=NSEW)

        self.search_input = StringVar()
        self.search_entry = ttk.Entry(self.mainframe, width=60, textvariable=self.search_input)
        self.search_entry.grid(column=1, row=0, sticky=NW)
        self.search_button = ttk.Button(self.mainframe, text="Search", command=self.on_click_search)
        self.search_button.grid(column=0, row=0, sticky=NE)

        self.categories_lb = Listbox(self.mainframe, selectmode="multiple", exportselection=False)
        self.categories_lb.grid(column=0, row=9, sticky=N + W)
        for category in TAGS.keys():
            self.categories_lb.insert(0, category)

        self.search_mode_combo = ttk.Combobox(self.mainframe)
        self.search_mode_combo.grid(column=0, row=3, sticky=N+W)
        self.search_mode_combo['values'] = tuple([str(key.value) for key in SearchMode])
        self.search_mode_combo.set(self.search_mode_combo['values'][0])

        self.date_asc = BooleanVar()
        #self.sort_checkbox = ttk.Checkbutton(self.mainframe, text='Sort by oldest', variable=self.date_asc)
        #self.sort_checkbox.grid(column=0, row=4, sticky=NW)

        self.start_date_lbl = ttk.Label(self.mainframe, text="Start date: ").grid(column=0, row=5, sticky=NW)
        self.start_cal = DateEntry(self.mainframe, width=15, background="grey", foreground="white", bd=2, date_pattern="y/mm/dd")
        self.start_cal.grid(column=0, row=6, sticky=NW)
        self.start_cal._top_cal.overrideredirect(False)

        self.end_date_lbl = ttk.Label(self.mainframe, text="End date: ").grid(column=0, row=7, sticky=NW)
        self.end_cal = DateEntry(self.mainframe, width= 15, background="white", foreground="black", bd=2, date_pattern="y/mm/dd")
        self.end_cal.grid(column=0, row=8, sticky=NW)
        self.end_cal._top_cal.overrideredirect(False)

        self.prog_lbl = ttk.Label(self.mainframe, text="")
        self.prog_lbl.grid(column=1, row=1, sticky=S+E+W)
        self.progress = Progressbar(self.mainframe, orient=HORIZONTAL,
                               length=100, mode='determinate')
        self.progress.grid(column=0, row=1, sticky=S+E+W)

        for child in self.mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)



    def callback(url):
       webbrowser.open_new_tab(url)


if __name__ == "__main__":
    app = App()
    app.run()




