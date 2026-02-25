# Google Cloud SDK Setup Guide

## Installation Options

### Option 1: Homebrew (Recommended for macOS)

```bash
brew install --cask google-cloud-sdk
```

If you encounter Python version issues, set the Python path:

```bash
export CLOUDSDK_PYTHON=/usr/bin/python3
brew reinstall --cask google-cloud-sdk
```

### Option 2: Direct Download

1. Download from: https://cloud.google.com/sdk/docs/install
2. Extract and run the install script:

```bash
cd ~/Downloads
tar -xzf google-cloud-cli-darwin-x86_64.tar.gz
./google-cloud-sdk/install.sh
```

3. Add to your PATH (add to `~/.zshrc` or `~/.bash_profile`):

```bash
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
```

4. Restart your terminal or run:

```bash
source ~/.zshrc  # or source ~/.bash_profile
```

## Authentication

### For Local Development

```bash
# Authenticate with your Google account
gcloud auth login

# Set application default credentials (for Python SDK)
gcloud auth application-default login

# Set your project
gcloud config set project my-project-oscar-487814
```

### For Production (Cloud Run)

No authentication needed! Cloud Run automatically provides credentials through the service account.

## Verify Installation

```bash
# Check gcloud version
gcloud version

# Check authentication
gcloud auth list

# Check current project
gcloud config get-value project
```

## Enable Required APIs

```bash
# Enable Vertex AI APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable vectorsearch.googleapis.com
```

## Create Service Account (Optional - for local testing)

```bash
# Create service account
gcloud iam service-accounts create dandori-dev \
  --display-name="Dandori Development"

# Grant Vertex AI permissions
gcloud projects add-iam-policy-binding my-project-oscar-487814 \
  --member="serviceAccount:dandori-dev@my-project-oscar-487814.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Download key (keep this secure!)
gcloud iam service-accounts keys create ~/dandori-dev-key.json \
  --iam-account=dandori-dev@my-project-oscar-487814.iam.gserviceaccount.com

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=~/dandori-dev-key.json
```

## Troubleshooting

### "gcloud: command not found"

Add gcloud to your PATH:

```bash
# For Homebrew installation
export PATH="/usr/local/share/google-cloud-sdk/bin:$PATH"

# For direct download
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
```

### Python Version Issues

Set the Python path explicitly:

```bash
export CLOUDSDK_PYTHON=/usr/bin/python3
```

Or use Python 3.10+:

```bash
brew install python@3.12
export CLOUDSDK_PYTHON=/usr/local/bin/python3.12
```

### Permission Denied

Make sure your Google account has the necessary roles:
- Vertex AI User
- Service Account User (if using service accounts)

Check with:

```bash
gcloud projects get-iam-policy my-project-oscar-487814 \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:YOUR_EMAIL"
```

## Alternative: Use Service Account Key

If you can't install gcloud, you can use a service account key file:

1. Create a service account in GCP Console
2. Grant it Vertex AI User role
3. Create and download a JSON key
4. Set environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

Then your Python code will automatically use this for authentication.

## Next Steps

After authentication, you can:

1. Create the Vertex AI collection:
   ```bash
   python scripts/create_vertex_collection.py
   ```

2. Test the connection:
   ```bash
   python -c "from google.cloud import aiplatform; aiplatform.init(project='my-project-oscar-487814', location='europe-west2'); print('✅ Connected!')"
   ```

3. Run your application:
   ```bash
   python app.py
   ```
