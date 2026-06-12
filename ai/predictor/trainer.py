"""训练器 — 管理训练/验证/早停"""
import os
from typing import Optional, Callable
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint
from torch.utils.data import DataLoader, random_split
import torch

from .models.lstm import LSTMPredictor
from .models.transformer import TransformerPredictor
from .dataset import KlineDataset, MultiStockDataset


class PredictorTrainer:
    """深度学习预测器训练管理器"""

    def __init__(self, model_type: str = "lstm", **hyperparams):
        """
        :param model_type: "lstm" 或 "transformer"
        :param hyperparams: 超参数 (lookback, forecast, hidden_dim, layers, etc.)
        """
        self.model_type = model_type
        self.hparams = hyperparams
        self.model = None
        self.dataset = None
        self.trainer = None
        self._results = {"train_loss": [], "val_loss": []}

    def prepare_data(self, storage, codes: list = None,
                     start_date: str = "2020-01-01",
                     end_date: str = "2025-01-01"):
        """准备数据"""
        if codes:
            self.dataset = MultiStockDataset(
                storage, codes,
                lookback=self.hparams.get("lookback", 60),
                forecast=self.hparams.get("forecast", 5),
                target_type="direction",
                start_date=start_date, end_date=end_date,
            )
        return len(self.dataset) if self.dataset else 0

    def build_model(self):
        """构建模型"""
        input_dim = 5  # OHLCV
        hidden_dim = self.hparams.get("hidden_dim", 128)
        num_layers = self.hparams.get("num_layers", 2)
        dropout = self.hparams.get("dropout", 0.2)
        lr = self.hparams.get("learning_rate", 1e-3)

        if self.model_type == "lstm":
            self.model = LSTMPredictor(
                input_dim=input_dim, hidden_dim=hidden_dim,
                num_layers=num_layers, dropout=dropout, output_dim=1,
                learning_rate=lr,
            )
        elif self.model_type == "transformer":
            self.model = TransformerPredictor(
                input_dim=input_dim, d_model=hidden_dim,
                n_heads=self.hparams.get("n_heads", 4),
                num_layers=num_layers, dropout=dropout, output_dim=1,
                learning_rate=lr,
            )
        else:
            raise ValueError(f"未知模型类型: {self.model_type}")

        return self.model

    def train(self, epochs: int = 100, batch_size: int = 64,
              val_split: float = 0.2,
              progress_callback: Optional[Callable] = None) -> dict:
        """训练模型"""
        if self.dataset is None or len(self.dataset) == 0:
            return {"error": "无训练数据"}

        if self.model is None:
            self.build_model()

        # 划分训练/验证集
        total = len(self.dataset)
        val_size = int(total * val_split)
        train_size = total - val_size
        train_ds, val_ds = random_split(self.dataset, [train_size, val_size])

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size)

        # 回调
        early_stop = EarlyStopping(
            monitor="val_loss", patience=20, mode="min"
        )
        checkpoint = ModelCheckpoint(
            monitor="val_loss", mode="min",
            save_top_k=1, dirpath="data/models/",
            filename=f"{self.model_type}-{{epoch:02d}}-{{val_loss:.4f}}",
        )

        # Loss 历史记录
        self._results = {"train_loss": [], "val_loss": []}

        class LossLogger(pl.Callback):
            def on_train_epoch_end(self, trainer, pl_module):
                logs = trainer.callback_metrics
                self._results["train_loss"].append(
                    float(logs.get("train_loss", 0))
                )
                self._results["val_loss"].append(
                    float(logs.get("val_loss", 0))
                )
                if progress_callback:
                    progress_callback(
                        trainer.current_epoch + 1, epochs,
                        float(logs.get("val_loss", float("inf")))
                    )

        loss_logger = LossLogger()
        loss_logger._results = self._results

        # 训练
        self.trainer = pl.Trainer(
            max_epochs=epochs,
            callbacks=[early_stop, checkpoint, loss_logger],
            enable_progress_bar=False,
            log_every_n_steps=10,
        )
        self.trainer.fit(self.model, train_loader, val_loader)

        return {
            "model_type": self.model_type,
            "epochs_trained": self.trainer.current_epoch + 1,
            "best_model_path": checkpoint.best_model_path,
            "best_val_loss": float(checkpoint.best_model_score),
            "train_loss": self._results["train_loss"],
            "val_loss": self._results["val_loss"],
        }

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """推理"""
        if self.model is None:
            raise RuntimeError("模型未训练")
        return self.model.predict(x)
