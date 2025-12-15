# Fitness Tracker Development Product Roadmap

[X] Utilize data from new workout_performance table to enrich weekly summary txt file generation
Description:

- Using the new data being collected in the streamlit app under the workout_calendar tab for strength and yoga
  workouts specifically I want to enrich the weekly summary text file that is being generated
- Some complications with this, is we will need to blend the performance data being input and match it with the
  respective workout data found in my Training Peaks files/Fit files/proposed workout data.
- The section I would like the performance data to be output is within each of the respective daily workout details, exclusively for yoga and strength workouts
- There is currently a section at the end of strength workouts where the strength based data can be output, which we could repurpose for this, but the Yoga (or 'Other') workouts don't necessarily have logic to add this section in the workout details
- We could potentially (instead of saving these details as a seperate workout_performance table) save these to the existing proposed workout table in a new column, which already are being pulled into the generate_weekly_summary function, and matching with the appropriate workouts, and then just have that output a section in the final output only when those fields have been populated.

Implementation Notes:

- Implemented data retrieval from workout_performance table in database.py
- Created matching logic to retrieve workout performance data using workout_id and date
- Enhanced the weekly summary text file export to include detailed performance data for strength, yoga, and other workout types
- Included exercise names, sets, reps, weights, and notes in the output for a comprehensive workout summary

Story Points:

1. Analyze current data structures and determine optimal approach (2 points) ✓
2. Implement data retrieval from workout_performance table (3 points) ✓
3. Create matching logic to link performance data with workout data (5 points) ✓
4. Modify weekly summary generation to include performance data for strength workouts (3 points) ✓
5. Extend weekly summary generation for yoga/other workouts (3 points) ✓
6. Add tests and validation (2 points) ✓
7. Documentation and code cleanup (1 point) ✓

[X] Enhance Workout Calendar Display for Strength, Yoga, and Mobility Workouts
Description:

- The workout calendar currently doesn't display all the detailed information present in the JSON files for Strength, Yoga, and Mobility workouts
- Looking at Week 16 data, several important workout details are missing or not properly formatted in the UI
- The Thursday mobility workout shows limited routine details compared to what's available in the JSON data
- Need to enhance the display_strength_workout_with_tracking function to properly show all available workout data

Implementation Notes:

- Need to enhance weight information display to handle various formats:
  - Round-specific weights (e.g., "round1": "bodyweight", "round2": { "min": 10, "max": 15, "unit": "lbs" })
  - Simple value weights (e.g., "value": 10, "unit": "lbs")
  - Bodyweight specification
  - Min/max ranges with units
- Improve exercise cue display to include:
  - Proper formatting of cues as bullet points
  - Display of "modifications" field separate from cues
  - "perSide" indicators for exercises performed on each side
- Enhance mobility workout display:
  - Properly format longer instruction notes
  - Better display of duration-based exercises vs. rep-based exercises
  - Clear visual indication of different exercise types
- Add missing field display:
  - Exercise direction attributes
  - Tempo guidance
  - Focus information
  - Round-specific instructions
- Improve overall workout display formatting:
  - Clearer visual hierarchy for workout sections with color-coded headers and section type indicators
  - Better formatting of complex notes arrays
  - Visual indicators for exercises with special attributes (per side, modifications, etc.)
- Added exercise reference button:
  - Quick access button next to each exercise name
  - Links directly to Google image search for the exercise
  - Makes it easy to see proper form and technique without leaving the app

Story Points:

1. Analyze current display_strength_workout_with_tracking function limitations (3 points)
2. Enhance weight information display with support for all formats (4 points)
3. Improve exercise cue and modification display (3 points)
4. Add support for "perSide" indicators and direction attributes (2 points)
5. Enhance formatting for mobility workouts and duration-based exercises (4 points)
6. Add display for round-specific instructions and progressions (3 points)
7. Improve overall visual formatting and hierarchy (3 points)
8. Test with various workout types from Week 16 data (2 points)
9. Documentation and code cleanup (1 point)

[X] Zwift workout automation
Description:

- I want to use the json format that I upload into the proposed workout tables, also generate a .zwo file for cycling workouts, using the interval data, and place the created .zwo files in my Zwift application directory so I can access them in the application
- The Zwift application is a virtual training application, and by placing them in the appropriate folder, it will allow me to have auto-created workouts instead of me manually having to create these each week.
- The file path to the Zwift location to drop the files is: /Users/jacobrobinson/Documents/Zwift/Workouts/6870291
- An example version of a .zwo file can be found in the repo titled: 'nf4x27da4n.zwo'
- I want the files to be named with the date that I should be doing the workout along with the cycling workout title

Implementation Notes:

