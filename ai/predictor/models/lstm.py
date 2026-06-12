"""LSTM 价格预测模型"""
import torch
import torch.nn as nn
import pytorch_lightning as pl
from torch.optim.lr_scheduler import ReduceLROnPlateau


class LSTMPredictor(pl.LightningModule):
    """LSTM 时序预测器"""

    def __init__(self, input_dim: int = 5, hidden_dim: int = 128,
                 num_layers: int = 2, dropout: float = 0.2,
                 output_dim: int = 1, learning_rate: float = 1e-3):
        super().__init__()
        self.save_hyperparameters()

        self.lstm = nn.LSTM(
            input_dim, hidden_dim, num_layers,
            batch_first=True, dropout=dropout if num_layers > 1 else 0,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim),
        )
        self.learning_rate = learning_rate

    def forward(self, x):
        # x: (batch, seq_len, features)
        lstm_out, _ = self.lstm(x)
        last_out = lstm_out[:, -1, :]  # 取最后时间步
        last_out = self.dropout(last_out)
        return self.fc(last_out)

    def _step(self, batch, batch_idx, name: str):
        x, y = batch
        y = y.view(-1, 1)
        y_pred = self(x)
        loss = nn.MSELoss()(y_pred, y)

        # 方向准确率
        if y_pred.shape == y.shape:
            pred_dir = (torch.sigmoid(y_pred) > 0.5).float()  # 二分类用 sigmoid
            true_dir = (y > 0.5).float() if y.std() > 0 else y
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

    def test_step(self, batch, batch_idx):
        return self._step(batch, batch_idx, "test")

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(
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
        """推理预测"""
        self.eval()
        with torch.no_grad():
            return self(x)
