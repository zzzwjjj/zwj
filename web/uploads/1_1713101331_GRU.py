import pandas as pd

# 加载数据
data_path = './function_features.xlsx'
data = pd.read_excel(data_path)

# 1. 移除'name'列
data = data.drop(columns=['name'])


# 2. 转换'Package'和'Environment'列
# 先定义一个函数来处理这两列
def split_comma_separated_values(row, column_name):
    values = row[column_name].split(',')
    return [int(value.strip()) for value in values]


# 应用转换
package_columns = data.apply(lambda row: split_comma_separated_values(row, 'Package'), axis=1)
environment_columns = data.apply(lambda row: split_comma_separated_values(row, 'Environment'), axis=1)

# 将这些列扩展到原始DataFrame中
max_package_len = max(len(values) for values in package_columns)
max_environment_len = max(len(values) for values in environment_columns)

for i in range(max_package_len):
    data[f'Package_{i + 1}'] = package_columns.apply(lambda x: x[i] if i < len(x) else 0)

for i in range(max_environment_len):
    data[f'Environment_{i + 1}'] = environment_columns.apply(lambda x: x[i] if i < len(x) else 0)

# 移除原始的'Package'和'Environment'列
data = data.drop(columns=['Package', 'Environment'])

# 3. 重命名标签列
data = data.rename(columns={'Unnamed: 11': 'label'})

# 4. 特征和标签分离
X = data.drop(columns=['label'])
y = data['label']

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import numpy as np

# 假设 X 和 y 已经是您准备好的特征和标签
# 注意：请先执行之前的数据准备步骤，包括数据标准化和形状调整

# 数据标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 调整数据形状以适应GRU层输入
X_reshaped = np.reshape(X_scaled, (X_scaled.shape[0], 1, X_scaled.shape[1]))

y_integers = np.array(y)

# 分割数据集
X_train, X_temp, y_train, y_temp = train_test_split(X_reshaped, y_integers, test_size=0.2, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

# 转换为PyTorch张量
X_train_tensor = torch.tensor(X_train, dtype=torch.float)
y_train_tensor = torch.tensor(y_train, dtype=torch.long)
X_val_tensor = torch.tensor(X_val, dtype=torch.float)
y_val_tensor = torch.tensor(y_val, dtype=torch.long)
X_test_tensor = torch.tensor(X_test, dtype=torch.float)
y_test_tensor = torch.tensor(y_test, dtype=torch.long)

# 定义数据集
train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
val_dataset = TensorDataset(X_val_tensor, y_val_tensor)
test_dataset = TensorDataset(X_test_tensor, y_test_tensor)

# 定义数据加载器
train_loader = DataLoader(dataset=train_dataset, batch_size=32, shuffle=True)
val_loader = DataLoader(dataset=val_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(dataset=test_dataset, batch_size=32, shuffle=False)


# 定义模型
class GRUModel(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, num_classes):
        super(GRUModel, self).__init__()
        self.gru = nn.GRU(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        _, h_n = self.gru(x)  # GRU的输出是(output, h_n)
        h_n = h_n[-1, :, :]  # 取最后一层的h_n
        out = self.fc(h_n)
        return out


model = GRUModel(input_size=X_train.shape[2], hidden_size=32, num_layers=1, num_classes=2)
# model.load_state_dict(torch.load('best_model_weights_6.pth'))
# model.train()
# 定义损失和优化器
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 训练模型
best_val_loss = float('inf')
num_epochs = 100
for epoch in range(num_epochs):
    model.train()
    for inputs, labels in train_loader:
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

    # 验证阶段
    model.eval()
    val_loss = 0
    with torch.no_grad():
        for inputs, labels in val_loader:
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            val_loss += loss.item()

    val_loss /= len(val_loader)

    print(f'Epoch {epoch + 1}/{num_epochs}, Loss: {loss.item():.4f}, Val Loss: {val_loss:.4f}')

    # 保存最佳模型
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(model.state_dict(), 'best_model_weights_1.pth')
        print('Best model weights saved.')

# 评估模型
model.eval()
with torch.no_grad():
    correct = 0
    total = 0
    for inputs, labels in test_loader:
        outputs = model(inputs)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

print(f"acc:{correct / total}")
