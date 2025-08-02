#!/bin/bash
# Script to start UberH3 Anomaly Detection system with Docker

echo "🚀 Starting UberH3 Anomaly Detection with Docker..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Copy environment file
if [ ! -f .env ]; then
    echo "📋 Creating environment file..."
    cp .env.docker .env
fi

# Build and start services
echo "🔨 Building Docker images..."
docker-compose -f deployment/docker-compose.yml build

echo "🚀 Starting services..."
docker-compose -f deployment/docker-compose.yml up -d

echo "⏳ Waiting for services to be ready..."
sleep 20

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📊 Available services:"
echo "   • FastAPI Server:      http://localhost:8000"
echo "   • Streamlit Dashboard: http://localhost:8506"
echo "   • MLflow UI:          http://localhost:5000"
echo ""
echo "📋 To view logs: docker-compose -f deployment/docker-compose.yml logs -f [service-name]"
echo "🛑 To stop:      docker-compose -f deployment/docker-compose.yml down"
echo "🗑️  To cleanup:   docker-compose -f deployment/docker-compose.yml down -v"
