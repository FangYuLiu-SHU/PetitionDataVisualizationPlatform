import jieba
import re
import jieba.analyse
import fool
import json
import csv
import xlrd
import xlwt


# 判断是否以数字和字母结尾
def end_num_or_character(string):
    text = re.compile(r".*[0-9][A-Z][a-z]$")
    if text.match(string):
        return False
    else:
        return True

#获取关键信息
def get_keyinfo(s):
    '''
    input:  string
    output： json-str （date\location\org\keywords）
    '''
    dic = {'date':[],'location':[],'org':[],'keywords':[]}
    #时间正则表示
    pattern = re.compile('\d{2,4}[\\/年]{1}\d{1,2}[\/月]{1}\d{1,2}[日号]{0,1}|\d{2,4}[\/年]{1}\d{1,2}[\/月]{1}|\d{1,2}[\/月]{1}\d{1,2}[日号]{0,1}|\d{1,2}[\/月]{1}|\d{4}[年]{1}')
    dic['date'] = pattern.findall(s)
    #keywords获取
    keywords = jieba.analyse.extract_tags(s, topK=5, withWeight=True, allowPOS=())
    dic['keywords'] = [keyword for keyword,score in keywords]
    #location的获取
    #org的获取
    for info in fool.analysis(s)[1][0]:
        if info[2] == 'org' or info[2] == 'company':
            if info[3] not in dic['org']:#去除重复
                dic['org'].append(info[3])
        if info[2] == 'location':
            if len(info[3])>1 and '甬' not in info[3] and end_num_or_character(info[3]) and info[3] not in['莱绅','伊利','中国']:
                if info[3] not in dic[info[2]]:#去除重复
                    dic['location'].append(info[3])
    return dic

# 获取用户需求
def get_request_by_keyword(s):
    keyword = jieba.analyse.extract_tags(s, topK=1, withWeight=True, allowPOS=())[0][0]
    # 返回的是字符串
    return [i for i in re.split('[，,.。]', s) if keyword in i][-1]

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
    return flag

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

#危险程度词汇，按危险等级从低到高排序
dangerous_word = [
    ['查处', '整改', '协调', '核查', '要求', '建议', '出行不便', '不方便', '不合理', '交通拥堵', '处理', '咨询', '核实', '帮忙', '调查',
     '协调', '核查', '确认', '建议', '换货', '退货', '发票', '退款', '退费', '退还'],
    ['来电咨询', '处罚', '投诉', '无证经营', '赔偿', '后果', '整顿', '违章', '异响', '噪音', '隐患', '违章', '赔偿', '管制', '诉求',
     '报警', '加强管理', '罚款', '补贴', '维修', '交通', '排查', '无证'],
    ['安全隐患', '消防隐患', '扰民', '导致', '极大不便', '随意执法', '报复', '受伤', '污染', '极度不便', '强拆', '偷拆', '交通事故',
     '被偷', '违规征收', '高烧', '精神损失', '污染', '毁坏', '威胁', '污水', '排污', '刺鼻', '维修', '违规建造', '违规建筑', '噪音'],
    ['犯法', '违法', '严重威胁', '严重侵害', '严重损害', '损失惨重', '严重影响安全', '严重安全隐患', '非常严重', '严重影响', '严重']
]
#根据词汇危险程度，得到一段文字的危险等级，1、2、3、4、5危险程度从底到高，默认最不危险
#[1~5]分别对应['可忽略危险', '临界危险', '一般危险', '破坏性危险', '毁灭性危险']
def dangerous_degree_classification(content_text, dangerous_word):
    flag = 1
    for index in range(3, -1, -1):
        for word in dangerous_word[index]:
            if word in content_text:
                flag = index
                return flag + 1
    return flag