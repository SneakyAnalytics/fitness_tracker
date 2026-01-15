#!/bin/bash
# Setup script for News API integration (optional but recommended)

echo "=================================================="
echo "Text Event Enhancement - News API Setup"
echo "=================================================="
echo ""
echo "This script will help you set up the News API for enhanced"
echo "text events with current event headlines + AI summaries."
echo ""
echo "Benefits:"
echo "  ✅ Trending news headlines during workouts"
echo "  ✅ AI-generated summaries in plain language"
echo "  ✅ Stay informed while training"
echo ""
echo "Free tier: 100 requests/day (plenty for workouts)"
echo ""

# Check if already configured
if [ -n "$NEWS_API_KEY" ]; then
    echo "✅ NEWS_API_KEY is already configured!"
    echo "   Current value: ${NEWS_API_KEY:0:10}..."
    echo ""
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing configuration."
        exit 0
    fi
fi

echo "Step 1: Get your free API key"
echo "----------------------------"
echo "1. Go to: https://newsapi.org/register"
echo "2. Fill out the registration form"
echo "3. Confirm your email"
echo "4. Copy your API key from the dashboard"
echo ""
read -p "Press Enter when you have your API key..."

echo ""
echo "Step 2: Enter your API key"
echo "----------------------------"
read -p "Paste your News API key: " api_key

if [ -z "$api_key" ]; then
    echo "❌ No API key provided. Exiting."
    exit 1
fi

# Validate format (basic check)
if [ ${#api_key} -lt 20 ]; then
    echo "⚠️  Warning: API key seems too short. Please double-check."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Step 3: Configure environment"
echo "----------------------------"

# Determine shell config file
if [ -n "$ZSH_VERSION" ]; then
    shell_config="$HOME/.zshrc"
    shell_name="zsh"
elif [ -n "$BASH_VERSION" ]; then
    shell_config="$HOME/.bashrc"
    shell_name="bash"
else
    shell_config="$HOME/.profile"
    shell_name="shell"
fi

echo "Detected shell: $shell_name"
echo "Config file: $shell_config"
echo ""

# Check if already exists in config
if grep -q "export NEWS_API_KEY=" "$shell_config" 2>/dev/null; then
    echo "Found existing NEWS_API_KEY in $shell_config"
    echo "Updating..."
    # Backup
    cp "$shell_config" "${shell_config}.backup_$(date +%Y%m%d_%H%M%S)"
    # Update
    sed -i.tmp "s|export NEWS_API_KEY=.*|export NEWS_API_KEY=\"$api_key\"|" "$shell_config"
    rm "${shell_config}.tmp"
else
    echo "Adding NEWS_API_KEY to $shell_config"
    echo "" >> "$shell_config"
    echo "# News API for Zwift workout text events" >> "$shell_config"
    echo "export NEWS_API_KEY=\"$api_key\"" >> "$shell_config"
fi

# Set for current session
export NEWS_API_KEY="$api_key"

echo ""
echo "Step 4: Test the configuration"
echo "----------------------------"

# Quick Python test
python3 << 'EOF'
import os
import sys

api_key = os.getenv('NEWS_API_KEY')
if not api_key:
    print("❌ NEWS_API_KEY not found in environment")
    sys.exit(1)

print(f"✅ NEWS_API_KEY configured: {api_key[:10]}...")

# Try to make a test request
try:
    import requests
    response = requests.get(
        'https://newsapi.org/v2/top-headlines',
        params={
            'apiKey': api_key,
            'language': 'en',
            'pageSize': 1
        },
        timeout=5
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('articles'):
            article = data['articles'][0]
            print(f"\n✅ API key works! Test headline:")
            print(f"   {article.get('title', 'N/A')[:80]}")
            print("\n🎉 Setup complete!")
        else:
            print("\n⚠️  API key valid but no articles returned")
    elif response.status_code == 401:
        print("\n❌ API key invalid or unauthorized")
        print("   Please check your key and try again")
        sys.exit(1)
    elif response.status_code == 429:
        print("\n⚠️  Rate limit reached (you may have tested too many times)")
        print("   But your key is probably valid!")
    else:
        print(f"\n⚠️  Unexpected response: {response.status_code}")
        print(f"   {response.text[:200]}")

except ImportError:
    print("\n⚠️  'requests' library not available for testing")
    print("   But NEWS_API_KEY is configured!")
except Exception as e:
    print(f"\n⚠️  Test failed: {e}")
    print("   But NEWS_API_KEY is configured!")

EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✅ Setup Complete!"
    echo "=================================================="
    echo ""
    echo "Next steps:"
    echo "  1. Reload your shell or run: source $shell_config"
    echo "  2. Generate a new Zwift workout"
    echo "  3. Look for 📰 News headlines + 💡 summaries"
    echo ""
    echo "Without reloading shell, run:"
    echo "  export NEWS_API_KEY=\"$api_key\""
    echo ""
    echo "Your workouts will now include:"
    echo "  📰 Trending news headlines"
    echo "  💡 AI-generated plain-language summaries"
    echo "  🔬 Science stories with explanations"
    echo "  📚 Research papers made understandable"
    echo ""
else
    echo ""
    echo "⚠️  Configuration saved but test failed"
    echo "   NEWS_API_KEY is set in $shell_config"
    echo "   Reload shell: source $shell_config"
    echo ""
fi

echo "Notes:"
echo "  • Free tier: 100 requests/day"
echo "  • Each workout uses ~1-3 requests"
echo "  • Without key: Falls back to HackerNews/arXiv"
echo ""
