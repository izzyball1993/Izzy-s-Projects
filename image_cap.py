"""simple image captioning file"""
import requests
from PIL import Image
from transformers import AutoProcessor, BlipForConditionalGeneration

# Load the pretrained processor and model
processor = AutoProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# Load your image 
img_path = "20200322_150848.jpeg" #for now, must manually enter image name as saved in your files
# convert it into an RGB format 
image = Image.open(img_path).convert('RGB')

# prepare output caption 
text = "the image is of"
inputs = processor(images=image, text=text, return_tensors="pt")
# Generate a caption for the image
outputs = model.generate(**inputs, max_length=50)

# Decode the generated tokens to text
caption = processor.decode(outputs[0], skip_special_tokens=True)
# Print the caption
print(caption)
