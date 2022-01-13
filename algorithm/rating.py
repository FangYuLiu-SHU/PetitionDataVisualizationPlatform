import xlutils
from xlutils.copy import copy

from algorithm.group_huefen import *
from algorithm.group_0 import *

from flask import Flask, render_template, request
import json
import sys
import datetime
import torch
import numpy as np
from algorithm import prediction
from algorithm.groupBehaviorPrediction.DataLoader import Dataloader
from algorithm.groupBehaviorPrediction.LSTMGCNPMAgbp import LSTMGCNPMAGbp
import sqlite3
from gevent import pywsgi
import os

# 微博可视化部分添加的库
import pandas as pd
import snownlp as sn
from snownlp import sentiment
import jieba
import wordcloud
import re
import matplotlib.pyplot as plt
import glob
import imageio
from wordcloud import WordCloud, ImageColorGenerator
from snownlp import sentiment
from PIL import Image, ImageDraw, ImageFont
from os import path
import math as m
import networkx as nx

# 谣言可视化部分添加的库
from flask import jsonify
from algorithm import gameTheory
from algorithm import sourceDetection as sd
from algorithm import SIModel as si
from algorithm import SIRModel as sir
from algorithm import opinionEvolution as oe
from algorithm import hawkesProcess
from algorithm import GE_sourceDetection as GE
import random
import copy
from flask_socketio import SocketIO
from flask_mail import Mail, Message

data_path_cache = os.path.dirname(__file__) + '/static/data/weibo/analysis_cache'

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

# 单条微博情感分析，后端数据请求服务
def EmotionalAnalysisOfSingleWeiboPostData(content):
    data = {}
    global senti_value
    global content_err
    if content != '':
        content_err = 1
        senti_value = sen_value(clearTxt(content))
    else:
        content_err = 0
        senti_value = 0
    data['senti_value'] = senti_value
    data['content_err'] = content_err
    return senti_value
    # newData = json.dumps(data)  # json.dumps封装
    # return newData

#紧急词汇
emergency_word = ['尽快', '马上', '及时', '盼复', '盼', '反映多次', '多次反映', '要求回复', '投诉', '多次询问', '严重', '催补',
                  '抓紧', '加快', '再次处理', '再次反映', '再次来电', '反映过', '加急', '重新处理', '强制', '严重', '再次', '多次',
                  '立马解决', '立刻', '立马', '立即', '刻不容缓', '迫不及待', '十万火急', '火烧眉毛', '迫在眉睫', '殷切', '遑急',
                  '危殆', '紧要', '告急', '垂危', '危机', '急切', '遑急', '危急', '蹙迫', '火速', '要紧', '急迫', '紧迫', '火急',
                  '迫切', '弁急', '急不可待', '急不可耐', '急不暇择']
#划分紧急程度
def emergency_degree_classification(content_text, key_word):
    #是否紧急
    flag = False
    for word in key_word:
        if word in content_text:
            flag = True
        # print(word, flag)
    return flag
# #紧急词匹配，测试
# content_text = '尊敬的领导：我是海达公寓的一位租户 ，海达公寓（原名：积家公寓）位于浙江省宁波市镇海区蛟川街道311号，荣明管道建材旁的小巷子里，' \
#                '垃圾满巷子都是，无人清理，最近疫情严重，还是得注意环境卫生，希望相关部门负责人出面处理，谢谢！2021.11.01'
# print(emergency_degree_classification(content_text, emergency_word))

#诉求词汇，按频次排序
request_word = ['要求', '反映', '处理', '投诉', '现来电', '来电要求', '请', '望', '解决', '建议', '来电投诉', '查处', '咨询',
                '诉求', '举报', '请求', '核实', '来电咨询', '严重影响', '希望', '调查处理', '询问', '核查', '帮助', '为什么', '责令',
                '来电表示', '请问', '请求帮助', '来电建议', '反应', '公示', '请帮忙', '恳请', '请核实', '盼', '来电询问',
                '望有关部门', '市民投诉', '建议相关部门', '求助', '主要诉求', '来电求助', '恳求', '采取措施', '来访请求', '来电确认',
                '来电感谢', '帮忙确认', '烦请采取措施']
request_double_word = [['请', '处理'], ['要求', '处理']]
#根据诉求关键词，匹配提取出诉求主句
def get_request(content_text, key_word, key_double_word):
    request = ''
    content_list = content_text.split('，')
    for word in key_word:
        for content in content_list:
            if word in content:
                sub_content_list = content.split('。')
                for sub_content in sub_content_list:
                    if word in sub_content:
                        return sub_content
    for word in key_double_word:
        for content in content_list:
            if word[0] in content and word[1] in content:
                return content
    return request

#获取词的频次
def count_word(content_text, key_word, word_num):
    for word in key_word:
        if word in content_text:
            word_num[word] += 1
    return word_num

#按字典value值排序
def dict_sort_by_value(mydict, reverse=True):
    return sorted(mydict.items(), key=lambda kv: (kv[1], kv[0]), reverse=reverse)

import csv
import xlrd
import xlwt

dir = './static/data/'
name = 'excel_with_emergency_degree.xlsx'
save_name = 'excel_with_request.xlsx'
file_path = os.path.join(dir, name)
save_path = os.path.join(dir, save_name)

# 打开文件
workbook = xlrd.open_workbook(file_path)
index = workbook.sheet_names()[0]
sheet = workbook.sheet_by_name(index)

## 或者如果你只是想创建一张空表
copy_workbook = xlwt.Workbook(encoding='utf-8')
# 创建一个sheet
copy_sheet = copy_workbook.add_sheet('sheet')
# 获取一个已存在的sheet
copy_sheet = copy_workbook.get_sheet('sheet')

# 写入一个值，括号内分别为行数、列数、内容
copy_sheet.write(0, 0, "xfrsq")
copy_sheet.write(0, 1, "value")
copy_sheet.write(0, 2, "紧急程度")
copy_sheet.write(0, 3, "诉求")

# 遍历
nrows = sheet.nrows
for i in range(1, nrows):
    row_list = sheet.row_values(i)
    copy_sheet.write(i, 0, row_list[0])
    copy_sheet.write(i, 1, row_list[1])
    copy_sheet.write(i, 2, row_list[2])
    copy_sheet.write(i, 3, get_request(row_list[0], request_word, request_double_word))

copy_workbook.save(save_path)