- Created a standalone python script (generate_zwift.py) to generate .zwo files from workout data
- Implemented a new API endpoint /zwift/generate_workouts that generates Zwift workout files for all cycling workouts in a specified date range
- Added conversion logic to transform proposed workout interval data into Zwift-compatible XML format
- Included smart naming convention with date prefixes and cleaned workout names
- Made FTP value configurable (default: 258 watts) to adapt as fitness improves
- Set default output directory to the correct Zwift workouts folder:
  - /Users/jacobrobinson/Documents/Zwift/Workouts/6870291

Story Points:

1. Analyze Zwift .zwo file format using example file (2 points) ✓
2. Design .zwo file generator from proposed workout data (3 points) ✓
3. Implement workout interval to .zwo conversion logic (5 points) ✓
4. Add file naming convention with date and workout title (1 point) ✓
5. Create file placement functionality to save to Zwift directory (2 points) ✓
6. Implement automatic generation on workout upload (3 points) ✓
7. Add validation and error handling (2 points) ✓
8. Testing with various workout types (2 points) ✓
9. Fix FAST API error that is now being caused from an edit done earlier to the app.py file, you can see this error in the Error_message_3_2.txt file (1 point)✓
10. Setup zwift files to land in the appropriate user folder, creating a new folder within that folder for each week making it easy to know which folder I should open each week (2 points)✓
11. Ensure that the processing of the intervals in biking workouts is correctly being calculated as a percentage of FTP as there are some issues in the users testing process, specifically with the second bike workout which is supposed to be a light effort (around 170-190 watts) but is registering as (400+ watts) (2 points)✓

[X] TrainingPeaks Automation
Description:

- Automated sync of workout data from TrainingPeaks website
- Eliminates manual CSV export and FIT file download process
- Uses Playwright browser automation to log in, export data, and download FIT files
- Implements filename-based deduplication to prevent duplicate workout entries
- Preserves all existing manual upload functionality as backup
- Integrated into Streamlit UI with credential management

Implementation Notes:

- Created trainingpeaks_sync.py orchestrator using Playwright sync API
- Built trainingpeaks_file_processor.py for FIT file parsing and database insertion
- Added deduplication logic in database.py checking (workout_day, workout_title, file_name)
- Updated .gitignore to exclude automation downloads and temp directories
- Added comprehensive documentation to README.md with setup and usage instructions
- Maintains sequence numbers for multiple workouts per day while keeping matching algorithm independent

Story Points:

1. Research Playwright automation approach (2 points) ✓
2. Implement TrainingPeaks login and navigation (3 points) ✓
3. Build CSV export automation (3 points) ✓
4. Create FIT file download automation (4 points) ✓
5. Implement file processing and database insertion (4 points) ✓
6. Add filename-based deduplication logic (3 points) ✓
7. Create Streamlit UI integration (3 points) ✓
8. Add credential management and validation (2 points) ✓
9. Testing and error handling (3 points) ✓
10. Documentation and cleanup (2 points) ✓

[ ] AI Coaching System - Full Automation Loop
Description:

- Implement end-to-end AI coaching system that analyzes weekly workout data and generates proposed workouts for the upcoming week
- AI coach reviews weekly summary data, queries historical database for context, and provides:
  1. Weekly performance analysis (highlights, lowlights, coaching insights)
  2. Trend analysis and improvement suggestions
  3. Generated JSON for proposed workouts matching app requirements
  4. High-level overview of constructed workouts for following week
- AI coach maintains continuity via "coaching notes" file that persists personality, athlete observations, and coaching focus areas
- User provides weekly input for scheduling constraints (e.g., "snow on mountain, add XC skiing workout")
- Approval workflow: user reviews AI-generated workouts before they're processed into Zwift files and weekly dashboard
- Preserves all existing manual workflow options during development and testing

Technical Implementation:

- AI Model: Claude Sonnet 4.5 via API (testing with cheaper models initially)
- Database Access: AI coach has SQL query tool to analyze full training history
- Knowledge Base: Import cycling science principles and workout format requirements from Claude Project
- Memory System: Persistent coaching notes file stores:
  - Athlete behavior patterns and observations
  - Coaching focus areas and goals
  - Personality/style preferences (can be customized for different coaching styles)
  - Week-to-week continuity notes
- Input: Streamlit form for weekly scheduling constraints and preferences
- Output: Combined markdown analysis + validated JSON workout plan
- Integration: New "AI Coach" tab in Streamlit (separate from manual workflow)
- Validation: Multi-layer validation during development:
  - JSON schema validation
  - Workout parameter bounds checking
  - Manual review/approval step before finalizing
  - Gradual removal of validation layers as confidence grows

Workflow:

1. Generate weekly summary (existing functionality)
2. User opens "AI Coach" tab, inputs any scheduling constraints/notes
3. AI coach queries database for historical context
4. AI coach reads previous coaching notes for continuity
5. AI analyzes weekly summary + historical data + coaching notes
6. AI generates:
   - Detailed weekly analysis (markdown/text)
   - Proposed workouts JSON (validated against schema)
   - Updated coaching notes for next week
