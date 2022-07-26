from enum import Enum
import threading
from urllib import request
import json
from PyPDF2 import PdfReader
from io import BytesIO
from dateutil import parser

from const import DATE_DESCENDING, DATA_KEY, ORIGINAL_DATE_KEY, TOTAL_KEY, DATE_ASCENDING, TITLE_KEY, DATE_KEY, \
    REQUEST_SIZE


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

    TAGS = {
        "PSC Overdue Payables": "71Tb4ZwcYqRp2Kzg34zxOc",
        "Players' and Match Agents' Disputes": "5Zs7XCOIH3V0PIu73GNNsk",
        "Coach Disputes": "32c894g2DJcV5Fwk6fmX8P",
        "Club vs. Club Disputes": "4aZS15znbShw74IgyNrBth",
        "Disciplinary Committee": "5Zm4iscqBagohkrC4V1fNB",
        "Ethics Committee": "REfRLYazlDecPI4V5PsJF"
    }

    def __init__(self, term, latest=None, earliest=None, tags="", sort_order=DATE_DESCENDING, mode=SearchMode.FULL):
        self.total = 0
        self.term = term.lower()
        self.sort_order = sort_order
        self.earliest_date = None
        self.latest_date = None
        self.target_earliest = earliest
        self.target_latest = latest
        self.tags = tags
        self.mode = mode

    def retrieve_entries(self, offset, size=REQUEST_SIZE):
        api_url = f"https://www.fifa.com/api/get-card-content?requestLocale=en&requestContentTypes=Document&" \
                  f"requestSize={size}&requestFrom={offset}&requestSort={self.sort_order}&" \
                  f"requestTags={self.tags}&" \
                  f"requestExcludeIds=&requestTagHandlingQuery=OR"
        resp = request.urlopen(api_url)
        resp_text = resp.read()
        text = resp_text.decode('utf-8')
        data = json.loads(text)
        content_key = 'topicContent'
        entries = []
        if content_key in data:
            entries = data[content_key]

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


class SearchThread(threading.Thread):
    def __init__(self, search, matched_cb, update_cb=update_fn, end_cb=end_fn, stop_event=None):
        super().__init__()
        self.daemon = True
        self.matched_cb = matched_cb
        self.update_cb = update_cb
        self.end_cb = end_cb
        self.search = search
        self.stop_event = stop_event

    def run(self):
        self.init_search()
        if self.is_valid_search():
            self.search_entries_for_term()
        else:
            print("Invalid search.")
            self.end_cb(False)
        self.end_cb(True)


    def init_search(self):
        entries = self.search.retrieve_entries(0, size=1)
        self.search.total = entries[TOTAL_KEY]
        latest_data = entries[DATA_KEY]
        latest_date = parse_date(latest_data[0][ORIGINAL_DATE_KEY])
        self.search.latest_date = latest_date
        last_entries = self.search.retrieve_entries(self.search.total - 1, size=1)
        earliest_data = last_entries[DATA_KEY]
        date_str = earliest_data[-1][ORIGINAL_DATE_KEY]
        earliest_date = parse_date(date_str)
        self.search.earliest_date = earliest_date


    def search_entries_for_term(self):
        term = self.search.term.lower()
        matching_entries = []
        target_date = self.search.target_latest
        if self.search.sort_order == DATE_ASCENDING:
            target_date = self.search.target_earliest

        offset = self.locate_start_offset(target_date)
        start_offset = offset
        if offset == -1:
            print('No entries found in date range.')
            return matching_entries
        while True:
            if self.stop_event and self.stop_event.is_set():
                return matching_entries
            entries_resp = self.search.retrieve_entries(offset)
            if DATA_KEY in entries_resp:
                entries = entries_resp[DATA_KEY]
            if len(entries) == 0:
                break
            entry_index = 0
            for entry in entries:
                if self.stop_event and self.stop_event.is_set():
                    return matching_entries
                progress = int(((offset-start_offset + entry_index)/(self.search.total-start_offset)) * 100)
                self.update_cb(progress, f"{entry[TITLE_KEY][:50]} - {entry[DATE_KEY]}")

                matched = False
                if self.search.term in entry[TITLE_KEY].lower() or self.search.term in entry['tag'].lower():
                    matched = True
                if self.search.mode == SearchMode.META_DATA_ONLY:
                    continue
                try:
                    pdf_url = entry['download']['url']
                    cover_only = False
                    if self.search.mode == SearchMode.META_AND_COVER:
                        cover_only = True
                    if self.scan_pdf_for_match(pdf_url, entry, cover_only=cover_only):
                        matched = True

                except Exception as e:
                    print("Could not load pdf.")
                    print(e)
                if self.stop_event.is_set():
                    return matching_entries
                elif matched:
                    matching_entries.append(entry)
                    self.matched_cb(len(matching_entries), self.search.term, entry)
                entry_index += 1
            offset += REQUEST_SIZE

        return matching_entries

    def scan_pdf_for_match(self, pdf_url, entry, cover_only=False):
        pdf_file = request.urlopen(pdf_url)
        bytes_stream = BytesIO(pdf_file.read())
        reader = PdfReader(bytes_stream)
        index = 0
        for page in reader.pages:
            if self.stop_event and self.stop_event.is_set():
                return False
            text = page.extractText().lower()
            if self.search.term in text:
                entry['page'] = index
                return True

                break
            if cover_only:
                break
            index += 1
        return False

    #True if date range contains any entries
    def is_valid_search(self):
        first_entry = self.search.retrieve_entries(0, size=1)
        first_date = parse_date(first_entry[DATA_KEY][0][ORIGINAL_DATE_KEY])
        last_entry = self.search.retrieve_entries(self.search.total - 1, size=1)
        last_date = parse_date(last_entry[DATA_KEY][-1][ORIGINAL_DATE_KEY])

        if self.search.target_earliest > first_date or self.search.target_latest < last_date:
            return False
        return True

    #Binary search for request offset containing given date
    def locate_start_offset(self, date):
        low = 0
        high = self.search.total
        first_entry = self.search.retrieve_entries(0, size=1)
        first_date = parse_date(first_entry[DATA_KEY][0][ORIGINAL_DATE_KEY])
        last_entry = self.search.retrieve_entries(self.search.total - 1, size=1)
        last_date = parse_date(last_entry[DATA_KEY][-1][ORIGINAL_DATE_KEY])
        if self.search.target_earliest < last_date:
            self.search.target_earliest = last_date
        if self.search.target_latest > first_date:
            self.search.target_latest = first_date
        if self.search.target_earliest > first_date or self.search.target_latest < last_date:
            return -1
        if self.search.target_latest >= first_date:
            return 0
        while low < high:
            mid_offset = (((high - low) // 2) - REQUEST_SIZE) + low
            mid_entries = self.search.retrieve_entries(mid_offset)
            if DATA_KEY not in mid_entries or len(mid_entries[DATA_KEY]) == 0:
                break
            data = mid_entries[DATA_KEY]
            first_date = parse_date(data[0][ORIGINAL_DATE_KEY])
            last_date = parse_date(data[-1][ORIGINAL_DATE_KEY])

            if date > first_date:
                high = mid_offset
            elif date < last_date:
                low = mid_offset
            else:
                return mid_offset


