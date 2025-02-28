# Fitness Tracker Development Product Roadmap

[ ] Utilize data from new workout_performance table to enrich weekly summary txt file generation
Description:

- Using the new data being collected in the streamlit app under the workout_calendar tab for strength and yoga
  workouts specifically I want to enrich the weekly summary text file that is being generated
- Some complications with this, is we will need to blend the performance data being input and match it with the
  respective workout data found in my Training Peaks files/Fit files/proposed workout data.
- The section I would like the performance data to be output is within each of the respective daily workout details, exclusively for yoga and strength workouts
- There is currently a section at the end of strength workouts where the strength based data can be output, which we could repurpose for this, but the Yoga (or 'Other') workouts don't necessarily have logic to add this section in the workout details
- We could potentially (instead of saving these details as a seperate workout_performance table) save these to the existing proposed workout table in a new column, which already are being pulled into the generate_weekly_summary function, and matching with the appropriate workouts, and then just have that output a section in the final output only when those fields have been populated.

[ ] Zwift workout automation
Description:

- I want to use the json format that I upload into the proposed workout tables, also generate a .zwo file for cycling workouts, using the interval data, and place the created .zwo files in my Zwift application directory so I can access them in the application
- The Zwift application is a virtual training application, and by placing them in the appropriate folder, it will allow me to have auto-created workouts instead of me manually having to create these each week.
- The file path to the Zwift location to drop the files is:
- An example version of a .zwo file can be found in the repo titled: 'nf4x27da4n.zwo'
- I want the files to be named with the date that I should be doing the workout along with the cycling workout title

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

[ ] Stylize Streamlit pages
Description:

- Since I will be using this streamlit application as a main hub to maintain my fitness, I want the interface to be personalized to me and be something I enjoy interacting with and I want it to be a representation of my interests
- I am an employee at Nike and I love sports, I am a graduate of the University of Oregon, and grew up in Bend Oregon
- My favorite activities that I will be logging activities into the app are Nordic Cross Country Skiing, Running, Yoga, Strength Workouts, and my current favorite Cycling (specifically gravel biking)
- I love being in the outdoors, and my local landscape in Portland Oregon is Forrested areas, that have lots of Mountains
- I am open on color schemes but I like something that is modern looking and complimentary and enjoyable to look at
- I am also open to fonts
- An additional item of note are my favorite sports teams are the New York Mets (MLB Baseball), Kansas City Chiefs (NFL Football), Portland Timbers (MLS Soccer), and the Oregon Ducks (College Football) in case you want to weave that into color schemes/fonts etc.

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

[ ] Repo Clean Up
Description:

- As a part of this application build I have assembled all sorts of mechanisms to build and test various features, some of them have remained in the application, and remain useful, and some of them are old artifacts that are no longer useful and just need to be cleaned up
- I want to review and edit out those unnecessary elements of my application
- I also want to clean up my code formatting and naming conventions to ensure that my logic is very clear
- I would love if my styling throughout my py files could actually be sports themed including emojis/comments/etc as a nice touch to make the code enjoyable to look at and read through
