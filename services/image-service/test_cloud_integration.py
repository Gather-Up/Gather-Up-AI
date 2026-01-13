"""
Quick test to verify cloud-based LLM integration
Tests the OllamaService with cloud configuration
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.ollama_service import OllamaService
from dotenv import load_dotenv

async def main():
    print("=" * 60)
    print("Testing Cloud-Based LLM Integration")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    
    # Initialize service
    print("\n1. Initializing OllamaService with cloud configuration...")
    ollama = OllamaService()
    
    # Check connection
    print("\n2. Checking cloud LLM connection...")
    is_connected = await ollama.check_connection()
    
    if is_connected:
        print("✅ Cloud LLM connected successfully!")
    else:
        print("❌ Cloud LLM connection failed (will use rule-based fallback)")
    
    # Test prompt enhancement
    print("\n3. Testing prompt enhancement...")
    test_prompt = "birthday party decorations"
    
    try:
        result = await ollama.enhance_prompt(
            user_input=test_prompt,
            event_context={
                "theme": "Birthday",
                "color_scheme": "pink and gold",
                "mood": "festive"
            }
        )
        
        print(f"\n📝 Original prompt: {result['original_prompt']}")
        print(f"✨ Enhanced prompt: {result['enhanced_prompt'][:200]}...")
        print(f"🤖 Model used: {result['model_used']}")
        print("\n✅ Prompt enhancement working!")
        
    except Exception as e:
        print(f"❌ Error during prompt enhancement: {e}")
    
    # Test variations
    print("\n4. Testing prompt variations...")
    try:
        variations = await ollama.generate_multiple_variations(test_prompt, count=3)
        print(f"✅ Generated {len(variations)} variations")
        for i, var in enumerate(variations, 1):
            print(f"   {i}. {var['enhanced_prompt'][:80]}...")
    except Exception as e:
        print(f"❌ Error generating variations: {e}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
