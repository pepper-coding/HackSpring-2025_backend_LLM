from transformers import TimesformerModel

model = TimesformerModel.from_pretrained("facebook/timesformer-base-finetuned-k600")
model.save_pretrained("./models/timesformer")
