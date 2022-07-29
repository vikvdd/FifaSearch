from enum import Enum
import ssl
import threading
from urllib import request
import json
from PyPDF2 import PdfReader
from io import BytesIO
from dateutil import parser

from const import DATE_DESCENDING, DATA_KEY, ORIGINAL_DATE_KEY, TOTAL_KEY, DATE_ASCENDING, TITLE_KEY, DATE_KEY, \
    REQUEST_SIZE, TAG_KEY, URL_KEY, DOWNLOAD_KEY, PAGE_KEY, CONTENT_KEY, TAGS


@staticmethod
def update_fn(*args, **kwargs):
    print("Thread work active")

@staticmethod
def end_fn(*args, **kwargs):
    print("Thread completed task.")


def parse_date(date_str):
    try:
        date = parser.parse(date_str, fuzzy=True)
        return date
    except Exception as e:
        print(e)
        print("Failed to parse date.")
        return None

class SearchMode(Enum):
    FULL = "Full search"
    META_DATA_ONLY = "Only search metadata"
    META_AND_COVER = "Search metadata & cover page"

class Search:

    def __init__(self, term, newest=None, oldest=None, tags="", sort_order=DATE_DESCENDING, mode=SearchMode.FULL):
        self.total = 0
        self.deep_search = False
        if len(term) > 2 and term[0] == "*" and term[-1] == "*":
            self.deep_search = True
            term = term[1:-1]
            term.replace(" ", "")
        self.term = term.strip().lower()
        self.sort_order = sort_order
        self.date_desc = True
        if sort_order == DATE_ASCENDING:
            self.date_desc = False
        self.oldest_date = None
        self.newest_date = None
        self.target_oldest = oldest
        self.target_newest = newest
        self.tags = tags
        self.tag_str = self.get_tag_str(self.tags)
        self.mode = mode
        self.matching_entries = []
        self.total_searched = 0


    def retrieve_entries(self, offset, size=REQUEST_SIZE):
        api_url = f"https://www.fifa.com/api/get-card-content?requestLocale=en&requestContentTypes=Document&" \
                  f"requestSize={size}&requestFrom={offset}&requestSort={self.sort_order}&" \
                  f"requestTags={self.tag_str}&" \
                  f"requestExcludeIds=&requestTagHandlingQuery=OR"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        resp = request.urlopen(api_url, context=ctx)
        resp_text = resp.read()
        text = resp_text.decode('utf-8')
        data = json.loads(text)

        entries = []
        if CONTENT_KEY in data:
            entries = data[CONTENT_KEY]

        return entries

    def get_date_range(self):
        first = self.retrieve_entries(0, 1)
        first_data = first[DATA_KEY]
        first_date = parse_date(first_data[0][ORIGINAL_DATE_KEY])
        total = first[TOTAL_KEY]
        last = self.retrieve_entries(total-1, 1)
        last_data = last[DATA_KEY]
        last_date = parse_date(last_data[-1][ORIGINAL_DATE_KEY])
        return first_date, last_date


    def get_tag_str(self, tags):
        tag_str = ""
        for tag in tags:
            if not tag_str == "":
                tag_str += ","
            tag_str += TAGS[tag]
        return tag_str


