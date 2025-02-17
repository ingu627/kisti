# 출처 : https://towardsdatascience.com/text-classification-with-bert-in-pytorch-887965e5820f
# Text Classification with BERT in PyTorch
import pandas as pd
datapath = './data/bbc-text.csv'
df = pd.read_csv(datapath)
df.head()
df.groupby(['category']).size().plot.bar()
# !pip install transformers
from transformers import BertTokenizer

tokenizer = BertTokenizer.from_pretrained('bert-base-cased')

example_text = 'I will watch Memento tonight'
bert_input = tokenizer(example_text, padding='max_length', max_length=10,
                       truncation=True, return_tensors='pt')

print(bert_input)
bert_input.input_ids[0]
# tensor([  101,   146,  1209,  2824,  2508, 26173,  3568,   102,     0,     0])

example_text = tokenizer.decode(bert_input.input_ids[0])

print(example_text)

import torch
import numpy as np
from transformers import BertTokenizer

tokenizer = BertTokenizer.from_pretrained('bert-base-cased')
labels = {
    'business':0,
    'entertainment':1,
    'sport':2,
    'tech':3,
    'politics':4
}

class Dataset(torch.utils.data.Dataset):
    
    def __init__(self, df):
        
        self.labels = [labels[label] for label in df['category']]
        self.texts = [tokenizer(text,
                                padding='max_length', max_length=512, truncation=True,
                                return_tensors='pt') for text in df['text']]
        
    def classes(self):
        return self.labels
    
    def __len__(self):
        return len(self.labels)
    
    def get_batch_labels(self, idx):
        # Fetch a batch of labels
        return np.array(self.labels[idx])
    
    def get_batch_texts(self, idx):
        # Fetch a batch of inputs
        return self.texts[idx]
        
    def __getitem__(self, idx):
        
        batch_texts = self.get_batch_texts(idx)
        batch_y = self.get_batch_labels(idx)
        
        return batch_texts, batch_y
        
        
np.random.seed(112)
df_train, df_val, df_test = np.split(df.sample(frac=1, random_state=42),
                                     [int(.8*len(df)), int(.9*len(df))])

print(len(df_train), len(df_val), len(df_test))
from torch import nn
from transformers import BertModel

class BertClassifier(nn.Module):
    
    def __init__(self, dropout=0.5):
        
        super(BertClassifier, self).__init__()
        
        self.bert = BertModel.from_pretrained('bert-base-cased')
        self.dropout = nn.Dropout(dropout)
        self.linear = nn.Linear(768, 5)
        self.relu = nn.ReLU()
        
    def forward(self, input_id, mask):
        
        _, pooled_output = self.bert(
            input_ids = input_id, 
            attention_mask = mask, 
            return_dict=False)
        dropout_output = self.dropout(pooled_output)
        linear_output = self.linear(dropout_output)
        final_layer = self.relu(linear_output)
        
        return final_layer
from torch.optim import Adam
from tqdm import tqdm

def train(model, train_data, val_data, learning_rate, epochs):
    
    train, val = Dataset(train_data), Dataset(val_data)
    
    train_dataloader = torch.utils.data.DataLoader(train, batch_size=2, shuffle=True)
    val_dataloader = torch.utils.data.DataLoader(val, batch_size = 2)
    
    use_cuda = torch.cuda.is_available()
    device = torch.device('cuda' if use_cuda else 'cpu')
    
    criterion = nn.CrossEntropyLoss()
    optimizer = Adam(model.parameters(), lr=learning_rate)
    
    if use_cuda:
        
        model = model.cuda()
        criterion = criterion.cuda()
        
    for epoch_num in range(epochs):
        
        total_acc_train = 0 
        total_loss_train = 0
        
        for train_input, train_label in tqdm(train_dataloader):
            
            train_label = train_label.to(device)
            mask = train_input['attention_mask'].to(device)
            input_id = train_input['input_ids'].squeeze(1).to(device)
            
            output = model(input_id, mask)
            
            batch_loss = criterion(output, train_label.long())
            total_loss_train += batch_loss.item()
            
            acc = (output.argmax(dim=1) == train_label).sum().item()
            total_acc_train += acc
             
            model.zero_grad()
            batch_loss.backward()
            optimizer.step()
            
        total_acc_val = 0
        total_loss_val = 0
        
        with torch.no_grad():
            
            for val_input, val_label in val_dataloader:
                
                val_label = val_label.to(device)
                mask = val_input['attention_mask'].to(device)
                input_id = val_input['input_ids'].squeeze(1).to(device)
                
                output = model(input_id, mask)
                
                batch_loss = criterion(output, val_label.long())
                total_loss_val += batch_loss.item()
                
                acc = (output.argmax(dim=1) == val_label).sum().item()
                total_acc_val += acc
                
        print(
            f'Epoch: {epoch_num + 1} | Train Loss: {total_loss_train / len(train_data): .3f} \
            | Train Accuracy: {total_acc_train / len(train_data): .3f} \
            | Val Loss: {total_loss_val / len(val_data): .3f} \
            | Val Accuracy: {total_acc_val / len(val_data): .3f}'
        )

EPOCHS = 5
model = BertClassifier()
LR = 1e-6

train(model, df_train, df_val, LR, EPOCHS)
def evaluate(model, test_data):
    
    test = Dataset(test_data)
    
    test_dataloader = torch.utils.data.DataLoader(test, batch_size=2)
    
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    
    if use_cuda:
        
        model = model.cuda()
        
    total_acc_test = 0
    with torch.no_grad():
        
        for test_input, test_label in test_dataloader:
            
            test_label = test_label.to(device)
            mask = test_input['attention_mask'].to(device)
            input_id = test_input['input_ids'].squeeze(1).to(device)
            
            output = model(input_id, mask)
            
            acc = (output.argmax(dim=1) == test_label).sum().item()
            total_acc_test += acc
    
    print(f'Test Accuracy: {total_acc_test / len(test_data): .3f}')

evaluate(model, df_test)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
inverse_labels = {v:k for k,v in labels.items()}
def predict(device, model, sentence):
    sentence = sentence
    sentence_input = tokenizer(sentence, 
                               padding='max_length', 
                               max_length=512, truncation=True, 
                               return_tensors='pt').to(device)
    input_id = sentence_input['input_ids']
    mask = sentence_input['attention_mask']
    output = model(input_id, mask)
    predicted_class_label = output.argmax(dim=1)
    predicted_class = inverse_labels[predicted_class_label.item()]
    print(f'The predicted class is : {predicted_class}')
predict(device, model, 'son heung min is a world best player in EPL')