# Image Generation Service - Quick Start Guide

## Overview
The Image Service generates high-quality event graphics using **Stable Diffusion XL (SDXL)** via **ComfyUI**. It includes intelligent prompt enhancement using **Llama 3.2 3B**.

## Architecture
- **Port**: 8003
- **Model**: Stable Diffusion XL Base 1.0 + Refiner 1.0 (2-stage pipeline)
- **ComfyUI**: Running on port 8000 (not default 8188)
- **Template**: Custom SDXL Base + Refiner workflow
- **Prompt Enhancement**: Llama 3.2 3B via Ollama (port 11434)

## Prerequisites

### 1. ComfyUI Setup
Make sure ComfyUI is installed and running:
```bash
# Navigate to your ComfyUI directory
cd path/to/ComfyUI

# Start ComfyUI on port 8000
python main.py --port 8000
```

**Important**: The service expects ComfyUI on port 8000 (configured in `.env`)

### 2. Required Models
ComfyUI needs BOTH SDXL models for best quality:
- **Base Model**: `sd_xl_base_1.0.safetensors` (required)
- **Refiner Model**: `sd_xl_refiner_1.0.safetensors` (required for quality)
- Location: `ComfyUI/models/checkpoints/`
- Download from: [Hugging Face - SDXL Base](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) and [SDXL Refiner](https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0)

**How it works**:
1. Base model generates the image (80% of denoising steps)
2. Refiner model enhances details and quality (20% of steps)
3. Result: Professional quality images!

### 3. Ollama (Prompt Enhancement)
```bash
# Install Ollama
# Windows: Download from ollama.ai

# Pull Llama 3.2 3B model
ollama pull llama3.2:3b
```

## Starting the Service

### Option 1: Start All Services
```bash
python start_all.py
```

### Option 2: Image Service Only
```bash
cd services/image-service
python main.py
```

The service will start on http://localhost:8003

## API Endpoints

### 1. Generate Images (Non-Streaming)
**Endpoint**: `POST /api/images/generate`

Waits for generation to complete and returns base64 encoded images.

**Request Body**:
```json
{
  "prompt": "Professional social media post design, elegant wedding venue with floral decorations, bold text overlay 'WEDDING' in elegant serif font, subtitle 'SAVE THE DATE', text 'COLOMBO' included, soft gold and white, Instagram-ready graphic design, high resolution",
  "num_images": 1,
  "negative_prompt": "blurry, low quality, distorted, deformed, ugly, bad anatomy, watermark, logo",
  "width": 1024,
  "height": 1024,
  "steps": 30,
  "cfg_scale": 7.5,
  "sampler_name": "dpmpp_2m",
  "scheduler": "karras",
  "seed": null,
  "denoise": 1.0
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Successfully generated 1 image(s)",
  "images": [
    {
      "index": 1,
      "data": "base64_encoded_image_data...",
      "filename": "GatherUp_AI_00001_.png",
      "format": "png",
      "seed": 123456789,
      "generation_time": 15.3
    }
  ],
  "enhanced_prompt": "Professional social media post...",
  "generation_params": {
    "width": 1024,
    "height": 1024,
    "steps": 30,
    "cfg_scale": 7.5,
    "sampler": "dpmpp_2m",
    "scheduler": "karras",
    "seeds": [123456789],
    "negative_prompt": "blurry, low quality..."
  },
  "total_generation_time": 18.2
}
```

### 2. Generate Images (Streaming)
**Endpoint**: `POST /api/images/generate/stream`

Returns Server-Sent Events (SSE) with real-time progress updates.

**Same request body as non-streaming**

**Response (SSE)**:
```
data: {"status": "queued", "message": "Preparing workflow...", "progress_percent": 0}

data: {"status": "processing", "message": "Generation starting...", "progress_percent": 20}

data: {"status": "generating", "message": "Generating image...", "progress_percent": 50}

data: {"status": "completed", "image_data": {...}, "progress_percent": 100}

data: [DONE]
```

### 3. Enhance Prompt Only
**Endpoint**: `POST /api/images/enhance-prompt?prompt=your_prompt_here`

Uses Llama 3.2 to enhance the prompt without generating images.

**Response**:
```json
{
  "enhanced_prompt": "Professional social media post design...",
  "context": "Used event type analysis and social media graphic principles"
}
```

### 4. Health Check
**Endpoint**: `GET /health`

Checks if the service and ComfyUI connection are working.

## Via API Gateway

All endpoints are also available through the API Gateway (port 8080):

- `POST http://localhost:8080/api/v1/images/generate`
- `POST http://localhost:8080/api/v1/images/generate/stream`
- `POST http://localhost:8080/api/v1/images/enhance-prompt`

