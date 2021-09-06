'''
Requires:
    Python 3x
    The module 'bibtexparser'
How it works:
    Read a TeX file.
    Read master Bib file.
    Write a new Bib file with only the entries cited in the original TeX file.
'''

import os
import re
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

tex = input("Enter name or path to TeX file: ")
while (not os.path.exists(tex)) :
    print('I did not find the file: \"%s\" ' % str(tex))
    tex = input('Try again or press \"Q+Enter\" to exit: ')
    if tex == 'q':
        raise SystemExit
with open(tex, encoding='utf8') as openedtex : 
    read_texFile = openedtex.read()
words = read_texFile.split()

citations = []
# Loop word by word and from those which have the string 'cite',
# copy the stuff that comes between curly brackets, ignore the rest.
[citations.append(re.findall(r'(?<=\{).+?(?=\})',word)) for word in words if re.findall(r'cite',word)] 

# Join all words in a single list.
citations = [''.join(citation) for citation in citations]

# Split strings containing multiple citations. It will create a list of lists.
split_citations = []
[split_citations.append(re.split(r'\,', citation)) for citation in citations]

# Flatten the lists of lists into a single list.
citations = [item for sublist in split_citations for item in sublist]

bib = input("Enter name or path to Bib file: ")
while (not os.path.exists(bib)) :
    print('I did not find the file: \"%s\" ' % str(bib))
    bib = input('Try again or press \"Q+Enter\" to exit: ')
    if bib == 'q':
        raise SystemExit
with open(bib, encoding="utf8") as bibtex_file :
    bib_database = bibtexparser.load(bibtex_file)

new_bib = []
[new_bib.append(item) for item in bib_database.entries if item['ID'] in citations]
db = BibDatabase()
db.entries = new_bib

print("Enter name of new bib file:")
new_bib_file = input()

writer = BibTexWriter()
with open(new_bib_file, 'w') as bibfile:
    bibfile.write(writer.write(db))

print("Your new bib file has been created!")
