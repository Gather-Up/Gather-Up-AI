# 🎉 Gather-Up-AI - Intelligent Event Planning Assistant

**Gather-Up-AI** is a microservices-based event planning platform that leverages AI to help users find the perfect vendors and venues for their events. Using natural language processing and intelligent recommendation systems, it simplifies the event planning process.

---

## 🌟 Features

- 🤖 **AI-Powered Recommendations**: Uses cloud-based LLM and RAG (Retrieval-Augmented Generation) for intelligent vendor suggestions
- 📍 **Smart Location Search**: Integrates with Google Places API to find ideal event venues
- 🎨 **AI Image Generation**: Creates stunning event visuals using Zephyr Image Turbo (cloud-based model)
- 🔗 **Microservices Architecture**: Scalable, modular design with separate services for different functionalities
- 🚀 **FastAPI Backend**: High-performance async API services
- 🧠 **Vector Search**: Semantic similarity search using sentence transformers
- 📡 **Real-time Streaming**: Server-Sent Events for live image generation progress
- ☁️ **Cloud-First AI**: Uses online models via Ollama cloud API with optional local fallback

---

## 📁 Project Structure

```
Gather-Up-AI/
│
├── services/
│   ├── api-gateway/              # Main entry point - Routes requests to services
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   ├── .env
│   │   └── tests/
│   │       └── test_main.py
│   │
│   ├── location-service/         # Venue/location search using Google Places API
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── schemas.py
│   │   ├── .env.example
│   │   ├── routes/
│   │   │   └── location_routes.py
│   │   ├── services/
│   │   │   └── places_service.py
│   │   └── tests/
│   │       └── test_main.py
│   │
│   ├── vendor-service/           # RAG-based vendor recommendations
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── database.py
│   │   ├── schemas.py
│   │   ├── .env.example
│   │   ├── .env
│   │   ├── routes/
│   │   │   └── vendor_routes.py
│   │   ├── services/
│   │   │   ├── llama_service.py
│   │   │   └── vector_service.py
│   │   └── tests/
│   │       └── test_main.py
│   │
│   └── image-service/            # 🆕 AI Image Generation with SDXL
│       ├── main.py
│       ├── requirements.txt
│       ├── schemas.py
│       ├── .env
│       ├── routes/
│       │   └── image_routes.py
│       ├── services/
│       │   ├── comfyui_service.py
│       │   └── llama_service.py
│       ├── test_service.py
│       └── README.md
│
├── .venv/
├── start_all.py                  # 🔥 One-click launcher for all services
├── COMFYUI_SETUP.md             # 🎨 ComfyUI installation guide
├── .gitignore
└── README.md
```

---

## 🏗️ Architecture

### **API Gateway** (Port: 8000)
- Central entry point for all client requests
- Routes requests to appropriate microservices
- Handles CORS and request/response aggregation
- Supports streaming responses for image generation

### **Vendor Service** (Port: 8001)
- Manages vendor data in MongoDB
- Uses sentence transformers for semantic search
- Implements RAG pattern with LLM for intelligent recommendations
- Vector similarity search for matching user requirements

### **Location Service** (Port: 8002)
- Integrates with Google Places API
- Searches for venues based on location and event type
- Returns detailed venue information including ratings and contact details

### **Image Service** (Port: 8000) 🆕
- AI-powered image generation using Zephyr Image Turbo (cloud-optimized model)
- Prompt enhancement with cloud-based LLM for better results
- Real-time progress streaming via Server-Sent Events
- Integration with ComfyUI for professional image generation
- Supports customizable image generation with modern turbo diffusion
- Uses qwen_3_4b text encoder for superior text understanding

---

## 🛠️ Technology Stack

- **Framework**: FastAPI
- **Language**: Python 3.10+
- **Database**: MongoDB (Vendor Service)
- **AI/ML**: 
  - PyTorch
  - Sentence Transformers
  - Hugging Face Transformers
  - Zephyr Image Turbo (via ComfyUI)
  - Cloud-based LLM via Ollama (glm-4.6:cloud)
  - qwen_3_4b text encoder
- **External APIs**: Google Places API, Ollama Cloud API
- **Image Generation**: ComfyUI with Zephyr Image Turbo
- **HTTP Client**: HTTPX, Requests, aiohttp
- **Environment Management**: python-dotenv
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **CI/CD**: GitHub Actions

---

## 🚀 Quick Start

### Prerequisites

- Python **3.10+** installed
- MongoDB instance (for vendor service)
- Google Places API key (for location service)
- **ComfyUI with Zephyr Image Turbo models** (for image service)
  - qwen_3_4b.safetensors (text encoder)
  - z_image_turbo_bf16.safetensors (diffusion model)
  - ae.safetensors (VAE)
- **Cloud-based Ollama API access** (or local Ollama with models)

### 1️⃣ Clone the Repository

