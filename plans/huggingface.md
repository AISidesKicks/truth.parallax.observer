# HuggingFace Token Setup

> How to get and configure HuggingFace API token for parallax.observer

## Token Required For

| Model | Status | Reason |
|-------|--------|--------|
| granite3.3:2b | ✅ Open | Available via Ollama, no token needed |
| granite4:tiny-h | ✅ Open | Available via Ollama, no token needed |
| granite4:micro-h | ✅ Open | Available via Ollama, no token needed |
| qwen3-vl:2b | ✅ Open | Available via Ollama, no token needed |
| nomic-ai/modernbert-embed-base | ✅ Open | No token needed |

**Current project uses open models via Ollama - no HuggingFace token required.**

## When You Might Need a Token

| Reason | Description |
|--------|-------------|
| **Gated Models** | Some models require license acceptance + authentication |
| **Rate Limits** | Anonymous requests have strict rate limits |
| **Faster Downloads** | Authenticated requests get priority bandwidth |
| **Private Models** | Access to private/organization models |

## Step-by-Step: Get Your Token

### 1. Create HuggingFace Account

Visit: https://huggingface.co/join

- Use email, GitHub, or Google login
- Verify email address

### 2. Access Gated Models (if needed)

For gated models like Gemma:

1. Visit the model page on HuggingFace
2. Click **"Access repository"**
3. Read and accept license terms
4. Fill in your information
5. Wait for approval (usually instant)

### 3. Generate API Token

1. Go to: https://huggingface.co/settings/tokens
2. Click **"Create new token"**
3. Choose token type:

| Type | Use Case |
|------|----------|
| **Read** | Download models (recommended) |
| **Write** | Upload models, manage repos |
| **Fine-grained** | Specific permissions per repo |

4. Select **"Read"** token
5. Give it a name: `parallax.observer`
6. Click **"Generate token"**
7. **Copy token immediately** (shown only once!)

### 4. Store Token Securely

**Option A: Environment Variable (Recommended)**

```bash
# Add to ~/.bashrc or ~/.zshrc
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Reload shell
source ~/.bashrc
```

**Option B: .env File**

```bash
# Copy sample
cp .env.sample .env

# Edit and add your token
# .env
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Option C: HuggingFace CLI**

```bash
pip install huggingface-hub

# Login interactively
huggingface-cli login

# Or with token
huggingface-cli login --token hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Usage in Code

### Python

```python
import os
from huggingface_hub import login

# From environment
login(os.environ.get("HF_TOKEN"))
```

### Transformers

```python
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "google/gemma-3n-e4b",
    token=os.environ.get("HF_TOKEN")
)
```

### Docker

```bash
# Pass to container
docker run -e HF_TOKEN=hf_xxx ... 

# Or in docker-compose.yml
services:
  app:
    environment:
      - HF_TOKEN=${HF_TOKEN}
```

## Security Best Practices

| ✅ Do | ❌ Don't |
|-------|----------|
| Use environment variables | Commit token to git |
| Use read-only tokens | Share tokens publicly |
| Rotate tokens periodically | Store in code files |
| Use fine-grained tokens | Use write tokens unless needed |
| Add `.env` to `.gitignore` | Send token in messages/chats |

## Token in .gitignore

The `.gitignore` file already excludes:

```
.env
.env.local
*.env
```

## Troubleshooting

### "401 Client Error"

Token missing or invalid:

```bash
# Check token is set
echo $HF_TOKEN

# Re-login
huggingface-cli login
```

### "Access to model is restricted"

Model not approved:

1. Visit the model page
2. Accept the license terms
3. Wait for approval

### Rate Limit Errors

Anonymous requests limited:

```bash
# Ensure token is set
export HF_TOKEN=hf_xxx
```

### Token Not Recognized

Regenerate token:

1. Go to https://huggingface.co/settings/tokens
2. Delete old token
3. Create new token
4. Update environment

## Related Files

- [.env.sample](../.env.sample) - Environment template
- [.gitignore](../.gitignore) - Excludes .env files
- [plans/dev.md](dev.md) - Development setup
