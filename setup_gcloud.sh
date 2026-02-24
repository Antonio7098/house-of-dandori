#!/bin/bash
# Setup script for Google Cloud authentication and Vertex AI collection creation

GCLOUD="/Users/oscarfernandes/Desktop/DF/AI/GroupAnt/house-of-dandori/google-cloud-sdk/bin/gcloud"

echo "=========================================="
echo "Google Cloud Setup for Dandori Project"
echo "=========================================="
echo ""

# Check if already authenticated
if $GCLOUD auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "✅ Already authenticated with Google Cloud"
    $GCLOUD auth list
else
    echo "🔐 Authenticating with Google Cloud..."
    echo "This will open a browser window for authentication."
    echo ""
    $GCLOUD auth application-default login
fi

echo ""
echo "📋 Current configuration:"
$GCLOUD config list

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Enable required APIs:"
echo "   ./gcloud.sh services enable aiplatform.googleapis.com"
echo "   ./gcloud.sh services enable vectorsearch.googleapis.com"
echo ""
echo "2. Create the Vector Search collection:"
echo "   python scripts/create_vertex_collection.py"
echo ""
echo "3. Start your application:"
echo "   python app.py"
echo ""
