import re
import snownlp as sn
import jieba
import os

# data_path_cache = os.path.dirname(__file__) + '../static/data/weibo/analysis_cache'
data_path_cache = os.path.join(os.path.dirname(__file__), '../static/data/weibo/analysis_cache')
# 分词，去除停用词、英文、符号和数字等
def clearTxt(sentence):
    if sentence != '':
        sentence = sentence.strip()  # 去除文本前后空格
        # 去除文本中的英文和数字
        sentence = re.sub("[a-zA-Z0-9]", "", sentence)
        # 去除文本中的中文符号和英文符号
        sentence = re.sub("[\s+\.\!\/_,$%^*(+]\"\']+|[+——！，:\[\]。!：？?～”,、\.\/~@#￥%……&*【】 （）]+", "", sentence)
        sentence = jieba.lcut(sentence, cut_all=False)
        stopwords = [line.strip() for line in
                     open(data_path_cache + '/stopwords.txt', encoding='gbk').readlines()]
        outstr = ''
        # 去停用词
        for word in sentence:
            if word not in stopwords:
                if word != '\t':
                    outstr += word
                    outstr += " "
        # print(outstr)
        return outstr

# 求文本的情感倾向值，>0.57则默认为积极，<0.5则默认为消极，0.57与0.5之间可默认为中性
def sen_value(text):
    senti = sn.SnowNLP(text)
    senti_value = round((senti.sentiments), 2)
    return senti_value