```powershell
git clone https://github.com/Gather-Up/Gather-Up-AI
cd Gather-Up-AI
```

### 2️⃣ Create Virtual Environment

```powershell
python -m venv .venv
```

### 3️⃣ Activate Virtual Environment

**Windows PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Command Prompt:**
```cmd
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

You should see `(.venv)` before your terminal prompt.

### 4️⃣ Install Dependencies

Install all service dependencies into the shared virtual environment:

```powershell
pip install -r services/api-gateway/requirements.txt
pip install -r services/location-service/requirements.txt
pip install -r services/vendor-service/requirements.txt
pip install -r services/image-service/requirements.txt
```

**Note**: For GPU support with PyTorch, use:
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu129
```

### 5️⃣ Configure Environment Variables

Each service has an `.env.example` file. Copy and configure them:

**API Gateway:**
```powershell
cd services/api-gateway
cp .env.example .env
# Edit .env with your configuration
```

**Location Service:**
```powershell
cd services/location-service
cp .env.example .env
# Add your GOOGLE_PLACES_API_KEY
```

**Vendor Service:**
```powershell
cd services/vendor-service
cp .env.example .env
# Add your MONGODB_URI and other configurations
```

**Image Service:** 🆕
```powershell
cd services/image-service
# .env already created - verify COMFYUI_URL and OLLAMA_API_URL
```

### 5.5️⃣ Setup ComfyUI (for Image Service) 🎨

Required models for Zephyr Image Turbo:

1. **Text Encoder**: `qwen_3_4b.safetensors`
2. **Diffusion Model**: `z_image_turbo_bf16.safetensors`
3. **VAE**: `ae.safetensors`

Place models in:
```
ComfyUI/models/
├── text_encoders/qwen_3_4b.safetensors
├── diffusion_models/z_image_turbo_bf16.safetensors
└── vae/ae.safetensors
```

Start ComfyUI on port 8000 and verify at `http://localhost:8000`

### 6️⃣ Run the Services

**Option A: One-Click Launcher** 🔥 **RECOMMENDED**

```powershell
# From project root
python start_all.py
```

This will open separate windows for:
- API Gateway (8000)
- Vendor Service (8001)
- Location Service (8002)
- Image Service (8000)

**Option B: Manual Start**

Open **4 separate terminal windows**, activate the virtual environment in each, and run:

**Terminal 1 - API Gateway:**
```powershell
cd services/api-gateway
python main.py
```
Runs on: `http://localhost:8000`

**Terminal 2 - Vendor Service:**
```powershell
cd services/vendor-service
python main.py
```
Runs on: `http://localhost:8001`

**Terminal 3 - Location Service:**
```powershell
cd services/location-service
python main.py
```
Runs on: `http://localhost:8002`

---

## 📡 API Endpoints

### API Gateway (`:8000`)
- `GET /` - Root endpoint
- `GET /health` - Health check for all services
- `POST /plan-event` - Main event planning endpoint (natural language input)

### Vendor Service (`:8001`)
- `GET /` - Service info
- `GET /health` - Health check
- `POST /api/vendors/recommend` - Get vendor recommendations
- `POST /api/vendors` - Add new vendor
- `GET /api/vendors` - List all vendors

### Location Service (`:8002`)
- `GET /` - Service info
- `GET /health` - Health check
- `POST /api/locations/search` - Search venues by location and type

---

## 🔧 Development

### Adding New Dependencies

After installing new packages:

```powershell
pip freeze > services/<service-name>/requirements.txt
```

### Running Individual Tests

To run a specific test file:

```powershell
cd services/<service-name>
pytest tests/test_main.py -v
```

To run tests with detailed output:

```powershell
pytest tests/ -v -s
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Document functions with docstrings

---

## 🐛 Troubleshooting

### Virtual Environment Issues

If you move or rename the project folder, recreate the virtual environment:

```powershell
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# Reinstall dependencies
```

### Port Already in Use

Change the port in the respective service's `.env` file:
- `API_GATEWAY_PORT=8000`
- `VENDOR_SERVICE_PORT=8001`
- `LOCATION_SERVICE_PORT=8002`

### MongoDB Connection Issues

Ensure MongoDB is running and the `MONGODB_URI` in `.env` is correct.

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)
- [Sentence Transformers](https://www.sbert.net/)
- [Google Places API](https://developers.google.com/maps/documentation/places/web-service)

---

## 👥 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 👤 Author

**Sachitha Samadhi**
- GitHub: [@Gather-Up](https://github.com/Gather-Up)

---

## 🙏 Acknowledgments

- Google Places API for venue data
- Hugging Face for transformer models
- FastAPI framework for the excellent async support

---

## 📝 Notes

- The shared `.venv` ensures consistency and avoids duplicate installations
- Do not move the `.venv` folder after creation — paths inside it are absolute
- All services must be running simultaneously for full functionality

---

**Happy Event Planning! 🎊**
