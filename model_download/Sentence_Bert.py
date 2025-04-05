from sentence_transformers import SentenceTransformer

model_sbert = SentenceTransformer("all-MiniLM-L6-v2")
model_sbert.save("./models/sbert")  
