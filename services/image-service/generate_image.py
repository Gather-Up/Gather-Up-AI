from google import genai
from google.genai import types
from PIL import Image

client = genai.Client(api_key="")
print("\n-----------------------------------\n")

image_prompt = (
    "A post for instagram with words \"Cricket Mela 2025\" The words are center and bold more nice and elagant, background with a cricket feel more realistic and futuristic no any disturbance forcus more on words than other graphics"
)

image_response = client.models.generate_content(
    model="models/gemini-2.5-flash-image", 
    contents=[image_prompt]
)

for part in image_response.parts:
    if part.inline_data:
        image = part.as_image()
        image.save("generated_image.png")
        print("✅ Image saved as generated_image.png")
