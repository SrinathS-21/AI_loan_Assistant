# AI Loan Advisor

This project implements an intelligent loan advisory system using multi-modal AI interactions and vector similarity search for personalized financial guidance. It leverages Google's Gemini Pro for natural language processing and Weaviate vector database for context-aware responses, trained on comprehensive loan documentation and financial guidelines.

Key Components:
- Multi-lingual voice interface supporting 12 Indian languages using Sarvam AI's STT/TTS APIs
- Vector embedding-based retrieval system for contextual loan information using Weaviate
- Machine learning model for loan safety predictions based on user financial metrics
- Community knowledge base with 1000+ financial posts and user interactions
- Real-time profile-aware response generation using LangChain and Gemini Pro

The system is built on a Flask backend with MongoDB for data persistence, and a React frontend with Tailwind CSS for the user interface. It processes both text and voice inputs, making financial advice accessible to a diverse user base.
