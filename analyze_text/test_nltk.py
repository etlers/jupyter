import nltk
nltk.download("book", quiet=True)
from nltk.book import *

print(nltk.corpus.gutenberg.fileids())

emma_raw = nltk.corpus.gutenberg.raw("austen-emma.txt")
print(emma_raw[:1302])

from nltk.tokenize import sent_tokenize
print(sent_tokenize(emma_raw[:1000])[3])

from nltk.tokenize import word_tokenize
print(word_tokenize(emma_raw[50:100]))

from nltk.tokenize import RegexpTokenizer
retokenize = RegexpTokenizer("[\w]+")
print(retokenize.tokenize(emma_raw[50:100]))