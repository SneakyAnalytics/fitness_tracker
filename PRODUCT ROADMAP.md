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

[ ] AI Analysis of fit file results
Description:

- The raw fit files that I upload into my database after I have completed the workouts have an enormous amount of moment by moment data from my workouts, this data would provide tremendous benefit, if a set of non-biased qualitative responses could be given to answer a subset of questions surrounding key measures I am tracking that show signs of positive/negative changes to my fitness
- I am want this AI summary analysis to be performed for my bike workouts only
- I want these responses to be included in my weekly workout analysis text file in the daily analysis sections
- I want to use the google gemini or another free model to provide this analysis (as I want this analysis to be free since I will be using this application long term)
- There are existing portions of the application that started to build out this AI analysis structure, and these likely can be removed as a part of this build (or repurposed if there are reusable elements)
- I would like the AI to have the context frame that they are a professional athlete trainer, focused on improving this one athlete to achieve their fitness goals which include 50-100 mile gravel bike rides in his state of Oregon in the USA, which encompass large amounts of climbing and challenging terrain, as well as overall improving his endurance, strength, and fitness over time.
- If there are any other suggested opportunities for improving this type of workout analysis within this build to improve the overall effectiveness, or quality insights, feel free to have flexibility to explore these
- The questions for the bike workouts I would like answered along with any other notable fitness trends are as follows:

1. Heart Rate Response Questions:

   - Does HR steadily increase during steady power?
   - How long to recover between intervals?
   - Any unusual heart rate spikes?

2. Power Delivery Response Questions:
   - Ability to maintain cadence?
   - Any power drops or apparent struggles based on the data set?
   - Any other notable Power Delivery Trends?

Story Points:

1. Research and set up Google Gemini API (3 points)
2. Analyze fit file structure and extract relevant data points (5 points)
3. Develop data processing pipeline for heart rate analysis (5 points)
4. Implement power delivery analysis (5 points)
5. Create AI prompt engineering with professional trainer context (3 points)
6. Implement API integration and response handling (3 points)
7. Integrate AI analysis into weekly summary generation (4 points)
8. Add caching to minimize API costs (2 points)
9. Testing with different workout types and intensities (3 points)
10. Refactor/remove existing partial AI implementation (2 points)
11. Add documentation and monitoring (2 points)

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

[ ] Build AI Workout Planner into the application based on the historical context
Description:

- Currently I use the text output generated from my weekly summary text files to feed into an AI conversation, which has the context of all of my previous weeks of workouts, and progress over time, to then have the AI agent provide a set of weekly proposed workouts for the following week based on the results
- In this conversation I will note if I have any upcoming conflicts or special scenarios which would prevent me from doing daily workouts for the week, and a few brief weekly notes occasionally if I have other context to add aside from the data I am providing
- I would love if all of this context could be provided within my application using my database, with an AI, to look back at the history of my workout data (whatever amount of time makes sense), to create the proposed workouts for the next week (instead of me having to generate this manually by taking the data and feeding it into an AI prompt service)
- In this conversation I have noted any small/large goals that I am working towards, but in general I just want to always be improving my fitness, while being highly intelligent and following best industry practices and scientifically backed from an athlete training perspective, using all the most up to date and data backed strategies to ensure I am healthily improving while maximizing my time and effort for the best improvements
- I have the general guidance of being comfortable working out for an hour to two hours a day during the week (with also the occasional day where I am comfortable doing multiple workouts in a day), with generally more time available on the weekends
- I like going off of the recent trends of my conversation with an AI agent, to help generally steer the types of activities I am interested in doing (like seasonally I do XC skiing in the winter, and some more running, hiking etc. in the spring fall and summertime, and sometimes I just want to focus on cycling)
- I would like if the results of this AI analysis could be delivered into my database, instead of me needing to upload a json with all the proposed workout data, but I am sure the elements of my application in which I have built to show the proposed workout data, and merge that data into the weekly summary could be repurposed easily to maintain all of these functionalities just removing the need to get a file and deliver it back into the application
- I am flexible about this overall design but obviously am trying to build an end to end data application that manages and provides professional training all in one utilizing AI for workout suggestion, and analysis

Story Points:

1. Research and select appropriate AI model (3 points)
2. Design database schema for storing training goals and preferences (3 points)
3. Create data extraction pipeline for historical workout analysis (5 points)
4. Develop input interface for weekly conflicts and special notes (3 points)
5. Implement prompt engineering for workout planning (8 points)
6. Create seasonal activity preference logic (3 points)
7. Design workout generation algorithm with validation rules (5 points)
8. Develop database integration for storing AI-generated workouts (4 points)
9. Create UI for reviewing and modifying AI suggestions (4 points)
10. Implement feedback loop to improve future suggestions (3 points)
11. Add extensive testing with various scenarios (3 points)
12. Create documentation and user guide (2 points)

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