7. User reviews analysis and proposed workouts
8. User approves/edits workouts
9. System processes approved JSON:
   - Saves to proposed_workouts table
   - Generates Zwift .zwo files
   - Updates weekly dashboard
10. AI coaching notes saved for next week

Story Points:

1. Research and configure Claude API integration (3 points)
2. Design coaching notes file structure and persistence (2 points)
3. Build database query tool for AI coach (5 points)
4. Create knowledge base from Claude Project resources (4 points)
5. Design Streamlit "AI Coach" tab UI (3 points)
6. Implement weekly constraints/preferences input form (2 points)
7. Build AI prompt engineering with trainer context (5 points)
8. Implement coaching notes read/write logic (3 points)
9. Create weekly analysis generation pipeline (4 points)
10. Build proposed workout JSON generation (5 points)
11. Implement multi-layer validation system (4 points)
12. Create user review/approval interface (3 points)
13. Integrate with existing proposed workout processing (3 points)
14. Build automatic Zwift file generation trigger (2 points)
15. Add cost tracking and model switching capability (3 points)
16. Testing with multiple weeks of data (4 points)
17. Create coaching personality customization options (2 points)
18. Documentation and user guide (3 points)

[ ] Stylize Streamlit pages
Description:

- Since I will be using this streamlit application as a main hub to maintain my fitness, I want the interface to be personalized to me and be something I enjoy interacting with and I want it to be a representation of my interests
- I am an employee at Nike and I love sports, I am a graduate of the University of Oregon, and grew up in Bend Oregon
- My favorite activities that I will be logging activities into the app are Nordic Cross Country Skiing, Running, Yoga, Strength Workouts, and my current favorite Cycling (specifically gravel biking)
- I love being in the outdoors, and my local landscape in Portland Oregon is Forrested areas, that have lots of Mountains
- I am open on color schemes but I like something that is modern looking and complimentary and enjoyable to look at
- I am also open to fonts
- An additional item of note are my favorite sports teams are the New York Mets (MLB Baseball), Kansas City Chiefs (NFL Football), Portland Timbers (MLS Soccer), and the Oregon Ducks (College Football) in case you want to weave that into color schemes/fonts etc.

Story Points:

1. Research Streamlit theming and customization options (2 points)
2. Create color scheme options based on personal preferences and team colors (3 points)
3. Design custom header with personal branding elements (2 points)
4. Implement activity-specific icons and visual elements (3 points)
5. Develop custom CSS for layout improvements (3 points)
6. Create themed data visualizations (4 points)
7. Implement responsive design for different device sizes (3 points)
8. Add animated transitions and micro-interactions (2 points)
9. User testing and refinement (2 points)

[ ] AI Analysis of Individual Workout FIT Files (Future Enhancement)
Description:

- Deep-dive analysis of individual cycling workout FIT files for per-workout insights
- This is a complementary feature to the weekly AI coaching system
- Analyzes moment-by-moment data from bike workouts only
- Provides detailed qualitative responses about workout execution quality
- Could be integrated into weekly summary or accessed on-demand per workout

Key Analysis Questions:

1. Heart Rate Response:

   - Does HR steadily increase during steady power?
   - Recovery time between intervals
   - Unusual heart rate spikes or drift

2. Power Delivery:
   - Ability to maintain target cadence
   - Power drops or struggles during intervals
   - Consistency and smoothness trends

Implementation Considerations:

- May use cheaper/free model (Google Gemini) since it's per-workout analysis
- Could be optional add-on to weekly coaching analysis
- Lower priority than full coaching system
- May repurpose or remove existing partial AI implementation

Story Points: TBD (lower priority than main AI coaching system)

[ ] Repo Clean Up
Description:

- As a part of this application build I have assembled all sorts of mechanisms to build and test various features, some of them have remained in the application, and remain useful, and some of them are old artifacts that are no longer useful and just need to be cleaned up
- I want to review and edit out those unnecessary elements of my application
- I also want to clean up my code formatting and naming conventions to ensure that my logic is very clear
- I would love if my styling throughout my py files could actually be sports themed including emojis/comments/etc as a nice touch to make the code enjoyable to look at and read through

Story Points:

1. Code audit and inventory of unused components (5 points)
2. Remove deprecated code and files (3 points)
3. Standardize code formatting across codebase (3 points)
4. Implement consistent naming conventions (2 points)
5. Add sports-themed comments and docstrings (2 points)
6. Create emoji guide for code annotations (1 point)
7. Refactor duplicate functionality (3 points)
8. Improve error handling and logging (3 points)
9. Update documentation with new styling guidelines (2 points)
10. Final testing after cleanup (2 points)
