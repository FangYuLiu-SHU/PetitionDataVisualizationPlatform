from importlib import import_module
import torch
from model.Bert.utils import build_iterator


#输入一段话输出类别

def predict(string):
    '''
    string: input one sentence
    path: save great model file path
    '''
    # dataset = 'THUCNews'#单独运行predict.py时
    dataset = './model/Bert/THUCNews'
    # x = import_module('models.bert')#单独运行predict.py时
    x = import_module('model.Bert.models.bert')
    config = x.Config(dataset)
    config.device = torch.device('cpu')
    config.batch_size= 1
    model = x.Model(config)
    model.load_state_dict(torch.load(config.save_path))
    model.eval()

    PAD, CLS = '[PAD]', '[CLS]'  # padding符号, bert中综合信息符号
    def load_dataset(content, pad_size=32):
        contents = []
        token = config.tokenizer.tokenize(content)
        token = [CLS] + token
        seq_len = len(token)
        mask = []
        token_ids = config.tokenizer.convert_tokens_to_ids(token)

        if pad_size:
            if len(token) < pad_size:
                mask = [1] * len(token_ids) + [0] * (pad_size - len(token))
                token_ids += ([0] * (pad_size - len(token)))
            else:
                mask = [1] * pad_size
                token_ids = token_ids[:pad_size]
                seq_len = pad_size
        contents.append((token_ids, 0, seq_len, mask))
        return contents
    
    test_data = load_dataset(string,config.pad_size)
    test_iter = build_iterator(test_data, config)
    text,_ = next(test_iter)
    output = model(text)
    predic = torch.max(output.data, 1)[1]
    class_num = predic.item()
    class_name = config.class_list[class_num]

    return class_name

if __name__ == "__main__":
    string = '市民8月16日在海曙区石碶街道鄞县大道后仓村北祥龙4S店购买了一辆吉利汽车，但是出现质量问题送回4S店维修，维修期间商家表示没有备用车辆提供，市民对此不认可，现来电要求提供备用车辆。'
    print(predict(string))

