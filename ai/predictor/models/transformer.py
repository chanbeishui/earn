"""Transformer 时序预测模型"""
import torch
import torch.nn as nn
import pytorch_lightning as pl
from torch.optim.lr_scheduler import ReduceLROnPlateau
import math


class PositionalEncoding(nn.Module):
    """位置编码"""
    def __init__(self, d_model: int, max_len: int = 500):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float() *
                             -(math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, :x.size(1)]


class TransformerPredictor(pl.LightningModule):
    """Transformer Encoder 时序预测器"""

    def __init__(self, input_dim: int = 5, d_model: int = 128,
                 n_heads: int = 4, num_layers: int = 3,
                 dropout: float = 0.1, output_dim: int = 1,
                 learning_rate: float = 1e-3):
        super().__init__()
        self.save_hyperparameters()

        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model, n_heads, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers)

        self.fc = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, output_dim),
        )
        self.learning_rate = learning_rate

    def forward(self, x):
        # x: (batch, seq_len, features)
        x = self.input_proj(x)
        x = self.pos_encoder(x)
        x = self.encoder(x)
        last_out = x[:, -1, :]  # 取最后时间步
        return self.fc(last_out)

    def _step(self, batch, batch_idx, name: str):
        x, y = batch
        y = y.view(-1, 1)
        y_pred = self(x)
        loss = nn.MSELoss()(y_pred, y)

        # 方向准确率
        if name == "train":
            pred_dir = (torch.sigmoid(y_pred) > 0.5).float()
            true_dir = y
            acc = (pred_dir == true_dir).float().mean()
        else:
            acc = torch.tensor(0.0)

        self.log(f"{name}_loss", loss, prog_bar=True)
        self.log(f"{name}_acc", acc, prog_bar=True)
        return loss

    def training_step(self, batch, batch_idx):
        return self._step(batch, batch_idx, "train")

    def validation_step(self, batch, batch_idx):
        return self._step(batch, batch_idx, "val")

    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(
            self.parameters(), lr=self.learning_rate
        )
        scheduler = ReduceLROnPlateau(
            optimizer, mode="min", patience=10, factor=0.5
        )
        return {
            "optimizer": optimizer,
            "lr_scheduler": {"scheduler": scheduler, "monitor": "val_loss"},
        }

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            return self(x)
