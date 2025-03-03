# Zwift Workout Generator Updates

## Fixed Issues

1. **XML Tag Fix**: Changed `<n>` tags to `<name>` tags for Zwift compatibility
2. **Power Calculation Improvements**: Fixed power calculation logic for ranges and absolute watts
   - Properly detects if power values are in watts vs percentage of FTP
   - Converts absolute watts to FTP percentage correctly using configurable FTP value
3. **Weekly Folder Organization**: Added weekly folder structure based on workout date
   - Files are now organized as `Week_X/YYYY_MM_DD_Workout_Name.zwo`
4. **Date in Workout Names**: Included the date in workout names for better identification in Zwift
   - Format: "MM/DD Workout Name"

## Technical Notes

1. Terminal/display issues with `<name>` vs `<n>` tags:
   - There appeared to be a rendering issue with tag names in the terminal or tools
   - Fixed by working directly with the byte level replacements

2. Added post-processing to ensure all generated .zwo files use the correct XML tags:
   - Implemented `fix_xml_tag_in_file()` function that's called after file generation
   - Function replaces `<n>` with `<name>` tags in the output files

3. Refactored power calculation logic:
   - Added explicit checks for watts vs FTP percentages
   - Range calculations now properly handle both absolute watts and percentage values

4. Created weekly folder structure:
   - Uses ISO week number from workout date
   - Automatically creates folders if they don't exist

## Usage

```python
from src.utils.zwift_workout_generator import generate_zwift_workout

# Generate a single workout file
output_file = generate_zwift_workout(
    workout_date="2025-03-02",
    workout_name="Test Workout",
    intervals=[
        {"duration": 300, "powerTarget": {"type": "percent_ftp", "value": 65}}
    ],
    description="Sample workout",
    ftp=258,  # Optional, defaults to 258 watts
    output_dir="/path/to/output"  # Optional, defaults to current directory
)

# Generate workouts from database for a specific week
from src.utils.zwift_workout_generator import generate_zwift_workouts_from_db
from src.storage.database import Database

db = Database()
generated_files = generate_zwift_workouts_from_db(
    db_connection=db,
    start_date="2025-03-01",
    end_date="2025-03-07",
    ftp=258,  # Optional, defaults to 258 watts
    output_dir="/path/to/output"  # Optional, defaults to current directory
)
```

## Testing

The implementation has been tested with various workout types:
- Steady state workouts (percent FTP)
- Steady state workouts (absolute watts)
- Range-based workouts (both percent FTP and watts)
- Ramp intervals
- Rest intervals

All generated files should be compatible with Zwift's .zwo format.
