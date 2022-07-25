import queue
import threading
from enum import Enum
from urllib import request
import json
from PyPDF2 import PdfReader
from io import BytesIO
from search import Search, SearchThread, parse_date
from tkinter import *
from tkinter import ttk
from tkHyperlinkManager import HyperlinkManager
import webbrowser
from functools import partial
from tkcalendar import Calendar, DateEntry
from dateutil import parser
from datetime import timezone, datetime


REQUEST_SIZE = 50
DATE_ASCENDING = "dateAsc"
DATE_DESCENDING = "dateDesc"
DATA_KEY = "data"
TOTAL_KEY = "total"
TITLE_KEY = "title"
DATE_KEY = "date"
ORIGINAL_DATE_KEY = "originalDate"

TAGS = {
    "PSC Overdue Payables": "71Tb4ZwcYqRp2Kzg34zxOc",
    "Players' and Match Agents' Disputes": "5Zs7XCOIH3V0PIu73GNNsk",
    "Coach Disputes": "32c894g2DJcV5Fwk6fmX8P",
    "Club vs. Club Disputes": "4aZS15znbShw74IgyNrBth",
    "Disciplinary Committee": "5Zm4iscqBagohkrC4V1fNB",
    "Ethics Committee": "REfRLYazlDecPI4V5PsJF"
}


class SearchMode(Enum):
    FULL = "Full search",
    META_DATA_ONLY = "Only search metadata",
    META_AND_COVER = "Search metadata & cover page"





def update_result_view(index, search_term, entry):
    result_text.insert(1.0, '------------------------\n')
    result_text.insert(1.0,f"\nPage matched: {entry['page']}\n\n")
    hyperlink = HyperlinkManager(result_text)
    result_text.insert(1.0, "\nView PDF", hyperlink.add(partial(webbrowser.open, entry['download']['url'])))
    result_text.insert(1.0, f"\nOriginal Date: {entry[ORIGINAL_DATE_KEY]}")
    result_text.insert(1.0,f"\nDate: {entry['date']}")
    result_text.insert(1.0, f"\nTag: {entry['tag']}")
    result_text.insert(1.0, f"\nTitle: {entry['title']}")
    result_text.insert(1.0, f"\nFound match for term: {search_term}\n")
    result_text.insert(1.0, f"\n#{index}:\n")

def callback(url):
   webbrowser.open_new_tab(url)

def print_matched_entry(entry, search_term, found_in_pdf=False):
    print('------------------------')
    print(f"\nFound match for term: {search_term}\n")
    print(f"Title: {entry['title']}")
    print(f"Tag: {entry['tag']}")
    print(f"Date: {entry['date']}")
    print(f"Original Date: {entry[ORIGINAL_DATE_KEY]}")
    print(f"PDF: {entry['download']['url']}")
    print(f"Page matched: {entry['page']}\n")


def on_click_search():
    search_term = str(search_input.get())
    if search_term == "":
        return

    start_date = datetime.combine(parse_date(start_cal.get()), datetime.min.time()).replace(tzinfo=timezone.utc)
    end_date = datetime.combine(parse_date(end_cal.get()), datetime.min.time()).replace(tzinfo=timezone.utc)
    tags = ""
    for i in categories_lb.curselection():
        item = categories_lb.get(i)
        if not tags == "":
            tags += ","
        tags += TAGS[item]
    new_search = Search(search_term, start_date, end_date, tags)
    search_thread = SearchThread(update_result_view, new_search)
    searches.append(new_search)
    print(f'Searching for term: {search_term}\n')
    sort_by_oldest = bool(date_asc.get())
    search_thread.start()


start_search = Search("")
searches = []

root = Tk()
root.title("Fifa Legal Search")
#root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}")
mainframe = ttk.Frame(root, padding="3 3 12 12", height=root.winfo_height(), width=root.winfo_width())
mainframe.pack(fill=BOTH, expand=True)
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
mainframe.columnconfigure(1, weight=1)
mainframe.columnconfigure(3,pad=7)

result_text = Text(mainframe)
result_text.grid(column=1, row=1, columnspan=4, rowspan=15, sticky=N)

search_input = StringVar()
search_entry = ttk.Entry(mainframe, width=40, textvariable=search_input)
search_entry.grid(column=1, row=0, sticky=(W, E))
ttk.Button(mainframe, text="Search", command=on_click_search).grid(column=0, row=0, sticky=E)


categories_lb = Listbox(mainframe, selectmode="multiple")
categories_lb.grid(column=0, row=1, sticky=W)
for category in TAGS.keys():
    categories_lb.insert(0, category)


search_mode_combo = ttk.Combobox(mainframe)
search_mode_combo.grid(column=0, row=2, sticky=W+N)

date_asc = BooleanVar()
sort_checkbox = ttk.Checkbutton(mainframe, text='Sort by oldest', variable=date_asc)
sort_checkbox.grid(column=0, row=3, sticky=W+N)

start_date_lbl = ttk.Label(mainframe, text="Start date: ").grid(column=0, row=4, sticky=W)
start_cal = DateEntry(mainframe, width=15, background="magenta3", foreground="white", bd=2)
start_cal.grid(column=0, row=5, sticky=W)
start_cal._top_cal.overrideredirect(False)

end_date_lbl = ttk.Label(mainframe, text="End date: ").grid(column=0, row=6, sticky=W)
end_cal = DateEntry(mainframe, width= 15, background="magenta3", foreground="white", bd=2)
end_cal.grid(column=0, row=7, sticky=W)
end_cal._top_cal.overrideredirect(False)

for child in mainframe.winfo_children():
    child.grid_configure(padx=5, pady=5)


root.mainloop()


#if __name__ == "__main__":
   # main()
    #print(f"Searching for term: {sys.argv[1]}")
    #matches = search_entries_for_term(sys.argv[1])




