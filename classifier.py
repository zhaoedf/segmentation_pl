import pytorch_lightning as pl
import torch.nn.functional as F
import torch


from pytorch_lightning import LightningModule
from torchmetrics.functional import accuracy

class LitClassifier(pl.LightningModule):

    # --------------- computations ---------------
    def __init__(self, model, learning_rate):
        super().__init__()
        self.model = model
        self.save_hyperparameters(ignore='model')

        # # mlflow
        # self.mlflow_client = self.logger.experiment
        # self.exp_name = exp_name
        # self.exp_id = client.get_experiment_by_name(self.exp_name).experiment_id
        # self.run_id = client.list_run_infos(exp_id)[0].run_id

    # --------------- training loop ---------------
    def training_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self.model(x)
        loss = F.cross_entropy(y_hat, y)

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
        loss, acc = self._shared_eval_step(batch, batch_idx)
        metrics = {"val_acc": acc} # , "val_loss": loss
        # self.log_dict(metrics,  on_epoch=True, prog_bar=True, logger=True)
        # return metrics
        # self.log("val_acc", acc, on_step=False, on_epoch=True, logger=True)
        self.log("val_acc", acc, on_step = False, on_epoch=True, prog_bar=True, logger=False, sync_dist=True)
        return metrics

    def on_validation_end(self):
        val_acc = self.trainer.callback_metrics['val_acc']
        self.logger.log_metrics({'val_acc':val_acc.item()}, step=self.trainer.current_epoch)

    # --------------- test loop ---------------
    def test_step(self, batch, batch_idx):
        loss, acc = self._shared_eval_step(batch, batch_idx)
        # metrics = {"test_acc": acc, "test_loss": loss}
        # self.log_dict(metrics)
        # return metrics
        self.log("test_acc", acc, on_step=False, on_epoch=True, logger=True, sync_dist=True)
        return acc

    def _shared_eval_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self.model(x)
        loss = F.cross_entropy(y_hat, y)
        acc = accuracy(y_hat, y)
        return loss, acc

    # --------------- optimizers ---------------
    def configure_optimizers(self):
        return torch.optim.Adam(self.model.parameters(), lr=self.hparams['learning_rate'])

    # --------------- not-neccessary ---------------
    # In the case where you want to scale your inference, you should be using predict_step()
    def predict_step(self, batch, batch_idx, dataloader_idx=None):
        # demo
        x, y = batch
        return self.model(x)


