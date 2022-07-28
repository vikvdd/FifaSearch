# FIFA SEARCH 
Search app for the Fifa legal database

## Quick installation 

1. Download the latest version from [the releases page.](https://github.com/vikvdd/FifaSearch/releases/)

## Manual Installation

1. Download  and install Python from [the official website.](https://www.python.org/) (If necessary)
2. Download and install Git from [the official website.](https://git-scm.com/downloads) (If necessary)

### Mac
1. Open the terminal application
2. Enter the following command: `git clone https://github.com/vikvdd/FifaSearch.git;cd FifaSearch/src;pip3 install -r requirements.txt`
3. Installation complete, you may now run the program using command: `python3 app.py`

[========]


### Usage:
1. Enter search term/s.
2. Select a search mode from the dropdown menu:
    - Full search (default): Search through every entry, including the entire contents of the attached PDF
    - Only search metadata: Only search the entry metadata (title, date posted) 
    - Search metadata & cover page: Search metadata and the first page of attached PDF (Ideal for case numbers, authors, titles)
3. Select the start date. Only entries posted before the start date will be searched.
4. Select the end date. Only entries posted after the end date will be searched


**If you are searching for case numbers, try wrap the search terms in asterisks** (*)
> eg: \*FPGP-3430\*

[========]

### ISSUES & SUGGESTIONS
If you have any bugs, issues or feature requests, please open an issue on Github:
https://github.com/vikvdd/FifaSearch/issues

In case of bugs, try running the FifaSearchDebug version and copying the error message, it will help fix it far easier.
