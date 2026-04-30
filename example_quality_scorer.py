#!/usr/bin/env python3
"""Example usage of the ResponseQualityScorer."""

import asyncio
import json
from loom.quality_scorer import research_quality_score, ResponseQualityScorer


def example_1_basic_usage():
    """Basic usage of ResponseQualityScorer."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Quality Scoring")
    print("="*70)

    scorer = ResponseQualityScorer()

    response = "Python is widely used in data science and machine learning."
    result = scorer.score(response)

    print(f"\nResponse: {response}")
    print(f"\nTotal Score: {result['total_score']}/10")
    print(f"Quality Tier: {result['quality_tier']}")
    print(f"\nDimension Scores:")
    for dim, score in sorted(result["dimensions"].items()):
        print(f"  {dim:20s}: {score:5.2f}")
    print(f"\nWeakest Dimension: {result['weakest_dimension']}")
    print(f"\nImprovement Suggestions:")
    for i, suggestion in enumerate(result["improvement_suggestions"], 1):
        print(f"  {i}. {suggestion}")


def example_2_with_query():
    """Score response in context of a query."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Scoring with Query Context")
    print("="*70)

    scorer = ResponseQualityScorer()

    query = "How do I implement authentication in a REST API?"
    response = """## REST API Authentication

### Overview
Authentication protects your API from unauthorized access.

### Implementation Steps

1. **Choose an auth method**
   - JWT (JSON Web Tokens) - stateless, scalable
   - OAuth 2.0 - industry standard, delegated access
   - API Keys - simple but less secure

2. **Install dependencies**
   ```bash
   pip install fastapi python-jose python-multipart cryptography
   ```

3. **Implement JWT**
   ```python
   from fastapi import FastAPI, Depends, HTTPException
   from fastapi.security import HTTPBearer, HTTPAuthCredentials

   app = FastAPI()
   security = HTTPBearer()

   @app.post("/token")
   async def login(username: str, password: str):
       # Verify credentials
       # Generate JWT token
       return {"access_token": token}

   @app.get("/protected")
   async def protected(credentials: HTTPAuthCredentials = Depends(security)):
       # Verify token
       return {"message": "Success"}
   ```

### Best Practices
- Always use HTTPS for token transmission
- Implement token expiration (15-60 minutes recommended)
- Use refresh tokens for long-lived sessions
- Store secrets in environment variables, never hardcode

### Security Trade-offs
- **JWT**: Stateless but token can't be revoked immediately
- **Sessions**: Stateful but requires server storage
- Consider your scale: JWT for microservices, sessions for monoliths

**Next Step**: Implement token expiration to prevent stale tokens.
"""

    result = scorer.score(response, query=query, model="gpt-4")

    print(f"\nQuery: {query}")
    print(f"\nResponse Length: {result['metadata']['response_length']} chars")
    print(f"\nTotal Score: {result['total_score']}/10")
    print(f"Quality Tier: {result['quality_tier']}")
    print(f"\nTop 5 Dimension Scores:")
    for dim, score in sorted(result["dimensions"].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {dim:20s}: {score:5.2f}")


def example_3_comparing_responses():
    """Compare quality scores of two responses."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Comparing Response Quality")
    print("="*70)

    scorer = ResponseQualityScorer()

    query = "What is machine learning?"

    # Response 1: Vague
    vague_response = "Machine learning is about computers learning from data."
    vague_result = scorer.score(vague_response, query=query)

    # Response 2: Detailed
    detailed_response = """## Machine Learning: A Comprehensive Overview

Machine learning (ML) is a subset of artificial intelligence (AI) that enables systems to learn and improve from experience without explicit programming.

### Core Concepts

**1. Supervised Learning**
- Labeled training data guides the learning process
- Examples: Classification (email spam detection), Regression (price prediction)
- Algorithms: Linear Regression, Random Forest, SVM, Neural Networks

**2. Unsupervised Learning**
- Unlabeled data reveals hidden patterns
- Examples: Clustering (customer segmentation), Dimensionality reduction
- Algorithms: K-Means, DBSCAN, PCA

**3. Reinforcement Learning**
- Agent learns through interaction with environment
- Rewards and penalties guide behavior
- Examples: Game AI, Robotics, Autonomous vehicles

### Key Metrics
- **Accuracy**: Correct predictions / Total predictions (80-95% typical)
- **Precision**: True positives / Predicted positives
- **Recall**: True positives / Actual positives
- **F1-Score**: Harmonic mean of precision and recall

### Implementation Stack (2024)
- Languages: Python (primary), R, Julia
- Libraries: TensorFlow, PyTorch, scikit-learn
- Infrastructure: TensorFlow Serving, MLflow, Hugging Face

### Real-World Applications
- Healthcare: Disease diagnosis (95% accuracy in some cases)
- Finance: Fraud detection, algorithmic trading
- E-commerce: Recommendation systems, demand forecasting
- NLP: Chatbots, translation (BLEU score: 30-40)

### Trade-offs to Consider
- **Accuracy vs Interpretability**: Complex models are accurate but hard to explain
- **Training Time vs Performance**: Larger models perform better but take longer
- **Data Quality vs Quantity**: High-quality smaller datasets often beat messy large ones

### Getting Started
1. Learn Python fundamentals
2. Study statistics and linear algebra
3. Start with scikit-learn for classical ML
4. Progress to deep learning (TensorFlow/PyTorch)
5. Build projects on Kaggle

Machine learning is transforming industries at an unprecedented scale—this is
your opportunity to be part of the revolution.
"""
    detailed_result = scorer.score(detailed_response, query=query)

    print(f"\nQuery: {query}\n")

    print("RESPONSE 1 (Vague):")
    print(f"  Text: '{vague_response}'")
    print(f"  Total Score: {vague_result['total_score']:.2f}/10 ({vague_result['quality_tier']})")
    print(f"  Specificity: {vague_result['dimensions']['specificity']:.2f}")
    print(f"  Completeness: {vague_result['dimensions']['completeness']:.2f}")

    print("\nRESPONSE 2 (Detailed):")
    print(f"  Length: {len(detailed_response)} chars")
    print(f"  Total Score: {detailed_result['total_score']:.2f}/10 ({detailed_result['quality_tier']})")
    print(f"  Specificity: {detailed_result['dimensions']['specificity']:.2f}")
    print(f"  Completeness: {detailed_result['dimensions']['completeness']:.2f}")

    print(f"\nScore Improvement: +{detailed_result['total_score'] - vague_result['total_score']:.2f} points")


async def example_4_async_usage():
    """Async usage of the research_quality_score tool."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Async Tool Usage")
    print("="*70)

    response = """## API Rate Limiting

Rate limiting protects your API from abuse and ensures fair resource allocation.

### Implementation Methods

1. **Token Bucket** - Allows burst traffic
2. **Sliding Window** - Precise tracking
3. **Leaky Bucket** - Smooth traffic flow

### Best Practices
- Set realistic limits (100-1000 req/min depending on service)
- Return 429 status code when limit exceeded
- Include RateLimit headers in response
- Document limits in API documentation

### Python Example
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/users")
@limiter.limit("100/minute")
async def get_users(request: Request):
    return {"users": [...]}
```
"""

    result = await research_quality_score(
        response=response,
        query="How do I implement rate limiting?",
        model="gpt-4-turbo"
    )

    print(f"\nAsync tool execution completed!")
    print(f"Total Score: {result['total_score']:.2f}/10")
    print(f"Quality Tier: {result['quality_tier']}")
    print(f"Model: {result['metadata']['model_id']}")
    print(f"\nAll 10 dimensions scored successfully:")
    for dim in sorted(result["dimensions"].keys()):
        print(f"  ✓ {dim}")


if __name__ == "__main__":
    example_1_basic_usage()
    example_2_with_query()
    example_3_comparing_responses()
    asyncio.run(example_4_async_usage())

    print("\n" + "="*70)
    print("All examples completed successfully!")
    print("="*70)
