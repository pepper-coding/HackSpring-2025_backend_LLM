from transformers import DetrForObjectDetection

model_detr = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50")
model_detr.save_pretrained("./models/detr")
