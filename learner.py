import pytorch_lightning as pl
import torch.nn.functional as F
import torch
import torch.nn as nn 

from pytorch_lightning import LightningModule
from torchmetrics.functional import accuracy

from utils import dice_coeff


class SegLearner(pl.LightningModule):

    # --------------- computations ---------------
    def __init__(self, model, learning_rate):
        super().__init__()
        self.model = model
        self.save_hyperparameters(ignore='model')
        
        self.loss_func = nn.BCEWithLogitsLoss()
        self.dice_coeff = dice_coeff


    # --------------- training loop ---------------
    def training_step(self, batch, batch_idx):
        x, y = batch['image'], batch['mask']

        y_hat = self.model(x)
        loss = self.loss_func(y_hat, y)

        # logs metrics for each training_step,
        # and the average across the epoch, to the progress bar and logger
        self.log("loss_step", loss, on_step=True, on_epoch=False, prog_bar=True, logger=True)
        self.log("loss_epoch", loss, on_step=False, on_epoch=True, prog_bar=True, logger=False, sync_dist=True)
        return loss

    def on_train_epoch_end(self):
        loss_epoch = self.trainer.callback_metrics['loss_epoch']
        self.logger.log_metrics({'loss_epoch':loss_epoch.item()}, step=self.trainer.current_epoch)

    # --------------- validation loop ---------------
    def validation_step(self, batch, batch_idx):
        loss, miou = self._shared_eval_step(batch, batch_idx)
        metrics = {"val_miou": miou} # , "val_loss": loss

        self.log("val_miou", miou, on_step = False, on_epoch=True, prog_bar=True, logger=False, rank_zero_only=True)
        return metrics

    def on_validation_end(self):
        val_miou = self.trainer.callback_metrics['val_miou']
        self.logger.log_metrics({'val_miou':val_miou.item()}, step=self.trainer.current_epoch)

    # --------------- test loop ---------------
    def test_step(self, batch, batch_idx):
        loss, miou = self._shared_eval_step(batch, batch_idx)
        metrics = {"test_miou": miou}

        self.log("test_miou", miou, on_step=False, on_epoch=True, logger=True, rank_zero_only=True)
        return metrics

    def on_test_end(self):
        test_miou = self.trainer.callback_metrics['test_miou']
        self.logger.log_metrics({'test_miou':test_miou.item()}, step=self.trainer.current_epoch)

    def _shared_eval_step(self, batch, batch_idx):
        x, y = batch['image'], batch['mask']
        
        y_hat = self.model(x)
        loss = self.loss_func(y_hat, y)
        # miou = self.dice_coeff(y, y_hat)
        miou = -loss
        # acc = accuracy(y_hat, y)
        return loss, miou

    # --------------- optimizers ---------------
    def configure_optimizers(self):
        return torch.optim.Adam(self.model.parameters(), lr=self.hparams['learning_rate'])

    # --------------- not-neccessary ---------------
    def get_progress_bar_dict(self):
        # don't show the version number
        items = super().get_progress_bar_dict()
        items.pop("v_num", None)
        # items["nb_seen_classes"] = self.nb_seen_classes
        return items
