import threading
from urllib import request
import json
from PyPDF2 import PdfReader
from io import BytesIO
from dateutil import parser

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

def parse_date(date_str):
    try:
        date = parser.parse(date_str, fuzzy=True)
        return date
    except Exception as e:
        print(e)
        print("Failed to parse date.")
        return None

class Search:
    def __init__(self, term, latest=None, earliest=None, tags="", sort_order=DATE_DESCENDING):
        self.total = 0
        self.term = term
        self.sort_order = sort_order
        self.earliest_date = None
        self.latest_date = None
        self.target_earliest = earliest
        self.target_latest = latest
        self.tags = tags


class SearchThread(threading.Thread):
    def __init__(self, cb, search, stop_at_first_match=False):
        super().__init__()
        self.daemon = True
        self.cb = cb
        self.search = search
        self.stop_at_first_match = stop_at_first_match

    def run(self):

        self.init_search()
        self.search_entries_for_term()

    def init_search(self):
        entries = self.retrieve_entries(0, size=1)
        self.search.total = entries[TOTAL_KEY]
        latest_data = entries[DATA_KEY]
        latest_date = parse_date(latest_data[0][ORIGINAL_DATE_KEY])
        self.search.latest_date = latest_date
        last_entries = self.retrieve_entries(self.search.total - 1, size=1)
        earliest_data = last_entries[DATA_KEY]
        date_str = earliest_data[-1][ORIGINAL_DATE_KEY]
        earliest_date = parse_date(date_str)
        self.search.earliest_date = earliest_date

    def retrieve_entries(self, offset, size=REQUEST_SIZE):
        api_url = f"https://www.fifa.com/api/get-card-content?requestLocale=en&requestContentTypes=Document&" \
                  f"requestSize={size}&requestFrom={offset}&requestSort={self.search.sort_order}&" \
                  f"requestTags=71Tb4ZwcYqRp2Kzg34zxOc,4aZS15znbShw74IgyNrBth&" \
                  f"requestExcludeIds=&requestTagHandlingQuery=OR"
        resp = request.urlopen(api_url)
        resp_text = resp.read()
        text = resp_text.decode('utf-8')
        data = json.loads(text)
        tag = 'topicContent'
        entries = []
        if tag in data:
            entries = data[tag]

        return entries

    def search_entries_for_term(self):
        term = self.search.term.lower()
        matching_entries = []
        target_date = self.search.target_latest
        if self.search.sort_order == DATE_ASCENDING:
            target_date = self.search.target_earliest

        offset = self.locate_start_offset(target_date)
        if offset == -1:
            print('No entries found in date range.')
            return matching_entries
        while True:
            entries_resp = self.retrieve_entries(offset)
            if DATA_KEY in entries_resp:
                entries = entries_resp[DATA_KEY]
            if len(entries) == 0:
                break

            for entry in entries:
                entry_date = parse_date(entry[ORIGINAL_DATE_KEY])
                if entry_date > self.search.target_latest:
                    if self.search.sort_order == DATE_ASCENDING:
                        break
                    else:
                        continue
                elif entry_date < self.search.target_earliest:
                    if self.search.sort_order == DATE_DESCENDING:
                        break
                    else:
                        continue

                try:
                    matched = False
                    if self.search.term in entry[TITLE_KEY] or self.search.term in entry['tag']:
                        matching_entries.append()
                        matched = True
                        #print_matched_entry(entry, self.search.term)
                        if self.stop_at_first_match:
                            return matching_entries
                    pdf_url = entry['download']['url']
                    pdf_file = request.urlopen(pdf_url)
                    bytes_stream = BytesIO(pdf_file.read())
                    reader = PdfReader(bytes_stream)
                    index = 0
                    for page in reader.pages:
                        text = page.extractText().lower()
                        if term.lower() in text:
                            entry['page'] = index
                            matching_entries.append(entry)
                            matched = True

                            #print_matched_entry(entry, self.search.term, True)
                            if self.stop_at_first_match:
                                return matching_entries
                            break
                        index += 1
                    if matched:
                        self.cb(len(matching_entries), self.search.term, entry)
                except Exception as e:
                    print("Could not load pdf.")
                    print(e)

            offset += REQUEST_SIZE

        return matching_entries

    def locate_start_offset(self, date):
        low = 0
        high = self.search.total
        first_entry = self.retrieve_entries(0, size=1)
        first_date = parse_date(first_entry[DATA_KEY][0][ORIGINAL_DATE_KEY])
        last_entry = self.retrieve_entries(self.search.total - 1, size=1)
        last_date = parse_date(last_entry[DATA_KEY][-1][ORIGINAL_DATE_KEY])
        if date < last_date or date > first_date:
            return -1
        while low < high:
            mid_offset = (((high - low) // 2) - REQUEST_SIZE) + low
            mid_entries = self.retrieve_entries(mid_offset)
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

