from transformers import RobertaModel

model_roberta = RobertaModel.from_pretrained("roberta-base")
model_roberta.save_pretrained("./models/roberta")