## Parameters Explained

### Core Parameters
- **prompt**: Description of what you want to generate
- **num_images**: Number of images (1-3)
- **width/height**: Image dimensions (512-2048, optimal: 1024x1024)
- **steps**: Denoising steps (20-50 recommended, higher = better quality but slower)
- **cfg_scale**: How closely to follow the prompt (7-9 recommended)

### Advanced Parameters
- **sampler_name**: Sampling algorithm
  - `dpmpp_2m` (recommended, fast and high quality)
  - `euler_a` (good for creative results)
  - `ddim` (deterministic)
- **scheduler**: Noise schedule
  - `karras` (recommended)
  - `normal`, `exponential`, `simple`
- **seed**: Random seed for reproducibility (null = random)
- **negative_prompt**: What to avoid in generation

## Example Prompts

### Wedding Event
```
Professional social media post design, elegant wedding venue with floral decorations, bold text overlay 'WEDDING' in elegant serif font, subtitle 'SAVE THE DATE', text 'COLOMBO' included, soft gold and white, Instagram-ready graphic design, high resolution
```

### Birthday Party
```
Vibrant event poster, colorful birthday celebration theme, balloons and confetti, bold text 'BIRTHDAY BASH', modern typography, festive atmosphere, party decorations, Instagram-ready design
```

### Corporate Event
```
Professional corporate event poster, modern conference hall, business networking theme, bold text 'TECH SUMMIT 2026', minimalist design, blue and white color scheme, professional typography, LinkedIn-ready graphic
```

## Workflow

1. **User sends prompt** → `"I need a wedding venue in Colombo"`
2. **Llama 3.2 enhances** → Converts to social media graphic prompt with text overlays
3. **ComfyUI generates** → Uses SD XL Simple template
4. **Service returns** → Base64 encoded PNG image

## Troubleshooting

### ComfyUI Connection Error
```
❌ ComfyUI connection error: Connection refused
```
**Solution**: Make sure ComfyUI is running on port 8000
```bash
cd path/to/ComfyUI
python main.py --port 8000
```

### Model Not Found Error
```
Error loading checkpoint sd_xl_base_1.0.safetensors
Error loading checkpoint sd_xl_refiner_1.0.safetensors
```
**Solution**: Download BOTH SDXL models to `ComfyUI/models/checkpoints/`
- Base: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
- Refiner: https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0

### Prompt Enhancement Fails
```
❌ Llama service error
```
**Solution**: Make sure Ollama is running and model is installed
```bash
ollama pull llama3.2:3b
ollama serve
```

### Generation Timeout
**Solution**: Increase timeout in `.env`
```
COMFYUI_TIMEOUT=600
```

## Postman Collection

Import `Gather-Up-AI.postman_collection.json` to test all endpoints.

Key collections:
- **API Gateway (Port 8080)** - Main entry point
- **Image Service (Port 8003)** - Direct access

## Integration Example (Frontend)

### Non-Streaming (Simple)
```javascript
const response = await fetch('http://localhost:8080/api/v1/images/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: "Professional wedding poster design",
    num_images: 1,
    width: 1024,
    height: 1024
  })
});

const data = await response.json();
const imageBase64 = data.images[0].data;
// Display: <img src={`data:image/png;base64,${imageBase64}`} />
```

### Streaming (Real-time Progress)
```javascript
const eventSource = new EventSource('http://localhost:8080/api/v1/images/generate/stream', {
  method: 'POST',
  body: JSON.stringify({ prompt: "Wedding poster", num_images: 1 })
});

eventSource.onmessage = (event) => {
  if (event.data === '[DONE]') {
    eventSource.close();
    return;
  }
  
  const progress = JSON.parse(event.data);
  console.log(`Progress: ${progress.progress_percent}%`);
  console.log(`Status: ${progress.message}`);
  
  if (progress.status === 'completed') {
    const imageData = progress.image_data.data;
    // Display image
  }
};
```

## Performance

- **Generation Time**: ~15-30 seconds per image (depends on steps)
- **Optimal Settings**: 1024x1024, 30 steps, cfg_scale 7.5
- **GPU Required**: NVIDIA GPU with CUDA recommended for ComfyUI
- **Memory**: ~8GB VRAM for SDXL

## Notes

- Images are returned as base64 encoded PNG files
- Each image is ~2-4MB (base64 encoded ~3-5MB)
- Seed parameter allows reproducing exact same images
- Prompt enhancement adds 1-2 seconds processing time
- ComfyUI runs separately - must be started manually