class SearchThread(threading.Thread):
    def __init__(self, search, matched_cb, update_cb=update_fn, end_cb=end_fn, stop_event=None):
        super().__init__()
        self.daemon = True
        self.matched_cb = matched_cb
        self.update_cb = update_cb
        self.end_cb = end_cb
        self.search = search
        self.stop_event = stop_event
        self.offset = -1
        self.start_offset = -1
        self.end_offset = -1
        self.search_complete = False

    def run(self):
        self.init_search()
        if self.is_valid_search():
            self.search_entries_for_term()
        else:
            print("Invalid search.")
            self.end_cb(False)
        self.end_cb(True, len(self.search.matching_entries), self.search.total_searched)

    def init_search(self):
        entries = self.search.retrieve_entries(0, size=1)
        self.search.total = entries[TOTAL_KEY]
        newest_data = entries[DATA_KEY]
        newest_date = parse_date(newest_data[0][ORIGINAL_DATE_KEY])
        self.search.newest_date = newest_date
        oldest_entries = self.search.retrieve_entries(self.search.total - 1, size=1)
        oldest_data = oldest_entries[DATA_KEY]
        date_str = oldest_data[-1][ORIGINAL_DATE_KEY]
        oldest_date = parse_date(date_str)
        self.search.oldest_date = oldest_date
        if self.search.target_oldest < oldest_date:
            self.search.target_oldest = oldest_date
        if self.search.target_newest > newest_date:
            self.search.target_newest = newest_date

    def search_entries_for_term(self):
        new_offset = self.locate_start_offset(self.search.target_newest, self.search.date_desc)
        old_offset = self.locate_start_offset(self.search.target_oldest, not self.search.date_desc)
        self.offset = new_offset
        self.end_offset = old_offset
        if not self.search.date_desc:
            self.offset = old_offset
            self.end_offset = new_offset
        self.start_offset = self.offset
        if self.offset == -1:
            print('No entries found in date range.')
            return
        while not self.stop_event.is_set() and not self.search_complete:
            if self.stop_event and self.stop_event.is_set():
                return
            entries_resp = self.search.retrieve_entries(self.offset)
            if DATA_KEY in entries_resp:
                entries = entries_resp[DATA_KEY]
            if len(entries) == 0:
                break
            self.scan_entries_for_match(entries)
            self.offset += REQUEST_SIZE
        return

    def scan_entries_for_match(self, entries):
        index = 0
        for entry in entries:
            if self.stop_event.is_set() or self.search_complete:
                return
            try:
                progress = self.calculate_progress(self.offset, index, self.start_offset,
                                                   self.end_offset)
                self.update_cb(progress, f"{entry[DATE_KEY]} - {entry[TITLE_KEY][:50]}")
                self.scan_entry_for_match(entry)
                index += 1
                self.search.total_searched += 1
            except Exception as e:
                print(e)
                print("An error occurred while searching entry. Skipped.")

    def scan_entry_for_match(self, entry):
        entry_date = parse_date(entry[ORIGINAL_DATE_KEY])
        if entry_date > self.search.target_newest:
            return
        elif entry_date < self.search.target_oldest:
            self.search_complete = True
            return

        matched = False
        if self.search.term in entry[TITLE_KEY].lower() or self.search.term in entry[TAG_KEY].lower() \
                or self.search.term in entry[DOWNLOAD_KEY][URL_KEY].lower():
            matched = True
        if not self.search.mode == SearchMode.META_DATA_ONLY:
            try:
                pdf_url = entry[DOWNLOAD_KEY][URL_KEY]
                cover_only = False
                if self.search.mode == SearchMode.META_AND_COVER:
                    cover_only = True
                if self.scan_pdf_for_match(pdf_url, entry, cover_only=cover_only):
                    matched = True

            except Exception as e:
                print("Could not load pdf.")
                print(e)
        if self.stop_event.is_set():
            return
        elif matched:
            self.search.matching_entries.append(entry)
            self.matched_cb(len(self.search.matching_entries), self.search.term, entry)


    def scan_pdf_for_match(self, pdf_url, entry, cover_only=False):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        pdf_file = request.urlopen(pdf_url, context=ctx)
        bytes_stream = BytesIO(pdf_file.read())
        reader = PdfReader(bytes_stream)
        index = 0
        for page in reader.pages:
            if self.stop_event and self.stop_event.is_set():
                return False
            text = page.extractText().lower()
            if self.search.deep_search:
                deep = text.replace(" ", "")
                if self.search.term in deep:
                    entry[PAGE_KEY] = index
                    return True
            if self.search.term in text:
                entry[PAGE_KEY] = index
                return True
            if cover_only:
                break
            index += 1
        return False

    #True if date range contains any entries
    def is_valid_search(self):
        newest_entry = self.search.retrieve_entries(0, size=1)
        newest_date = parse_date(newest_entry[DATA_KEY][0][ORIGINAL_DATE_KEY])
        oldest_entry = self.search.retrieve_entries(self.search.total - 1, size=1)
        oldest_date = parse_date(oldest_entry[DATA_KEY][-1][ORIGINAL_DATE_KEY])

        if self.search.target_oldest > newest_date or self.search.target_newest < oldest_date:
            return False
        return True

    #Binary search for closest request offset containing given date
    def locate_start_offset(self, target, desc=True):
        low = 0
        high = self.search.total
        newest_entry = self.search.retrieve_entries(0, size=1)
        newest_date = parse_date(newest_entry[DATA_KEY][0][ORIGINAL_DATE_KEY])
        oldest_entry = self.search.retrieve_entries(self.search.total - 1, size=1)
        oldest_date = parse_date(oldest_entry[DATA_KEY][-1][ORIGINAL_DATE_KEY])

        if (desc and target < oldest_date) or (not desc and target > newest_date):
            return -1
        elif desc and target >= newest_date:
            return 0
        elif not desc and target <= oldest_date:
            return self.search.total
        while low < high:
            mid_offset = ((high - low) // 2) + low
            mid_entries = self.search.retrieve_entries(mid_offset)
            if DATA_KEY not in mid_entries or len(mid_entries[DATA_KEY]) == 0:
                return -1
            data = mid_entries[DATA_KEY]
            newest_date = parse_date(data[0][ORIGINAL_DATE_KEY])
            oldest_date = parse_date(data[-1][ORIGINAL_DATE_KEY])
            if target > newest_date:
                high = mid_offset
            elif target < oldest_date:
                low = mid_offset
            else:
                return mid_offset
        return -1

    def calculate_progress(self, offset, index, start_offset, end_offset, date_desc=True):
        progress = (((offset - start_offset) + index) / (end_offset - start_offset)) * 100
        progress = int(progress)
        if not date_desc:
            progress = 1 - progress
        return progress


