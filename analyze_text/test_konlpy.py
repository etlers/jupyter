import warnings
warnings.simplefilter("ignore")

import konlpy
print(konlpy.__version__)

from konlpy.corpus import kolaw
print(kolaw.fileids())

c = kolaw.open('constitution.txt').read()
print(c[:40])

from konlpy.corpus import kobill
print(kobill.fileids())

d = kobill.open('1809890.txt').read()
print(d[:40])

from konlpy.tag import *

hannanum = Hannanum()
kkma = Kkma()
komoran = Komoran()
# mecab = Mecab()
okt = Okt()

# print(hannanum.nouns(c[:40]))
# print(kkma.nouns(c[:40]))
# # komoran은 빈줄이 있으면 에러가 남
# print(komoran.nouns("\n".join([s for s in c[:40].split("\n") if s])))
# print(okt.nouns(c[:40]))
print(c)