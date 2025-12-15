#!/bin/bash
# prepare_for_github.sh
# Sanitizes personal data before pushing to GitHub

set -e

echo "🧹 Preparing repository for GitHub push..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: Must run from project root${NC}"
    exit 1
fi

# 1. Backup personal data
echo -e "${YELLOW}📦 Step 1: Backing up personal data...${NC}"
mkdir -p .backup_personal_data
if [ -f "data/fitness_data.db" ]; then
    cp data/fitness_data.db .backup_personal_data/
    echo "  ✅ Backed up fitness_data.db"
fi
if [ -f "data/coaching_notes.json" ]; then
    cp data/coaching_notes.json .backup_personal_data/
    echo "  ✅ Backed up coaching_notes.json"
fi
if [ -f ".env" ]; then
    cp .env .backup_personal_data/
    echo "  ✅ Backed up .env"
fi
echo ""

# 2. Create sanitized coaching notes
echo -e "${YELLOW}📝 Step 2: Creating example coaching notes...${NC}"
cat > data/coaching_notes.json << 'EOF'
{
  "athlete_profile": {
    "name": "Your Name",
    "current_ftp": 250,
    "starting_ftp": 200,
    "primary_goals": [
      "Improve FTP to 270W+",
      "Complete first century ride",
      "Build sustainable endurance",
      "Maintain consistent training"
    ],
    "weekly_availability": "1-2 hours weekdays, flexible weekends",
    "seasonal_preferences": {
      "winter": ["indoor cycling", "strength training"],
      "spring": ["outdoor cycling", "running"],
      "summer": ["long rides", "events"],
      "fall": ["base building", "cross-training"]
    }
  },
  "observations": [
    {
      "date": "2024-12-01",
      "week_number": 48,
      "observation": "Example observation: Strong consistency in training adherence.",
      "focus_areas": ["consistency", "endurance", "recovery"],
      "athlete_response": "Responding well to structured training"
    }
  ],
  "personality": {
    "style": "data-driven, encouraging, scientific",
    "voice": "professional yet personable",
    "approach": "progressive overload with proper recovery",
    "communication_preferences": [
      "Use data to support recommendations",
      "Explain the 'why' behind workouts",
      "Balance hard work with recovery"
    ]
  },
  "coaching_continuity": [],
  "next_week_focus": "Build aerobic base with progressive endurance development",
  "current_training_phase": "Base Building",
  "last_updated": "2024-12-14T00:00:00"
}
EOF
echo "  ✅ Created example coaching_notes.json"
echo ""

# 3. Remove database (not needed in repo)
echo -e "${YELLOW}🗄️  Step 3: Removing personal database...${NC}"
if [ -f "data/fitness_data.db" ]; then
    rm data/fitness_data.db
    echo "  ✅ Removed fitness_data.db (backed up)"
else
    echo "  ℹ️  No database to remove"
fi
echo ""

# 4. Clear logs
echo -e "${YELLOW}📋 Step 4: Clearing logs...${NC}"
if [ -d "logs" ]; then
    rm -f logs/*.log logs/*.err
    # Keep .gitkeep if it exists
    touch logs/.gitkeep
    echo "  ✅ Cleared log files"
else
    echo "  ℹ️  No logs to clear"
fi
echo ""

# 5. Clear AI coach output (contains personal analysis)
echo -e "${YELLOW}🤖 Step 5: Clearing AI coach output...${NC}"
if [ -d "data/ai_coach_output" ]; then
    rm -f data/ai_coach_output/*.txt data/ai_coach_output/*.json
    # Keep .gitkeep if it exists
    touch data/ai_coach_output/.gitkeep
    echo "  ✅ Cleared AI coach output files"
else
    echo "  ℹ️  No AI output to clear"
fi
echo ""

# 6. Remove Week folders (personal workouts)
echo -e "${YELLOW}🚴 Step 6: Removing personal workout files...${NC}"
rm -rf Week_*/ 2>/dev/null || true
echo "  ✅ Removed Week_* folders"
echo ""

# 7. Verify .env is gitignored
echo -e "${YELLOW}🔐 Step 7: Verifying sensitive files are gitignored...${NC}"
if grep -q "\.env" .gitignore; then
    echo "  ✅ .env is gitignored"
else
    echo -e "${RED}  ❌ Warning: .env not in .gitignore!${NC}"
fi
if grep -q "fitness_data\.db" .gitignore; then
    echo "  ✅ fitness_data.db is gitignored"
else
    echo -e "${RED}  ❌ Warning: fitness_data.db not in .gitignore!${NC}"
fi
echo ""

# 8. Create example .env
echo -e "${YELLOW}🔑 Step 8: Creating .env.example...${NC}"
cat > .env.example << 'EOF'
# TrainingPeaks Credentials
TRAININGPEAKS_USERNAME=your_email@example.com
TRAININGPEAKS_PASSWORD=your_password

# AI API Keys
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Custom Paths
ZWIFT_WORKOUTS_DIR=~/Documents/Zwift/Workouts/YOUR_ZWIFT_ID
DB_PATH=data/fitness_data.db

# Optional: Email Notifications
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_RECIPIENT=your_email@gmail.com
EOF
echo "  ✅ Created .env.example"
echo ""

# 9. Check for any remaining personal data
echo -e "${YELLOW}🔍 Step 9: Checking for remaining personal data...${NC}"

# Check for common personal info patterns
PERSONAL_FOUND=0

# Check for email addresses in tracked files
if git ls-files | xargs grep -l "@.*\.com" 2>/dev/null | grep -v ".env.example" | grep -v "README" | grep -v ".md"; then
    echo -e "${RED}  ⚠️  Found email addresses in tracked files${NC}"
    PERSONAL_FOUND=1
else
    echo "  ✅ No email addresses in tracked files"
fi

# Check for common names (example - customize for your name)
if git ls-files | xargs grep -il "jacob\|robinson" 2>/dev/null | grep -v "README" | grep -v ".md" | grep -v "coaching_notes.json"; then
    echo -e "${YELLOW}  ⚠️  Found potential name references${NC}"
    PERSONAL_FOUND=1
else
    echo "  ✅ No obvious name references"
fi

echo ""

# 10. Summary
echo -e "${GREEN}✅ Repository prepared for GitHub!${NC}"
echo ""
echo "📦 Personal data backed up to: .backup_personal_data/"
echo ""
echo "Next steps:"
echo "1. Review changes: git status"
echo "2. Review sanitized files manually"
echo "3. Commit changes: git add . && git commit -m 'Prepare for public release'"
echo "4. Push to GitHub: git push origin main"
echo ""
echo "⚠️  After pushing, restore your personal data:"
echo "   cp .backup_personal_data/fitness_data.db data/"
echo "   cp .backup_personal_data/coaching_notes.json data/"
echo "   cp .backup_personal_data/.env ./"
echo ""

if [ $PERSONAL_FOUND -eq 1 ]; then
    echo -e "${YELLOW}⚠️  WARNING: Potential personal data found. Review carefully before pushing!${NC}"
    echo ""
fi
