import torch
from torch import nn
import torch.nn.functional as F

class conv1DBlock(nn.Module):
    def __init__(self, c_in, c_out, kernel, stride, padding, activate=True):
        super().__init__()
        
        self.block = nn.Sequential(
            nn.Conv1d(c_in, c_out, kernel, stride, padding),
            nn.BatchNorm1d(c_out)
        )
        self.acti = activate
        
    def forward(self, x):
        out = self.block(x)
        if self.acti:
            out = F.relu(out)
        return out

class flatten(nn.Module):
    def __init__(self):
        super().__init__()
    
    def forward(self, x):
        return x.view(x.size(0), -1)

class tsPredCNNBinaryClassifier(nn.Module):
    '''
    channels : channels should start with the original number of channels and 
               have 1 more element comparing with everything else.
    '''
    def __init__(self, channels, kernel_sizes, strides, paddings, linear_layers):
        super().__init__()
        layers = []
        for i in range(len(channels) - 1):
            layers.append(conv1DBlock(
                channels[i], channels[i + 1], kernel_sizes[i], strides[i], 
                paddings[i], True
            ))
        layers.append(flatten())
        for i in range(len(linear_layers)):
            if i == 0:
                layers.append(nn.Linear(channels[len(channels) - 1], linear_layers[0]))
            else:
                layers.append(nn.Linear(linear_layers[i - 1], linear_layers[i]))
            if i == len(linear_layers) - 1:
                layers.append(nn.BatchNorm1d(linear_layers[i]))
                layers.append(nn.ReLU())

        self.layers = nn.Sequential(*layers)
        
    def forward(self, x):
        return torch.sigmoid(self.layers(x))